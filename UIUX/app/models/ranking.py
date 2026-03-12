"""
사용자의 최고 분석 기록을 랭킹용으로 따로 저장하는 모델 파일입니다.
"""
from app import db
from datetime import datetime

class Ranking(db.Model):
    """
    집계 및 그룹화 쿼리에 최적화된 랭킹 데이터를 저장합니다.
    """
    __tablename__ = 'rankings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pitcher_id = db.Column(db.Integer, db.ForeignKey('pitchers.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='rankings')
    pitcher = db.relationship('Pitcher')