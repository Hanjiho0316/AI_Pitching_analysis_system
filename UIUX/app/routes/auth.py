"""
사용자 계정 생성, 인증(로그인/로그아웃) 및 프로필 관리를 전담하는 라우터 모듈입니다.
보안을 위해 비밀번호는 PBKDF2 방식의 SHA256 해시로 처리되며, 
사용자 식별이 필요한 라우트에는 @login_required 데코레이터를 적용합니다.
"""
import os
from PIL import Image
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.models.analysis import Analysis
from app.models.ranking import PitcherRanking, HitterRanking
from app import db
from werkzeug.utils import secure_filename


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    사용자의 회원가입 절차를 처리합니다.
    
    GET: 회원가입 폼 화면을 렌더링합니다.
    POST: 사용자가 입력한 이메일, 닉네임, 비밀번호를 수신하여 중복을 검사하고, 
          비밀번호를 해싱한 뒤 새로운 계정을 데이터베이스에 저장합니다.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        nickname = request.form.get('nickname')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('이미 존재하는 이메일입니다.')
            return redirect(url_for('auth.signup'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(email=email, nickname=nickname, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('auth.login'))

    return render_template('signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    사용자의 로그인 절차를 처리합니다.
    
    GET: 로그인 폼 화면을 렌더링합니다.
    POST: 입력된 이메일을 데이터베이스에서 찾고 해싱된 비밀번호의 일치 여부를 검증한 후, 
          성공 시 Flask-Login을 통해 세션을 발급합니다.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('main.index'))
        else:
            flash('이메일 또는 비밀번호가 올바르지 않습니다.')
            return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    로그인한 사용자의 닉네임 변경 및 프로필 이미지 업로드를 처리합니다.
    
    업로드된 이미지는 Pillow 라이브러리를 통해 정사각형(1:1 비율)으로 
    중앙을 기준하여 크롭(Crop)된 후 고유한 경로에 안전하게 저장됩니다.
    """
    if request.method == 'POST':
        new_nickname = request.form.get('nickname')
        profile_img = request.files.get('profile_image')
        
        if profile_img:
            ext = os.path.splitext(profile_img.filename)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg']:
                ext = '.png'
            filename = f"image{ext}"

            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles', str(current_user.id))
            os.makedirs(upload_path, exist_ok=True)
            
            filepath = os.path.join(upload_path, filename)
            
            img = Image.open(profile_img)
            
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            width, height = img.size
            min_dim = min(width, height)
            left = (width - min_dim) / 2
            top = (height - min_dim) / 2
            right = (width + min_dim) / 2
            bottom = (height + min_dim) / 2
            
            img = img.crop((left, top, right, bottom))
            img.save(filepath)
            
            current_user.profile_image = f"{current_user.id}/{filename}"

        current_user.nickname = new_nickname
        db.session.commit()
        flash('정보가 성공적으로 수정되었습니다.')
        
        return redirect(url_for('main.mypage', nickname=current_user.nickname))
        
    return render_template('edit_profile.html')


@auth_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """
    현재 로그인된 사용자의 계정을 탈퇴 처리합니다.
    
    데이터베이스의 외래 키(Foreign Key) 제약 조건을 준수하기 위해 
    사용자와 연관된 Analysis 기록 및 Ranking 기록을 선행 삭제한 후, 
    최종적으로 User 객체를 삭제하고 세션을 만료시킵니다.
    """
    user_id = current_user.id
    
    Analysis.query.filter_by(user_id=user_id).delete()
    PitcherRanking.query.filter_by(user_id=user_id).delete()
    HitterRanking.query.filter_by(user_id=user_id).delete()
    
    user = User.query.get(user_id)
    logout_user()
    
    db.session.delete(user)
    db.session.commit()
    
    flash('회원 탈퇴가 완료되었습니다.')
    return redirect(url_for('main.index'))


@auth_bp.route('/logout')
@login_required
def logout():
    """
    로그인된 사용자의 세션을 만료시켜 로그아웃을 수행하고 메인 화면으로 리다이렉트합니다.
    """
    logout_user()

    return redirect(url_for('main.index'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """
    사용자의 로그인 비밀번호를 변경합니다.
    
    GET: 비밀번호 변경 입력 폼을 렌더링합니다.
    POST: 사용자가 입력한 현재 비밀번호가 해시값과 일치하는지 검증하고, 
          새 비밀번호와 확인용 비밀번호가 동일한지 대조한 후 새 해시값을 저장합니다.
    """
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not check_password_hash(current_user.password_hash, current_password):
            flash('현재 비밀번호가 일치하지 않습니다.')
            return redirect(url_for('auth.change_password'))

        if new_password != confirm_password:
            flash('새 비밀번호가 서로 일치하지 않습니다.')
            return redirect(url_for('auth.change_password'))

        current_user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()
        
        flash('비밀번호가 성공적으로 변경되었습니다.')
        return redirect(url_for('main.mypage', nickname=current_user.nickname))

    return render_template('passwd.html')