import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename
from app.models.user import User
from app.services.ml_service import start_analysis_task, get_task_status

# 'api'라는 이름의 블루프린트를 생성합니다.
# app/__init__.py에서 등록할 때 url_prefix='/api'를 설정했으므로,
# 실제 주소는 /api/check-email 형태가 됩니다.
api_bp = Blueprint('api', __name__)

@api_bp.route('/check-email', methods=['POST'])
def check_email():
    # 클라이언트(브라우저)에서 보낸 JSON 데이터를 받습니다.
    data = request.get_json()
    email = data.get('email')
    
    if not email:
         return jsonify({'is_duplicate': False, 'message': '이메일을 입력해주세요.'}), 400
         
    # 데이터베이스에서 해당 이메일이 존재하는지 검색합니다.
    user = User.query.filter_by(email=email).first()
    
    if user:
        return jsonify({'is_duplicate': True, 'message': '이미 사용 중인 이메일입니다.'})
    
    return jsonify({'is_duplicate': False, 'message': '사용 가능한 이메일입니다.'})

@api_bp.route('/check-nickname', methods=['POST'])
def check_nickname():
    # 클라이언트에서 보낸 닉네임 데이터를 받습니다.
    data = request.get_json()
    nickname = data.get('nickname')
    
    if not nickname:
         return jsonify({'is_duplicate': False, 'message': '닉네임을 입력해주세요.'}), 400
         
    # 데이터베이스에서 해당 닉네임이 존재하는지 검색합니다.
    user = User.query.filter_by(nickname=nickname).first()
    
    if user:
        return jsonify({'is_duplicate': True, 'message': '이미 사용 중인 닉네임입니다.'})
    
    return jsonify({'is_duplicate': False, 'message': '사용 가능한 닉네임입니다.'})

@api_bp.route('/upload_async', methods=['POST'])
def upload_async():
    if 'pitching_video' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['pitching_video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        # 1. 원본 파일명 안전하게 처리 및 확장자 추출
        original_filename = secure_filename(file.filename)
        ext = os.path.splitext(original_filename)[1]
        
        # 2. 고유한 파일명 생성 (예: 20260311_153022_a1b2c3d4.mp4)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        unique_filename = f"{timestamp}_{unique_id}{ext}"
        
        # 3. 사용자별 폴더 경로 설정 (비로그인 사용자는 guest 폴더로 분류)
        if current_user.is_authenticated:
            user_folder = current_user.nickname
        else:
            user_folder = "guest"
            
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], user_folder)
        os.makedirs(upload_folder, exist_ok=True)
        
        # 4. 최종 파일 경로 조합 및 저장
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        
        base_dir = os.path.dirname(current_app.root_path)
        
        # 5. 백그라운드 작업 시작 시 상대 경로도 함께 전달하면 DB 저장 시 유리합니다.
        relative_path = os.path.join('uploads', user_folder, unique_filename).replace('\\', '/')
        
        task_id = start_analysis_task(filepath, base_dir)
        
        return jsonify({'task_id': task_id, 'status': 'started'})

@api_bp.route('/status/<task_id>', methods=['GET'])
def check_status(task_id):
    # 작업 상태를 조회하여 프론트엔드에 전달합니다.
    task_info = get_task_status(task_id)
    return jsonify(task_info)