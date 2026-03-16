####
## 모델 검증용 코드
####
import cv2
import numpy as np
import os
import pandas as pd
from ultralytics import YOLO
import tensorflow as tf
import joblib
from collections import deque
import matplotlib.pyplot as plt
import time  # 시간 측정을 위해 추가

# [기존 설정 및 모델 로드 섹션 유지]
MODEL_PATH = r"saved_models_yolo_high_acc/final_best_95plus_model.h5" 
ENCODER_PATH = r"saved_models_yolo_3d/label_encoder.pkl"
YOLO_MODEL_PATH = "yolov8n-pose.pt"
VIDEO_PATH = r"C:\Users\kccistc\Desktop\녹음 2026-03-13 162139.mp4"
OUTPUT_DIR = "analysis_results"

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

pose_model = YOLO(YOLO_MODEL_PATH)
action_model = tf.keras.models.load_model(MODEL_PATH)
le = joblib.load(ENCODER_PATH)
all_labels = le.classes_

MAX_FRAMES = 60
NUM_JOINTS = 13
CHANNELS = 6
JOINT_INDICES = [0, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

# [기존 preprocess_instant 함수 유지]
def preprocess_instant(frames_data):
    df = pd.DataFrame(frames_data)
    coords_2d = np.stack([df.iloc[:, [i*3 for i in range(NUM_JOINTS)]].values, 
                          df.iloc[:, [i*3 + 1 for i in range(NUM_JOINTS)]].values], axis=-1)
    conf = df.iloc[:, [i*3 + 2 for i in range(NUM_JOINTS)]].values
    hip_l, hip_r = coords_2d[:, 7, :], coords_2d[:, 8, :]
    hip_widths = np.linalg.norm(hip_l - hip_r, axis=1)
    avg_width = np.mean(hip_widths) if np.mean(hip_widths) > 0 else 0.1
    z_pseudo = np.tile((avg_width / (hip_widths + 1e-6))[:, np.newaxis, np.newaxis], (1, NUM_JOINTS, 1))
    coords_3d = np.concatenate([coords_2d, z_pseudo], axis=-1)
    hip_center = (coords_3d[:, 7, :] + coords_3d[:, 8, :]) / 2
    for f in range(coords_3d.shape[0]): coords_3d[f] -= hip_center[f]
    deltas_3d = np.diff(coords_3d, axis=0, prepend=coords_3d[0:1, :, :])
    conf_exp = np.expand_dims(conf, axis=-1)
    combined = np.concatenate([coords_3d * conf_exp, deltas_3d * conf_exp], axis=-1)
    if len(combined) < MAX_FRAMES:
        pad = np.zeros((MAX_FRAMES - len(combined), NUM_JOINTS, CHANNELS))
        combined = np.vstack([combined, pad])
    else: combined = combined[-MAX_FRAMES:]
    return np.expand_dims(combined.astype('float32'), axis=0)

# ==============================
# 🚀 3. 분석 실행 (시간 체크 로직 포함)
# ==============================
cap = cv2.VideoCapture(VIDEO_PATH)
frame_buffer = deque(maxlen=MAX_FRAMES)
main_target_id = None
accumulated_predictions = []

# 시간 통계용 변수
total_start_time = time.time()
frame_times = []
yolo_times = []
preprocess_times = []
action_model_times = []
frame_count = 0

print(f"🔎 영상 분석 시작: {os.path.basename(VIDEO_PATH)}")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    
    frame_count += 1
    loop_start = time.time()

    # --- 1단계: YOLO Pose Tracking 시간 측정 ---
    yolo_start = time.time()
    results = pose_model.track(frame, persist=True, verbose=False, conf=0.3)[0]
    yolo_times.append(time.time() - yolo_start)

    if results.boxes is not None and results.boxes.id is not None:
        ids = results.boxes.id.cpu().numpy().astype(int)
        if main_target_id is None:
            areas = results.boxes.xywh.cpu().numpy()[:, 2] * results.boxes.xywh.cpu().numpy()[:, 3]
            main_target_id = ids[np.argmax(areas)]
        
        if main_target_id in ids:
            idx = np.where(ids == main_target_id)[0][0]
            points = results.keypoints.data[idx].cpu().numpy()
            
            curr_data = []
            for j_idx in JOINT_INDICES:
                jx, jy, jconf = points[j_idx]
                curr_data.extend([jx / frame.shape[1], jy / frame.shape[0], jconf])
            frame_buffer.append(curr_data)
            
            if len(frame_buffer) >= 10:
                # --- 2단계: 데이터 전처리 시간 측정 ---
                pre_start = time.time()
                input_data = preprocess_instant(list(frame_buffer))
                preprocess_times.append(time.time() - pre_start)

                # --- 3단계: Action Model 추론 시간 측정 ---
                action_start = time.time()
                prediction = action_model.predict(input_data, verbose=0)[0]
                action_model_times.append(time.time() - action_start)
                
                accumulated_predictions.append(prediction)

    frame_times.append(time.time() - loop_start)

    # 100프레임마다 중간 보고
    if frame_count % 100 == 0:
        avg_fps = 1 / np.mean(frame_times[-100:])
        print(f"📊 {frame_count}프레임 처리 중... 현재 FPS: {avg_fps:.2f}")

cap.release()
total_end_time = time.time()

# ==============================
# ⏱️ 최종 시간 리포트 출력
# ==============================
print("\n" + "="*50)
print("⏱️ [ 분석 시간 상세 리포트 ]")
print("="*50)
print(f"✔️ 전체 처리 시간: {total_end_time - total_start_time:.2f}초")
print(f"✔️ 총 처리 프레임: {frame_count} 프레임")
print(f"✔️ 평균 FPS: {frame_count / (total_end_time - total_start_time):.2f}")
print("-" * 50)
print(f"1️⃣ YOLO 추적 (평균):   {np.mean(yolo_times)*1000:.2f}ms")
print(f"2️⃣ 데이터 전처리 (평균): {np.mean(preprocess_times)*1000:.2f}ms")
print(f"3️⃣ 액션 모델 추론 (평균): {np.mean(action_model_times)*1000:.2f}ms")
print("="*50)

# [기존 결과 리포트 생성 및 그래프 저장 섹션 유지]