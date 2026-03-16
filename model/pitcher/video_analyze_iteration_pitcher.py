# from video_extract_interpolation import analyze_pitcher_video <-- 미디어파이프
from video_extract_interpolation_pitcher import analyze_pitcher_video  # <-- YOLOv8n
import os

def video_analyze_iteration():
    DATA_DIR = "pitch_clips"
    BASE_OUTPUT_DIR = f"pitch_clips/yolo_exp"

    if not os.path.exists(DATA_DIR):
        print(f"오류: {DATA_DIR} 디렉토리를 찾을 수 없습니다.")
        return

    # 영상 파일 목록 추출
    valid_extensions = ('.mp4', '.avi', '.mkv', '.mov')
    video_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(valid_extensions)]

    for folder_name in os.listdir(DATA_DIR):
        folder_path = os.path.join(DATA_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue
        target_output_path = os.path.join(BASE_OUTPUT_DIR, folder_name)
        if os.path.isdir(target_output_path):
            print(f"이미 분석 완료, 스킵: {folder_name}")
            continue
        
        video_files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)]
    
        for video_name in video_files:
            target_output_path = os.path.join(BASE_OUTPUT_DIR, folder_name, video_name)
            if os.path.isfile(target_output_path):
                continue
            
            print(f"새 분석 시작: {folder_name}/{video_name}")
            try:
                analyze_pitcher_video(folder_name, video_name)
            except Exception as e:
                print(f"오류 발생 ({video_name}): {e}")

if __name__ == "__main__":
    video_analyze_iteration()
