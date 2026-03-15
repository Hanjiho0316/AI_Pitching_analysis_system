from app import db
from datetime import datetime

class Hitter(db.Model):
    """
    모델 레이블과 매칭되는 타자의 영문/국문 이름 및 설명을 저장합니다.
    
    Attributes:
        model_label (str)   : ML 모델이 예측하는 클래스 레이블 (고유값)
        name_en (str)       : 선수의 영문 이름 (파일 탐색용)
        name_ko (str)       : 선수의 국문 이름
        description (text)  : 선수의 투구 폼 특징 및 이력 설명
    """
    __tablename__ = 'hitters'

    id = db.Column(db.Integer, primary_key=True)
    model_label = db.Column(db.String(50), unique=True, nullable=False)
    name_en = db.Column(db.String(50), nullable=False) 
    name_ko = db.Column(db.String(50), nullable=False) 
    description = db.Column(db.Text, nullable=False) 
    created_at = db.Column(db.DateTime, default=datetime.now())