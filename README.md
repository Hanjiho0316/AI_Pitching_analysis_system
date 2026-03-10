# AI_Pitching_analysis_system
- 모델 파트: 한지호, 김재위
- UI/UX 파트: 최민석, 문형철
- 

# 프로젝트 디렉토리 구성
깃허브에 왜 빈 디렉토리 안올라감;;;
```
pitching_project/UI/UX
├── app.py  
├── config.py
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── routes.py
│   ├── models/
│   ├── services/
│   │   ├── video_processor.py
│   │   └── analyzer.py
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   ├── uploads/
│   │   └── results/
│   └── templates/
│       ├── index.html
│       ├── upload.html
│       └── result.html
├── ml_models/
└── data/
```

# UI/UX 구성 목표
- 반응형 웹 설계
- 스타일은 미니멀리즘 + 다크/라이트 모드
- 약간 심리테스트 사이트 느낌으로?
- 촬영 가이드 아이콘으로 표시
- PC에서 업로드는 -> 드래그 앤 드롭으로 간편하게
- 모바일에서 업로드는 카메라로 리다이렉션 해주기
- 사용자 스켈레톤 영상 + 프로 투수 투구 영상 2개 배치
- 분석 결과는 깔끔한 카드 레이아웃으로 (선수 얼굴 + 유사도)
- 주요 수치는 릴리즈 포인트 높이, 팔 각도 등
- 결과 저장 및 공유 가능하게 (링크, 가능하면 SNS까지)
- 회원가입? + 랭킹 기능 만들어야 하니까 DB 넣기
- GCP든 AWS든 테스트용으로 배포하기 (스크린 야구장 가려고)

# 화면 구성
- 메인 화면
- 업로드 화면
- 분석 결과 화면
- 랭킹?
- 투구폼 대결?
- 마이페이지?

# 데이터베이스 구성
- ㅇㅇ...
