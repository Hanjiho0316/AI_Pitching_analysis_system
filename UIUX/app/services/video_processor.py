import os
import random

def analyze_user_video(video_path):
    # 나중에 여기에 우리가 만든 YOLO + MediaPipe (STEP 1) 코드가 들어올 거야!
    # 지금은 웹사이트 화면이 잘 넘어가는지 테스트하기 위해 가짜 데이터를 뱉게 해뒀어.
    
    dummy_xfactor = random.randint(40, 65)
    dummy_elbow = random.randint(50, 90)
    
    risk_status = "✅ 안전"
    if dummy_elbow < 65: risk_status = "🚨 위험 (토미존 경고!)"
    
    return {
        "x_factor": dummy_xfactor,
        "elbow_angle": dummy_elbow,
        "risk_status": risk_status,
        "feedback": "릴리스 포인트가 살짝 낮습니다. 하체를 더 끌고 나오세요!"
    }