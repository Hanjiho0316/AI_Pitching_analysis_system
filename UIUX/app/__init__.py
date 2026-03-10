# app/__init__.py
from flask import Flask

app = Flask(__name__)
app.secret_key = "pitch_types_secret_key_123" # 보안(메시지 띄우기)을 위한 임시 키

# 라우트(경로) 파일 연결
from app import routes