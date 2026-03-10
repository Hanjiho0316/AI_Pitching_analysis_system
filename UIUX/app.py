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

if __name__ == '__main__':
    app.run(debug=True, port=5000)