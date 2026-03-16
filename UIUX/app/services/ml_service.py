"""
비전 기반 투구/타격 분석 서비스 모듈입니다.
YOLOv8 Pose 및 TensorFlow 모델을 결합하여 사용자의 폼을 분석하고 
데이터베이스에 저장된 프로 선수 데이터와 비교합니다.
"""
import os
import cv2
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
MAX_FRAMES = 60
NUM_JOINTS = 13

# [투수/타자 공통] 관절 인덱스 및 이름 (YOLOv8 Pose 기준)
JOINT_INDICES = [0, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
JOINT_NAMES = ["NOSE", "L_SHOULDER", "R_SHOULDER", "L_ELBOW", "R_ELBOW",
               "L_WRIST", "R_WRIST", "L_HIP", "R_HIP", "L_KNEE", "R_KNEE", "L_ANKLE", "R_ANKLE"]
SMOOTHING_WINDOW = 5

# 비동기 작업의 상태와 결과를 임시 저장하는 딕셔너리
task_store = {}


def calibrate_score(raw_score, c=10):
    """모델의 원시 정확도(0~100)를 로그 스케일로 보정"""
    if raw_score <= 0:
        return 0.0
    if raw_score >= 100:
        return 100.0
    
    adjusted = 100 * (math.log10(c * raw_score + 1) / math.log10(c * 100 + 1))
    return round(adjusted, 2)


def get_detailed_analysis_yolo(df):
    """추출된 YOLO 관절 데이터를 바탕으로 물리적 수치 계산"""
    if df.empty:
        return {"tilt": 0, "height": 0, "stride": 0}
    
    try:
        tilt = (df['R_SHOULDER_y'] - df['L_SHOULDER_y']).max()
        release_height = min(df['R_WRIST_y'].min(), df['L_WRIST_y'].min())
        stride = np.abs(df['R_ANKLE_x'] - df['L_ANKLE_x']).max()
        return {"tilt": float(tilt), "height": float(release_height), "stride": float(stride)}
    except Exception:
        return {"tilt": 0, "height": 0, "stride": 0}


def preprocess_pitch_data(df):
    """[투수 전용] 좌표 데이터를 보간, 스무딩 후 패딩 및 정규화합니다."""
    x_cols    = [f"{n}_x" for n in JOINT_NAMES]
    y_cols    = [f"{n}_y" for n in JOINT_NAMES]
    conf_cols = [f"{n}_conf" for n in JOINT_NAMES]

    coords = np.stack([df[x_cols].values, df[y_cols].values], axis=-1)
    conf   = df[conf_cols].values

    # 골반 중심 정규화
    hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
    for f in range(coords.shape[0]):
        coords[f] -= hip_center[f]

    # 변화량(델타) 및 신뢰도 가중치 적용
    deltas = np.diff(coords, axis=0, prepend=coords[0:1])
    deltas *= np.expand_dims(conf, axis=-1)

    combined = np.concatenate([coords, deltas], axis=-1)

    # 제로 패딩 (Zero-Padding)
    if len(combined) > MAX_FRAMES:
        combined = combined[:MAX_FRAMES]
    else:
        pad = np.zeros((MAX_FRAMES - len(combined), NUM_JOINTS, 4))
        combined = np.vstack([combined, pad])

    return np.expand_dims(combined.astype('float32'), axis=0)


def preprocess_hit_data(frames_data):
    """[타자 전용] 타자 분석을 위한 좌표 데이터를 패딩 및 정규화합니다."""
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
    
    # Zero-Padding
    current_len = len(combined)
    if current_len < MAX_FRAMES:
        pad = np.zeros((MAX_FRAMES - current_len, NUM_JOINTS, 6))
        combined = np.vstack([combined, pad])
    else:
        combined = combined[-MAX_FRAMES:]
        
    return np.expand_dims(combined.astype('float32'), axis=0)


def swap_lr_joints_df(df):
    """판다스 데이터프레임의 L(좌)와 R(우) 관절 좌표 및 신뢰도를 교체합니다."""
    temp_df = df.copy()
    body_parts = ['SHOULDER', 'ELBOW', 'WRIST', 'HIP', 'KNEE', 'ANKLE']
    for part in body_parts:
        for suffix in ['_x', '_y', '_conf']:
            l_col = f"L_{part}{suffix}"
            r_col = f"R_{part}{suffix}"
            if l_col in df.columns and r_col in df.columns:
                df[l_col] = temp_df[r_col]
                df[r_col] = temp_df[l_col]
    return df


def preprocess_hit_data(frames_data, handedness='right'):
    """[타자 전용] 타자 분석을 위한 좌표 데이터를 패딩 및 정규화합니다. (좌타자 반전 처리 포함)"""
    df = pd.DataFrame(frames_data)
    
    if handedness == 'left':
        temp_df = df.copy()
        pairs = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]
        for l_idx, r_idx in pairs:
            for offset in range(3):
                df.iloc[:, l_idx*3 + offset] = temp_df.iloc[:, r_idx*3 + offset]
                df.iloc[:, r_idx*3 + offset] = temp_df.iloc[:, l_idx*3 + offset]
                
    x_cols = [i*3 for i in range(NUM_JOINTS)]
    y_cols = [i*3 + 1 for i in range(NUM_JOINTS)]
    conf_cols = [i*3 + 2 for i in range(NUM_JOINTS)]
    
    coords_2d = np.stack([df.iloc[:, x_cols].values, df.iloc[:, y_cols].values], axis=-1)
    conf = df.iloc[:, conf_cols].values
    
    hip_l, hip_r = coords_2d[:, 7, :], coords_2d[:, 8, :]
    hip_widths = np.linalg.norm(hip_l - hip_r, axis=1)
    avg_width = np.mean(hip_widths) if np.mean(hip_widths) > 0 else 0.1
    z_pseudo = avg_width / (hip_widths + 1e-6)
    z_pseudo = np.tile(z_pseudo[:, np.newaxis, np.newaxis], (1, NUM_JOINTS, 1))
    
    coords_3d = np.concatenate([coords_2d, z_pseudo], axis=-1)
    hip_center = (coords_3d[:, 7, :] + coords_3d[:, 8, :]) / 2
    for f in range(coords_3d.shape[0]):
        coords_3d[f] -= hip_center[f]
        
    deltas_3d = np.diff(coords_3d, axis=0, prepend=coords_3d[0:1, :, :])
    conf_exp = np.expand_dims(conf, axis=-1)
    combined = np.concatenate([coords_3d * conf_exp, deltas_3d * conf_exp], axis=-1)
    
    current_len = len(combined)
    if current_len < MAX_FRAMES:
        pad = np.zeros((MAX_FRAMES - current_len, NUM_JOINTS, 6))
        combined = np.vstack([combined, pad])
    else:
        combined = combined[-MAX_FRAMES:]
        
    return np.expand_dims(combined.astype('float32'), axis=0)


def process_video_background(task_id, filepath, ml_model_path, encoder_path, yolo_path, app, user_id, analysis_type='pitch', handedness='right'):
    """백그라운드 비디오 분석 로직 (좌우반전 적용)"""
    try:
        task_store[task_id]['status'] = 'processing'
        
        classifier_model = tf.keras.models.load_model(ml_model_path)
        le = joblib.load(encoder_path)
        
        cap = cv2.VideoCapture(filepath)
        width, height = int(cap.get(3)), int(cap.get(4))

        prediction_name = "Unknown"
        prediction_conf = 0.0
        analysis_data = {"tilt": 0, "height": 0, "stride": 0}

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
                    
                    if main_target_id is None:
                        areas = results.boxes.xywh.cpu().numpy()[:, 2] * results.boxes.xywh.cpu().numpy()[:, 3]
                        main_target_id = ids[np.argmax(areas)]
                        
                    if main_target_id in ids:
                        idx = np.where(ids == main_target_id)[0][0]
                        if hasattr(results, 'keypoints') and results.keypoints is not None:
                            points = results.keypoints.data[idx].cpu().numpy()
                            
                            curr_data = []
                            for j_idx in JOINT_INDICES:
                                jx, jy, jconf = points[j_idx]
                                curr_data.extend([jx / width, jy / height, jconf])
                            frame_buffer.append(curr_data)
                            
                            if len(frame_buffer) > 0:
                                input_data = preprocess_hit_data(list(frame_buffer), handedness)
                                prediction = classifier_model.predict(input_data, verbose=0)
                                
                                class_idx = np.argmax(prediction[0])
                                prob = float(prediction[0][class_idx] * 100)
                                
                                if prob > best_prob:
                                    best_prob = prob
                                    best_name = le.inverse_transform([class_idx])[0]
                                    
            cap.release()
            prediction_name = best_name
            prediction_conf = best_prob

        else:
            yolo_pose_model = YOLO("yolov8n-pose.pt")
            
            ROI_X1, ROI_X2 = int(width * 0.3), int(width * 0.65)
            ROI_Y1, ROI_Y2 = int(height * 0.3), int(height * 0.8)

            raw_data = []
            pitcher_id = None
            lost_frames = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break

                results = yolo_pose_model.track(frame, persist=True, conf=0.3, verbose=False)[0]
                frame_data = [np.nan] * (len(JOINT_INDICES) * 3)

                if results.boxes is not None and results.boxes.id is not None:
                    ids = results.boxes.id.cpu().numpy().astype(int)
                    boxes = results.boxes.xyxy.cpu().numpy()

                    if pitcher_id is None:
                        for i, box in enumerate(boxes):
                            cx = (box[0] + box[2]) / 2
                            cy = (box[1] + box[3]) / 2
                            if ROI_X1 < cx < ROI_X2 and ROI_Y1 < cy < ROI_Y2:
                                pitcher_id = ids[i]
                                break

                    if pitcher_id is not None and pitcher_id in ids:
                        lost_frames = 0
                        target_idx = np.where(ids == pitcher_id)[0][0]
                        if hasattr(results, 'keypoints') and results.keypoints is not None:
                            points = results.keypoints.data[target_idx].cpu().numpy()
                            temp_data = []
                            for idx in JOINT_INDICES:
                                x, y, conf = points[idx]
                                if conf > 0.1:
                                    temp_data.extend([x / width, y / height, conf])
                                else:
                                    temp_data.extend([np.nan, np.nan, conf])
                            frame_data = temp_data
                    elif pitcher_id is not None:
                        lost_frames += 1
                        if lost_frames > 5:
                            pitcher_id, lost_frames = None, 0

                raw_data.append(frame_data)

            cap.release()

            cols = []
            for name in JOINT_NAMES:
                cols.extend([f"{name}_x", f"{name}_y", f"{name}_conf"])
                
            df = pd.DataFrame(raw_data, columns=cols)
            
            if handedness == 'left':
                df = swap_lr_joints_df(df)
                
            df = df.interpolate(method='linear', limit_direction='both')
            df.fillna(0, inplace=True)
            
            coord_cols = [c for c in df.columns if '_x' in c or '_y' in c]
            df[coord_cols] = df[coord_cols].rolling(window=SMOOTHING_WINDOW, center=True, min_periods=1).mean()

            input_data = preprocess_pitch_data(df)
            prediction = classifier_model.predict(input_data, verbose=0)
            
            class_idx = np.argmax(prediction[0])
            prediction_conf = float(prediction[0][class_idx] * 100)
            prediction_name = le.inverse_transform([class_idx])[0]
            analysis_data = get_detailed_analysis_yolo(df)

        clean_name = prediction_name.replace('.mp4', '')
        clean_name = ''.join([i for i in clean_name if not i.isdigit()])
        
        adjusted_score = calibrate_score(prediction_conf)
        
        task_store[task_id]['result'] = {
            'similarity': adjusted_score,
            'match_player': clean_name,
            'player_img': prediction_name,
            'details': analysis_data,
            'handedness': handedness
        }

        if user_id is not None:
            with app.app_context():
                user = User.query.get(user_id)
                current_score = task_store[task_id]['result']['similarity']
                
                if analysis_type == 'hit':
                    from app.models.hitter import Hitter
                    from app.models.ranking import HitterRanking
                    
                    hitter_info = Hitter.query.filter_by(model_label=prediction_name).first()
                    hitter_id = hitter_info.id if hitter_info else 1
                    
                    new_analysis = Analysis(
                        user_id=user_id,
                        analysis_type='hit',
                        hitter_id=hitter_id,
                        similarity=current_score,
                        user_video_path=filepath
                    )
                    db.session.add(new_analysis)
                    
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
                        
                else: 
                    from app.models.pitcher import Pitcher
                    from app.models.ranking import PitcherRanking
                    
                    pitcher_info = Pitcher.query.filter_by(model_label=prediction_name).first()
                    pitcher_id = pitcher_info.id if pitcher_info else 1
                    
                    new_analysis = Analysis(
                        user_id=user_id,
                        analysis_type='pitch',
                        pitcher_id=pitcher_id,
                        similarity=current_score,
                        user_video_path=filepath
                    )
                    db.session.add(new_analysis)
                    
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
                
                if current_score > user.best_score:
                    user.best_score = current_score
                
                db.session.commit()
                task_store[task_id]['analysis_id'] = new_analysis.id

        task_store[task_id]['status'] = 'completed'
        
    except Exception as e:
        task_store[task_id]['status'] = 'error'
        task_store[task_id]['error_message'] = str(e)
        print(f"Error during analysis: {e}")


def start_analysis_task(filepath, ml_model_path, encoder_path, yolo_path, app, user_id, analysis_type='pitch', handedness='right'):
    """작업 시작 시 handedness 파라미터를 추가로 전달합니다."""
    task_id = str(uuid.uuid4())
    task_store[task_id] = {
        'status': 'pending',
        'filepath': filepath,
        'result': None,
        'analysis_type': analysis_type,
        'handedness': handedness
    }
    
    thread = threading.Thread(
        target=process_video_background, 
        args=(task_id, filepath, ml_model_path, encoder_path, yolo_path, app, user_id, analysis_type, handedness)
    )
    thread.daemon = True
    thread.start()
    
    return task_id


def get_task_status(task_id):
    return task_store.get(task_id, {'status': 'not_found'})