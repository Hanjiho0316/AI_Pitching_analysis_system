import cv2
import numpy as np
import os
import pandas as pd
from ultralytics import YOLO
import glob

# ==============================
# ⚙️ 사용자 설정
# ==============================
INPUT_DIR = r"C:\Users\kccistc\Desktop\workspace\project\batter_original\parkhaemin" 
OUTPUT_DIR = r"C:\Users\kccistc\Desktop\workspace\project\batter_output_results\parkhaemin"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 모델 로드 (추적 기능을 위해 persist=True와 함께 사용)
model = YOLO("yolov8n-pose.pt") 

JOINT_INDICES = [0, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
JOINT_NAMES = ["NOSE", "L_SHOULDER", "R_SHOULDER", "L_ELBOW", "R_ELBOW", 
               "L_WRIST", "R_WRIST", "L_HIP", "R_HIP", "L_KNEE", "R_KNEE", "L_ANKLE", "R_ANKLE"]

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
    
    output_video_path = os.path.join(OUTPUT_DIR, f"{file_basename}_fixed_target.mp4")
    out_writer = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    
    raw_data_accumulator = []
    main_target_id = None  # 처음 결정된 주인공의 ID를 저장할 변수

    print(f"\n[주인공 고정 분석] {file_name}")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        # .track()을 사용하여 객체에 고유 ID를 부여합니다.
        results = model.track(frame, persist=True, conf=0.3, verbose=False)[0]
        
        frame_data = [np.nan] * (len(JOINT_INDICES) * 3)
        annotated_frame = frame.copy()

        # 사람이 감지되었고 ID가 부여된 경우
        if results.boxes is not None and results.boxes.id is not None:
            ids = results.boxes.id.cpu().numpy().astype(int)
            
            # --- 주인공 결정 로직 (처음 딱 한 번만 실행) ---
            if main_target_id is None:
                boxes_xywh = results.boxes.xywh.cpu().numpy()
                areas = boxes_xywh[:, 2] * boxes_xywh[:, 3]
                max_idx = np.argmax(areas)
                main_target_id = ids[max_idx]  # 가장 큰 사람의 ID를 주인공으로 박제
                print(f" >> 주인공 결정! (ID: {main_target_id}, 면적: {areas[max_idx]:.1f})")

            # --- 주인공 추적 로직 ---
            if main_target_id in ids:
                # 현재 프레임에서 주인공 ID의 인덱스 찾기
                target_idx = np.where(ids == main_target_id)[0][0]
                
                # 주인공의 키포인트 추출
                points = results.keypoints.data[target_idx].cpu().numpy()
                
                temp_data = []
                for idx in JOINT_INDICES:
                    x, y, conf = points[idx]
                    if conf > 0.1:
                        temp_data.extend([x / width, y / height, conf])
                        cv2.circle(annotated_frame, (int(x), int(y)), 5, (0, 255, 0), -1)
                    else:
                        temp_data.extend([np.nan, np.nan, conf])
                frame_data = temp_data
                
                # 시각화 (주인공 박스 표시)
                bx1, by1, bx2, by2 = results.boxes.xyxy[target_idx].cpu().numpy()
                cv2.rectangle(annotated_frame, (int(bx1), int(by1)), (int(bx2), int(by2)), (0, 255, 255), 2)
                cv2.putText(annotated_frame, f"Target ID: {main_target_id}", (int(bx1), int(by1)-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        raw_data_accumulator.append(frame_data)
        out_writer.write(annotated_frame)

        cv2.imshow("Fixed Batter Tracker", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    out_writer.release()
    cv2.destroyAllWindows()

    if raw_data_accumulator:
        cols = []
        for name in JOINT_NAMES:
            cols.extend([f"{name}_x", f"{name}_y", f"{name}_conf"])
        df = pd.DataFrame(raw_data_accumulator, columns=cols)
        df = df.interpolate(method='linear', limit_direction='both')
        
        output_csv_path = os.path.join(OUTPUT_DIR, f"{file_basename}_fixed_target.csv")
        df.to_csv(output_csv_path, index=False)
        print(f" >> [성공] ID {main_target_id}번 주인공 데이터 저장 완료.")

print("\n🎉 모든 영상의 주인공 고정 분석이 완료되었습니다!")
