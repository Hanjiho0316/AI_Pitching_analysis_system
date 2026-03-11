import os

# 프로젝트 최상위 디렉토리의 절대 경로를 구합니다.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # 세션 및 쿠키 보안을 위한 비밀키입니다. (실제 서비스 시에는 복잡한 무작위 문자열 사용 권장)
    SECRET_KEY = 'pitchtypes-secret-key-debugging'
    
    # 데이터베이스 파일의 저장 위치를 설정합니다.
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'pitching.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 영상 업로드 및 결과 저장 폴더 설정
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    RESULT_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'results')
    
    # 업로드 가능한 최대 파일 용량 제한 (32MB)
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024

    