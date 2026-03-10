from app import db
from datetime import datetime

class Analysis(db.Model):
    __tablename__ = 'analyses'

    id = db.Column(db.Integer, primary_key=True)
    # 어느 유저의 분석 결과인지 외래키로 연결합니다
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    video_path = db.Column(db.String(255), nullable=False)
    result_video_path = db.Column(db.String(255), nullable=True)
    similarity_score = db.Column(db.Float, nullable=False)
    matched_player = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)