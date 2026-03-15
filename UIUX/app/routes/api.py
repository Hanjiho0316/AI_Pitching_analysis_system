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
from app.models.ranking import PitcherRanking, HitterRanking
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
    분석 타입(pitch/hit)에 따라 적절한 모델을 선택합니다.
    """
    # 프론트엔드에서 전달받은 분석 타입 (기본값: pitch)
    analysis_type = request.form.get('analysis_type', 'pitch')
    
    # 투구 업로드와 타격 업로드의 파일 폼 이름 호환성 처리
    file = request.files.get('video_file') or request.files.get('pitching_video')
    
    if not file or file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        original_filename = secure_filename(file.filename)
        ext = os.path.splitext(original_filename)[1]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        unique_filename = f"{timestamp}_{unique_id}{ext}"
        
        if current_user.is_authenticated:
            user_folder = str(current_user.id)
        else:
            user_folder = "guest"
            
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], user_folder)
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        
        # 분석 종류에 따른 모델 설정 분기
        if analysis_type == 'hit':
            ml_model_path = current_app.config.get('HIT_ML_MODEL_PATH')
            encoder_path = current_app.config.get('HIT_LABEL_ENCODER_PATH')
        else:
            ml_model_path = current_app.config.get('PITCH_ML_MODEL_PATH')
            encoder_path = current_app.config.get('PITCH_LABEL_ENCODER_PATH')
            
        yolo_path = current_app.config.get('YOLO_MODEL_PATH')
        
        app_instance = current_app._get_current_object()
        user_id = current_user.id if current_user.is_authenticated else None
        
        task_id = start_analysis_task(
            filepath, 
            ml_model_path, 
            encoder_path, 
            yolo_path, 
            app_instance, 
            user_id,
            analysis_type
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


@api_bp.route('/rankings', methods=['GET'])
def get_rankings():
    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 10, type=int)
    ranking_type = request.args.get('type', 'pitch')
    
    result = []
    
    if ranking_type == 'hit':
        from app.models.ranking import HitterRanking
        rankings = HitterRanking.query.order_by(HitterRanking.score.desc(), HitterRanking.recorded_at.desc()).offset(offset).limit(limit).all()
        for rank in rankings:
            safe_image_name = rank.hitter.name_en + '.jpg' if rank.hitter else 'default_logo.png'
            player_name = rank.hitter.name_ko if rank.hitter else '알 수 없음'
            result.append({
                'nickname': rank.user.nickname,
                'profile_image': rank.user.profile_image,
                'player_name': player_name,
                'player_image': safe_image_name,
                'score': rank.score,
                'type': 'hit'
            })
    else:
        from app.models.ranking import PitcherRanking
        rankings = PitcherRanking.query.order_by(PitcherRanking.score.desc(), PitcherRanking.recorded_at.desc()).offset(offset).limit(limit).all()
        for rank in rankings:
            safe_image_name = rank.pitcher.name_en + '.jpg' if rank.pitcher else 'default_logo.png'
            player_name = rank.pitcher.name_ko if rank.pitcher else '알 수 없음'
            result.append({
                'nickname': rank.user.nickname,
                'profile_image': rank.user.profile_image,
                'player_name': player_name,
                'player_image': safe_image_name,
                'score': rank.score,
                'type': 'pitch'
            })
            
    return jsonify(result)