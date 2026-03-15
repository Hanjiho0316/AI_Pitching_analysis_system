"""
웹사이트의 화면 렌더링을 담당하는 메인 라우터입니다.
페이지 이동 및 분석 완료 후 결과 화면을 구성하기 위한 데이터를 템플릿에 전달합니다.
"""
import os
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from flask_login import login_required
from app.services.ml_service import get_task_status
from app.models.analysis import Analysis
from app.models.pitcher import Pitcher 
from app.models.ranking import PitcherRanking, HitterRanking
from app.models.user import User


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """메인 화면을 렌더링합니다."""
    return render_template('index.html')


@main_bp.route('/upload_pitch')
def upload_pitch():
    """투구 영상 업로드 화면을 렌더링합니다."""
    return render_template('upload_pitch.html')


@main_bp.route('/upload_hit')
def upload_hit():
    """타격 영상 업로드 화면을 렌더링합니다."""
    return render_template('upload_hit.html')


@main_bp.route('/battle')
def battle():
    """폼 대결 화면을 렌더링합니다."""
    return render_template('battle.html')


@main_bp.route('/result_pitch')
def result_pitch():
    """투구 폼 분석 결과 화면을 렌더링합니다."""
    task_id = request.args.get('task_id')
    
    if not task_id:
        flash('잘못된 접근입니다.')
        return redirect(url_for('main.index'))
        
    task_info = get_task_status(task_id)
    
    if task_info['status'] != 'completed':
        flash('분석이 아직 완료되지 않았거나 찾을 수 없습니다.')
        return redirect(url_for('main.index'))
        
    analysis_result = task_info['result']
    filepath = task_info['filepath']
    
    path_parts = os.path.normpath(filepath).split(os.sep)
    user_folder = path_parts[-2]
    file_name = path_parts[-1]
    relative_filename = f"{user_folder}/{file_name}"
    
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
    
    top_rankings = PitcherRanking.query.order_by(PitcherRanking.score.desc()).limit(3).all()
    
    return render_template('result_pitch.html', result=analysis_result, pitcher=pitcher_info, filename=relative_filename, top_rankings=top_rankings)


@main_bp.route('/result_hit')
def result_hit():
    """타격 폼 분석 결과 화면을 렌더링합니다."""
    task_id = request.args.get('task_id')
    
    if not task_id:
        flash('잘못된 접근입니다.')
        return redirect(url_for('main.index'))
        
    task_info = get_task_status(task_id)
    
    if task_info['status'] != 'completed':
        flash('분석이 아직 완료되지 않았거나 찾을 수 없습니다.')
        return redirect(url_for('main.index'))
        
    analysis_result = task_info['result']
    filepath = task_info['filepath']
    
    path_parts = os.path.normpath(filepath).split(os.sep)
    user_folder = path_parts[-2]
    file_name = path_parts[-1]
    relative_filename = f"{user_folder}/{file_name}"
    
    match_player_raw = analysis_result['player_img']
    from app.models.hitter import Hitter
    hitter_info = Hitter.query.filter_by(model_label=match_player_raw).first()
    
    if not hitter_info:
        hitter_info = {
            'name_ko': analysis_result['match_player'],
            'description': '분석된 타자의 상세 정보가 곧 업데이트될 예정입니다.',
            'name_en': 'default'
        }
    
    if analysis_result['similarity'] < 0.0:
        return render_template('failure.html')
    
    from app.models.ranking import HitterRanking
    top_rankings = HitterRanking.query.order_by(HitterRanking.score.desc()).limit(3).all()
    
    return render_template('result_hit.html', result=analysis_result, hitter=hitter_info, filename=relative_filename, top_rankings=top_rankings)


@main_bp.route('/ranking')
def ranking():
    """AJAX 기반 단일 랭킹 화면의 틀을 렌더링합니다."""
    return render_template('ranking.html')


@main_bp.route('/mypage/<nickname>')
def mypage(nickname):
    """마이페이지 화면을 렌더링하고 사용자 분석 기록을 조회합니다."""
    user = User.query.filter_by(nickname=nickname).first_or_404()
    
    from app.models.analysis import Analysis
    analyses = Analysis.query.filter_by(user_id=user.id).order_by(Analysis.created_at.desc()).all()
    
    from app.models.ranking import PitcherRanking, HitterRanking
    best_pitch_record = PitcherRanking.query.filter_by(user_id=user.id).order_by(PitcherRanking.score.desc()).first()
    best_hit_record = HitterRanking.query.filter_by(user_id=user.id).order_by(HitterRanking.score.desc()).first()
    
    best_pitch = best_pitch_record.score if best_pitch_record else 0.0
    best_hit = best_hit_record.score if best_hit_record else 0.0
    
    return render_template('mypage.html', user=user, analyses=analyses, best_pitch=best_pitch, best_hit=best_hit)


@main_bp.route('/settings')
@login_required
def settings():
    """사용자 환경설정 화면을 렌더링합니다."""
    return render_template('settings.html')
