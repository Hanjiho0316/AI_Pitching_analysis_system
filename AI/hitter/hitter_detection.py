import cv2
import numpy as np
import os
import pandas as pd
from ultralytics import YOLO
import tensorflow as tf
import joblib
from collections import deque

# ==============================
# ⚙️ 사용자 설정 및 모델 로드
# ==============================
MODEL_PATH = r"saved_models_yolo_3d/yolo_3d_fold_1.h5" 
ENCODER_PATH = r"saved_models_yolo_3d/label_encoder.pkl"
YOLO_MODEL_PATH = "yolov8n-pose.pt"
VIDEO_PATH = r"C:\Users\kccistc\Desktop\workspace\project\batter_output_results\choijung\녹음 2026-03-13 114629_fixed_target.mp4"

pose_model = YOLO(YOLO_MODEL_PATH)
action_model = tf.keras.models.load_model(MODEL_PATH)
le = joblib.load(ENCODER_PATH)

MAX_FRAMES = 60
NUM_JOINTS = 13
CHANNELS = 6
JOINT_INDICES = [0, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

# ==============================
# 🛠️ 실시간 전처리 함수 (Zero-padding 적용)
# ==============================
def preprocess_instant(frames_data):
    """
    현재까지 쌓인 데이터가 MAX_FRAMES보다 적어도 분석 가능하게 패딩 처리
    """
    df = pd.DataFrame(frames_data)
    
    # 1. 2D 좌표 및 신뢰도 추출
    x_cols = [i*3 for i in range(NUM_JOINTS)]
    y_cols = [i*3 + 1 for i in range(NUM_JOINTS)]
    conf_cols = [i*3 + 2 for i in range(NUM_JOINTS)]
    
    coords_2d = np.stack([df.iloc[:, x_cols].values, df.iloc[:, y_cols].values], axis=-1)
    conf = df.iloc[:, conf_cols].values
    
    # 2. 가상 Z축 연산
    hip_l, hip_r = coords_2d[:, 7, :], coords_2d[:, 8, :]
    hip_widths = np.linalg.norm(hip_l - hip_r, axis=1)
    avg_width = np.mean(hip_widths) if np.mean(hip_widths) > 0 else 0.1
    z_pseudo = avg_width / (hip_widths + 1e-6)
    z_pseudo = np.tile(z_pseudo[:, np.newaxis, np.newaxis], (1, NUM_JOINTS, 1))
    
    # 3. 3D 좌표 구성 및 정규화
    coords_3d = np.concatenate([coords_2d, z_pseudo], axis=-1)
    hip_center = (coords_3d[:, 7, :] + coords_3d[:, 8, :]) / 2
    for f in range(coords_3d.shape[0]):
        coords_3d[f] -= hip_center[f]
        
    # 4. 변화량 및 신뢰도 가중치
    deltas_3d = np.diff(coords_3d, axis=0, prepend=coords_3d[0:1, :, :])
    conf_exp = np.expand_dims(conf, axis=-1)
    combined = np.concatenate([coords_3d * conf_exp, deltas_3d * conf_exp], axis=-1)
    
    # [핵심] 부족한 프레임만큼 뒤에 0을 채움 (Zero-Padding)
    current_len = len(combined)
    if current_len < MAX_FRAMES:
        pad = np.zeros((MAX_FRAMES - current_len, NUM_JOINTS, CHANNELS))
        combined = np.vstack([combined, pad])
    else:
        combined = combined[-MAX_FRAMES:]
        
    return np.expand_dims(combined.astype('float32'), axis=0)
# ==============================
# 🚀 메인 실행 루프
# ==============================
cap = cv2.VideoCapture(VIDEO_PATH)
frame_buffer = deque(maxlen=MAX_FRAMES)
main_target_id = None

print("\n" + "="*50)
print("🚀 야구 타격 폼 분석 시스템 가동")
print(f"🎬 분석 대상: {os.path.basename(VIDEO_PATH)}")
print("="*50 + "\n")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    
    display_frame = frame.copy()
    h, w, _ = frame.shape
    
    # YOLO 추적
    results = pose_model.track(frame, persist=True, verbose=False, conf=0.2)[0]

    if results.boxes is not None and results.boxes.id is not None:
        ids = results.boxes.id.cpu().numpy().astype(int)
        
        if main_target_id is None:
            areas = results.boxes.xywh.cpu().numpy()[:, 2] * results.boxes.xywh.cpu().numpy()[:, 3]
            main_target_id = ids[np.argmax(areas)]
            print(f"🎯 타자 고정 완료! (Target ID: {main_target_id})")
        
        if main_target_id in ids:
            idx = np.where(ids == main_target_id)[0][0]
            points = results.keypoints.data[idx].cpu().numpy()
            
            curr_data = []
            for j_idx in JOINT_INDICES:
                jx, jy, jconf = points[j_idx]
                curr_data.extend([jx / w, jy / h, jconf])
            frame_buffer.append(curr_data)
            
            # 분석 수행
            if len(frame_buffer) > 0:
                input_data = preprocess_instant(list(frame_buffer))
                prediction = action_model.predict(input_data, verbose=0)
                
                class_idx = np.argmax(prediction[0])
                prob = prediction[0][class_idx] * 100
                player_name = le.inverse_transform([class_idx])[0]
                
                # --- [콘솔 출력 로직] ---
                # 매 프레임 결과를 콘솔에 출력 (버퍼 진행률과 함께)
                print(f"[{len(frame_buffer):02d}/60] 분석 중... 결과: {player_name} ({prob:5.1f}%)", end='\r')
                
                # 화면 출력용 텍스트
                res_text = f"{player_name} ({prob:.1f}%)"
                bx1, by1, bx2, by2 = results.boxes.xyxy[idx].cpu().numpy()
                cv2.rectangle(display_frame, (int(bx1), int(by1)), (int(bx2), int(by2)), (0, 255, 0), 2)
                cv2.putText(display_frame, res_text, (int(bx1), int(by1)-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (36, 255, 12), 2)

    cv2.imshow("Real-time Similarity", display_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): 
        print("\n\n🛑 사용자에 의해 분석이 중단되었습니다.")
        break

print("\n\n✅ 분석 완료!")
cap.release()
cv2.destroyAllWindows()
