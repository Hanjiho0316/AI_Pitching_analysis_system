"""
사용자의 최고 분석 기록을 랭킹용으로 따로 저장하는 모델 파일입니다.
"""
from app import db
from datetime import datetime

class PitcherRanking(db.Model):
    __tablename__ = 'pitcher_rankings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pitcher_id = db.Column(db.Integer, db.ForeignKey('pitchers.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='pitcher_rankings')
    pitcher = db.relationship('Pitcher')

class HitterRanking(db.Model):
    __tablename__ = 'hitter_rankings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hitter_id = db.Column(db.Integer, db.ForeignKey('hitters.id'), nullable=True) # 추후 Hitter 모델 연동을 위해 임시로 비워둘 수 있게 설정
    score = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='hitter_rankings')
    hitter = db.relationship('Hitter')