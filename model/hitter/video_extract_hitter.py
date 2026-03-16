import cv2
import mediapipe as mp
import numpy as np
import os
import pandas as pd
from ultralytics import YOLO
import glob

# ==============================
# ⚙️ 사용자 설정
# ==============================
INPUT_DIR = r"C:\Users\kccistc\Desktop\workspace\project\batter_original\moonbokyung" 
OUTPUT_DIR = r"C:\Users\kccistc\Desktop\workspace\project\batter_output_results\moonbokyung"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================
# 모델 및 초기화
# ==============================
model = YOLO("yolov8n.pt")
mp_pose = mp.solutions.pose

# 전신 분석을 위해 정밀도 설정을 유지합니다.
pose = mp_pose.Pose(
    model_complexity=1, 
    min_detection_confidence=0.3, 
    min_tracking_confidence=0.3
)
mp_drawing = mp.solutions.drawing_utils

JOINT_MAP = {
    0: "NOSE", 11: "L_SHOULDER", 12: "R_SHOULDER", 13: "L_ELBOW", 14: "R_ELBOW",
    15: "L_WRIST", 16: "R_WRIST", 23: "L_HIP", 24: "R_HIP", 25: "L_KNEE",
    26: "R_KNEE", 27: "L_ANKLE", 28: "R_ANKLE"
}

# ==============================
# 메인 프로세스
# ==============================
video_files = glob.glob(os.path.join(INPUT_DIR, "*.mp4"))

for video_path in video_files:
    file_name = os.path.basename(video_path)
    file_basename = os.path.splitext(file_name)[0]
    
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width, height = int(cap.get(3)), int(cap.get(4))
    
    # 출력 파일 설정 (전체 프레임 저장)
    output_video_path = os.path.join(OUTPUT_DIR, f"{file_basename}_full_analysis.mp4")
    out_writer = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    
    raw_data_accumulator = []
    target_id = None

    print(f"\n[전체 분석 시작] {file_name}")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        annotated_frame = frame.copy()
        results = model.track(frame, persist=True, verbose=False)[0]
        current_target_box = None

        # 1. 대상 추적 (YOLO)
        if results.boxes.id is not None:
            ids = results.boxes.id.cpu().numpy().astype(int)
            if target_id is None: target_id = ids[0]
            if target_id in ids:
                idx = np.where(ids == target_id)[0][0]
                current_target_box = results.boxes.xyxy.cpu().numpy()[idx]

        frame_data = None
        
        # 2. 포즈 추출 (MediaPipe)
        if current_target_box is not None:
            x1, y1, x2, y2 = map(int, current_target_box)
            margin = 60 
            x1_m, y1_m = max(0, x1-margin), max(0, y1-margin)
            x2_m, y2_m = min(width, x2+margin), min(height, y2+margin)
            crop = frame[y1_m:y2_m, x1_m:x2_m]
            
            if crop.size > 0:
                # 업샘플링 적용 (확대 영상 대응)
                input_crop = cv2.resize(crop, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
                res = pose.process(cv2.cvtColor(input_crop, cv2.COLOR_BGR2RGB))
                
                if res.pose_landmarks:
                    # 원본 프레임에 스켈레톤 그리기
                    mp_drawing.draw_landmarks(
                        annotated_frame[y1_m:y2_m, x1_m:x2_m], 
                        res.pose_landmarks, 
                        mp_pose.POSE_CONNECTIONS
                    )
                    
                    lm = res.pose_landmarks.landmark
                    # 현재 프레임 데이터 생성
                    temp_data = []
                    for j_id in JOINT_MAP.keys():
                        temp_data.extend([lm[j_id].x, lm[j_id].y, lm[j_id].z, lm[j_id].visibility])
                    frame_data = temp_data

        # 3. 데이터 기록 (감지 여부와 상관없이 매 프레임 기록)
        if frame_data:
            raw_data_accumulator.append(frame_data)
        else:
            # 타자를 놓쳤을 경우 NaN으로 채워 행 수 유지
            raw_data_accumulator.append([np.nan] * (len(JOINT_MAP) * 4))
        
        out_writer.write(annotated_frame)

        cv2.imshow("Full Frame Analysis", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    out_writer.release()
    cv2.destroyAllWindows()

    # CSV 저장
    if raw_data_accumulator:
        cols = []
        for name in JOINT_MAP.values():
            cols.extend([f"{name}_x", f"{name}_y", f"{name}_z", f"{name}_vis"])
        df = pd.DataFrame(raw_data_accumulator, columns=cols)
        
        # 선형 보간으로 튀는 데이터나 누락된 부분 보정
        df = df.interpolate(method='linear', limit_direction='both')
        
        output_csv_path = os.path.join(OUTPUT_DIR, f"{file_basename}_full_data.csv")
        df.to_csv(output_csv_path, index=False)
        print(f" >> [저장 완료] CSV 행 수: {len(df)}")

print("\n🎉 모든 영상의 전체 프레임 분석이 완료되었습니다!")