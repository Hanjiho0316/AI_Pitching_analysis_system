"""
사용자 영상에 대한 모델 분석 결과를 기록하는 모델 파일입니다.
User 테이블과 Pitcher 테이블을 참조하는 외래 키를 가집니다.
"""
from app import db
from datetime import datetime

class Analysis(db.Model):
    """
    분석 수행 시간, 유사도 점수 및 영상 저장 경로를 관리합니다.
    
    Attributes:
        user_id (int): 분석을 수행한 사용자의 ID (FK)
        pitcher_id (int): 분석 결과 가장 유사하다고 판단된 투수의 ID (FK)
        similarity (float): 모델이 계산한 투구 폼 유사도 (0~1 사이 값)
        user_video_path (str): 서버 내 저장된 사용자 업로드 영상의 상대 경로
    """
    __tablename__ = 'analyses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    analysis_type = db.Column(db.String(10), nullable=False, default='pitch')
    pitcher_id = db.Column(db.Integer, db.ForeignKey('pitchers.id'), nullable=True)
    hitter_id = db.Column(db.Integer, db.ForeignKey('hitters.id'), nullable=True)
    similarity = db.Column(db.Float, nullable=False)
    user_video_path = db.Column(db.String(255), nullable=False)
    result_image_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    pitcher = db.relationship('Pitcher', backref='analysis_records')
    hitter = db.relationship('Hitter', backref='analysis_records')