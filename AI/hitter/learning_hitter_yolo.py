import os
import sys

# ==============================
# 0. GPU 환경 강제 설정 (기존 작동 방식 유지)
# ==============================
conda_base = r'C:\Users\kccistc\anaconda3\envs\proj'
dll_path = os.path.join(conda_base, 'Library', 'bin')

if os.path.exists(dll_path):
    os.environ['PATH'] = dll_path + os.pathsep + os.environ.get('PATH', '')
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(dll_path)
    print(f"🚀 핵심 DLL 경로 최우선 설정: {dll_path}")

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers, regularizers
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
import joblib

# GPU 인식 확인 및 메모리 설정
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f"✅ GPU 인식 완료: {len(gpus)}개")
    except RuntimeError as e:
        print(f"❌ GPU 설정 오류: {e}")

# ==============================
# 1. 설정 및 하이퍼파라미터
# ==============================
DATA_ROOT = r"C:\Users\kccistc\Desktop\workspace\project\batter_output_results"
MAX_FRAMES = 60    
NUM_JOINTS = 13   
CHANNELS = 6      # [변경] x, y, z, dx, dy, dz
BATCH_SIZE = 128  
EPOCHS = 200     # 가상 Z축 도입으로 패턴이 복잡해졌으므로 충분히 학습
K_FOLDS = 5  
MODEL_SAVE_DIR = "saved_models_yolo_3d"
LOG_DIR = "logs_yolo_3d"
USE_AUGMENTATION = True 

for d in [MODEL_SAVE_DIR, LOG_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# ==============================
# 2. 전처리 및 3D 데이터 증강
# ==============================
def apply_3d_augmentation(X, y):
    """가상 Z축을 포함한 3D 동작 증강을 수행합니다."""
    aug_X, aug_y = [X], [y]
    
    # 1. 미세 노이즈
    aug_X.append(X + np.random.normal(0, 0.005, X.shape))
    aug_y.append(y)
    
    # 2. 가상 Y축 회전 (Z축이 생겼으므로 가능!)
    # X[..., 0]: x, X[..., 2]: z
    def rotate_y(batch, angle_deg):
        angle_rad = np.radians(angle_deg)
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        new_batch = batch.copy()
        new_batch[..., 0] = batch[..., 0] * cos_a - batch[..., 2] * sin_a
        new_batch[..., 2] = batch[..., 0] * sin_a + batch[..., 2] * cos_a
        return new_batch
    
    aug_X.append(rotate_y(X, np.random.uniform(-10, 10)))
    aug_y.append(y)
    
    # 3. 스케일링 (몸집 크기 변화)
    aug_X.append(X * np.random.uniform(0.9, 1.1))
    aug_y.append(y)
    
    X_final = np.concatenate(aug_X, axis=0)
    y_final = np.concatenate(aug_y, axis=0)
    indices = np.random.permutation(len(X_final))
    return X_final[indices].astype('float32'), y_final[indices].astype('float32')

def robust_preprocess_yolo_with_z(df):
    """2D 데이터를 기반으로 가상 Z축을 생성하고 6채널로 변환합니다."""
    x_cols = [c for c in df.columns if '_x' in c.lower()][:NUM_JOINTS]
    y_cols = [c for c in df.columns if '_y' in c.lower()][:NUM_JOINTS]
    conf_cols = [c for c in df.columns if '_conf' in c.lower()][:NUM_JOINTS]
    
    coords_2d = np.stack([df[x_cols].values, df[y_cols].values], axis=-1) 
    conf = df[conf_cols].values 
    
    # --- 가상 Z축(Depth) 생성 로직 ---
    # 골반 너비(Index 7, 8)를 기준으로 카메라와의 거리를 역산
    hip_l, hip_r = coords_2d[:, 7, :], coords_2d[:, 8, :]
    hip_widths = np.linalg.norm(hip_l - hip_r, axis=1)
    
    # 전체 프레임 평균 너비를 기준으로 상대적 깊이 계산
    avg_width = np.mean(hip_widths) if np.mean(hip_widths) > 0 else 0.1
    z_pseudo = avg_width / (hip_widths + 1e-6)
    z_pseudo = np.tile(z_pseudo[:, np.newaxis, np.newaxis], (1, NUM_JOINTS, 1))
    
    # [x, y, z] 3D 좌표 구성
    coords_3d = np.concatenate([coords_2d, z_pseudo], axis=-1)
    
    # 힙 중심 정규화 (3D 기준)
    hip_center = (coords_3d[:, 7, :] + coords_3d[:, 8, :]) / 2
    for f in range(coords_3d.shape[0]):
        coords_3d[f] -= hip_center[f]
        
    # 변화량(Delta) 계산 [dx, dy, dz]
    deltas_3d = np.diff(coords_3d, axis=0, prepend=coords_3d[0:1, :, :])
    
    # 신뢰도 가중치 적용
    conf_exp = np.expand_dims(conf, axis=-1)
    coords_3d *= conf_exp
    deltas_3d *= conf_exp
    
    return np.concatenate([coords_3d, deltas_3d], axis=-1)

def load_dataset(root_path):
    temp_data = {}
    folders = sorted([d for d in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, d))])
    
    for folder in folders:
        temp_data[folder] = []
        class_dir = os.path.join(root_path, folder)
        csv_files = [f for f in os.listdir(class_dir) if f.endswith('.csv')]
        
        for file in csv_files:
            try:
                df = pd.read_csv(os.path.join(class_dir, file)).fillna(0)
                if len(df) < 15: continue
                combined = robust_preprocess_yolo_with_z(df)
                
                if len(combined) > MAX_FRAMES: combined = combined[:MAX_FRAMES]
                else:
                    pad = np.zeros((MAX_FRAMES - len(combined), NUM_JOINTS, CHANNELS))
                    combined = np.vstack([combined, pad])
                temp_data[folder].append(combined)
            except: pass
            
    min_samples = min([len(v) for v in temp_data.values()])
    print(f"📊 클래스 균형: 각 {min_samples}개 샘플 사용")
    
    final_x, final_y = [], []
    for label, data_list in temp_data.items():
        indices = np.random.choice(len(data_list), min_samples, replace=False)
        for idx in indices:
            final_x.append(data_list[idx])
            final_y.append(label)
    return np.array(final_x, dtype='float32'), np.array(final_y)

# ==============================
# 3. 모델 빌드 (6채널 대응)
# ==============================
def build_model(num_classes):
    inputs = layers.Input(shape=(MAX_FRAMES, NUM_JOINTS, CHANNELS))
    # 시공간 특징 추출을 위한 1D Conv 레이어
    x = layers.Reshape((MAX_FRAMES, NUM_JOINTS * CHANNELS))(inputs)

    x = layers.Conv1D(512, kernel_size=3, padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.SpatialDropout1D(0.4)(x)
    
    x = layers.Conv1D(256, kernel_size=3, padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling1D(2)(x)
    
    x = layers.GlobalAveragePooling1D()(x) 
    x = layers.Dense(256, activation='relu', kernel_regularizer=regularizers.l2(0.01))(x)
    x = layers.Dropout(0.5)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    return models.Model(inputs, outputs)

# ==============================
# 4. 학습 실행 루프
# ==============================
X_raw, y_raw = load_dataset(DATA_ROOT)
le = LabelEncoder()
y_int = le.fit_transform(y_raw)
num_classes = len(le.classes_)
joblib.dump(le, os.path.join(MODEL_SAVE_DIR, "label_encoder.pkl"))
y_onehot = tf.keras.utils.to_categorical(y_int, num_classes=num_classes)

skf = StratifiedKFold(n_splits=K_FOLDS, shuffle=True, random_state=42)
accuracies = []

for fold_no, (train_idx, val_idx) in enumerate(skf.split(X_raw, y_int), 1):
    print(f"\n--- 🚀 Fold {fold_no} 시작 ---")
    X_train, X_val = X_raw[train_idx], X_raw[val_idx]
    y_train, y_val = y_onehot[train_idx], y_onehot[val_idx]
    
    if USE_AUGMENTATION:
        X_train, y_train = apply_3d_augmentation(X_train, y_train)
        print(f"✅ 증강 완료: {len(X_train)} 샘플")
    
    model = build_model(num_classes)
    model.compile(optimizer=optimizers.Adam(1e-3), 
                  loss='categorical_crossentropy', 
                  metrics=['accuracy'])
    
    checkpoint = tf.keras.callbacks.ModelCheckpoint(
        os.path.join(MODEL_SAVE_DIR, f"yolo_3d_fold_{fold_no}.h5"), 
        save_best_only=True, monitor='val_accuracy'
    )

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS, batch_size=BATCH_SIZE,
        callbacks=[checkpoint],
        verbose=1
    )
    accuracies.append(max(history.history['val_accuracy']))

print(f"\n🏆 최종 평균 정확도: {np.mean(accuracies):.4f}")
