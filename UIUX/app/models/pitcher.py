from app import db
from datetime import datetime

class Pitcher(db.Model):
    __tablename__ = 'pitchers'
    
    id = db.Column(db.Integer, primary_key=True)
    name_ko = db.Column(db.String(50), nullable=False)
    name_en = db.Column(db.String(50), unique=True, nullable=False) # 파일명 매칭용 (예: sohyeongjun)
    description = db.Column(db.Text, nullable=True) # 선수의 고유한 투구 특징
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 분석 기록과의 1대다 관계 설정
    analyses = db.relationship('Analysis', backref='pitcher', lazy=True)