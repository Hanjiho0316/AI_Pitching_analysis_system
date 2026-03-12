"""
비전 기반 투구 분석 서비스 모듈입니다.
YOLOv8, MediaPipe, TensorFlow 모델을 결합하여 사용자의 투구 폼을 분석하고 
데이터베이스에 저장된 프로 투수 데이터와 비교합니다.
"""
import os
import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import joblib
import tensorflow as tf
from collections import deque
from ultralytics import YOLO
import threading
import uuid
from flask import current_app
from app import db
from app.models.analysis import Analysis
from app.models.ranking import Ranking
from app.models.pitcher import Pitcher
from app.models.user import User


# 모델 및 데이터 처리를 위한 설정값
MAX_FRAMES, NUM_JOINTS, CHANNELS = 60, 13, 6
JOINT_MAP = {
    0: "NOSE", 
    11: "L_SHOULDER", 
    12: "R_SHOULDER", 
    13: "L_ELBOW", 
    14: "R_ELBOW",
    15: "L_WRIST", 
    16: "R_WRIST", 
    23: "L_HIP", 
    24: "R_HIP", 
    25: "L_KNEE",
    26: "R_KNEE", 
    27: "L_ANKLE", 
    28: "R_ANKLE"
}

# 비동기 작업의 상태와 결과를 임시 저장하는 딕셔너리
task_store = {}


def get_detailed_analysis(df):
    """
    추출된 관절의 좌표 데이터를 바탕으로 
    투구 시 발생하는 물리적 수치 (기울기, 릴리스 포인트 높이, 보폭)를 계산합니다.

    Args:
        df (DataFrame): 프레임별 관절의 x, y, z 좌표 및 
            가시성(visibility) 데이터가 포함된 데이터프레임

    Returns:
        dict: 어깨 기울기(tilt), 릴리스 포인트 높이(height), 
            보폭(stride) 수치를 포함하는 딕셔너리. 
            데이터가 비어있을 경우 0으로 초기화된 값을 반환합니다.
    """
    if df.empty:
        return {"tilt": 0, "height": 0, "stride": 0}
    
    # 양쪽 어깨의 y좌표 차이로 상체 기울기 계산
    tilt = (df['R_SHOULDER_y'] - df['L_SHOULDER_y']).max()
    # 손목의 최소 y좌표로 공을 놓는 지점의 높이 추정
    release_height = min(df['R_WRIST_y'].min(), df['L_WRIST_y'].min())
    # 양 발목 사이의 최대 x축 거리를 통해 보폭 계산
    stride = np.abs(df['R_ANKLE_x'] - df['L_ANKLE_x']).max()

    return {"tilt": tilt, "height": release_height, "stride": stride}


def predict_and_analyze(raw_data, classifier_model, le):
    """
    수집된 프레임별 관절 데이터를 전처리하고 
    딥러닝 모델을 통해 가장 유사한 투수를 예측합니다.
    엉덩이 중심을 기준으로 좌표를 정규화하며, 
    입력 길이가 부족할 경우 마지막 프레임을 복사하여 패딩을 수행합니다.

    Args:
        raw_data (list)             : 투구 동작 구간 동안 수집된 프레임별 관절 데이터 리스트
        classifier_model (Model)    : 학습된 텐서플로우 투수 분류 모델
        le (LabelEncoder)           : 예측된 클래스 인덱스를 실제 투수 이름으로 변환할 라벨 인코더

    Returns:
        tuple: (예측된 투수 이름(str), 예측 신뢰도/유사도 백분율(float), 상세 분석 수치(dict))
    """
    if not raw_data or len(raw_data) == 0:
        return "Unknown", 0.0, {"tilt": 0, "height": 0, "stride": 0}

    # 좌표 데이터 파싱 및 힙 기반 정규화
    data = np.array(raw_data)[:, 1:].reshape(-1, NUM_JOINTS, 4)
    coords, vis = data[:, :, :3], data[:, :, 3]
    hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
    norm_coords = coords.copy()
    for f in range(coords.shape[0]):
        norm_coords[f] -= hip_center[f]
    
    # 프레임 간 속도 정보(deltas) 추출
    deltas = np.diff(norm_coords, axis=0, prepend=norm_coords[0:1, :, :])
    deltas *= np.expand_dims(vis, axis=-1)
    combined = np.concatenate([norm_coords, deltas], axis=-1).astype('float32')

    # 고정 길이(MAX_FRAMES) 입력을 위한 패딩 처리
    current_len = len(combined)
    if current_len >= MAX_FRAMES:
        combined = combined[:MAX_FRAMES]
    else:
        padding_size = MAX_FRAMES - current_len
        last_frame = combined[-1:] 
        padding = np.tile(last_frame, (padding_size, 1, 1))
        combined = np.vstack([combined, padding])
    
    # 모델 추론 및 레이블 디코딩
    input_tensor = np.expand_dims(combined, axis=0)
    preds = classifier_model.predict(input_tensor, verbose=0)
    name = le.inverse_transform([np.argmax(preds[0])])[0]
    conf = float(np.max(preds[0]) * 100)

    # 상세 수치 분석 호출
    cols = []
    for j_id in JOINT_MAP.values():
        cols.extend([f"{j_id}_x", f"{j_id}_y", f"{j_id}_z", f"{j_id}_vis"])
    df_temp = pd.DataFrame(np.array(raw_data)[:, 1:], columns=cols)
    analysis = get_detailed_analysis(df_temp)

    return name, conf, analysis


def process_video_background(task_id, filepath, ml_model_path, encoder_path, yolo_path, app, user_id):
    """
    백그라운드 스레드에서 실행되며, 업로드된 영상에서 
    객체 추적(YOLO) 및 자세 추정(MediaPipe)을 수행합니다.
    무릎과 엉덩이의 상대적 위치를 통해 투구의 시작(와인드업 등)을 감지하고, 
    데이터를 수집한 뒤 모델을 호출하여 결과를 전역 딕셔너리에 저장합니다.

    Args:
        task_id (str)   : 현재 분석 작업의 고유 식별자 (UUID)
        filepath (str)  : 분석할 영상 파일의 절대 경로
        base_dir (str)  : 어플리케이션의 기본 루트 디렉토리 (모델 파일 경로 탐색 시 사용)

    Returns:
        None: 결과를 직접 반환하지 않고 task_store 딕셔너리를 업데이트합니다.
    """
    
    try:
        task_store[task_id]['status'] = 'processing'
        
        # 스레드 내부에서 전달받은 경로를 사용하여 모델 로드 (충돌 방지)
        yolo_model = YOLO(yolo_path)
        classifier_model = tf.keras.models.load_model(ml_model_path)
        le = joblib.load(encoder_path)
        
        mp_pose = mp.solutions.pose
        pose = mp_pose.Pose(model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)
        
        cap = cv2.VideoCapture(filepath)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width, height = int(cap.get(3)), int(cap.get(4))

        pre_offset_frames, post_offset_frames = int(fps * 0.5), int(fps * 2.5)
        raw_data_accumulator = []
        is_recording = False
        post_frame_count = 0
        
        # 사람 탐지 시 검색할 화면의 관심 영역(ROI)을 중앙부로 한정합니다.
        ROI_X1, ROI_X2 = int(width * 0.3), int(width * 0.7)
        ROI_Y1, ROI_Y2 = int(height * 0.2), int(height * 0.9)

        prediction_name = "Unknown"
        prediction_conf = 0.0
        analysis_data = {}

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
                        
                        # 무릎이 엉덩이 높이 근처로 올라오면(레그 킥) 투구 동작 시작으로 간주합니다.
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
                    prediction_name, prediction_conf, analysis_data = predict_and_analyze(raw_data_accumulator, classifier_model, le)
                    break

        cap.release()
        
        # 영상이 끝난 후 혹시라도 녹화 중이었다면 분석 시도
        if is_recording and len(raw_data_accumulator) > 0 and prediction_name == "Unknown":
            prediction_name, prediction_conf, analysis_data = predict_and_analyze(raw_data_accumulator, classifier_model, le)

        # 모델 결과물에서 확장자 및 숫자를 제거하여 투수의 순수 이름을 추출합니다.
        clean_name = prediction_name.replace('.mp4', '')
        clean_name = ''.join([i for i in clean_name if not i.isdigit()])
        
        task_store[task_id]['result'] = {
            'similarity': round(prediction_conf, 1),
            'match_player': clean_name,
            'player_img': prediction_name,
            'details': analysis_data
        }

        # 분석이 완료된 후 DB 저장을 위해 앱 컨텍스트를 엽니다.
        if user_id is not None:
            with app.app_context():
                # 투수 ID 조회
                pitcher_info = Pitcher.query.filter_by(model_label=prediction_name).first()
                pitcher_id = pitcher_info.id if pitcher_info else 1
                
                # 1. Analysis 레코드 저장
                new_analysis = Analysis(
                    user_id=user_id,
                    pitcher_id=pitcher_id,
                    similarity=task_store[task_id]['result']['similarity'],
                    user_video_path=filepath
                )
                db.session.add(new_analysis)
                
                # 2. Ranking 및 User 베스트 스코어 갱신 로직
                user = User.query.get(user_id)
                current_score = task_store[task_id]['result']['similarity']
                
                if current_score > user.best_score:
                    user.best_score = current_score
                    
                    # 랭킹 테이블에도 최고 기록을 남깁니다.
                    new_ranking = Ranking(
                        user_id=user_id,
                        pitcher_id=pitcher_id,
                        score=current_score
                    )
                    db.session.add(new_ranking)
                
                db.session.commit()

        task_store[task_id]['status'] = 'completed'
        
    except Exception as e:
        task_store[task_id]['status'] = 'error'
        task_store[task_id]['error_message'] = str(e)
        print(f"Error during analysis: {e}")


def start_analysis_task(filepath, ml_model_path, encoder_path, yolo_path, app, user_id):
    """
    고유한 작업 ID를 발급하고 영상 분석을 백그라운드 스레드로 시작합니다.

    Args:
        filepath (str): 분석할 대상 영상의 시스템 경로
        base_dir (str): 어플리케이션의 기본 루트 경로

    Returns:
        str: 생성된 비동기 작업의 고유 식별자 (task_id)
    """
    task_id = str(uuid.uuid4())
    task_store[task_id] = {
        'status': 'pending',
        'filepath': filepath,
        'result': None
    }
    
    # 스레드 생성 시 경로들을 args로 전달합니다.
    thread = threading.Thread(
        target=process_video_background, 
        args=(task_id, filepath, ml_model_path, encoder_path, yolo_path, app, user_id)
    )
    thread.daemon = True
    thread.start()
    
    return task_id


def get_task_status(task_id):
    """
    발급된 작업 ID를 통해 현재 분석 진행 상태와 완료 시 결과를 조회합니다.

    Args:
        task_id (str): 상태를 조회할 작업의 고유 식별자

    Returns:
        dict: 작업의 현재 상태('pending', 'processing', 'completed', 'error' 등) 및 결과 데이터를 담은 딕셔너리
    """
    return task_store.get(task_id, {'status': 'not_found'})