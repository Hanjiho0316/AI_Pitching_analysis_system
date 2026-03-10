from app import create_app

# __init__.py에서 정의한 팩토리 함수로 앱 생성
app = create_app()

if __name__ == '__main__':
    # host='0.0.0.0' 설정을 통해 같은 와이파이를 쓰는 스마트폰에서도 접속 가능하게 합니다.
    # 개발 중에는 debug=True로 설정하여 코드 수정 시 서버가 자동 재시작되게 합니다.
    app.run(port=5000, debug=True)