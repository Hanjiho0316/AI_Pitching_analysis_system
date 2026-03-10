from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()

# LoginManager 인스턴스 생성
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '로그인이 필요한 서비스입니다.'

def create_app():
    app = Flask(__name__)
    
    # config.py 파일의 Config 클래스 내용을 불러와 적용합니다.
    app.config.from_object('config.Config')
    
    # 폴더 자동 생성 로직
    import os
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)
    
    db.init_app(app)
    login_manager.init_app(app)

    from app.models import user, analysis
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')

    return app
