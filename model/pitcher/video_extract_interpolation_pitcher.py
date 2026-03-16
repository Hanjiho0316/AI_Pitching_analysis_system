import cv2
import mediapipe as mp
import numpy as np
import os
import pandas as pd
import matplotlib.pyplot as plt
from collections import deque
from ultralytics import YOLO

def analyze_pitcher_video(video_name):
    # 경로 및 설정
    VIDEO_PATH = f"data/{video_name}"
    OUTPUT_CLIP_DIR = f"pitch_clips/{video_name}/"
    os.makedirs(OUTPUT_CLIP_DIR, exist_ok=True)

    # 모델 및 도구 초기화
    model = YOLO("yolov8n.pt")
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(model_complexity=2, 
                        min_detection_confidence=0.7, 
                        min_tracking_confidence=0.7)
    mp_drawing = mp.solutions.drawing_utils

    JOINT_MAP = {
        0: "NOSE", 11: "L_SHOULDER", 12: "R_SHOULDER", 13: "L_ELBOW", 14: "R_ELBOW",
        15: "L_WRIST", 16: "R_WRIST", 23: "L_HIP", 24: "R_HIP", 25: "L_KNEE",
        26: "R_KNEE", 27: "L_ANKLE", 28: "R_ANKLE"
    }

    # 데이터 처리 내부 함수
    def finalize_pitch_data(data_list, clip_id, output_dir):
        if not data_list: return
        columns = ['frame']
        for j_id in JOINT_MAP.keys():
            name = JOINT_MAP[j_id]
            columns.extend([f"{name}_x", f"{name}_y", f"{name}_z", f"{name}_vis"])
        
        df = pd.DataFrame(data_list, columns=columns)
        for j_id in JOINT_MAP.keys():
            name = JOINT_MAP[j_id]
            x_c, y_c, z_c, v_c = f"{name}_x", f"{name}_y", f"{name}_z", f"{name}_vis"
            df.loc[df[v_c] < 0.5, [x_c, y_c, z_c]] = np.nan
            if df[x_c].count() > 3:
                df[[x_c, y_c, z_c]] = df[[x_c, y_c, z_c]].interpolate(method='cubic', limit_direction='both')
            df[[x_c, y_c, z_c]] = df[[x_c, y_c, z_c]].interpolate(method='linear', limit_direction='both')

        df.to_csv(os.path.join(output_dir, f"pitch_data_{clip_id:03d}.csv"), index=False)
        
        plt.figure(figsize=(8, 4))
        plt.plot(df['frame'], df['R_WRIST_y'], label='R_Wrist Y', color='red')
        plt.gca().invert_yaxis()
        plt.title(f"Pitch {clip_id} Analysis")
        plt.savefig(os.path.join(output_dir, f"plot_{clip_id:03d}.png"))
        plt.close()

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"파일을 열 수 없습니다: {VIDEO_PATH}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width, height = int(cap.get(3)), int(cap.get(4))

    pre_offset_frames = int(fps * 0.75) # 0.5 -> 0.75
    post_offset_frames = int(fps * 2.0)

    frame_buffer = deque(maxlen=pre_offset_frames)
    clip_frames = []
    raw_data_accumulator = []
    is_recording = False
    post_frame_count, clip_count, cooldown = 0, 0, 0
    pitcher_id = None

    ROI_X1, ROI_X2 = int(width * 0.35), int(width * 0.65)
    ROI_Y1, ROI_Y2 = int(height * 0.2), int(height * 0.8)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        annotated_frame = frame.copy()
        results = model.track(frame, persist=True, verbose=False)[0]
        current_pitcher_candidate = None

        if results.boxes.id is not None:
            boxes = results.boxes.xyxy.cpu().numpy()
            ids = results.boxes.id.cpu().numpy().astype(int)
            
            if pitcher_id is None:
                for i, box in enumerate(boxes):
                    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                    if ROI_X1 < cx < ROI_X2 and ROI_Y1 < cy < ROI_Y2:
                        pitcher_id = ids[i]
                        break
            
            if pitcher_id in ids:
                idx = np.where(ids == pitcher_id)[0][0]
                current_pitcher_candidate = boxes[idx]
            else:
                pitcher_id = None

        if current_pitcher_candidate is not None:
            x1, y1, x2, y2 = map(int, current_pitcher_candidate)
            margin = 40
            y1_m, y2_m = max(0, y1-margin), min(height, y2+margin)
            x1_m, x2_m = max(0, x1-margin), min(width, x2+margin)
            crop = frame[y1_m:y2_m, x1_m:x2_m]
            
            if crop.size > 0:
                res = pose.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                if res.pose_landmarks:
                    mp_drawing.draw_landmarks(annotated_frame[y1_m:y2_m, x1_m:x2_m], 
                                              res.pose_landmarks, mp_pose.POSE_CONNECTIONS)

                    lm = res.pose_landmarks.landmark
                    knee_y = min(lm[25].y, lm[26].y)
                    hip_y = (lm[23].y + lm[24].y) / 2
                    
                    if knee_y < (hip_y + 0.12) and not is_recording and cooldown == 0:
                        print(f"!!! 초민감 투구 감지 성공 (Clip {clip_count}) !!!")
                        is_recording = True
                        clip_frames = list(frame_buffer)
                        raw_data_accumulator = []
                        post_frame_count = 0

                    if is_recording:
                        frame_data = [post_frame_count]
                        for j_id in JOINT_MAP.keys():
                            frame_data.extend([lm[j_id].x, lm[j_id].y, lm[j_id].z, lm[j_id].visibility])
                        raw_data_accumulator.append(frame_data)

        if not is_recording:
            frame_buffer.append(annotated_frame.copy())
        else:
            clip_frames.append(annotated_frame.copy())
            post_frame_count += 1
            
            if post_frame_count >= post_offset_frames:
                v_path = os.path.join(OUTPUT_CLIP_DIR, f"pitch_skele_{clip_count:03d}.mp4")
                out = cv2.VideoWriter(v_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
                for f in clip_frames: out.write(f)
                out.release()
                
                finalize_pitch_data(raw_data_accumulator, clip_count, OUTPUT_CLIP_DIR)
                clip_count += 1
                is_recording, cooldown, pitcher_id = False, int(fps * 3.0), None
                frame_buffer.clear()

        if cooldown > 0: cooldown -= 1
        cv2.rectangle(annotated_frame, (ROI_X1, ROI_Y1), (ROI_X2, ROI_Y2), (255, 255, 255), 1)
        cv2.imshow("Pitcher Skeleton Tracker", annotated_frame)
        if cv2.waitKey(1) & 0xFF == 27: break

    cap.release()
    cv2.destroyAllWindows()
    print(f"분석 완료: {video_name}, 총 {clip_count}개의 클립이 생성되었습니다.")

# 함수 호출 예시
# analyze_pitcher_video("2018kimkwanghyeon.mp4")
