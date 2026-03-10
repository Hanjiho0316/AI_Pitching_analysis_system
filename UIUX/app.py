from app import create_app, db

# 팩토리 함수를 통해 앱 인스턴스를 생성합니다.
app = create_app()

# 애플리케이션 컨텍스트 안에서 데이터베이스 테이블을 생성합니다.
# 이미 pitching.db 파일과 테이블이 존재한다면 덮어쓰지 않고 넘어갑니다.
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # 개발 중에는 debug=True로 설정하여 코드 수정 시 서버가 자동 재시작되게 합니다.
    app.run(host='0.0.0.0', port=5000, debug=True)
