"""
비전 기반 투구/타격 분석 서비스 모듈입니다.
YOLOv8, MediaPipe, TensorFlow 모델을 결합하여 사용자의 폼을 분석하고 
데이터베이스에 저장된 프로 선수 데이터와 비교합니다.
"""
import os
import cv2
import mediapipe as mp
import numpy as np
import math
import pandas as pd
import joblib
import tensorflow as tf
import threading
import uuid
from collections import deque
from ultralytics import YOLO
from flask import current_app
from app import db
from app.models.analysis import Analysis
from app.models.ranking import PitcherRanking, HitterRanking
from app.models.pitcher import Pitcher
from app.models.hitter import Hitter
from app.models.user import User

# 모델 및 데이터 처리를 위한 공통 설정값
MAX_FRAMES, NUM_JOINTS, CHANNELS = 60, 13, 6

# [투수 전용] 관절 매핑 (MediaPipe 기준)
JOINT_MAP = {
    0: "NOSE", 
    11: "L_SHOULDER", 12: "R_SHOULDER", 
    13: "L_ELBOW", 14: "R_ELBOW",
    15: "L_WRIST", 16: "R_WRIST", 
    23: "L_HIP", 24: "R_HIP", 
    25: "L_KNEE", 26: "R_KNEE", 
    27: "L_ANKLE", 28: "R_ANKLE"
}

# [타자 전용] 관절 인덱스 (YOLOv8 Pose 기준)
HIT_JOINT_INDICES = [0, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

# 비동기 작업의 상태와 결과를 임시 저장하는 딕셔너리
task_store = {}


def calibrate_score(raw_score, c=10):
    """
    모델의 원시 정확도(0~100)를 로그 스케일로 보정
    """
    if raw_score <= 0:
        return 0.0
    if raw_score >= 100:
        return 100.0
    
    adjusted = 100 * (math.log10(c * raw_score + 1) / math.log10(c * 100 + 1))

    return round(adjusted, 2)


def get_detailed_analysis(df):
    """추출된 관절의 좌표 데이터를 바탕으로 물리적 수치 계산 (주로 투수용)"""
    if df.empty:
        return {"tilt": 0, "height": 0, "stride": 0}
    tilt = (df['R_SHOULDER_y'] - df['L_SHOULDER_y']).max()
    release_height = min(df['R_WRIST_y'].min(), df['L_WRIST_y'].min())
    stride = np.abs(df['R_ANKLE_x'] - df['L_ANKLE_x']).max()
    return {"tilt": tilt, "height": release_height, "stride": stride}


def predict_and_analyze_pitch(raw_data, classifier_model, le):
    """[투수 전용] 프레임별 관절 데이터를 전처리하고 투수를 예측합니다."""
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

    # 마지막 프레임 복사 방식 패딩 (투수용)
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


def preprocess_hit_data(frames_data):
    """[타자 전용] 타자 분석을 위한 좌표 데이터를 패딩 및 정규화(Zero-padding)합니다."""
    df = pd.DataFrame(frames_data)
    
    x_cols = [i*3 for i in range(NUM_JOINTS)]
    y_cols = [i*3 + 1 for i in range(NUM_JOINTS)]
    conf_cols = [i*3 + 2 for i in range(NUM_JOINTS)]
    
    coords_2d = np.stack([df.iloc[:, x_cols].values, df.iloc[:, y_cols].values], axis=-1)
    conf = df.iloc[:, conf_cols].values
    
    # 가상 Z축 연산
    hip_l, hip_r = coords_2d[:, 7, :], coords_2d[:, 8, :]
    hip_widths = np.linalg.norm(hip_l - hip_r, axis=1)
    avg_width = np.mean(hip_widths) if np.mean(hip_widths) > 0 else 0.1
    z_pseudo = avg_width / (hip_widths + 1e-6)
    z_pseudo = np.tile(z_pseudo[:, np.newaxis, np.newaxis], (1, NUM_JOINTS, 1))
    
    # 3D 좌표 구성 및 정규화
    coords_3d = np.concatenate([coords_2d, z_pseudo], axis=-1)
    hip_center = (coords_3d[:, 7, :] + coords_3d[:, 8, :]) / 2
    for f in range(coords_3d.shape[0]):
        coords_3d[f] -= hip_center[f]
        
    # 변화량 및 신뢰도 가중치
    deltas_3d = np.diff(coords_3d, axis=0, prepend=coords_3d[0:1, :, :])
    conf_exp = np.expand_dims(conf, axis=-1)
    combined = np.concatenate([coords_3d * conf_exp, deltas_3d * conf_exp], axis=-1)
    
    # Zero-Padding (타자용)
    current_len = len(combined)
    if current_len < MAX_FRAMES:
        pad = np.zeros((MAX_FRAMES - current_len, NUM_JOINTS, CHANNELS))
        combined = np.vstack([combined, pad])
    else:
        combined = combined[-MAX_FRAMES:]
        
    return np.expand_dims(combined.astype('float32'), axis=0)


def process_video_background(task_id, filepath, ml_model_path, encoder_path, yolo_path, app, user_id, analysis_type='pitch'):
    """
    백그라운드에서 분석을 수행합니다. 
    analysis_type에 따라 타자(YOLO-Pose) 또는 투수(MediaPipe) 분석 로직으로 분기합니다.
    """
    try:
        task_store[task_id]['status'] = 'processing'
        
        classifier_model = tf.keras.models.load_model(ml_model_path)
        le = joblib.load(encoder_path)
        
        cap = cv2.VideoCapture(filepath)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width, height = int(cap.get(3)), int(cap.get(4))

        prediction_name = "Unknown"
        prediction_conf = 0.0
        analysis_data = {"tilt": 0, "height": 0, "stride": 0}

        # ----------------------------------------------------
        # 1. [타격 폼 분석] YOLOv8-Pose 기반 로직
        # ----------------------------------------------------
        if analysis_type == 'hit':
            yolo_pose_model = YOLO("yolov8n-pose.pt")
            frame_buffer = deque(maxlen=MAX_FRAMES)
            main_target_id = None
            
            best_prob = 0.0
            best_name = "Unknown"
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break
                
                results = yolo_pose_model.track(frame, persist=True, verbose=False, conf=0.2)[0]
                
                if results.boxes is not None and results.boxes.id is not None:
                    ids = results.boxes.id.cpu().numpy().astype(int)
                    
                    # 가장 큰 면적을 가진 타겟 고정
                    if main_target_id is None:
                        areas = results.boxes.xywh.cpu().numpy()[:, 2] * results.boxes.xywh.cpu().numpy()[:, 3]
                        main_target_id = ids[np.argmax(areas)]
                        
                    if main_target_id in ids:
                        idx = np.where(ids == main_target_id)[0][0]
                        if hasattr(results, 'keypoints') and results.keypoints is not None:
                            points = results.keypoints.data[idx].cpu().numpy()
                            
                            curr_data = []
                            for j_idx in HIT_JOINT_INDICES:
                                jx, jy, jconf = points[j_idx]
                                curr_data.extend([jx / width, jy / height, jconf])
                            frame_buffer.append(curr_data)
                            
                            # 데이터가 쌓일 때마다 추론하여 가장 높은 정확도를 가진 선수를 결과로 채택
                            if len(frame_buffer) > 0:
                                input_data = preprocess_hit_data(list(frame_buffer))
                                prediction = classifier_model.predict(input_data, verbose=0)
                                
                                class_idx = np.argmax(prediction[0])
                                prob = float(prediction[0][class_idx] * 100)
                                
                                if prob > best_prob:
                                    best_prob = prob
                                    best_name = le.inverse_transform([class_idx])[0]
                                    
            cap.release()
            prediction_name = best_name
            prediction_conf = best_prob

        # ----------------------------------------------------
        # 2. [투구 폼 분석] 기존 YOLO BBox + MediaPipe 기반 로직
        # ----------------------------------------------------
        else:
            yolo_model = YOLO(yolo_path)
            mp_pose = mp.solutions.pose
            pose = mp_pose.Pose(model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)
            
            pre_offset_frames, post_offset_frames = int(fps * 0.5), int(fps * 2.5)
            raw_data_accumulator = []
            is_recording = False
            post_frame_count = 0
            
            ROI_X1, ROI_X2 = int(width * 0.3), int(width * 0.7)
            ROI_Y1, ROI_Y2 = int(height * 0.2), int(height * 0.9)

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
                        prediction_name, prediction_conf, analysis_data = predict_and_analyze_pitch(raw_data_accumulator, classifier_model, le)
                        break

            cap.release()
            
            if is_recording and len(raw_data_accumulator) > 0 and prediction_name == "Unknown":
                prediction_name, prediction_conf, analysis_data = predict_and_analyze_pitch(raw_data_accumulator, classifier_model, le)

        # ====================================================
        # 분석 결과 처리 및 데이터베이스 저장 공통 로직
        # ====================================================
        clean_name = prediction_name.replace('.mp4', '')
        clean_name = ''.join([i for i in clean_name if not i.isdigit()])
        
        # 모델의 원시 점수(prediction_conf)를 로그 함수로 보정합니다.
        adjusted_score = calibrate_score(prediction_conf)
        
        task_store[task_id]['result'] = {
            'similarity': adjusted_score,
            'match_player': clean_name,
            'player_img': prediction_name,
            'details': analysis_data
        }

        if user_id is not None:
            with app.app_context():
                user = User.query.get(user_id)
                current_score = task_store[task_id]['result']['similarity']
                
                # 타격 분석 결과 DB 저장
                if analysis_type == 'hit':
                    from app.models.hitter import Hitter
                    from app.models.ranking import HitterRanking
                    
                    hitter_info = Hitter.query.filter_by(model_label=prediction_name).first()
                    hitter_id = hitter_info.id if hitter_info else 1
                    
                    # 분석 기록은 점수와 무관하게 무조건 저장합니다.
                    new_analysis = Analysis(
                        user_id=user_id,
                        analysis_type='hit',
                        hitter_id=hitter_id,
                        similarity=current_score,
                        user_video_path=filepath
                    )
                    db.session.add(new_analysis)
                    
                    # 타격 랭킹 중복 방지 및 최고점 갱신 로직
                    existing_ranking = HitterRanking.query.filter_by(user_id=user_id).first()
                    if existing_ranking:
                        if current_score > existing_ranking.score:
                            existing_ranking.score = current_score
                            existing_ranking.hitter_id = hitter_id
                    else:
                        new_ranking = HitterRanking(
                            user_id=user_id,
                            hitter_id=hitter_id,
                            score=current_score
                        )
                        db.session.add(new_ranking)
                        
                # 투구 분석 결과 DB 저장
                else: 
                    from app.models.pitcher import Pitcher
                    from app.models.ranking import PitcherRanking
                    
                    pitcher_info = Pitcher.query.filter_by(model_label=prediction_name).first()
                    pitcher_id = pitcher_info.id if pitcher_info else 1
                    
                    # 분석 기록은 점수와 무관하게 무조건 저장합니다.
                    new_analysis = Analysis(
                        user_id=user_id,
                        analysis_type='pitch',
                        pitcher_id=pitcher_id,
                        similarity=current_score,
                        user_video_path=filepath
                    )
                    db.session.add(new_analysis)
                    
                    # 투구 랭킹 중복 방지 및 최고점 갱신 로직
                    existing_ranking = PitcherRanking.query.filter_by(user_id=user_id).first()
                    if existing_ranking:
                        if current_score > existing_ranking.score:
                            existing_ranking.score = current_score
                            existing_ranking.pitcher_id = pitcher_id
                    else:
                        new_ranking = PitcherRanking(
                            user_id=user_id,
                            pitcher_id=pitcher_id,
                            score=current_score
                        )
                        db.session.add(new_ranking)
                
                # 마이페이지 표기용 절대 최고 점수 갱신
                if current_score > user.best_score:
                    user.best_score = current_score
                
                db.session.commit()

        task_store[task_id]['status'] = 'completed'
        
    except Exception as e:
        task_store[task_id]['status'] = 'error'
        task_store[task_id]['error_message'] = str(e)
        print(f"Error during analysis: {e}")


def start_analysis_task(filepath, ml_model_path, encoder_path, yolo_path, app, user_id, analysis_type='pitch'):
    task_id = str(uuid.uuid4())
    task_store[task_id] = {
        'status': 'pending',
        'filepath': filepath,
        'result': None,
        'analysis_type': analysis_type
    }
    
    thread = threading.Thread(
        target=process_video_background, 
        args=(task_id, filepath, ml_model_path, encoder_path, yolo_path, app, user_id, analysis_type)
    )
    thread.daemon = True
    thread.start()
    
    return task_id


def get_task_status(task_id):
    return task_store.get(task_id, {'status': 'not_found'})