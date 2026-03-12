import os

# 프로젝트 최상위 디렉토리의 절대 경로를 구합니다.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # 세션 관리용 키
    SECRET_KEY = 'pitchtypes-secret-key-debugging'
    
    # 데이터베이스 설정
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'pitching.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 영상 업로드 및 결과 저장 폴더 설정
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    RESULT_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'results')
    
    # 업로드 가능한 최대 파일 용량 제한 (32MB)
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024

    # 머신러닝 모델 파일 경로 설정
    ML_MODEL_PATH = os.path.join(BASE_DIR, 'ml_models', 'best_model_fold.h5')
    LABEL_ENCODER_PATH = os.path.join(BASE_DIR, 'ml_models', 'label_encoder.pkl')
    YOLO_MODEL_PATH = 'yolov8n.pt'

    