####
## 학습 코드
####
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers, regularizers
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import f1_score  # F1 Score 계산용
import joblib
import random
import csv

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
# 1. 하이퍼파라미터
# ==============================
DATA_ROOT = r"C:\Users\kccistc\Desktop\workspace\project\batter_output_results"
MAX_FRAMES = 60    
NUM_JOINTS = 13   
CHANNELS = 6      
BATCH_SIZE = 64  
EPOCHS = 1000     
K_FOLDS = 5  
MODEL_SAVE_DIR = "saved_models_final"
final_h5_path = os.path.join(MODEL_SAVE_DIR, "final_best_model.h5")

if not os.path.exists(MODEL_SAVE_DIR): os.makedirs(MODEL_SAVE_DIR)

# ==============================
# 2. 커스텀 로그 콜백 (F1-Score 포함)
# ==============================
class FoldLogger(tf.keras.callbacks.Callback):
    def __init__(self, fold_no, val_data, log_dir):
        super().__init__()
        self.fold_no = fold_no
        self.X_val, self.y_val = val_data
        self.log_path = os.path.join(log_dir, f"fold_{fold_no}_epoch_logs.csv")
        
        with open(self.log_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['epoch', 'loss', 'accuracy', 'val_loss', 'val_accuracy', 'val_f1_score'])

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        # 검증 데이터 예측 및 F1 계산
        val_pred = self.model.predict(self.X_val, verbose=0)
        val_pred_labels = np.argmax(val_pred, axis=1)
        val_true_labels = np.argmax(self.y_val, axis=1)
        f1 = f1_score(val_true_labels, val_pred_labels, average='weighted')
        
        row = [
            epoch + 1,
            f"{logs.get('loss', 0):.4f}",
            f"{logs.get('accuracy', 0):.4f}",
            f"{logs.get('val_loss', 0):.4f}",
            f"{logs.get('val_accuracy', 0):.4f}",
            f"{f1:.4f}"
        ]

        with open(self.log_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)
        
        print(f" - val_f1_score: {f1:.4f}")

# ==============================
# 3. 데이터 로드 및 전처리
# ==============================
def apply_3d_augmentation(X, y):
    aug_X, aug_y = [X], [y]
    aug_X.append(X + np.random.normal(0, 0.003, X.shape))
    aug_y.append(y)
    def rotate_y(batch, angle_deg):
        rad = np.radians(angle_deg)
        c, s = np.cos(rad), np.sin(rad)
        nb = batch.copy()
        nb[..., 0] = batch[..., 0] * c - batch[..., 2] * s
        nb[..., 2] = batch[..., 0] * s + batch[..., 2] * c
        return nb
    aug_X.append(rotate_y(X, np.random.uniform(-15, 15)))
    aug_y.append(y)
    return np.concatenate(aug_X, axis=0).astype('float32'), np.concatenate(aug_y, axis=0).astype('float32')

def robust_preprocess_yolo_with_z(df):
    x_cols = [c for c in df.columns if '_x' in c.lower()][:NUM_JOINTS]
    y_cols = [c for c in df.columns if '_y' in c.lower()][:NUM_JOINTS]
    conf_cols = [c for c in df.columns if '_conf' in c.lower()][:NUM_JOINTS]
    coords_2d = np.stack([df[x_cols].values, df[y_cols].values], axis=-1) 
    hip_l, hip_r = coords_2d[:, 7, :], coords_2d[:, 8, :]
    hip_widths = np.linalg.norm(hip_l - hip_r, axis=1)
    avg_width = np.mean(hip_widths) if np.mean(hip_widths) > 0 else 0.1
    z_pseudo = np.tile((avg_width / (hip_widths + 1e-6))[:, np.newaxis, np.newaxis], (1, NUM_JOINTS, 1))
    coords_3d = np.concatenate([coords_2d, z_pseudo], axis=-1)
    hip_center = (coords_3d[:, 7, :] + coords_3d[:, 8, :]) / 2
    for f in range(coords_3d.shape[0]): coords_3d[f] -= hip_center[f]
    deltas_3d = np.diff(coords_3d, axis=0, prepend=coords_3d[0:1, :, :])
    conf_exp = np.expand_dims(df[conf_cols].values, axis=-1)
    return np.concatenate([coords_3d * conf_exp, deltas_3d * conf_exp], axis=-1)

def load_dataset(root_path):
    final_x, final_y = [], []
    folders = sorted([d for d in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, d))])
    for folder in folders:
        path = os.path.join(root_path, folder)
        for f in os.listdir(path):
            if not f.endswith('.csv'): continue
            df = pd.read_csv(os.path.join(path, f)).fillna(0)
            if len(df) < 15: continue
            proc = robust_preprocess_yolo_with_z(df)
            if len(proc) > MAX_FRAMES: proc = proc[:MAX_FRAMES]
            else: proc = np.vstack([proc, np.zeros((MAX_FRAMES - len(proc), NUM_JOINTS, CHANNELS))])
            final_x.append(proc); final_y.append(folder)
    return np.array(final_x, dtype='float32'), np.array(final_y)

# ==============================
# 4. 모델 아키텍처
# ==============================
def build_model(num_classes):
    inputs = layers.Input(shape=(MAX_FRAMES, NUM_JOINTS, CHANNELS))
    x = layers.Reshape((MAX_FRAMES, NUM_JOINTS * CHANNELS))(inputs)
    
    x = layers.Conv1D(256, 3, padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    
    res = x
    x = layers.Conv1D(256, 3, padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.SpatialDropout1D(0.3)(x)
    x = layers.Conv1D(256, 3, padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Add()([res, x])
    x = layers.Activation('relu')(x)
    
    x = layers.MaxPooling1D(2)(x)
    x = layers.Conv1D(128, 3, padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.GlobalAveragePooling1D()(x) 
    
    x = layers.Dense(256, activation='relu', kernel_regularizer=regularizers.l2(0.005))(x)
    x = layers.Dropout(0.5)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    
    return models.Model(inputs, outputs)

# ==============================
# 5. K-Fold 학습 실행
# ==============================
X_raw, y_raw = load_dataset(DATA_ROOT)
le = LabelEncoder()
y_int = le.fit_transform(y_raw)
num_classes = len(le.classes_)
joblib.dump(le, os.path.join(MODEL_SAVE_DIR, "label_encoder.pkl"))
y_onehot = tf.keras.utils.to_categorical(y_int, num_classes=num_classes)

skf = StratifiedKFold(n_splits=K_FOLDS, shuffle=True, random_state=42)
global_best_acc = 0.0

for fold_no, (train_idx, val_idx) in enumerate(skf.split(X_raw, y_int), 1):
    print(f"\n🚀 --- FOLD {fold_no} / {K_FOLDS} 학습 시작 ---")
    X_train, X_val = X_raw[train_idx], X_raw[val_idx]
    y_train, y_val = y_onehot[train_idx], y_onehot[val_idx]
    
    # 훈련 데이터 증강
    X_train_aug, y_train_aug = apply_3d_augmentation(X_train, y_train)
    
    model = build_model(num_classes)
    model.compile(optimizer=optimizers.Adam(2e-4), 
                  loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1), 
                  metrics=['accuracy'])
    
    ckpt_path = os.path.join(MODEL_SAVE_DIR, f"fold_{fold_no}.h5")
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(ckpt_path, save_best_only=True, monitor='val_accuracy'),
        tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=15, min_lr=5e-5, verbose=1),
        FoldLogger(fold_no, (X_val, y_val), MODEL_SAVE_DIR) # CSV 로그 저장
    ]
    
    history = model.fit(X_train_aug, y_train_aug, 
                        validation_data=(X_val, y_val), 
                        epochs=EPOCHS, 
                        batch_size=BATCH_SIZE, 
                        callbacks=callbacks, 
                        verbose=1)
    
    # 전체 폴드 중 가장 성능 좋은 모델 저장
    if max(history.history['val_accuracy']) > global_best_acc:
        global_best_acc = max(history.history['val_accuracy'])
        model.load_weights(ckpt_path)
        model.save(final_h5_path)
        print(f"⭐ Global Best Model Updated (Fold {fold_no})")

print("\n--- 모든 학습 프로세스 종료 ---")
print(f"✅ 최고 정확도: {global_best_acc:.4f}")
print(f"📂 모델 및 로그 저장 위치: {os.path.abspath(MODEL_SAVE_DIR)}")