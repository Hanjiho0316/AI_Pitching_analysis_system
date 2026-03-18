"""
웹사이트의 화면 렌더링을 담당하는 메인 라우터 모듈입니다.
페이지 이동 및 분석 완료 후 결과 화면을 구성하기 위한 
데이터를 조회하여 템플릿에 전달합니다.
"""
import os
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from flask_login import login_required
from app.services.ml_service import get_task_status
from app.models.analysis import Analysis
from app.models.pitcher import Pitcher 
from app.models.hitter import Hitter
from app.models.ranking import PitcherRanking, HitterRanking
from app.models.user import User


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """
    서비스의 메인 화면을 렌더링합니다.
    투구 폼 분석과 타격 폼 분석으로 이동할 수 있는 분할 메뉴를 제공합니다.
    """
    return render_template('index.html')


@main_bp.route('/upload_pitch')
def upload_pitch():
    """
    투구 영상 업로드 화면을 렌더링합니다.
    촬영 가이드와 파일 업로드 폼을 제공합니다.
    """
    return render_template('upload_pitch.html')


@main_bp.route('/upload_hit')
def upload_hit():
   """
    타격 영상 업로드 화면을 렌더링합니다.
    촬영 가이드와 파일 업로드 폼을 제공합니다.
    """
   return render_template('upload_hit.html')


@main_bp.route('/battle')
def battle():
    """
    고스트 대결 메인 화면을 렌더링합니다.
    실시간으로 업데이트되는 다른 유저의 분석 기록 피드와 검색창을 제공합니다.
    """
    return render_template('battle.html')


@main_bp.route('/result_pitch')
def result_pitch():
    """
    투구 폼 분석 결과 화면을 렌더링합니다.
    
    URL 매개변수로 전달된 task_id를 통해 백그라운드 분석 결과를 조회하고,
    유사도 점수에 따라 성공 또는 실패(failure.html) 화면으로 분기합니다.
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
    analysis_id = task_info.get('analysis_id')
    
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
    
    if analysis_result['similarity'] < 3.0:
        return render_template('failure.html')
    
    from app.models.analysis import Analysis
    recent_analyses = Analysis.query.filter_by(analysis_type='pitch').order_by(Analysis.created_at.desc()).limit(3).all()
    
    return render_template('result_pitch.html', result=analysis_result, pitcher=pitcher_info, filename=relative_filename, recent_analyses=recent_analyses, analysis_id=analysis_id)


@main_bp.route('/result_hit')
def result_hit():
    """
    타격 폼 분석 결과 화면을 렌더링합니다.
    
    URL 매개변수로 전달된 task_id를 통해 백그라운드 분석 결과를 조회하고,
    유사도 점수에 따라 성공 또는 실패 화면으로 분기합니다.
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
    analysis_id = task_info.get('analysis_id')
    
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
    
    if analysis_result['similarity'] < 3.0:
        return render_template('failure.html')
    
    from app.models.analysis import Analysis
    recent_analyses = Analysis.query.filter_by(analysis_type='hit').order_by(Analysis.created_at.desc()).limit(3).all()
    
    return render_template('result_hit.html', result=analysis_result, hitter=hitter_info, filename=relative_filename, recent_analyses=recent_analyses, analysis_id=analysis_id)


@main_bp.route('/result_battle')
def result_battle():
    """
    고스트 대결 모드의 판정 결과를 연산하고 전용 결과 화면을 렌더링합니다.
    
    URL 매개변수로 전달된 본인의 task_id와 상대방의 target_id를 비교하여
    WIN, LOSE, DRAW 상태를 결정하고 양측의 선수 이미지 정보를 가공하여 전달합니다.
    """
    task_id = request.args.get('task_id')
    target_id = request.args.get('target_id')
    
    if not task_id or not target_id:
        flash('잘못된 대결 접근입니다.')
        return redirect(url_for('main.battle'))
        
    from app.services.ml_service import get_task_status
    task_info = get_task_status(task_id)
    
    if task_info['status'] != 'completed':
        flash('분석이 아직 완료되지 않았습니다.')
        return redirect(url_for('main.index'))

    my_result = task_info['result']
    my_score = my_result['similarity']
    my_type = task_info.get('analysis_type', 'pitch')
    
    target_record = Analysis.query.get(target_id)
    
    if not target_record:
        flash('상대방의 기록을 찾을 수 없습니다.')
        return redirect(url_for('main.battle'))
        
    target_score = target_record.similarity

    if my_score > target_score:
        match_result = "WIN"
    elif my_score < target_score:
        match_result = "LOSE"
    else:
        match_result = "DRAW"
        
    if target_record.analysis_type == 'pitch' and target_record.pitcher:
        target_player_name = target_record.pitcher.name_ko
        target_player_img = f"pitchers/{target_record.pitcher.name_en}.jpg"
    elif target_record.analysis_type == 'hit' and target_record.hitter:
        target_player_name = target_record.hitter.name_ko
        target_player_img = f"hitters/{target_record.hitter.name_en}.jpg"
    else:
        target_player_name = "알 수 없음"
        target_player_img = "default_logo.png"
        
    if my_type == 'hit':
        my_player = Hitter.query.filter_by(model_label=my_result['player_img']).first()
        my_folder = 'hitters'
    else:
        my_player = Pitcher.query.filter_by(model_label=my_result['player_img']).first()
        my_folder = 'pitchers'
        
    my_player_name = my_player.name_ko if my_player else my_result['match_player']
    my_player_img = f"{my_folder}/{my_player.name_en}.jpg" if my_player else "default_logo.png"
    
    return render_template('result_battle.html', 
                           my_score=my_score, my_player_name=my_player_name, my_player_img=my_player_img,
                           target=target_record, target_player_name=target_player_name, target_player_img=target_player_img,
                           match_result=match_result)


@main_bp.route('/ranking')
def ranking():
    """
    전체 랭킹 화면의 틀을 렌더링합니다.
    실제 랭킹 데이터는 프론트엔드에서 AJAX를 통해 동적으로 로드됩니다.
    """
    return render_template('ranking.html')


@main_bp.route('/mypage/<nickname>')
def mypage(nickname):
    """
    마이페이지 화면을 렌더링하고 사용자의 개인 분석 기록을 조회합니다.
    
    Args:
        nickname (str): 조회할 사용자의 닉네임
        
    Returns:
        조회된 사용자 정보, 누적 분석 리스트, 종목별 최고 점수를 포함한 템플릿
    """
    user = User.query.filter_by(nickname=nickname).first_or_404()
    
    analyses = Analysis.query.filter_by(user_id=user.id).order_by(Analysis.created_at.desc()).all()
    
    best_pitch_record = PitcherRanking.query.filter_by(user_id=user.id).order_by(PitcherRanking.score.desc()).first()
    best_hit_record = HitterRanking.query.filter_by(user_id=user.id).order_by(HitterRanking.score.desc()).first()
    
    best_pitch = best_pitch_record.score if best_pitch_record else 0.0
    best_hit = best_hit_record.score if best_hit_record else 0.0
    
    return render_template('mypage.html', user=user, analyses=analyses, best_pitch=best_pitch, best_hit=best_hit)


@main_bp.route('/settings')
@login_required
def settings():
    """
    사용자 환경설정 화면을 렌더링합니다.
    """
    return render_template('settings.html')


@main_bp.route('/roster')
def roster():
    """
    프로 선수 명단 화면을 렌더링합니다.
    데이터베이스에 저장된 투수와 타자 목록을 
    한글 이름(가나다) 순으로 정렬하고
    중복된 선수를 필터링하여 템플릿에 전달합니다.
    """
    pitchers_raw = Pitcher.query.order_by(Pitcher.name_ko.asc()).all()
    from app.models.hitter import Hitter
    hitters_raw = Hitter.query.order_by(Hitter.name_ko.asc()).all()

    seen_pitchers = set()
    pitchers = []
    for p in pitchers_raw:
        if p.name_ko not in seen_pitchers:
            seen_pitchers.add(p.name_ko)
            pitchers.append(p)

    # 타자 명단 중복 제거 (이름 기준)
    seen_hitters = set()
    hitters = []
    for h in hitters_raw:
        if h.name_ko not in seen_hitters:
            seen_hitters.add(h.name_ko)
            hitters.append(h)

    return render_template('roster.html', pitchers=pitchers, hitters=hitters)