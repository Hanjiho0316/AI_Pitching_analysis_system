from flask import Blueprint, request, jsonify
from app.models.user import User

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