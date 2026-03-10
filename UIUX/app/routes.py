from flask import Blueprint, render_template, request, redirect, url_for, current_app
import os
from werkzeug.utils import secure_filename

# 블루프린트 생성
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # 메인 화면(콘티로 그려주신 페이지)을 보여줍니다.
    return render_template('index.html')

@main_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # 파일이 전송되었는지 확인
        if 'pitching_video' not in request.files:
            return redirect(request.url)
        
        file = request.files['pitching_video']
        if file.filename == '':
            return redirect(request.url)
            
        if file:
            # 안전한 파일명으로 변경 후 저장
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # 이 부분에서 나중에 'services/analyzer.py'의 함수를 호출하여
            # 모델 분석을 수행하게 됩니다. 현재는 결과 페이지로 바로 이동합니다.
            return redirect(url_for('main.result'))
            
    # GET 방식 접근 시에는 인덱스로 보내거나 별도의 업로드 폼을 보여줄 수 있습니다.
    return render_template('index.html')

@main_bp.route('/result')
def result():
    # 분석이 완료된 후 결과 데이터를 result.html에 전달하여 보여줍니다.
    return render_template('result.html')