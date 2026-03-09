import os
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers, regularizers
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
import joblib

# ==============================
# 1. 설정 및 하이퍼파라미터
# ==============================
DATA_ROOT = r"C:\Users\kccistc\Desktop\workspace\project\dataset" 
MAX_FRAMES = 60    
NUM_JOINTS = 13   
CHANNELS = 6       
BATCH_SIZE = 32   
EPOCHS = 300      
K_FOLDS = 5  # K-Fold 설정
MODEL_SAVE_DIR = "saved_models"

if not os.path.exists(MODEL_SAVE_DIR):
    os.makedirs(MODEL_SAVE_DIR)

# ==============================
# 2. 유연한 데이터 로더 (기존 로직 유지)
# ==============================
def robust_preprocess(df):
    x_cols = [c for c in df.columns if '_x' in c.lower()][:NUM_JOINTS]
    y_cols = [c for c in df.columns if '_y' in c.lower()][:NUM_JOINTS]
    z_cols = [c for c in df.columns if '_z' in c.lower()][:NUM_JOINTS]
    v_cols = [c for c in df.columns if '_v' in c.lower() or '_vis' in c.lower()][:NUM_JOINTS]

    coords = np.stack([df[x_cols].values, df[y_cols].values, df[z_cols].values], axis=-1)
    vis = df[v_cols].values

    # 골반 중심 이동
    hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
    for f in range(coords.shape[0]):
        coords[f] -= hip_center[f]

    deltas = np.diff(coords, axis=0, prepend=coords[0:1, :, :])
    deltas *= np.expand_dims(vis, axis=-1)

    return np.concatenate([coords, deltas], axis=-1)

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
                if len(combined) > MAX_FRAMES: combined = combined[:MAX_FRAMES]
                else:
                    pad = np.zeros((MAX_FRAMES - len(combined), NUM_JOINTS, CHANNELS))
                    combined = np.vstack([combined, pad])
                x_data.append(combined)
                y_labels.append(folder_name)
            except: pass
    return np.array(x_data, dtype='float32'), np.array(y_labels)

# ==============================
# 3. 모델 빌드 함수
# ==============================
def build_model(num_classes):
    inputs = layers.Input(shape=(MAX_FRAMES, NUM_JOINTS, CHANNELS))
    x = layers.Reshape((MAX_FRAMES, NUM_JOINTS * CHANNELS))(inputs)
    
    x = layers.Conv1D(256, kernel_size=3, padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling1D(2)(x)
    
    x = layers.Conv1D(256, kernel_size=3, padding='same', activation='relu')(x)
    x = layers.GlobalAveragePooling1D()(x)
    
    x = layers.Dense(128, activation='relu', kernel_regularizer=regularizers.l2(0.01))(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    
    return models.Model(inputs, outputs)

# ==============================
# 4. 데이터 로드 및 K-Fold 학습 시작
# ==============================
X, y = load_pitching_dataset(DATA_ROOT)
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# LabelEncoder 저장 (나중에 예측할 때 필요)
joblib.dump(le, os.path.join(MODEL_SAVE_DIR, "label_encoder.pkl"))

# Stratified K-Fold 설정 (클래스 비율 유지)
skf = StratifiedKFold(n_splits=K_FOLDS, shuffle=True, random_state=42)

fold_no = 1
accuracies = []

for train_index, val_index in skf.split(X, y_encoded):
    print(f"\n--- 🚀 Fold {fold_no} / {K_FOLDS} 학습 시작 ---")
    
    X_train, X_val = X[train_index], X[val_index]
    y_train, y_val = y_encoded[train_index], y_encoded[val_index]
    
    model = build_model(len(le.classes_))
    
    # 학습률 스케줄러 (각 폴드마다 초기화)
    lr_schedule = optimizers.schedules.CosineDecay(
        1e-4, EPOCHS * (len(X_train)//BATCH_SIZE), alpha=0.1
    )
    
    model.compile(optimizer=optimizers.Adam(lr_schedule), 
                  loss='sparse_categorical_crossentropy', 
                  metrics=['accuracy'])
    
    # 모델 체크포인트 설정: 각 폴드에서 가장 좋은 모델 저장
    model_path = os.path.join(MODEL_SAVE_DIR, f"best_model_fold_{fold_no}.h5")
    checkpoint = tf.keras.callbacks.ModelCheckpoint(
        model_path, monitor='val_accuracy', verbose=0, save_best_only=True, mode='max'
    )

    history = model.fit(
        X_train, y_train, 
        validation_data=(X_val, y_val), 
        epochs=EPOCHS, 
        batch_size=BATCH_SIZE,
        callbacks=[checkpoint],
        verbose=1
    )
    
    # 검증 정확도 기록
    max_val_acc = max(history.history['val_accuracy'])
    accuracies.append(max_val_acc)
    print(f"✅ Fold {fold_no} 완료! 최고 검증 정확도: {max_val_acc:.4f}")
    
    fold_no += 1

# ==============================
# 5. 최종 결과 리포트
# ==============================
print("\n" + "="*50)
print(f"🏆 {K_FOLDS}-Fold 교차 검증 최종 결과")
print(f"평균 정확도: {np.mean(accuracies):.4f} (+/- {np.std(accuracies):.4f})")
print(f"모델 저장 경로: {os.path.abspath(MODEL_SAVE_DIR)}")
print("="*50)
