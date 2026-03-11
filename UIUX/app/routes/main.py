from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from flask_login import login_required
from app.services.ml_service import get_task_status
from app.models.pitcher import Pitcher 
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
    match_player_raw = analysis_result['player_img']
    pitcher_info = Pitcher.query.filter_by(model_label=match_player_raw).first()
    
    if not pitcher_info:
        pitcher_info = {
            'name_ko': analysis_result['match_player'],
            'description': '분석된 투수의 상세 정보가 곧 업데이트될 예정입니다.',
            'name_en': 'default'
        }
    
    if analysis_result['similarity'] < 0.0:
        return render_template('failure.html')
    
    return render_template('result.html', result=analysis_result, pitcher=pitcher_info, filename=filename)

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