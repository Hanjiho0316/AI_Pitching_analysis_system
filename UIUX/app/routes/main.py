from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_login import login_required, current_user
import os
from werkzeug.utils import secure_filename

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'pitching_video' not in request.files:
            return redirect(request.url)
        
        file = request.files['pitching_video']
        if file.filename == '':
            return redirect(request.url)
            
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return redirect(url_for('main.result'))
            
    return render_template('index.html')

@main_bp.route('/result')
def result():
    return render_template('result.html')

@main_bp.route('/ranking')
def ranking():
    return render_template('ranking.html')

@main_bp.route('/mypage/<nickname>')
@login_required
def mypage(nickname):
    return render_template('mypage.html', nickname=nickname)

@main_bp.route('/settings')
@login_required
def settings():
    return render_template('settings.html')