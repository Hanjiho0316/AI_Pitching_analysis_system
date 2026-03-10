import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import os
import tensorflow as tf
import joblib

# ==============================
# 1. 경로 설정 (d1.png 폴더 구조 반영)
# ==============================
# 현재 파일 위치: UIUX/app/services/video_processor.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) 
# 상위 폴더(UIUX) 찾기
BASE_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR)) 

# 🚨 d1.png 확인 결과: 폴더 구조가 model/model 아래에 파일이 있음
MODEL_DIR = os.path.join(BASE_DIR, "model", "model")
MODEL_PATH = os.path.join(MODEL_DIR, "best_model_fold_1.h5")
ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")

# 모델 로드 확인 로그
print(f"--- 경로 확인 모드 ---")
print(f"루트 경로: {BASE_DIR}")
print(f"모델 경로: {MODEL_PATH}")

model, le = None, None
if os.path.exists(MODEL_PATH) and os.path.exists(ENCODER_PATH):
    try:
        model = tf.keras.models.load_model(MODEL_PATH)
        le = joblib.load(ENCODER_PATH)
        print("✅ 조장님 AI 모델 로드 완료!")
    except Exception as e:
        print(f"❌ 모델 로드 오류: {e}")
else:
    print("⚠️ 모델 파일을 찾을 수 없습니다! 폴더 이름을 확인하세요.")

# MediaPipe 초기화
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# 상수 설정
MAX_FRAMES = 70
JOINT_INDICES = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    return 360-angle if angle > 180.0 else angle

def analyze_user_video(video_path, filename):
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    processed_filename = f"processed_{filename}"
    # static/uploads 경로 설정
    processed_path = os.path.join(BASE_DIR, 'app', 'static', 'uploads', processed_filename)
    
    fourcc = cv2.VideoWriter_fourcc(*'avc1') 
    out = cv2.VideoWriter(processed_path, fourcc, fps, (width, height))

    user_angles = []
    ai_data_frames = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            # 팔꿈치 각도
            angle = calculate_angle([lm[12].x, lm[12].y], [lm[14].x, lm[14].y], [lm[16].x, lm[16].y])
            user_angles.append(float(angle))
            
            # AI 데이터 (조장님 모델용)
            frame_pts = [[lm[i].x, lm[i].y, lm[i].z, lm[i].visibility] for i in JOINT_INDICES]
            ai_data_frames.append(frame_pts)
                
        out.write(frame)
    
    cap.release()
    out.release()

    # 조장님 모델 예측 로직
    best_match = "Anwoojin"
    confidence = 0

    if model and len(ai_data_frames) > 10:
        try:
            coords_all = np.array(ai_data_frames)
            coords = coords_all[:, :, :3]
            vis = coords_all[:, :, 3]

            hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
            for f in range(coords.shape[0]):
                coords[f] -= hip_center[f]

            deltas = np.diff(coords, axis=0, prepend=coords[0:1, :, :])
            deltas *= np.expand_dims(vis, axis=-1)
            combined = np.concatenate([coords, deltas], axis=-1).astype('float32')

            if len(combined) > MAX_FRAMES: combined = combined[:MAX_FRAMES]
            else:
                padding = np.tile(combined[-1:], (MAX_FRAMES - len(combined), 1, 1))
                combined = np.vstack([combined, padding])

            pred = model.predict(np.expand_dims(combined, axis=0), verbose=0)
            idx = np.argmax(pred[0])
            best_match = le.inverse_transform([idx])[0]
            confidence = float(pred[0][idx] * 100)
        except Exception as e:
            print(f"AI 예측 에러: {e}")

    # 데이터 정규화 및 CSV 로드
    user_norm = np.interp(np.linspace(0, len(user_angles)-1, 100), np.arange(len(user_angles)), user_angles).tolist()
    
    pro_norm = [0] * 100
    csv_path = os.path.join(BASE_DIR, 'app', 'services', 'data', f"{best_match}.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        try:
            p_angles = [calculate_angle([r['R_SHOULDER_x'], r['R_SHOULDER_y']], [r['R_ELBOW_x'], r['R_ELBOW_y']], [r['R_WRIST_x'], r['R_WRIST_y']]) for _, r in df.iterrows()]
            pro_norm = np.interp(np.linspace(0, len(p_angles)-1, 100), np.arange(len(p_angles)), p_angles).tolist()
        except: pass

    return {
        "similarity": int(confidence) if confidence > 0 else 50,
        "match_player": best_match,
        "player_img": f"{best_match}.jpg",
        "processed_video": processed_filename,
        "user_data": user_norm,
        "pro_data": pro_norm,
        "feedback": f"AI 분석 결과, {best_match} 투수와 폼이 가장 유사합니다!"
    }