import os
import sys

# ==============================
# 0. GPU DLL 경로 강제 지정 (가장 중요)
# ==============================
# 아나콘다 가상환경 내의 CUDA/cuDNN 라이브러리 경로를 파이썬에 직접 추가합니다.
conda_env_path = os.environ.get('CONDA_PREFIX')
if conda_env_path:
    # 가상환경 내의 Library\bin 폴더에 DLL 파일들이 들어있습니다.
    dll_path = os.path.join(conda_env_path, 'Library', 'bin')
    if os.path.exists(dll_path):
        os.add_dll_directory(dll_path)
        print(f"✅ DLL 경로 추가 완료: {dll_path}")

import os
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers, regularizers, callbacks
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
import joblib

# ==============================
# 0. GPU 설정 및 환경 최적화
# ==============================
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f"✅ GPU 가동 준비 완료: {gpus[0].name}")
    except RuntimeError as e:
        print(f"❌ GPU 설정 오류: {e}")

# ==============================
# 1. 설정 및 하이퍼파라미터
# ==============================
DATA_ROOT = r"C:\Users\kccistc\Desktop\workspace\project\dataset" 
MAX_FRAMES = 60
NUM_JOINTS = 13
CHANNELS = 6 
BATCH_SIZE = 64
EPOCHS = 3000
K_FOLDS = 5
MODEL_SAVE_DIR = "saved_models"
LOG_DIR = "logs"

USE_AUGMENTATION = True

if not os.path.exists(MODEL_SAVE_DIR): os.makedirs(MODEL_SAVE_DIR)
if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)

# ==============================
# 2. 강력한 데이터 증강 함수 (float32 보정)
# ==============================
def augment_pitching_data_hard(X, y):
    if not USE_AUGMENTATION: return X, y

    augmented_X, augmented_y = [X], [y]

    # 1. 가우시안 노이즈
    noise = np.random.normal(0, 0.015, X.shape).astype('float32')
    augmented_X.append(X + noise)
    augmented_y.append(y)

    # 2. 무작위 회전
    def rotate_y(batch, angle_deg):
        angle_rad = np.radians(angle_deg)
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        new_batch = batch.copy()
        new_batch[..., 0] = batch[..., 0] * cos_a - batch[..., 2] * sin_a
        new_batch[..., 2] = batch[..., 0] * sin_a + batch[..., 2] * cos_a
        return new_batch

    rotated_X = rotate_y(X, np.random.uniform(-13, 13)).astype('float32')
    augmented_X.append(rotated_X)
    augmented_y.append(y)

    # 3. 무작위 스케일링
    scales = np.random.uniform(0.85, 1.15, (len(X), 1, 1, 1)).astype('float32')
    scaled_X = (X * scales)
    augmented_X.append(scaled_X)
    augmented_y.append(y)

    # 4. 시간축 보간
    interpolated_X = np.zeros_like(X)
    for i in range(len(X)):
        for f in range(MAX_FRAMES - 1):
            interpolated_X[i, f] = (X[i, f] + X[i, f+1]) / 2
        interpolated_X[i, -1] = X[i, -1]
    augmented_X.append(interpolated_X.astype('float32'))
    augmented_y.append(y)

    return np.concatenate(augmented_X, axis=0), np.concatenate(augmented_y, axis=0)

# ==============================
# 3. 데이터 로더 및 전처리
# ==============================
def robust_preprocess(df):
    x_cols = [c for c in df.columns if '_x' in c.lower()][:NUM_JOINTS]
    y_cols = [c for c in df.columns if '_y' in c.lower()][:NUM_JOINTS]
    z_cols = [c for c in df.columns if '_z' in c.lower()][:NUM_JOINTS]
    v_cols = [c for c in df.columns if '_v' in c.lower() or '_vis' in c.lower()][:NUM_JOINTS]

    coords = np.stack([df[x_cols].values, df[y_cols].values, df[z_cols].values], axis=-1)
    vis = df[v_cols].values

    hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
    for f in range(coords.shape[0]):
        coords[f] -= hip_center[f]

    deltas = np.diff(coords, axis=0, prepend=coords[0:1, :, :])
    deltas *= np.expand_dims(vis, axis=-1)

    return np.concatenate([coords, deltas], axis=-1).astype('float32')

def load_pitching_dataset(root_path):
    x_data, y_labels = [], []
    pitcher_folders = sorted([d for d in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, d))])
    
    for folder_name in pitcher_folders:
        class_dir = os.path.join(root_path, folder_name)
        csv_files = [f for f in os.listdir(class_dir) if f.endswith('.csv')]
        for file in csv_files:
            try:
                df = pd.read_csv(os.path.join(class_dir, file)).fillna(0)
                if len(df) < 15: continue
                combined = robust_preprocess(df)
                
                if len(combined) > MAX_FRAMES: 
                    combined = combined[:MAX_FRAMES]
                else:
                    last_frame = combined[-1:]
                    padding_size = MAX_FRAMES - len(combined)
                    padding = np.tile(last_frame, (padding_size, 1, 1))
                    combined = np.vstack([combined, padding])
                
                x_data.append(combined)
                y_labels.append(folder_name)
            except: pass
    return np.array(x_data, dtype='float32'), np.array(y_labels)

# ==============================
# 4. 고성능 모델 빌드 (Inception + Residual)
# ==============================
def build_model(num_classes):
    # 입력: (60, 13, 6) -> (Time, Space, Channels)
    inputs = layers.Input(shape=(MAX_FRAMES, NUM_JOINTS, CHANNELS))
    
    # kernel_size=(3, 3)으로 시간(3프레임)과 공간(3개 관절)을 동시에 스캔
    x = layers.Conv2D(128, kernel_size=(5, 5), padding='same', activation='relu')(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.SpatialDropout2D(0.1)(x) 
    x = layers.MaxPooling2D(pool_size=(2, 1))(x) # 시간축만 줄여서 해상도 유지
    
    # Conv Block 2 (기존 Conv1D 128과 대응)
    x = layers.Conv2D(128, kernel_size=(5, 5), padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)  
    x = layers.Dropout(0.1)(x) 
    
    x = layers.Conv2D(128, kernel_size=(5, 5), padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)  
    x = layers.Dropout(0.1)(x) 
    # GAP2D: (H, W, C) -> (C,)로 압축
    x = layers.GlobalAveragePooling2D()(x)
    
    # Dense Block (기존 128 Dense와 대응)
    x = layers.Dense(64, activation='relu', kernel_regularizer=regularizers.l2(0.03))(x)
    x = layers.GaussianDropout(0.3)(x)
    
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    
    return models.Model(inputs, outputs)
# ==============================
# 5. 실행부 (GPU 가속 강제)
# ==============================
X_raw, y_raw = load_pitching_dataset(DATA_ROOT)
le = LabelEncoder()
y_int = le.fit_transform(y_raw)
num_classes = len(le.classes_)

joblib.dump(le, os.path.join(MODEL_SAVE_DIR, "label_encoder.pkl"))
y_onehot = tf.keras.utils.to_categorical(y_int, num_classes=num_classes).astype('float32')

skf = StratifiedKFold(n_splits=K_FOLDS, shuffle=True, random_state=42)
fold_no = 1
accuracies = []

# GPU 장치 안에서 학습 실행
with tf.device('/GPU:0'):
    for train_index, val_index in skf.split(X_raw, y_int):
        tf.keras.backend.clear_session()
        print(f"\n--- 🚀 Fold {fold_no} / {K_FOLDS} 학습 시작 ---")
        
        X_train_fold, X_val = X_raw[train_index], X_raw[val_index]
        y_train_fold, y_val = y_onehot[train_index], y_onehot[val_index]
        
        X_train_aug, y_train_aug = augment_pitching_data_hard(X_train_fold, y_train_fold)
        print(f"최종 학습 데이터 수: {len(X_train_aug)}개")
        
        model = build_model(num_classes)
        
        # 90% 이상을 위한 정교한 CosineDecay 설정
        lr_schedule = optimizers.schedules.CosineDecay(
            1e-4, EPOCHS * (len(X_train_aug)//BATCH_SIZE), alpha=0.1
        )
        
        model.compile(
            optimizer=optimizers.Adam(learning_rate=lr_schedule), 
            loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1), 
            metrics=['accuracy']
        )
        
        model_path = os.path.join(MODEL_SAVE_DIR, f"best_model_fold_{fold_no}.h5")
        checkpoint = callbacks.ModelCheckpoint(model_path, monitor='val_accuracy', save_best_only=True, mode='max', verbose=0)
        log_path = os.path.join(LOG_DIR, f"learning_log_fold_{fold_no}.csv")
        csv_logger = callbacks.CSVLogger(log_path, append=False)
        early_stop = callbacks.EarlyStopping(monitor='val_loss', patience=3000, restore_best_weights=True)

        history = model.fit(
            X_train_aug, y_train_aug, 
            validation_data=(X_val, y_val), 
            epochs=EPOCHS, 
            batch_size=BATCH_SIZE,
            callbacks=[checkpoint, csv_logger, early_stop],
            verbose=1
        )
        
        max_val_acc = max(history.history['val_accuracy'])  
        accuracies.append(max_val_acc)
        print(f"✅ Fold {fold_no} 완료! 최고 검증 정확도: {max_val_acc:.4f}")
        fold_no += 1

print("\n" + "="*50)
print(f"🏆 {K_FOLDS}-Fold 교차 검증 최종 결과")
print(f"평균 정확도: {np.mean(accuracies):.4f} (+/- {np.std(accuracies):.4f})")
print("="*50)
