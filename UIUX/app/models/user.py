"""
사용자 계정 및 인증 정보를 관리하는 모델 파일입니다.
Flask-Login의 UserMixin을 상속받아 세션 기반 인증을 지원하며, 
사용자와 분석 결과(Analysis) 간의 1대다 관계를 설정합니다.
"""
from app import db
from datetime import datetime
from flask_login import UserMixin
from app import login_manager

class User(UserMixin, db.Model):
    """
    사용자의 이메일, 닉네임, 비밀번호 해시 및 활동 데이터를 저장합니다.
    
    Attributes:
        email (str)             : 로그인에 사용되는 고유 이메일 주소
        nickname (str)          : 웹사이트 내에서 표시될 고유 닉네임
        password_hash (str)     : 암호화되어 저장된 비밀번호
        profile_image (str)     : 사용자 프로필 이미지 파일명
        best_score (float)      : 해당 사용자가 기록한 최고 유사도 점수
        analyses (relationship) : 사용자가 수행한 분석 결과 리스트와의 관계
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nickname = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.String(255), default='default_logo.png')
    best_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.now())

    analyses = db.relationship('Analysis', backref='user', lazy=True)

@login_manager.user_loader
def load_user(user_id):
    """세션에 저장된 사용자 ID를 통해 사용자 객체를 반환하는 콜백 함수입니다."""
    return User.query.get(int(user_id))