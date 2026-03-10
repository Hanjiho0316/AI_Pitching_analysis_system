import os
import shutil
import re

# 1. 경로 설정
base_dir = r"C:\Users\kccistc\Desktop\proj\pitch_clips1"
target_dir = r'C:\Users\kccistc\Documents\github\AI_Pitching_analysis_system\UIUX\app\static\images'

if not os.path.exists(target_dir):
    os.makedirs(target_dir)

print("🚀 26명 전원 검거 작전을 시작합니다...")

count = 0
for folder_name in os.listdir(base_dir):
    folder_path = os.path.join(base_dir, folder_name)
    
    if os.path.isdir(folder_path):
        # 선수 이름 정리 (연도 제거, .mp4 제거)
        clean_name = re.sub(r'\d{4}', '', folder_name)
        clean_name = clean_name.replace('.mp4', '').strip()
        
        # 🚨 [수정 포인트] 폴더 안을 뒤져서 '가장 먼저 나오는 .mp4 파일' 찾기
        found_video = None
        for file in os.listdir(folder_path):
            if file.lower().endswith('.mp4'):
                found_video = file
                break
        
        if found_video:
            src_file = os.path.join(folder_path, found_video)
            dest_file = os.path.join(target_dir, f"{clean_name}.mp4")
            shutil.copy(src_file, dest_file)
            print(f"✅ [{count+1}] 성공: {folder_name} -> {clean_name}.mp4")
            count += 1
        else:
            print(f"❌ 실패: {folder_name} (폴더 안에 mp4 파일 자체가 없음)")

print(f"\n✨ 작전 완료! 총 {count}명의 영상이 입고되었습니다.")