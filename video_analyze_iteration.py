from video_extract_interpolation import analyze_pitcher_video

import os

def video_analyze_iteration():
    DATA_DIR = "data"
    BASE_OUTPUT_DIR = "pitch_clips"

    if not os.path.exists(DATA_DIR):
        print(f"오류: {DATA_DIR} 디렉토리를 찾을 수 없습니다.")
        return

    # 영상 파일 목록 추출
    valid_extensions = ('.mp4', '.avi', '.mkv', '.mov')
    video_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(valid_extensions)]

    for video_name in video_files:
        target_output_path = os.path.join(BASE_OUTPUT_DIR, video_name)

        if os.path.isdir(target_output_path):
            # 이미 폴더가 있다면 분석 완료로 간주하고 스킵
            continue

        print(f"새 분석 시작: {video_name}")
        try:
            # 이전에 만든 함수 호출
            analyze_pitcher_video(video_name)
        except Exception as e:
            print(f"오류 발생 ({video_name}): {e}")

if __name__ == "__main__":
    video_analyze_iteration()