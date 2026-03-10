<<<<<<< HEAD
from app import create_app, db

# 팩토리 함수를 통해 앱 인스턴스를 생성합니다.
app = create_app()
=======
import os
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from app.services.video_processor import analyze_user_video

app = Flask(__name__, 
            template_folder='app/templates', 
            static_folder='app/static')

# 업로드 폴더 설정
UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_page')
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file or file.filename == '':
        return redirect(url_for('upload_page'))

    filename = secure_filename(file.filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)
    
    # AI 분석 시작 (뼈대 영상 생성 포함)
    result_data = analyze_user_video(save_path, filename)
    
    return render_template('result.html', 
                           result=result_data, 
                           filename=result_data['processed_video'])
>>>>>>> 691c78e7e8c218a664446852ce4fdb01e1e606c8

# 애플리케이션 컨텍스트 안에서 데이터베이스 테이블을 생성합니다.
# 이미 pitching.db 파일과 테이블이 존재한다면 덮어쓰지 않고 넘어갑니다.
with app.app_context():
    db.create_all()

if __name__ == '__main__':
<<<<<<< HEAD
    # 개발 중에는 debug=True로 설정하여 코드 수정 시 서버가 자동 재시작되게 합니다.
    app.run(host='0.0.0.0', port=5000, debug=True)
=======
    app.run(debug=True, port=5000)
>>>>>>> 691c78e7e8c218a664446852ce4fdb01e1e606c8
