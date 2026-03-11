import cv2
import mediapipe as mp
import numpy as np
import os
import pandas as pd
import joblib
import tensorflow as tf
from collections import deque
from ultralytics import YOLO

# ==============================
# 1. 경로 및 모델 설정
# ==============================
VIDEO_PATH = "test.mp4"
MODEL_PATH = "best_model_fold_4.h5"
ENCODER_PATH = "label_encoder.pkl"

if not os.path.exists(VIDEO_PATH):
    print(f"동영상 파일을 찾을 수 없습니다: {VIDEO_PATH}")
    exit()

yolo_model = YOLO("yolov8n.pt")
classifier_model = tf.keras.models.load_model(MODEL_PATH)
le = joblib.load(ENCODER_PATH)

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

JOINT_MAP = {
    0: "NOSE", 11: "L_SHOULDER", 12: "R_SHOULDER", 13: "L_ELBOW", 14: "R_ELBOW",
    15: "L_WRIST", 16: "R_WRIST", 23: "L_HIP", 24: "R_HIP", 25: "L_KNEE",
    26: "R_KNEE", 27: "L_ANKLE", 28: "R_ANKLE"
}

# 모델 규격 강제 지정
MAX_FRAMES, NUM_JOINTS, CHANNELS = 60, 13, 6 

# ==============================
# 2. 분석용 함수
# ==============================
def get_detailed_analysis(df):
    """관절 위치 기반 물리적 수치 추출"""
    if df.empty:
        return {"tilt": 0, "height": 0, "stride": 0}
    tilt = (df['R_SHOULDER_y'] - df['L_SHOULDER_y']).max()
    release_height = min(df['R_WRIST_y'].min(), df['L_WRIST_y'].min())
    stride = np.abs(df['R_ANKLE_x'] - df['L_ANKLE_x']).max()
    return {"tilt": tilt, "height": release_height, "stride": stride}

def predict_and_analyze(raw_data):
    """프레임 부족 시 패딩 처리를 포함한 예측 로직"""
    # 데이터가 아예 없는 경우 방어
    if not raw_data or len(raw_data) == 0:
        return "Unknown", 0.0, {"tilt": 0, "height": 0, "stride": 0}

    # 1. 데이터 파싱
    data = np.array(raw_data)[:, 1:].reshape(-1, NUM_JOINTS, 4)
    coords, vis = data[:, :, :3], data[:, :, 3]

    # 2. 정규화 및 델타 계산
    hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
    norm_coords = coords.copy()
    for f in range(coords.shape[0]):
        norm_coords[f] -= hip_center[f]
    
    deltas = np.diff(norm_coords, axis=0, prepend=norm_coords[0:1, :, :])
    deltas *= np.expand_dims(vis, axis=-1)

    # 3. 채널 결합 (6채널: 좌표 3 + 델타 3)
    combined = np.concatenate([norm_coords, deltas], axis=-1).astype('float32')

    # 4. 프레임 수 강제 조절 (핵심: 패딩 로직)
    current_len = len(combined)
    if current_len >= MAX_FRAMES:
        # 프레임이 많으면 자름
        combined = combined[:MAX_FRAMES]
    else:
        # 프레임이 부족하면 마지막 프레임을 복제하여 MAX_FRAMES(60)을 채움
        padding_size = MAX_FRAMES - current_len
        last_frame = combined[-1:] # 마지막 프레임 추출
        padding = np.tile(last_frame, (padding_size, 1, 1))
        combined = np.vstack([combined, padding])
    
    # 5. 모델 예측
    input_tensor = np.expand_dims(combined, axis=0)
    preds = classifier_model.predict(input_tensor, verbose=0)
    
    name = le.inverse_transform([np.argmax(preds[0])])[0]
    conf = np.max(preds[0]) * 100

    # 6. 상세 분석 수치 계산용 DF
    cols = []
    for j_id in JOINT_MAP.values():
        cols.extend([f"{j_id}_x", f"{j_id}_y", f"{j_id}_z", f"{j_id}_vis"])
    df_temp = pd.DataFrame(np.array(raw_data)[:, 1:], columns=cols)
    analysis = get_detailed_analysis(df_temp)

    return name, conf, analysis

# ==============================
# 3. 메인 루프
# ==============================
cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
width, height = int(cap.get(3)), int(cap.get(4))

# 녹화 설정 (fps 기반)
pre_offset_frames, post_offset_frames = int(fps * 0.5), int(fps * 2.5)
frame_buffer = deque(maxlen=pre_offset_frames)
raw_data_accumulator = []
is_recording = False
post_frame_count, cooldown = 0, 0
pitcher_id = None
prediction_text = "Searching Pitcher..."
detail_text = ""

# ROI 설정
ROI_X1, ROI_X2 = int(width * 0.3), int(width * 0.7)
ROI_Y1, ROI_Y2 = int(height * 0.2), int(height * 0.9)

print("🎬 분석 시스템 가동... (ESC: 종료)")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    annotated_frame = frame.copy()
    results = yolo_model.track(frame, persist=True, verbose=False)[0]
    current_pitcher_candidate = None

    if results.boxes.id is not None:
        boxes, ids = results.boxes.xyxy.cpu().numpy(), results.boxes.id.cpu().numpy().astype(int)
        for i, box in enumerate(boxes):
            cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            if ROI_X1 < cx < ROI_X2 and ROI_Y1 < cy < ROI_Y2:
                pitcher_id = ids[i]
                current_pitcher_candidate = box
                break

    if current_pitcher_candidate is not None:
        x1, y1, x2, y2 = map(int, current_pitcher_candidate)
        crop = frame[max(0, y1-20):min(height, y2+20), max(0, x1-20):min(width, x2+20)]
        
        if crop.size > 0:
            res = pose.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            if res.pose_landmarks:
                mp_drawing.draw_landmarks(annotated_frame[max(0,y1-20):min(height,y2+20), max(0,x1-20):min(width,x2+20)], 
                                          res.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                lm = res.pose_landmarks.landmark
                
                # 투구 감지 로직 (무릎 높이 기준)
                knee_y, hip_y = min(lm[25].y, lm[26].y), (lm[23].y + lm[24].y) / 2
                
                if not is_recording:
                    prediction_text = f"Ready... (Knee-Hip Diff: {abs(knee_y-hip_y):.2f})"

                if knee_y < (hip_y + 0.15) and not is_recording and cooldown == 0:
                    is_recording, raw_data_accumulator, post_frame_count = True, [], 0
                    print("🚀 투구 동작 감지! 데이터 수집 중...")

                if is_recording:
                    frame_data = [post_frame_count]
                    for j_id in JOINT_MAP.keys():
                        frame_data.extend([lm[j_id].x, lm[j_id].y, lm[j_id].z, lm[j_id].visibility])
                    raw_data_accumulator.append(frame_data)

    if is_recording:
        post_frame_count += 1
        prediction_text = f"Recording... [{post_frame_count}/{post_offset_frames}]"
        
        # 영상이 끝나기 전이나 지정된 프레임이 다 찼을 때 분석 수행
        if post_frame_count >= post_offset_frames:
            name, conf, analysis = predict_and_analyze(raw_data_accumulator)
            prediction_text = f"Result: {name} ({conf:.1f}%)"
            detail_text = f"Tilt: {analysis['tilt']:.2f} | H: {analysis['height']:.2f} | S: {analysis['stride']:.2f}"
            
            print(f"\n✅ 분석 완료: {name} ({conf:.1f}%)")
            is_recording, cooldown = False, int(fps * 2)

    if cooldown > 0: cooldown -= 1
    
    # UI 표시
    cv2.rectangle(annotated_frame, (ROI_X1, ROI_Y1), (ROI_X2, ROI_Y2), (255, 255, 255), 1)
    cv2.putText(annotated_frame, prediction_text, (30, 40), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(annotated_frame, detail_text, (30, 80), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 0), 1)
    
    cv2.imshow("Pitcher Analysis System", annotated_frame)
    if cv2.waitKey(1) & 0xFF == 27: break

# 만약 녹화 도중 영상이 끝났을 경우를 대비한 최종 분석 시도
if is_recording and len(raw_data_accumulator) > 0:
    name, conf, analysis = predict_and_analyze(raw_data_accumulator)
    print(f"\n영상 종료로 인한 최종 분석: {name} ({conf:.1f}%)")

cap.release()
cv2.destroyAllWindows()