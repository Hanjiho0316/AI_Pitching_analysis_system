import os
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers, regularizers
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
import joblib
import matplotlib.pyplot as plt
plt.switch_backend('Agg')

# ==============================
# 1. 설정 및 하이퍼파라미터
# ==============================
DATA_ROOT = r"C:\Users\kccistc\Documents\project\pitch_clips\yolo_exp" 
MAX_FRAMES = 60    
NUM_JOINTS = 13

# mediapipe -> yolov8n (no z on yolo)
# Channels: 6 -> 4
CHANNELS = 4        

BATCH_SIZE = 64   
EPOCHS = 300
K_FOLDS = 5

# 필요시 True 로 변경
USE_AUGMENTATION = False   # True: 데이터 증강 사용, False: 원본 데이터만 사용

MODEL_SAVE_DIR = r"C:\Users\kccistc\Documents\project\pitch_clips\yolo_exp"

if not os.path.exists(MODEL_SAVE_DIR):
    os.makedirs(MODEL_SAVE_DIR)

# ==============================
# 2. 데이터 증강 함수 (Hard Augmentation)
# ==============================
def augment_pitching_data_hard(X, y):
    augmented_X = [X]
    augmented_y = [y]

    # 필요하지 않은 증강은 코멘트아웃으로 제외시킬 수 잇음
    # 1. 가우시안 노이즈 
    noise = np.random.normal(0, 0.015, X.shape) # (강도 0.015)
    augmented_X.append(X + noise)
    augmented_y.append(y)

    # 2. 무작위 회전 (y축 기준 ±10도)
    # -> 삭제 (z축 없음), 기록용으로 코멘트 아웃
    # def rotate_y(batch, angle_deg):
    #     angle_rad = np.radians(angle_deg)
    #     cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
    #     new_batch = batch.copy()
    #     new_batch[..., 0] = batch[..., 0] * cos_a - batch[..., 2] * sin_a
    #     new_batch[..., 2] = batch[..., 0] * sin_a + batch[..., 2] * cos_a
    #     return new_batch

    # rotated_X = rotate_y(X, np.random.uniform(-10, 10))
    # augmented_X.append(rotated_X)
    # augmented_y.append(y)

    # 3. 무작위 스케일링 
    scales = np.random.uniform(0.8, 1.2, (len(X), 1, 1, 1)) # (80% ~ 120%)
    scaled_X = X * scales
    augmented_X.append(scaled_X)
    augmented_y.append(y)
    
    # # 4. 시간축 보간
    interpolated_X = np.zeros_like(X)
    for i in range(len(X)):
        for f in range(MAX_FRAMES - 1):
            interpolated_X[i, f] = (X[i, f] + X[i, f+1]) / 2
        interpolated_X[i, -1] = X[i, -1]
    augmented_X.append(interpolated_X)
    augmented_y.append(y)

    # 5. 랜덤 관절 마스킹
    masked_X = X.copy()
    for i in range(len(masked_X)):
        joints_to_mask = np.random.choice(NUM_JOINTS, 2, replace=False)
        masked_X[i, :, joints_to_mask, :] = 0
    augmented_X.append(masked_X)
    augmented_y.append(y)
    
    # 6. 랜덤 시간 이동
    shifted_X = np.zeros_like(X)
    for i in range(len(X)):
        shift = np.random.randint(-5, 6)
        if shift > 0:
            shifted_X[i, shift:] = X[i, :-shift]
        elif shift < 0:
            shifted_X[i, :shift] = X[i, -shift:]
        else:
            shifted_X[i] = X[i]
    augmented_X.append(shifted_X)
    augmented_y.append(y)
    
    # 7. 타임 워핑
    warped_X = np.zeros_like(X)
    for i in range(len(X)):
        indices = np.sort(np.random.uniform(0, MAX_FRAMES - 1, MAX_FRAMES))
        for j in range(NUM_JOINTS):
            for c in range(CHANNELS):
                warped_X[i, :, j, c] = np.interp(
                    np.arange(MAX_FRAMES), indices, X[i, :, j, c])
    augmented_X.append(warped_X)
    augmented_y.append(y)
    
    # 8. combined augmentation
    alpha = 0.2
    lam = np.random.beta(alpha, alpha, size=(len(X), 1, 1, 1))
    shuffle_idx = np.random.permutation(len(X))
    mixed_X = lam * X + (1 - lam) * X[shuffle_idx]
    mixed_y = lam.reshape(-1, 1) * y + (1 - lam.reshape(-1, 1)) * y[shuffle_idx]
    augmented_X.append(mixed_X)
    augmented_y.append(mixed_y)
    
    return np.concatenate(augmented_X, axis=0), np.concatenate(augmented_y, axis=0)
    
# ==============================
# 3. 데이터 로더 및 전처리
# ==============================
def robust_preprocess(df):
    x_cols = [c for c in df.columns if '_x' in c.lower()][:NUM_JOINTS]
    y_cols = [c for c in df.columns if '_y' in c.lower()][:NUM_JOINTS]
    conf_cols = [c for c in df.columns if '_conf' in c.lower()][:NUM_JOINTS]

    # Extractx xyz coords & confidence for 13 joints
    # then list thme up
    coords = np.stack([df[x_cols].values, df[y_cols].values], axis=-1)  # (frames, joints, 2)
    conf = df[conf_cols].values  # (frames, joints)
    
    # hip-centering
    # --> midpoint of left & right hip then subtracts it from all joints in every frame
    #     --> position invariant (removes effect from differenct camera positions)
    hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
    for f in range(coords.shape[0]):
        coords[f] -= hip_center[f]

    # delta = frame-to-frame velocity
    deltas = np.diff(coords, axis=0, prepend=coords[0:1, :, :])
    # masked by visibility --> missing joints dont produce false delta
    deltas *= np.expand_dims(conf, axis=-1)

    # concatenates coordinates & deltas --> 4 channels per joints
    return np.concatenate([coords, deltas], axis=-1)  # (frames, joints, 4)

def load_pitching_dataset(root_path):
    x_data, y_labels = [], []
    pitcher_folders = sorted([d for d in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, d))])

    # iterates through each pitcher's susfolder, reads csv files
    for folder_name in pitcher_folders:
        class_dir = os.path.join(root_path, folder_name)
        csv_files = [f for f in os.listdir(class_dir) if f.endswith('.csv')]
        for file in csv_files:
            try:
                # skips files that are too short ( < 15frames )
                df = pd.read_csv(os.path.join(class_dir, file)).fillna(0)
                if len(df) < 15: continue

                # apply preprocess
                combined = robust_preprocess(df)
                if len(combined) > MAX_FRAMES: combined = combined[:MAX_FRAMES]
                else:
                    pad = np.zeros((MAX_FRAMES - len(combined), NUM_JOINTS, CHANNELS))
                    combined = np.vstack([combined, pad])
                x_data.append(combined)
                y_labels.append(folder_name)
            except: pass

    # return all samples as "numpy array & pitcher name" as labels
    return np.array(x_data, dtype='float32'), np.array(y_labels)

# ==============================
# 4. 모델 빌드 (적정 깊이 유지 + 규제 강화)
# ==============================
def build_model(num_classes):

    # defines input shape,
    # tells which shpae of data (60 frame, 13 joints, 4 channels) is coming in
    inputs = layers.Input(shape=(MAX_FRAMES, NUM_JOINTS, CHANNELS))

    # flatten last two dimensions from (60, 13, 4) --> (60, 52)
    # why? conv1D expects 2D input
    x = layers.Reshape((MAX_FRAMES, NUM_JOINTS * CHANNELS))(inputs)
    
    # Conv Block 1
    #     256 convolutional filters
    #     3 kernels --> detects local temporal pattern over 3 frames
    #     padding = 'same' --> input length == output length
    #     Relu
    #     l2 = 0.05 (preventing overfitting)
    x = layers.Conv1D(256, kernel_size=3, padding='same', activation='relu',
                  kernel_regularizer=regularizers.l2(0.05))(x)
    
    x = layers.BatchNormalization()(x)
    x = layers.SpatialDropout1D(0.3)(x) # 프레임 단위 규제
    x = layers.MaxPooling1D(2)(x)
    
    # Conv Block 2
    x = layers.Conv1D(128, kernel_size=3, padding='same', activation='relu',
                  kernel_regularizer=regularizers.l2(0.05))(x)
    x = layers.BatchNormalization()(x)  
    
    # Conv Block 3
    x = layers.Conv1D(64, kernel_size=3, padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)
    
    x = layers.GlobalAveragePooling1D()(x) # 뽑은 feature를 평균값내서 보냄, 제일 마지막에 있어야됨
    
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    
    return models.Model(inputs, outputs)

# ==============================
# 5. 실행부 (K-Fold & One-hot & Label Smoothing)
# ==============================
X_raw, y_raw = load_pitching_dataset(DATA_ROOT)
le = LabelEncoder()
y_int = le.fit_transform(y_raw)
num_classes = len(le.classes_)

# LabelEncoder 저장
joblib.dump(le, os.path.join(MODEL_SAVE_DIR, "label_encoder.pkl"))

# One-hot 인코딩 변환 (for Label Smoothing)
y_onehot = tf.keras.utils.to_categorical(y_int, num_classes=num_classes)

# splits data into N folds
skf = StratifiedKFold(n_splits=K_FOLDS, shuffle=True, random_state=42)
fold_no = 1
accuracies = []

all_histories = []  # 학습 히스토리 저장
for train_index, val_index in skf.split(X_raw, y_int):
    print(f"\n--- 🚀 Fold {fold_no} / {K_FOLDS} 학습 시작 ---")
    
    X_train_fold, X_val = X_raw[train_index], X_raw[val_index]
    y_train_fold, y_val = y_onehot[train_index], y_onehot[val_index]
    
    # 데이터 증강 (Train 데이터에만, USE_AUGMENTATION 플래그에 따라)
    if USE_AUGMENTATION:
        X_train_aug, y_train_aug = augment_pitching_data_hard(X_train_fold, y_train_fold)
        print(f"증강 완료: {len(X_train_fold)} -> {len(X_train_aug)}개")
    else:
        X_train_aug, y_train_aug = X_train_fold, y_train_fold
        print(f"증강 미사용: {len(X_train_aug)}개 (원본 데이터)")
    
    model = build_model(num_classes)
    
    lr_schedule = optimizers.schedules.CosineDecay(
        3e-4, EPOCHS * (len(X_train_aug)//BATCH_SIZE), alpha=0.05
    )
    
    model.compile(
        optimizer=optimizers.Adam(lr_schedule), 
        # CategoricalCrossentropy에 label_smoothing 적용
        loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1), 
        metrics=['accuracy']
    )
    
    model_path = os.path.join(MODEL_SAVE_DIR, f"best_model_fold_{fold_no}.h5")
    checkpoint = tf.keras.callbacks.ModelCheckpoint(
        model_path, monitor='val_accuracy', verbose=0, save_best_only=True, mode='max'
    )
    
    # 과적합 방지를 위한 조기 종료 추가
    early_stop = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=200, restore_best_weights=True)

    history = model.fit(
        X_train_aug, y_train_aug,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=[checkpoint, early_stop],
        verbose=1
    )
    max_val_acc = max(history.history['val_accuracy'])
    accuracies.append(max_val_acc)
    print(f"✅ Fold {fold_no} 완료! 최고 검증 정확도: {max_val_acc:.4f}")
    
    fold_no += 1
    all_histories.append(history.history)

# ==============================
# 6. Loss vs Train graph
# ==============================
plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
for i, h in enumerate(all_histories):
    plt.plot(h['val_loss'], label=f'Fold {i+1}')
plt.title('Val Loss Across Folds')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

plt.subplot(1, 2, 2)
for i, h in enumerate(all_histories):
    plt.plot(h['val_accuracy'], label=f'Fold {i+1}')
plt.title('Val Accuracy Across Folds')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()

plt.tight_layout()
plt.savefig('all_folds_summary.png', dpi=150)
plt.show()

print("\n" + "="*50)
skip = 100
print(f"🏆 {K_FOLDS}-Fold 교차 검증 최종 결과")
avg_acc = np.mean(history.history['accuracy'][skip:])
avg_val_acc = np.mean(history.history['val_accuracy'][skip:])
avg_loss = np.mean(history.history['loss'][skip:])
avg_val_loss = np.mean(history.history['val_loss'][skip:])
print(f"average acc = {avg_acc:.4f}")
print(f"average val acc = {avg_val_acc:.4f}")
print(f"average loss = {avg_loss:.4f}")
print(f"average val loss = {avg_val_loss:.4f}")

print("="*50)

# ==============================
# 7. 추론용 최종 모델 & 설정 저장
# ==============================

# 가장 val_accuracy가 높은 fold의 모델을 최종 모델로 선택
best_fold = int(np.argmax(accuracies)) + 1
best_model_path = os.path.join(MODEL_SAVE_DIR, f"best_model_fold_{best_fold}.h5")
best_model = tf.keras.models.load_model(best_model_path)

# 최종 모델 저장 (.h5 + SavedModel 두 형식)
final_h5_path = os.path.join(MODEL_SAVE_DIR, "final_model.h5")
final_sm_path = os.path.join(MODEL_SAVE_DIR, "final_savedmodel")
best_model.save(final_h5_path)
best_model.save(final_sm_path)

# 추론에 필요한 설정값 저장
import json
inference_config = {
    "MAX_FRAMES": MAX_FRAMES,
    "NUM_JOINTS": NUM_JOINTS,
    "CHANNELS": CHANNELS,
    "num_classes": num_classes,
    "best_fold": best_fold,
    "best_val_accuracy": float(np.max(accuracies)),
    "class_names": le.classes_.tolist(),
}
config_path = os.path.join(MODEL_SAVE_DIR, "inference_config.json")
with open(config_path, "w", encoding="utf-8") as f:
    json.dump(inference_config, f, ensure_ascii=False, indent=2)

print(f"\n📦 추론용 저장 완료!")
print(f"  - 최종 모델 (h5):       {final_h5_path}")
print(f"  - 최종 모델 (SavedModel): {final_sm_path}")
print(f"  - LabelEncoder:          {os.path.join(MODEL_SAVE_DIR, 'label_encoder.pkl')}")
print(f"  - 설정 파일:             {config_path}")
print(f"  - 선택된 Fold: {best_fold} (val_acc: {np.max(accuracies):.4f})")
