import os
import pandas as pd
import numpy as np
import tensorflow as tf
import joblib

# ==============================
# 1. 환경 설정 및 파일 로드
# ==============================
MODEL_PATH = r"./saved_models/best_model_fold_1.h5"  # 가장 성능 좋은 모델 경로
ENCODER_PATH = r"./saved_models/label_encoder.pkl"
TEST_CSV_PATH = r"C:\Users\kccistc\Desktop\workspace\project\dataset\pitcher_A\sample_01.csv" # 테스트할 파일

MAX_FRAMES = 70
NUM_JOINTS = 13
CHANNELS = 6

# 모델 및 인코더 로드
if not os.path.exists(MODEL_PATH) or not os.path.exists(ENCODER_PATH):
    print("❌ 모델이나 레이블 인코더 파일을 찾을 수 없습니다!")
    exit()

model = tf.keras.models.load_model(MODEL_PATH)
le = joblib.load(ENCODER_PATH)
print("✅ 모델 및 인코더 로드 완료")

# ==============================
# 2. 실시간 예측용 전처리 함수 (기존 로직 유지)
# ==============================
def preprocess_single_csv(file_path):
    df = pd.read_csv(file_path).fillna(0)
    
    # 관절 컬럼 추출
    x_cols = [c for c in df.columns if '_x' in c.lower()][:NUM_JOINTS]
    y_cols = [c for c in df.columns if '_y' in c.lower()][:NUM_JOINTS]
    z_cols = [c for c in df.columns if '_z' in c.lower()][:NUM_JOINTS]
    v_cols = [c for c in df.columns if '_v' in c.lower() or '_vis' in c.lower()][:NUM_JOINTS]

    coords = np.stack([df[x_cols].values, df[y_cols].values, df[z_cols].values], axis=-1)
    vis = df[v_cols].values

    # 골반 중심 정규화
    hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
    for f in range(coords.shape[0]):
        coords[f] -= hip_center[f]

    # 변화량(Delta) 계산
    deltas = np.diff(coords, axis=0, prepend=coords[0:1, :, :])
    deltas *= np.expand_dims(vis, axis=-1)

    combined = np.concatenate([coords, deltas], axis=-1).astype('float32')

    # 프레임 수 맞추기 (Replication Padding)
    if len(combined) > MAX_FRAMES:
        combined = combined[:MAX_FRAMES]
    else:
        padding_size = MAX_FRAMES - len(combined)
        last_frame = combined[-1:]
        padding = np.tile(last_frame, (padding_size, 1, 1))
        combined = np.vstack([combined, padding])

    # 모델 입력을 위한 차원 확장 (1, 70, 13, 6)
    return np.expand_dims(combined, axis=0)

# ==============================
# 3. 예측 실행
# ==============================
try:
    input_data = preprocess_single_csv(TEST_CSV_PATH)
    
    # 예측 수행
    predictions = model.predict(input_data, verbose=0)
    predicted_class_idx = np.argmax(predictions[0])
    confidence = predictions[0][predicted_class_idx] * 100
    
    # 레이블 이름 변환
    pitcher_name = le.inverse_transform([predicted_class_idx])[0]

    print("\n" + "="*30)
    print(f"🔍 분석 결과")
    print(f"예측된 투수: {pitcher_name}")
    print(f"신뢰도(확률): {confidence:.2f}%")
    print("="*30)

    # 전체 확률 분포 보기
    print("\n[전체 확률 분포]")
    for idx, prob in enumerate(predictions[0]):
        name = le.inverse_transform([idx])[0]
        print(f"{name}: {prob*100:.2f}%")

except Exception as e:
    print(f"❌ 오류 발생: {e}")