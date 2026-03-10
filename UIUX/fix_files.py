import os
import shutil
import re

# 1. 절대 경로 설정 (네 환경에 맞게 수정됨)
base_dir = r'C:\Users\kccistc\Desktop\proj\pitch_clips1'
video_target = r'C:\Users\kccistc\Documents\github\AI_Pitching_analysis_system\UIUX\app\static\images'
csv_target = r'C:\Users\kccistc\Documents\github\AI_Pitching_analysis_system\UIUX\app\services\data' # CSV 저장 폴더

os.makedirs(video_target, exist_ok=True)
os.makedirs(csv_target, exist_ok=True)

print("🚀 26명 선수 데이터 일괄 정리를 시작합니다...")

count = 0
for folder_name in os.listdir(base_dir):
    folder_path = os.path.join(base_dir, folder_name)
    
    if os.path.isdir(folder_path):
        # 숫자를 모두 제거해서 이름만 추출 (예: 2022Anwoojin.mp4 -> Anwoojin)
        clean_name = re.sub(r'[0-9.]', '', folder_name).replace('mp', '')
        
        # 🎥 동영상 복사 (pitch_skele_000.mp4)
        src_video = os.path.join(folder_path, 'pitch_skele_000.mp4')
        if os.path.exists(src_video):
            shutil.copy(src_video, os.path.join(video_target, f"{clean_name}.mp4"))
            
        # 📊 CSV 파일 복사 (pitch_skele_000.csv - 파일명이 같다면)
        # 만약 CSV 파일명이 다르다면 그 이름을 여기에 적어줘!
        src_csv = os.path.join(folder_path, 'pitch_skele_000.csv') 
        if os.path.exists(src_csv):
            shutil.copy(src_csv, os.path.join(csv_target, f"{clean_name}.csv"))
            
        print(f"✅ [{count+1}] 정리 완료: {clean_name}")
        count += 1

print(f"\n✨ 총 {count}명의 데이터가 정리되었습니다!")