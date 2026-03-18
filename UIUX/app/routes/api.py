"""
클라이언트와 데이터를 JSON 형태로 주고받는 API 라우터 모듈입니다.
계정 중복 검사, 파일 비동기 업로드 처리, 작업 상태 폴링(Polling) 및 
랭킹 피드 조회를 담당합니다.
"""
import base64
import uuid
import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.user import User
from app.models.ranking import PitcherRanking, HitterRanking
from app.models.analysis import Analysis
from app.services.ml_service import start_analysis_task, get_task_status

api_bp = Blueprint('api', __name__)


@api_bp.route('/check-email', methods=['POST'])
def check_email():
    """
    회원가입 시 입력된 이메일의 중복 여부를 데이터베이스에서 검증합니다.
    
    Returns:
        Response: 중복 여부(is_duplicate) 불리언 값과 안내 메시지를 포함한 JSON 객체
    """
    data = request.get_json()
    email = data.get('email')
    
    if not email:
         return jsonify({'is_duplicate': False, 'message': '이메일을 입력해주세요.'}), 400

    user = User.query.filter_by(email=email).first()
    
    if user:
        return jsonify({'is_duplicate': True, 'message': '이미 사용 중인 이메일입니다.'})
    
    return jsonify({'is_duplicate': False, 'message': '사용 가능한 이메일입니다.'})


@api_bp.route('/check-nickname', methods=['POST'])
def check_nickname():
    """
    회원가입 시 입력된 닉네임의 중복 여부를 데이터베이스에서 검증합니다.
    
    Returns:
        Response: 중복 여부(is_duplicate) 불리언 값과 안내 메시지를 포함한 JSON 객체
    """
    data = request.get_json()
    nickname = data.get('nickname')
    
    if not nickname:
         return jsonify({'is_duplicate': False, 'message': '닉네임을 입력해주세요.'}), 400

    user = User.query.filter_by(nickname=nickname).first()
    
    if user:
        return jsonify({'is_duplicate': True, 'message': '이미 사용 중인 닉네임입니다.'})
    
    return jsonify({'is_duplicate': False, 'message': '사용 가능한 닉네임입니다.'})


@api_bp.route('/upload_async', methods=['POST'])
def upload_async():
    """
    사용자가 업로드한 영상 파일을 로컬 스토리지에 안전하게 저장하고, 
    백그라운드 스레드를 호출하여 AI 비전 분석 작업을 비동기로 시작합니다.
    
    Returns:
        Response: 생성된 백그라운드 작업의 고유 ID(task_id)와 시작 상태를 포함한 JSON 객체
    """
    analysis_type = request.form.get('analysis_type', 'pitch')
    handedness = request.form.get('handedness', 'right')
    
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
            analysis_type,
            handedness
        )
        
        return jsonify({'task_id': task_id, 'status': 'started'})


@api_bp.route('/status/<task_id>', methods=['GET'])
def check_status(task_id):
    """
    특정 분석 작업의 현재 진행 상태를 메모리 딕셔너리에서 조회하여 반환합니다.
    프론트엔드에서 주기적으로 호출(Polling)하여 완료 여부를 파악하는 데 사용됩니다.
    
    Args:
        task_id (str): 상태를 조회할 비동기 작업의 고유 ID
        
    Returns:
        Response: 작업 상태(pending, processing, completed, error) 및 결과를 포함한 JSON 객체
    """
    task_info = get_task_status(task_id)
    
    return jsonify(task_info)


@api_bp.route('/rankings', methods=['GET'])
def get_rankings():
    """
    무한 스크롤 및 페이지네이션을 지원하기 위해 
    랭킹 데이터를 지정된 개수만큼 조회하여 반환합니다.
    
    Query Parameters:
        offset (int): 건너뛸 레코드 수 (기본값: 0)
        limit (int): 가져올 최대 레코드 수 (기본값: 10)
        type (str): 조회할 랭킹 종류 (pitch 또는 hit)
        
    Returns:
        Response: 정렬된 랭킹 데이터 리스트를 포함한 JSON 배열
    """
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


@api_bp.route('/battle_feed', methods=['GET'])
def get_battle_feed():
    """
    고스트 대결 화면에서 표시될 실시간 최근 분석 기록(피드) 및
    사용자 검색 결과를 반환합니다.
    
    Query Parameters:
        q (str): 검색할 특정 유저의 닉네임 키워드 (선택적)
        
    Returns:
        Response: 최근 최대 30건의 분석 기록 정보가 담긴 JSON 배열
    """
    query = request.args.get('q', '')
    
    from app.models.analysis import Analysis
    from app.models.user import User
    
    base_query = Analysis.query.join(User).order_by(Analysis.created_at.desc())
    
    if query:
        base_query = base_query.filter(User.nickname.ilike(f'%{query}%'))
        
    recent_analyses = base_query.limit(30).all()
    
    result = []
    for analysis in recent_analyses:
        if analysis.analysis_type == 'pitch' and analysis.pitcher:
            player_name = analysis.pitcher.name_ko
            player_img = analysis.pitcher.name_en + '.jpg'
            folder = 'pitchers'
        elif analysis.analysis_type == 'hit' and analysis.hitter:
            player_name = analysis.hitter.name_ko
            player_img = analysis.hitter.name_en + '.jpg'
            folder = 'hitters'
        else:
            player_name = '알 수 없음'
            player_img = 'default_logo.png'
            folder = 'pitchers'
            
        result.append({
            'analysis_id': analysis.id,
            'nickname': analysis.user.nickname,
            'profile_image': analysis.user.profile_image,
            'type': analysis.analysis_type,
            'score': analysis.similarity,
            'player_name': player_name,
            'player_image': f"/static/images/{folder}/{player_img}",
            'time': analysis.created_at.strftime('%Y-%m-%d %H:%M')
        })
        
    return jsonify(result)


@api_bp.route('/save_card', methods=['POST'])
def save_card():
    """
    프론트엔드의 html2canvas 라이브러리를 통해 캡처된 Base64 포맷의 
    결과 카드 이미지를 디코딩하여 로컬 스토리지에 PNG 파일로 저장합니다.
    
    Returns:
        Response: 저장 성공 여부(success)를 나타내는 JSON 객체
    """    
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    analysis_id = data.get('analysis_id')
    image_data = data.get('image_data')
    
    if not analysis_id or not image_data:
        return jsonify({'error': 'Missing data'}), 400
        
    if ',' in image_data:
        image_data = image_data.split(',')[1]
        
    img_bytes = base64.b64decode(image_data)
    
    user_folder = os.path.join(current_app.config['RESULT_FOLDER'], str(current_user.id))
    os.makedirs(user_folder, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{timestamp}_{unique_id}.png"
    filepath = os.path.join(user_folder, filename)
    
    with open(filepath, 'wb') as f:
        f.write(img_bytes)
        
    analysis = Analysis.query.get(analysis_id)
    if analysis and analysis.user_id == current_user.id:
        analysis.result_image_path = f"{current_user.id}/{filename}"
        db.session.commit()
        
    return jsonify({'success': True})