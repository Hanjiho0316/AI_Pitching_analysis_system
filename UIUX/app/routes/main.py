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
from app.models.ranking import Ranking
from app.models.user import User


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """메인 화면을 렌더링합니다."""
    return render_template('index.html')


@main_bp.route('/upload')
def upload():
    """투구 영상 업로드 화면을 렌더링합니다."""
    return render_template('upload.html')

@main_bp.route('/battle')
def battle():
    """폼 대결 화면을 렌더링합니다."""
    return render_template('battle.html')


@main_bp.route('/result')
def result():
    """
    URL 파라미터로 전달된 task_id를 통해 
    분석 결과를 조회하고 결과 화면을 렌더링합니다.
    분석이 완료되지 않았거나 실패한 경우, 
    또는 유사도가 너무 낮은 경우 예외 처리를 수행합니다.
    """
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
    
    # 데이터베이스에서 점수 내림차순으로 상위 3명의 랭킹 데이터를 가져옵니다.
    top_rankings = Ranking.query.order_by(Ranking.score.desc()).limit(3).all()
    
    # 렌더링 시 top_rankings 데이터를 함께 전달합니다.
    return render_template('result.html', result=analysis_result, pitcher=pitcher_info, filename=relative_filename, top_rankings=top_rankings)


@main_bp.route('/ranking')
def ranking():
    """상위 10명의 랭킹 데이터를 점수 내림차순으로 가져옵니다."""
    top_rankings = Ranking.query.order_by(Ranking.score.desc()).limit(10).all()
    return render_template('ranking.html', rankings=top_rankings)


@main_bp.route('/mypage/<nickname>')
@login_required
def mypage(nickname):
    """닉네임을 통해 사용자 정보를 가져옵니다."""
    user = User.query.filter_by(nickname=nickname).first_or_404()
    
    # 다른 사람의 마이페이지 접근을 차단하고 싶다면 아래 주석을 해제하세요.
    # if current_user.nickname != nickname:
    #     flash('잘못된 접근입니다.')
    #     return redirect(url_for('main.index'))
        
    recent_analyses = Analysis.query.filter_by(user_id=user.id).order_by(Analysis.created_at.desc()).limit(10).all()
    
    return render_template('mypage.html', user=user, analyses=recent_analyses)


@main_bp.route('/settings')
@login_required
def settings():
    """사용자 환경설정 화면을 렌더링합니다."""
    return render_template('settings.html')
