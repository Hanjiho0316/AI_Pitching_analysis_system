from flask import Flask
import os

def create_app():
    # Flask 인스턴스 생성
    app = Flask(__name__)
    
    # 업로드 및 결과 저장 경로 설정
    app.config['UPLOAD_FOLDER'] = os.path.join('app', 'static', 'uploads')
    app.config['RESULT_FOLDER'] = os.path.join('app', 'static', 'results')
    
    # 보안을 위한 최대 업로드 용량 제한 (예: 32MB)
    app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
    
    # 필요한 폴더가 없을 경우 자동 생성
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

    # 블루프린트(라우팅 설정) 등록
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app