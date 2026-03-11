import os
import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import joblib
import tensorflow as tf
from collections import deque
from ultralytics import YOLO
import threading
import uuid
from flask import current_app

task_store = {}

# 모델 규격 설정
MAX_FRAMES, NUM_JOINTS, CHANNELS = 60, 13, 6
JOINT_MAP = {
    0: "NOSE", 11: "L_SHOULDER", 12: "R_SHOULDER", 13: "L_ELBOW", 14: "R_ELBOW",
    15: "L_WRIST", 16: "R_WRIST", 23: "L_HIP", 24: "R_HIP", 25: "L_KNEE",
    26: "R_KNEE", 27: "L_ANKLE", 28: "R_ANKLE"
}

def get_detailed_analysis(df):
    """관절 위치 기반 물리적 수치 추출"""
    if df.empty:
        return {"tilt": 0, "height": 0, "stride": 0}
    tilt = (df['R_SHOULDER_y'] - df['L_SHOULDER_y']).max()
    release_height = min(df['R_WRIST_y'].min(), df['L_WRIST_y'].min())
    stride = np.abs(df['R_ANKLE_x'] - df['L_ANKLE_x']).max()
    return {"tilt": tilt, "height": release_height, "stride": stride}

def predict_and_analyze(raw_data, classifier_model, le):
    """프레임 부족 시 패딩 처리를 포함한 예측 로직"""
    if not raw_data or len(raw_data) == 0:
        return "Unknown", 0.0, {"tilt": 0, "height": 0, "stride": 0}

    data = np.array(raw_data)[:, 1:].reshape(-1, NUM_JOINTS, 4)
    coords, vis = data[:, :, :3], data[:, :, 3]

    hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
    norm_coords = coords.copy()
    for f in range(coords.shape[0]):
        norm_coords[f] -= hip_center[f]
    
    deltas = np.diff(norm_coords, axis=0, prepend=norm_coords[0:1, :, :])
    deltas *= np.expand_dims(vis, axis=-1)

    combined = np.concatenate([norm_coords, deltas], axis=-1).astype('float32')

    current_len = len(combined)
    if current_len >= MAX_FRAMES:
        combined = combined[:MAX_FRAMES]
    else:
        padding_size = MAX_FRAMES - current_len
        last_frame = combined[-1:] 
        padding = np.tile(last_frame, (padding_size, 1, 1))
        combined = np.vstack([combined, padding])
    
    input_tensor = np.expand_dims(combined, axis=0)
    preds = classifier_model.predict(input_tensor, verbose=0)
    
    name = le.inverse_transform([np.argmax(preds[0])])[0]
    conf = float(np.max(preds[0]) * 100)

    cols = []
    for j_id in JOINT_MAP.values():
        cols.extend([f"{j_id}_x", f"{j_id}_y", f"{j_id}_z", f"{j_id}_vis"])
    df_temp = pd.DataFrame(np.array(raw_data)[:, 1:], columns=cols)
    analysis = get_detailed_analysis(df_temp)

    return name, conf, analysis

def process_video_background(task_id, filepath, base_dir):
    try:
        task_store[task_id]['status'] = 'processing'
        
        # 모델 경로 설정
        ml_dir = os.path.join(base_dir, 'ml_models')
        model_path = os.path.join(ml_dir, 'best_model_fold_4.h5')
        encoder_path = os.path.join(ml_dir, 'label_encoder.pkl')
        
        # 스레드 내부에서 모델 로드 (충돌 방지)
        yolo_model = YOLO("yolov8n.pt")
        classifier_model = tf.keras.models.load_model(model_path)
        le = joblib.load(encoder_path)
        
        mp_pose = mp.solutions.pose
        pose = mp_pose.Pose(model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)
        
        cap = cv2.VideoCapture(filepath)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width, height = int(cap.get(3)), int(cap.get(4))

        pre_offset_frames, post_offset_frames = int(fps * 0.5), int(fps * 2.5)
        raw_data_accumulator = []
        is_recording = False
        post_frame_count = 0
        
        ROI_X1, ROI_X2 = int(width * 0.3), int(width * 0.7)
        ROI_Y1, ROI_Y2 = int(height * 0.2), int(height * 0.9)

        prediction_name = "Unknown"
        prediction_conf = 0.0
        analysis_data = {}

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            results = yolo_model.track(frame, persist=True, verbose=False)[0]
            current_pitcher_candidate = None

            if results.boxes.id is not None:
                boxes = results.boxes.xyxy.cpu().numpy()
                for i, box in enumerate(boxes):
                    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                    if ROI_X1 < cx < ROI_X2 and ROI_Y1 < cy < ROI_Y2:
                        current_pitcher_candidate = box
                        break

            if current_pitcher_candidate is not None:
                x1, y1, x2, y2 = map(int, current_pitcher_candidate)
                crop = frame[max(0, y1-20):min(height, y2+20), max(0, x1-20):min(width, x2+20)]
                
                if crop.size > 0:
                    res = pose.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                    if res.pose_landmarks:
                        lm = res.pose_landmarks.landmark
                        knee_y, hip_y = min(lm[25].y, lm[26].y), (lm[23].y + lm[24].y) / 2
                        
                        if knee_y < (hip_y + 0.15) and not is_recording:
                            is_recording, raw_data_accumulator, post_frame_count = True, [], 0

                        if is_recording:
                            frame_data = [post_frame_count]
                            for j_id in JOINT_MAP.keys():
                                frame_data.extend([lm[j_id].x, lm[j_id].y, lm[j_id].z, lm[j_id].visibility])
                            raw_data_accumulator.append(frame_data)

            if is_recording:
                post_frame_count += 1
                if post_frame_count >= post_offset_frames:
                    prediction_name, prediction_conf, analysis_data = predict_and_analyze(raw_data_accumulator, classifier_model, le)
                    break # 분석이 끝나면 불필요한 영상 읽기를 중단합니다.

        cap.release()
        
        # 영상이 끝난 후 혹시라도 녹화 중이었다면 분석 시도
        if is_recording and len(raw_data_accumulator) > 0 and prediction_name == "Unknown":
            prediction_name, prediction_conf, analysis_data = predict_and_analyze(raw_data_accumulator, classifier_model, le)

        # 결과 텍스트 파싱 (예: 2022sohyeongjun.mp4 -> 소형준)
        # 사용자님의 데이터셋 형태에 맞춰 정규식이나 문자열 슬라이싱을 조절할 수 있습니다.
        clean_name = prediction_name.replace('.mp4', '')
        clean_name = ''.join([i for i in clean_name if not i.isdigit()])
        
        task_store[task_id]['result'] = {
            'similarity': round(prediction_conf, 1),
            'match_player': clean_name,
            'player_img': prediction_name, # 매칭된 선수의 원본 파일명 보존
            'details': analysis_data
        }
        task_store[task_id]['status'] = 'completed'
        
    except Exception as e:
        task_store[task_id]['status'] = 'error'
        task_store[task_id]['error_message'] = str(e)
        print(f"Error during analysis: {e}")

def start_analysis_task(filepath, base_dir):
    task_id = str(uuid.uuid4())
    task_store[task_id] = {
        'status': 'pending',
        'filepath': filepath,
        'result': None
    }
    
    thread = threading.Thread(target=process_video_background, args=(task_id, filepath, base_dir))
    thread.daemon = True
    thread.start()
    
    return task_id

def get_task_status(task_id):
    return task_store.get(task_id, {'status': 'not_found'})