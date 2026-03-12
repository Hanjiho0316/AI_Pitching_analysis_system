"""
Flask 어플리케이션 팩토리 함수가 정의된 패키지 초기화 파일입니다.
DB 설정, 로그인 매니저 초기화, 폴더 구조 생성 및 라우터 등록을 처리합니다.
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '로그인이 필요한 서비스입니다.'

def create_app():
    """
    설정을 로드하고 Flask 앱 인스턴스를 생성 및 반환합니다.
    
    Returns:
        app (Flask): 구성이 완료된 Flask 어플리케이션 인스턴스
    """
    app = Flask(__name__)

    app.config.from_object('config.Config')
    
    import os
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)
    
    db.init_app(app)
    login_manager.init_app(app)

    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')

    return app
