import os
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers, regularizers
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib

# ==============================
# 1. 설정 및 하이퍼파라미터
# ==============================
DATA_ROOT = r"C:\Users\kccistc\Desktop\workspace\project\dataset" 
MAX_FRAMES = 60   
NUM_JOINTS = 13   # Nose 다시 포함 (안정성 유지)
CHANNELS = 6      # x,y,z + dx,dy,dz
BATCH_SIZE = 32   
EPOCHS = 300      # 학습률이 낮으므로 Epoch를 조금 더 늘림

# ==============================
# 2. 유연한 데이터 로더 (컬럼명 자동 인식)
# ==============================
def robust_preprocess(df):
    # 컬럼 패턴 매칭
    x_cols = [c for c in df.columns if '_x' in c.lower()][:NUM_JOINTS]
    y_cols = [c for c in df.columns if '_y' in c.lower()][:NUM_JOINTS]
    z_cols = [c for c in df.columns if '_z' in c.lower()][:NUM_JOINTS]
    v_cols = [c for c in df.columns if '_v' in c.lower() or '_vis' in c.lower()][:NUM_JOINTS]

    coords = np.stack([df[x_cols].values, df[y_cols].values, df[z_cols].values], axis=-1)
    vis = df[v_cols].values

    # 골반 중심 이동 (Hip-Centered)
    # 7, 8번 관절을 골반으로 가정 (Nose 포함 기준)
    hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
    for f in range(coords.shape[0]):
        coords[f] -= hip_center[f]

    # 이동량(Delta) 계산
    deltas = np.diff(coords, axis=0, prepend=coords[0:1, :, :])
    
    # 💡 가중치 적용: 0으로 만들지 않고, 델타에만 신뢰도를 곱해 '불확실한 움직임' 억제
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
            except Exception as e:
                pass # 에러 파일 무시
                
    return np.array(x_data, dtype='float32'), np.array(y_labels)

# ==============================
# 3. 모델 및 학습 (LR: 1e-4 고정 후 막판에 감쇠)
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

X, y = load_pitching_dataset(DATA_ROOT)
le = LabelEncoder()
y_encoded = le.fit_transform(y)

X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.20, stratify=y_encoded, random_state=42)

model = build_model(len(le.classes_))

# 학습률을 1e-4로 조금 더 유지하다가 1e-5로 떨어지도록 alpha 조정
lr_schedule = optimizers.schedules.CosineDecay(1e-4, EPOCHS * (len(X_train)//BATCH_SIZE), alpha=0.1)

model.compile(optimizer=optimizers.Adam(lr_schedule), loss='sparse_categorical_crossentropy', metrics=['accuracy'])

print("🚀 다시 성능을 올리기 위한 재학습 시작...")
model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=EPOCHS, batch_size=BATCH_SIZE)
