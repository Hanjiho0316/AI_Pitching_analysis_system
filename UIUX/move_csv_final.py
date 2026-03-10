import os
import shutil
import re

# 1. 경로 설정 (절대 경로)
base_dir = r'C:\Users\kccistc\Desktop\proj\pitch_clips1'
csv_target = r'C:\Users\kccistc\Documents\github\AI_Pitching_analysis_system\UIUX\app\services\data'

# 목적지 폴더 생성
os.makedirs(csv_target, exist_ok=True)

print("📊 pitch_data_*.csv 파일을 수색하여 선수 이름으로 바꿉니다...")

count = 0
for folder_name in os.listdir(base_dir):
    folder_path = os.path.join(base_dir, folder_name)
    
    if os.path.isdir(folder_path):
        # 폴더명에서 연도 및 불필요한 글자 제거 (예: 2022Anwoojin.mp4 -> Anwoojin)
        # re.sub를 이용해 숫자와 .mp4 등을 깔끔하게 제거
        clean_name = re.sub(r'[0-9.]', '', folder_name).replace('mp', '')
        
        # 🚨 폴더 안에서 pitch_data_로 시작하는 CSV 파일 찾기
        found_csv = False
        for file in os.listdir(folder_path):
            if file.startswith('pitch_data_') and file.lower().endswith('.csv'):
                src_path = os.path.join(folder_path, file)
                dest_path = os.path.join(csv_target, f"{clean_name}.csv")
                
                shutil.copy(src_path, dest_path)
                print(f"✅ [{count+1}] 발견: {folder_name}/{file} -> {clean_name}.csv")
                found_csv = True
                count += 1
                break
        
        if not found_csv:
            print(f"⚠️  경고: {folder_name} 폴더에 pitch_data_*.csv 파일이 없습니다!")

print(f"\n✨ 총 {count}개의 CSV 파일이 'app/services/data/' 폴더로 입고되었습니다!")