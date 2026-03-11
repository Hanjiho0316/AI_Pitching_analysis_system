from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db
import os
from werkzeug.utils import secure_filename

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
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
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        profile_img = request.files.get('profile_image')
        
        if profile_img:
            filename = secure_filename(f"user_{current_user.id}_{profile_img.filename}")
            upload_path = os.path.join(current_app.config['BASE_DIR'], 'app/static/uploads/profiles')
            os.makedirs(upload_path, exist_ok=True)
            profile_img.save(os.path.join(upload_path, filename))
            current_user.profile_image = f"uploads/profiles/{filename}"

        current_user.nickname = nickname
        db.session.commit()
        flash('정보가 성공적으로 수정되었습니다.')
        return redirect(url_for('main.mypage', nickname=current_user.nickname))
        
    return render_template('edit.html')

@auth_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    user = User.query.get(current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash('회원 탈퇴가 완료되었습니다.')
    return redirect(url_for('main.index'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 1. 현재 비밀번호가 맞는지 확인
        if not check_password_hash(current_user.password_hash, current_password):
            flash('현재 비밀번호가 일치하지 않습니다.')
            return redirect(url_for('auth.change_password'))

        # 2. 새 비밀번호와 확인용 비밀번호가 일치하는지 확인
        if new_password != confirm_password:
            flash('새 비밀번호가 서로 일치하지 않습니다.')
            return redirect(url_for('auth.change_password'))

        # 3. 비밀번호 업데이트 (해싱 처리)
        current_user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()
        
        flash('비밀번호가 성공적으로 변경되었습니다.')
        return redirect(url_for('main.mypage', nickname=current_user.nickname))

    # GET 요청 시 비밀번호 변경 화면을 보여줍니다.
    return render_template('passwd.html')