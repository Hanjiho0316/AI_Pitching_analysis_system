# app/routes.py
import os
from flask import render_template, request, redirect, url_for, flash
from app import app
from app.services.video_processor import analyze_user_video

# 업로드된 영상이 저장될 폴더 (폴더가 없으면 알아서 만듦)
UPLOAD_FOLDER = 'app/static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 🏠 메인 홈 화면 (Pitch Types 대문)
@app.route('/')
def index():
    return render_template('index.html')

# 📤 업로드 및 분석 화면
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # 1. 파일이 제대로 들어왔는지 확인
        if 'video_file' not in request.files:
            flash('파일이 없습니다.')
            return redirect(request.url)
            
        file = request.files['video_file']
        if file.filename == '':
            flash('선택된 파일이 없습니다.')
            return redirect(request.url)
            
        # 2. 파일 저장 후 AI 분석기 가동!
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            # 3. services/video_processor.py 에 있는 AI 함수 실행
            result_data = analyze_user_video(filepath)
            
            # 4. 분석 결과(result_data)를 들고 결과 화면으로 이동
            return render_template('result.html', result=result_data, filename=file.filename)
            
    # GET 방식(처음 들어왔을 때)은 업로드 화면 보여주기
    return render_template('upload.html')