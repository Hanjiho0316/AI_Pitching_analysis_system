# Model Description

이 디렉토리는 **AI Pitching Analysis System**에서 사용하는 모델 관련 코드와 구조를 관리하는 폴더입니다.
투수와 타자의 동작 분석을 위해 모델을 **pitcher**와 **hitter** 두 영역으로 분리하여 구성했습니다.

각 영역은 다음과 같은 기능을 포함합니다.

* 스켈레톤 기반 관절 좌표 추출
* 데이터 전처리
* 모델 학습
* 모델 검증

---

# Directory Structure

```
model
├ pitcher
│   ├ pitcher_learning
│   ├ pitcher_modelcheck
│   ├ LRchanger
│   └ video_analyze_iteration_pitcher
│
└ hitter
    ├ hitter_learning
    ├ hitter_detection
    ├ LRchanger
    └ video_extract_hitter
```

---

# Pitcher Model

투수의 투구 동작 분석을 위한 모델 코드가 포함되어 있습니다.

### pitcher_learning

투수 동작 데이터를 이용하여 **투구 분석 모델을 학습하는 코드**입니다.

### pitcher_modelcheck

학습된 모델의 **성능을 검증하고 테스트하는 코드**입니다.

### LRchanger

좌투수와 우투수 데이터를 통일하기 위해 **스켈레톤 좌표를 좌우 반전하는 전처리 코드**입니다.

### video_analyze_iteration_pitcher

폴더 내 **mp4 영상을 입력받아 스켈레톤 기반 관절 좌표 데이터를 추출하는 코드**입니다.

---

# Hitter Model

타자의 스윙 동작 분석을 위한 모델 코드가 포함되어 있습니다.

### hitter_learning

타자 스윙 데이터를 이용하여 **타격 동작 분석 모델을 학습하는 코드**입니다.

### hitter_detection

타자의 **스윙 동작을 탐지하거나 모델 성능을 검증하는 코드**입니다.

### LRchanger

좌타자와 우타자의 스윙 데이터를 통일하기 위한 **좌우 반전 전처리 코드**입니다.

### video_extract_hitter

폴더 내 **mp4 영상을 분석하여 스켈레톤 기반 관절 좌표 데이터를 추출하는 코드**입니다.

---

# Model Pipeline

전체 모델 파이프라인은 다음과 같은 순서로 동작합니다.

```
Video Input
   ↓
Player Detection
   ↓
Pose Estimation (Skeleton Extraction)
   ↓
Data Preprocessing (LRchanger)
   ↓
Model Training
   ↓
Model Evaluation
```

---

# Example Result

## Skeleton Detection Example

투수 영상을 입력하면 스켈레톤 랜드마크가 추출되고 투구 동작이 자동으로 감지됩니다.

![Pitch Skeleton Demo](images/pitch_demo.gif)

---