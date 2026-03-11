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
VIDEO_PATH = r"C:\Users\kccistc\Desktop\workspace\project\pitch_original\2022moondongju.mp4"
OUTPUT_CLIP_DIR = r"C:\Users\kccistc\Desktop\workspace\project\pitch_clips"
MODEL_PATH = r"./saved_models/best_model_fold_1.h5"
ENCODER_PATH = r"./saved_models/label_encoder.pkl"

os.makedirs(OUTPUT_CLIP_DIR, exist_ok=True)

yolo_model = YOLO("yolov8n.pt")
classifier_model = tf.keras.models.load_model(MODEL_PATH)
le = joblib.load(ENCODER_PATH)

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(model_complexity=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

JOINT_MAP = {
    0: "NOSE", 11: "L_SHOULDER", 12: "R_SHOULDER", 13: "L_ELBOW", 14: "R_ELBOW",
    15: "L_WRIST", 16: "R_WRIST", 23: "L_HIP", 24: "R_HIP", 25: "L_KNEE",
    26: "R_KNEE", 27: "L_ANKLE", 28: "R_ANKLE"
}

MAX_FRAMES = 80
NUM_JOINTS = 13
CHANNELS = 9

# ==============================
# 2. 분석용 함수 (예측 및 상세 비교)
# ==============================
def calculate_angle(a, b, c):
    ba = a - b
    bc = c - b
    cosine_angle = np.sum(ba * bc, axis=-1) / (np.linalg.norm(ba, axis=-1) * np.linalg.norm(bc, axis=-1) + 1e-6)
    return np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0)))

def get_detailed_analysis(df):
    """관절 위치를 바탕으로 투구 폼의 물리적 특징 추출"""
    # 1. 어깨 기울기 (Shoulder Tilt): 투구 시 양 어깨의 높낮이 차이
    # Mediapipe 기준 y값이 클수록 아래쪽이므로 (R_y - L_y)가 양수면 오른쪽이 더 낮음
    tilt = df['R_SHOULDER_y'] - df['L_SHOULDER_y']
    max_tilt = tilt.max() # 투구 중 가장 크게 기운 각도 지표
    
    # 2. 릴리스 포인트 팔 높이 (Relative Release Height)
    # 손목이 가장 높이 올라갔을 때(y값이 최소일 때)의 값
    release_height = min(df['R_WRIST_y'].min(), df['L_WRIST_y'].min())
    
    # 3. 스트라이드 너비 (Stride Width): 발 사이의 최대 거리
    stride = np.abs(df['R_ANKLE_x'] - df['L_ANKLE_x']).max()
    
    return {
        "tilt": max_tilt,
        "height": release_height,
        "stride": stride
    }

def predict_and_analyze(raw_data):
    # 텐서 변환 및 예측 (기존 로직)
    data = np.array(raw_data)[:, 1:].reshape(-1, NUM_JOINTS, 4)
    coords, vis = data[:, :, :3], data[:, :, 3]

    # 각도 계산
    elbow_angle = calculate_angle(coords[:, 2, :], coords[:, 4, :], coords[:, 6, :])
    knee_angle = calculate_angle(coords[:, 8, :], coords[:, 10, :], coords[:, 12, :])
    shoulder_angle = calculate_angle(coords[:, 8, :], coords[:, 2, :], coords[:, 4, :])
    
    angles = np.stack([elbow_angle, knee_angle, shoulder_angle], axis=-1)
    angle_features = np.tile(np.expand_dims(angles, axis=1), (1, NUM_JOINTS, 1))

    # 정규화 및 델타
    hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
    norm_coords = coords.copy()
    for f in range(coords.shape[0]): norm_coords[f] -= hip_center[f]
    deltas = np.diff(norm_coords, axis=0, prepend=norm_coords[0:1, :, :])
    
    combined = np.concatenate([norm_coords, deltas, angle_features], axis=-1).astype('float32')

    if len(combined) > MAX_FRAMES: combined = combined[:MAX_FRAMES]
    else: combined = np.vstack([combined, np.tile(combined[-1:], (MAX_FRAMES - len(combined), 1, 1))])
    
    preds = classifier_model.predict(np.expand_dims(combined, axis=0), verbose=0)
    name = le.inverse_transform([np.argmax(preds[0])])[0]
    conf = np.max(preds[0]) * 100

    # 상세 수치 분석용 데이터프레임 생성
    cols = []
    for j_id in JOINT_MAP.values(): cols.extend([f"{j_id}_x", f"{j_id}_y", f"{j_id}_z", f"{j_id}_vis"])
    df_temp = pd.DataFrame(np.array(raw_data)[:, 1:], columns=cols)
    analysis = get_detailed_analysis(df_temp)

    return name, conf, analysis

# ==============================
# 3. 메인 루프
# ==============================
cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
width, height = int(cap.get(3)), int(cap.get(4))

pre_offset_frames, post_offset_frames = int(fps * 0.5), int(fps * 2.5)
frame_buffer = deque(maxlen=pre_offset_frames)
clip_frames, raw_data_accumulator = [], []
is_recording = False
post_frame_count, clip_count, cooldown = 0, 0, 0
pitcher_id = None
prediction_text = "Waiting..."
detail_text = ""

ROI_X1, ROI_X2 = int(width * 0.40), int(width * 0.7)
ROI_Y1, ROI_Y2 = int(height * 0.25), int(height * 0.85)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    annotated_frame = frame.copy()
    results = yolo_model.track(frame, persist=True, verbose=False)[0]
    current_pitcher_candidate = None

    if results.boxes.id is not None:
        boxes, ids = results.boxes.xyxy.cpu().numpy(), results.boxes.id.cpu().numpy().astype(int)
        if pitcher_id is None:
            for i, box in enumerate(boxes):
                cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                if ROI_X1 < cx < ROI_X2 and ROI_Y1 < cy < ROI_Y2: pitcher_id = ids[i]; break
        if pitcher_id in ids:
            idx = np.where(ids == pitcher_id)[0][0]
            current_pitcher_candidate = boxes[idx]

    if current_pitcher_candidate is not None:
        x1, y1, x2, y2 = map(int, current_pitcher_candidate)
        margin = 40
        y1_m, y2_m, x1_m, x2_m = max(0, y1-margin), min(height, y2+margin), max(0, x1-margin), min(width, x2+margin)
        crop = frame[y1_m:y2_m, x1_m:x2_m]
        
        if crop.size > 0:
            res = pose.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            if res.pose_landmarks:
                mp_drawing.draw_landmarks(annotated_frame[y1_m:y2_m, x1_m:x2_m], res.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                lm = res.pose_landmarks.landmark
                knee_y, hip_y = min(lm[25].y, lm[26].y), (lm[23].y + lm[24].y) / 2
                
                if knee_y < (hip_y + 0.12) and not is_recording and cooldown == 0:
                    is_recording, clip_frames, raw_data_accumulator, post_frame_count = True, list(frame_buffer), [], 0
                    prediction_text = "Analyzing Form..."

                if is_recording:
                    frame_data = [post_frame_count]
                    for j_id in JOINT_MAP.keys(): frame_data.extend([lm[j_id].x, lm[j_id].y, lm[j_id].z, lm[j_id].visibility])
                    raw_data_accumulator.append(frame_data)

    if not is_recording: frame_buffer.append(annotated_frame.copy())
    else:
        clip_frames.append(annotated_frame.copy()); post_frame_count += 1
        if post_frame_count >= post_offset_frames:
            name, conf, analysis = predict_and_analyze(raw_data_accumulator)
            prediction_text = f"Result: {name} ({conf:.1f}%)"
            
            # 비교 텍스트 생성 (예: 문동주 평균 대비 어깨 기울기가 10% 더 낮음 등)
            detail_text = f"Tilt: {analysis['tilt']:.2f} | Height: {analysis['height']:.2f} | Stride: {analysis['stride']:.2f}"
            
            print(f"\n🎯 [분석 결과] 투수: {name} ({conf:.1f}%)")
            print(f"   - 어깨 기울기: {analysis['tilt']:.3f} (높을수록 오버핸드)")
            print(f"   - 릴리스 높이: {analysis['height']:.3f} (낮을수록 높은 타점)")
            print(f"   - 스트라이드 폭: {analysis['stride']:.3f} (중심 이동 거리)")

            clip_count += 1
            is_recording, cooldown, pitcher_id = False, int(fps * 3.0), None
            frame_buffer.clear()

    if cooldown > 0: cooldown -= 1
    cv2.putText(annotated_frame, prediction_text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(annotated_frame, detail_text, (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    cv2.imshow("Advanced Pitcher Analysis System", annotated_frame)
    if cv2.waitKey(1) & 0xFF == 27: break

cap.release()
cv2.destroyAllWindows()
