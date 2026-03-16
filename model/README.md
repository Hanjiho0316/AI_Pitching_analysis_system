# Model Description

이 디렉토리는 **AI Pitching Analysis System**에서 사용하는 모델 관련 코드와 구조를 관리하는 폴더입니다.
투수와 타자의 동작 분석을 위해 모델을 **pitcher / hitter** 두 영역으로 분리하여 구성했습니다.

---

# Directory Structure

```
model
├ pitcher
│   ├ pitcher_learning
│   ├ pitcher_modelcheck
│   └ video_extract_interpolation_pithcer
│
└ hitter
    ├ swing_model
    └ swing_analysis
```

---

# Pitcher Model

`pitcher` 폴더는 투수의 투구 동작을 분석하기 위한 모델 관련 코드가 포함되어 있습니다.

## 주요 기능

* 투수 객체 탐지
* 투수 추적 (tracking)
* 스켈레톤 기반 관절 좌표 추출
* 투구 동작 자동 감지
* 투구 클립 생성

## 사용 모델

* YOLO 기반 플레이어 탐지
* MediaPipe Pose 기반 스켈레톤 추출

## 처리 과정

```
Video Input
   ↓
Pitcher Detection (YOLO)
   ↓
Pitcher Tracking
   ↓
Pose Estimation (MediaPipe)
   ↓
Pitch Motion Detection
   ↓
Skeleton Data Generation
```

---

# Hitter Model

`hitter` 폴더는 타자의 스윙 동작 분석을 위한 모델을 관리합니다.

## 주요 기능

* 타자 탐지
* 스윙 동작 분석
* 스윙 구간 추출
* 타격 동작 데이터 생성

---

# Model Output

모델 실행 후 다음과 같은 데이터가 생성됩니다.

```
pitch_clips
├ pitch_skele_000.mp4
├ pitch_skele_001.mp4
├ pitch_data_000.csv
└ plot_000.png
```

설명

* **mp4** : 스켈레톤이 표시된 투구 영상
* **csv** : 관절 좌표 데이터
* **png** : 관절 움직임 그래프

---

# Future Work

* 투구폼 자동 분류 모델
* 선수별 투구폼 비교 분석
* 신체 비율 기반 투구폼 추천 모델
* 실시간 투구 분석 시스템
