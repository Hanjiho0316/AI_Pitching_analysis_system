from app import db
from datetime import datetime

class Analysis(db.Model):
    __tablename__ = 'analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pitcher_id = db.Column(db.Integer, db.ForeignKey('pitchers.id'), nullable=False)
    
    similarity = db.Column(db.Float, nullable=False)
    user_video_path = db.Column(db.String(255), nullable=False) # 사용자가 업로드한 영상 경로
    created_at = db.Column(db.DateTime, default=datetime.utcnow)