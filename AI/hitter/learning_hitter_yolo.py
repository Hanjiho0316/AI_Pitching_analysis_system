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
# 1. 하이퍼파라미터 및 설정 (변수 정의 확인)
# ==============================
DATA_ROOT = r"C:\Users\kccistc\Desktop\workspace\project\batter_output_results"
MAX_FRAMES = 60    
NUM_JOINTS = 13   
CHANNELS = 6      
BATCH_SIZE = 128  
EPOCHS = 200      
K_FOLDS = 5  

# [중요] 누락되었던 변수 정의
USE_AUGMENTATION = True 
MODEL_SAVE_DIR = "saved_models_yolo_3d"
final_best_model_path = os.path.join(MODEL_SAVE_DIR, "final_best_yolo_3d_model.h5")

if not os.path.exists(MODEL_SAVE_DIR): 
    os.makedirs(MODEL_SAVE_DIR)

# ==============================
# 2. 전처리 및 증강 함수
# ==============================
def apply_3d_augmentation(X, y):
    aug_X, aug_y = [X], [y]
    # 미세 노이즈
    aug_X.append(X + np.random.normal(0, 0.005, X.shape))
    aug_y.append(y)
    
    # 가상 Y축 회전
    def rotate_y(batch, angle_deg):
        angle_rad = np.radians(angle_deg)
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        new_batch = batch.copy()
        new_batch[..., 0] = batch[..., 0] * cos_a - batch[..., 2] * sin_a
        new_batch[..., 2] = batch[..., 0] * sin_a + batch[..., 2] * cos_a
        return new_batch
    
    aug_X.append(rotate_y(X, np.random.uniform(-10, 10)))
    aug_y.append(y)
    
    X_final = np.concatenate(aug_X, axis=0)
    y_final = np.concatenate(aug_y, axis=0)
    indices = np.random.permutation(len(X_final))
    return X_final[indices].astype('float32'), y_final[indices].astype('float32')

def robust_preprocess_yolo_with_z(df):
    x_cols = [c for c in df.columns if '_x' in c.lower()][:NUM_JOINTS]
    y_cols = [c for c in df.columns if '_y' in c.lower()][:NUM_JOINTS]
    conf_cols = [c for c in df.columns if '_conf' in c.lower()][:NUM_JOINTS]
    
    coords_2d = np.stack([df[x_cols].values, df[y_cols].values], axis=-1) 
    conf = df[conf_cols].values 
    
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
    return np.concatenate([coords_3d * conf_exp, deltas_3d * conf_exp], axis=-1)

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
    final_x, final_y = [], []
    for label, data_list in temp_data.items():
        indices = np.random.choice(len(data_list), min_samples, replace=False)
        for idx in indices:
            final_x.append(data_list[idx])
            final_y.append(label)
    return np.array(final_x, dtype='float32'), np.array(final_y)

# ==============================
# 3. 모델 정의
# ==============================
def build_model(num_classes):
    inputs = layers.Input(shape=(MAX_FRAMES, NUM_JOINTS, CHANNELS))
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
# 4. 학습 실행 루프 (정의되지 않은 변수 해결)
# ==============================
X_raw, y_raw = load_dataset(DATA_ROOT)
le = LabelEncoder()
y_int = le.fit_transform(y_raw)
num_classes = len(le.classes_)
joblib.dump(le, os.path.join(MODEL_SAVE_DIR, "label_encoder.pkl"))
y_onehot = tf.keras.utils.to_categorical(y_int, num_classes=num_classes)

skf = StratifiedKFold(n_splits=K_FOLDS, shuffle=True, random_state=42)
accuracies = []
global_best_acc = 0.0
best_fold_num = 0

for fold_no, (train_idx, val_idx) in enumerate(skf.split(X_raw, y_int), 1):
    print(f"\n🚀 Fold {fold_no}/{K_FOLDS} 시작")
    X_train, X_val = X_raw[train_idx], X_raw[val_idx]
    y_train, y_val = y_onehot[train_idx], y_onehot[val_idx]
    
    if USE_AUGMENTATION:
        X_train, y_train = apply_3d_augmentation(X_train, y_train)
    
    model = build_model(num_classes)
    model.compile(optimizer=optimizers.Adam(1e-3), loss='categorical_crossentropy', metrics=['accuracy'])
    
    # 폴드별 임시 저장 경로
    temp_fold_path = os.path.join(MODEL_SAVE_DIR, f"temp_fold_{fold_no}.h5")
    checkpoint = tf.keras.callbacks.ModelCheckpoint(
        temp_fold_path, save_best_only=True, monitor='val_accuracy', mode='max', verbose=0
    )

    history = model.fit(
        X_train, y_train, validation_data=(X_val, y_val),
        epochs=EPOCHS, batch_size=BATCH_SIZE, callbacks=[checkpoint], verbose=1
    )
    
    current_fold_best = max(history.history['val_accuracy'])
    accuracies.append(current_fold_best)
    
    # 전체 최고 모델 갱신 로직
    if current_fold_best > global_best_acc:
        global_best_acc = current_fold_best
        best_fold_num = fold_no
        model.load_weights(temp_fold_path)
        model.save(final_best_model_path)
        print(f"🌟 글로벌 최고 모델 갱신! (Acc: {global_best_acc:.4f})")

# ==============================
# 5. 최종 결과 리포트
# ==============================
print("\n" + "="*50)
print("📊 [ 최종 학습 결과 리포트 ]")
print(f"1️⃣ 전체 폴드 평균 정확도: {np.mean(accuracies):.4f}")
print(f"2️⃣ 역대 최고 정확도 (Best): {global_best_acc:.4f} (Fold {best_fold_num})")
print(f"3️⃣ 최종 모델 저장 경로: {final_best_model_path}")
print("="*50)
