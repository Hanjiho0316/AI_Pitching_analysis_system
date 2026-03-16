import cv2
import numpy as np
import pandas as pd
import tensorflow as tf
import joblib
import json
import os
from ultralytics import YOLO

# ==============================
# Config
# ==============================
MODEL_PATH = "pitch_clips/yolo_exp/best_model_fold_4.h5"
ENCODER_PATH = "pitch_clips/yolo_exp/label_encoder.pkl"
CONFIG_PATH = "pitch_clips/yolo_exp/inference_config.json"
YOLO_MODEL_PATH = "yolov8n-pose.pt"

JOINT_INDICES = [0, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
JOINT_NAMES = ["NOSE", "L_SHOULDER", "R_SHOULDER", "L_ELBOW", "R_ELBOW",
               "L_WRIST", "R_WRIST", "L_HIP", "R_HIP", "L_KNEE", "R_KNEE", "L_ANKLE", "R_ANKLE"]
SMOOTHING_WINDOW = 5

# ==============================
# Load models once at startup
# ==============================
with open(CONFIG_PATH) as f:
    config = json.load(f)

MAX_FRAMES = config["MAX_FRAMES"]
NUM_JOINTS  = config["NUM_JOINTS"]
CHANNELS    = config["CHANNELS"]

model = tf.keras.models.load_model(MODEL_PATH)
le    = joblib.load(ENCODER_PATH)
yolo  = YOLO(YOLO_MODEL_PATH)

# ==============================
# Pose extraction (matches pitcher_extract_yolo.py)
# ==============================
def extract_pose_from_video(video_path):
    cap = cv2.VideoCapture(video_path)
    width  = int(cap.get(3))
    height = int(cap.get(4))

    ROI_X1, ROI_X2 = int(width * 0.3),  int(width * 0.65)
    ROI_Y1, ROI_Y2 = int(height * 0.3), int(height * 0.8)

    raw_data, pitcher_id, lost_frames = [], None, 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = yolo.track(frame, persist=True, conf=0.3, verbose=False)[0]
        frame_data = [np.nan] * (len(JOINT_INDICES) * 3)

        if results.boxes is not None and results.boxes.id is not None:
            ids   = results.boxes.id.cpu().numpy().astype(int)
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
                target_idx  = np.where(ids == pitcher_id)[0][0]
                points       = results.keypoints.data[target_idx].cpu().numpy()
                temp_data    = []
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
    df = df.interpolate(method='linear', limit_direction='both')
    coord_cols = [c for c in df.columns if '_x' in c or '_y' in c]
    df[coord_cols] = df[coord_cols].rolling(
        window=SMOOTHING_WINDOW, center=True, min_periods=1
    ).mean()

    return df

# ==============================
# Preprocess (compatible with YOLO CSV: x, y, conf — no z/vis)
# ==============================
# def preprocess(df):
#     x_cols    = [f"{n}_x"    for n in JOINT_NAMES]
#     y_cols    = [f"{n}_y"    for n in JOINT_NAMES]
#     conf_cols = [f"{n}_conf" for n in JOINT_NAMES]

#     coords = np.stack([
#         df[x_cols].values,
#         df[y_cols].values,
#         np.zeros((len(df), NUM_JOINTS))   # z = 0 (not available)
#     ], axis=-1)                            # (T, 13, 3)

#     vis = df[conf_cols].values             # (T, 13) — use conf as visibility proxy

#     # Hip-center normalization (joints 7=L_HIP, 8=R_HIP)
#     hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
#     for f in range(coords.shape[0]):
#         coords[f] -= hip_center[f]

#         combined = np.concatenate([coords, np.expand_dims(vis, axis=-1)], axis=-1)  # (T, 13, 4)

#     # Pad or trim to MAX_FRAMES
#     if len(combined) > MAX_FRAMES:
#         combined = combined[:MAX_FRAMES]
#     else:
#         pad = np.zeros((MAX_FRAMES - len(combined), NUM_JOINTS, CHANNELS))
#         combined = np.vstack([combined, pad])

#     return combined.astype('float32')
def preprocess(df):
    x_cols    = [f"{n}_x"    for n in JOINT_NAMES]
    y_cols    = [f"{n}_y"    for n in JOINT_NAMES]
    conf_cols = [f"{n}_conf" for n in JOINT_NAMES]

    coords = np.stack([df[x_cols].values, df[y_cols].values], axis=-1)  # (T, 13, 2)
    conf   = df[conf_cols].values                                         # (T, 13)

    hip_center = (coords[:, 7, :] + coords[:, 8, :]) / 2
    for f in range(coords.shape[0]):
        coords[f] -= hip_center[f]

    deltas = np.diff(coords, axis=0, prepend=coords[0:1])
    deltas *= np.expand_dims(conf, axis=-1)

    combined = np.concatenate([coords, deltas], axis=-1)  # (T, 13, 4)

    if len(combined) > MAX_FRAMES:
        combined = combined[:MAX_FRAMES]
    else:
        pad = np.zeros((MAX_FRAMES - len(combined), NUM_JOINTS, 4))
        combined = np.vstack([combined, pad])

    return combined.astype('float32')
# ==============================
# Predict
# ==============================
def predict(video_path):
    print(f"[1/3] Extracting pose from: {video_path}")
    df = extract_pose_from_video(video_path)

    print("[2/3] Preprocessing...")
    X = preprocess(df)
    X = np.expand_dims(X, axis=0)  # (1, 80, 13, 4)

    print("[3/3] Running inference...")
    probs = model.predict(X, verbose=0)[0]

    print("\n📊 All Results (sorted by confidence):")
    sorted_indices = np.argsort(probs)[::-1]
    for idx in sorted_indices:
        print(f"  {le.classes_[idx]:<30} {probs[idx]*100:5.1f}%")

    top1_idx = sorted_indices[0]
    return {"pitcher": le.classes_[top1_idx], "confidence": round(float(probs[top1_idx]) * 100, 1)}


if __name__ == "__main__":
    import sys
    video = sys.argv[1] if len(sys.argv) > 1 else "test.mp4"
    result = predict(video)
    print(f"\n🎯 Result: {result['pitcher']} ({result['confidence']}% confidence)")
