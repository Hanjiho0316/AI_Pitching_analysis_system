"""
사용자 계정 생성, 인증(로그인/로그아웃), 프로필 관리 기능을 처리하는 라우터입니다.
보안을 위해 비밀번호는 해싱하여 처리하며, 
회원 전용 기능에는 @login_required 데코레이터를 사용합니다.
"""
import os
from PIL import Image
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db
from werkzeug.utils import secure_filename


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    GET: 회원가입 폼 화면을 렌더링합니다.
    POST: 사용자가 제출한 정보로 새 계정을 생성하고 데이터베이스에 저장합니다.
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
    GET: 로그인 폼 화면을 렌더링합니다.
    POST: 이메일과 비밀번호를 확인하여 일치할 경우 세션을 생성(로그인)합니다.
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
    로그인한 사용자의 닉네임 및 프로필 이미지를 수정합니다.
    업로드된 이미지는 고유한 파일명으로 변환되어 안전하게 저장됩니다.
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
        
    return render_template('edit.html')


@auth_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """현재 로그인된 사용자의 계정을 데이터베이스에서 삭제하고 로그아웃 처리합니다."""
    user = User.query.get(current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash('회원 탈퇴가 완료되었습니다.')

    return redirect(url_for('main.index'))


@auth_bp.route('/logout')
@login_required
def logout():
    """사용자 세션을 종료하고 메인 화면으로 이동합니다."""
    logout_user()

    return redirect(url_for('main.index'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """
    사용자의 비밀번호를 변경합니다.
    현재 비밀번호 확인 및 새 비밀번호의 일치 여부를 검증한 후 해싱하여 저장합니다.
    """
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 현재 비밀번호가 맞는지 확인
        if not check_password_hash(current_user.password_hash, current_password):
            flash('현재 비밀번호가 일치하지 않습니다.')
            return redirect(url_for('auth.change_password'))

        # 새 비밀번호와 확인용 비밀번호가 일치하는지 확인
        if new_password != confirm_password:
            flash('새 비밀번호가 서로 일치하지 않습니다.')
            return redirect(url_for('auth.change_password'))

        # 비밀번호 업데이트 (해싱 처리)
        current_user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()
        
        flash('비밀번호가 성공적으로 변경되었습니다.')
        return redirect(url_for('main.mypage', nickname=current_user.nickname))

    # GET 요청 시 비밀번호 변경 화면을 보여줍니다.
    return render_template('passwd.html')