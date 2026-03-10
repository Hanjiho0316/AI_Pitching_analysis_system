from app import db
from datetime import datetime
from flask_login import UserMixin
from app import login_manager # __init__.py에서 만든 객체를 불러옵니다.

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nickname = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.String(255), default='default_logo.png')
    best_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 분석 결과 테이블과의 1대다 관계 설정
    analyses = db.relationship('Analysis', backref='user', lazy=True)

# 세션에 저장된 유저 id를 통해 유저 객체를 불러오는 콜백 함수입니다.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))