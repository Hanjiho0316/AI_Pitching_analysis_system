"""
사용자의 최고 분석 기록을 랭킹용으로 따로 저장하는 모델 파일입니다.
"""
from app import db
from datetime import datetime

class PitcherRanking(db.Model):
    """
    사용자의 투구 폼 분석 결과 중 최고 점수를 기록하는 모델입니다.
    
    Attributes:
        id (int)              : 랭킹 기록의 고유 식별자 (PK)
        user_id (int)         : 랭킹에 등록된 사용자의 식별자 (FK)
        pitcher_id (int)      : 매칭된 투수의 식별자 (FK)
        score (float)         : 기록된 최고 유사도 점수
        recorded_at (datetime): 랭킹이 기록되거나 마지막으로 갱신된 시간
        user (relationship)   : 해당 랭킹을 기록한 사용자 연관 객체
        pitcher (relationship): 매칭된 투수 연관 객체
    """
    __tablename__ = 'pitcher_rankings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pitcher_id = db.Column(db.Integer, db.ForeignKey('pitchers.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='pitcher_rankings')
    pitcher = db.relationship('Pitcher')

class HitterRanking(db.Model):
    """
    사용자의 타격 폼 분석 결과 중 최고 점수를 기록하는 모델입니다.
    
    Attributes:
        id (int)              : 랭킹 기록의 고유 식별자 (PK)
        user_id (int)         : 랭킹에 등록된 사용자의 식별자 (FK)
        hitter_id (int)       : 매칭된 타자의 식별자 (FK)
        score (float)         : 기록된 최고 유사도 점수
        recorded_at (datetime): 랭킹이 기록되거나 마지막으로 갱신된 시간
        user (relationship)   : 해당 랭킹을 기록한 사용자 연관 객체
        hitter (relationship) : 매칭된 타자 연관 객체
    """
    __tablename__ = 'hitter_rankings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hitter_id = db.Column(db.Integer, db.ForeignKey('hitters.id'), nullable=True) # 추후 Hitter 모델 연동을 위해 임시로 비워둘 수 있게 설정
    score = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='hitter_rankings')
    hitter = db.relationship('Hitter')