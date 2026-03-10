import os
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
# 우리가 만든 분석 엔진 불러오기
from app.services.video_processor import analyze_user_video

# Flask 앱 설정 (보통 app.py에서 호출하거나 여기서 직접 정의)
app = Flask(__name__)

# 🚨 파일 업로드 경로 설정
# Flask 실행 위치 기준 static/uploads 폴더에 저장됩니다.
UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 허용하는 영상 확장자
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv'}

def allowed_file(filename):
    """파일 확장자 체크 함수"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """메인 업로드 페이지"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    """
    영상 업로드를 처리하고 분석 결과를 반환하는 핵심 라우트
    """
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # 1. 원본 파일 안전하게 저장
        filename = secure_filename(file.filename)
        # 폴더가 없으면 생성
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        
        # 2. [자동 스켈레톤 생성 및 분석]
        # analyze_user_video는 뼈대 영상을 생성하고 분석 결과 딕셔너리를 반환함
        result_data = analyze_user_video(save_path, filename)
        
        # 3. 결과 페이지로 이동
        # result: 분석 점수, 선수명, 피드백 등
        # filename: 결과 페이지에서 보여줄 '뼈대가 그려진 영상'의 이름
        return render_template(
            'result.html', 
            result=result_data, 
            filename=result_data['processed_video']
        )
    
    return "허용되지 않는 파일 형식입니다.", 400

# 서버 실행 (app.py를 따로 쓰지 않는다면 여기서 실행 가능)
if __name__ == '__main__':
    app.run(debug=True, port=5000)