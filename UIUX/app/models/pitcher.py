from app import db
from datetime import datetime

class Pitcher(db.Model):
    __tablename__ = 'pitchers'

    id = db.Column(db.Integer, primary_key=True)
    model_label = db.Column(db.String(50), unique=True, nullable=False)
    name_en = db.Column(db.String(50), nullable=False) 
    name_ko = db.Column(db.String(50), nullable=False) 
    description = db.Column(db.Text, nullable=False) 
    created_at = db.Column(db.DateTime, default=datetime.now())