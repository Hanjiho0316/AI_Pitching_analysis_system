"""
어플리케이션의 실행을 담당하는 메인 스크립트입니다.
앱 컨텍스트를 활성화하여 DB 테이블을 생성하고 개발 서버를 가동합니다.
"""

from app import create_app, db

# 팩토리 함수를 통해 앱 인스턴스를 생성합니다.
app = create_app()

# 애플리케이션 컨텍스트 안에서 데이터베이스 테이블을 생성합니다.
# 이미 pitching.db 파일과 테이블이 존재한다면 덮어쓰지 않고 넘어갑니다.
with app.app_context():
    from app.models.analysis import Analysis
    from app.models.pitcher import Pitcher
    from app.models.ranking import Ranking
    from app.models.user import User
    db.create_all()

if __name__ == '__main__':
    # 외부 접속 허용을 위해 0.0.0.0 호스트로 5000번 포트에서 실행합니다.
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
