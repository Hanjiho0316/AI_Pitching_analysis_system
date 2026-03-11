from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from flask_login import login_required, current_user
from app.services.ml_service import get_task_status
from werkzeug.utils import secure_filename
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/upload')
def upload():
    return render_template('upload.html')

@main_bp.route('/result')
def result():
    task_id = request.args.get('task_id')
    
    if not task_id:
        flash('잘못된 접근입니다.')
        return redirect(url_for('main.index'))
        
    task_info = get_task_status(task_id)
    
    if task_info['status'] != 'completed':
        flash('분석이 아직 완료되지 않았거나 찾을 수 없습니다.')
        return redirect(url_for('main.index'))
        
    analysis_result = task_info['result']
    filename = os.path.basename(task_info['filepath'])

    if analysis_result['similarity'] < 40.0:
        return render_template('failure.html')
    
    return render_template('result.html', result=analysis_result, filename=filename)

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