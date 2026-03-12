"""
클라이언트(주로 JavaScript)와 데이터를 JSON 형태로 주고받는 API 라우터입니다.
중복 검사, 파일 업로드 처리 및 백그라운드 분석 작업 상태 조회를 담당합니다.
"""
import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename
from app.models.user import User
from app.models.ranking import Ranking
from app.services.ml_service import start_analysis_task, get_task_status

api_bp = Blueprint('api', __name__)


@api_bp.route('/check-email', methods=['POST'])
def check_email():
    """
    회원가입 시 입력된 이메일의 중복 여부를 확인합니다.
    
    Returns:
        Response: 중복 여부(is_duplicate)와 메시지를 포함한 JSON 객체
    """
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
    """
    회원가입 시 입력된 닉네임의 중복 여부를 확인합니다.
    
    Returns:
        Response: 중복 여부(is_duplicate)와 메시지를 포함한 JSON 객체
    """
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
    """
    사용자가 업로드한 영상을 서버에 저장하고, 백그라운드 분석 작업을 시작합니다.
    로그인한 사용자는 닉네임 폴더에, 비로그인 사용자는 guest 폴더에 영상을 저장합니다.
    
    Returns:
        Response: 생성된 작업 ID(task_id)와 상태를 포함한 JSON 객체
    """
    if 'pitching_video' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['pitching_video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        # 원본 파일명 추출
        original_filename = secure_filename(file.filename)
        ext = os.path.splitext(original_filename)[1]
        
        # 고유한 파일명 생성 (예: 20260311_153022_a1b2c3d4.mp4)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        unique_filename = f"{timestamp}_{unique_id}{ext}"
        
        # 사용자별 폴더 경로 설정 (비로그인 사용자는 guest 폴더로 분류)
        if current_user.is_authenticated:
            user_folder = current_user.nickname
        else:
            user_folder = "guest"
            
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], user_folder)
        os.makedirs(upload_folder, exist_ok=True)
        
        # 최종 파일 경로 조합 및 저장
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        
        # current_app.config에서 모델 경로들을 가져옵니다.
        ml_model_path = current_app.config.get('ML_MODEL_PATH')
        encoder_path = current_app.config.get('LABEL_ENCODER_PATH')
        yolo_path = current_app.config.get('YOLO_MODEL_PATH')
        
        # 비동기 스레드에서 DB에 접근하기 위해 현재 앱 인스턴스를 가져옵니다.
        app_instance = current_app._get_current_object()
        
        # 비로그인 사용자(guest)의 경우 DB 저장을 생략하거나 별도 처리하기 위해 분기합니다.
        user_id = current_user.id if current_user.is_authenticated else None
        
        task_id = start_analysis_task(
            filepath, 
            ml_model_path, 
            encoder_path, 
            yolo_path, 
            app_instance, 
            user_id
        )
        
        return jsonify({'task_id': task_id, 'status': 'started'})


@api_bp.route('/status/<task_id>', methods=['GET'])
def check_status(task_id):
    """
    특정 분석 작업의 현재 진행 상태를 반환합니다.
    
    Args:
        task_id (str): 상태를 조회할 작업의 고유 ID
        
    Returns:
        Response: 작업 상태 및 완료 시 결과를 포함한 JSON 객체
    """
    task_info = get_task_status(task_id)
    
    return jsonify(task_info)


@api_bp.route('/more-rankings', methods=['GET'])
def more_rankings():
    offset = request.args.get('offset', 10, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    rankings = Ranking.query.order_by(Ranking.score.desc()).offset(offset).limit(limit).all()
    
    result = []
    for rank in rankings:
        # 복잡한 replace 대신 깔끔하게 저장된 name_en 속성을 활용합니다.
        safe_image_name = rank.pitcher.name_en + '.jpg'
        
        result.append({
            'nickname': rank.user.nickname,
            'profile_image': rank.user.profile_image,
            'pitcher_name': rank.pitcher.name_ko,
            'pitcher_image': safe_image_name,
            'score': rank.score
        })
        
    return jsonify(result)