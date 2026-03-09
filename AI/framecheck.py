import os
import glob
import pandas as pd
import streamlit as st

def check_data_quality(pitcher_list, base_dir, lefty_hints, player_names):
    """
    전수 데이터의 품질을 검수하고 결함이 있는 데이터 목록을 반환합니다.
    """
    bad_data_list = []
    
    for pitcher_dir in pitcher_list:
        # 해당 투수의 모든 csv 파일 경로 가져오기
        csv_files = glob.glob(os.path.join(base_dir, pitcher_dir, "pitch_data_*.csv"))
        
        # 좌투/우투 판별 (Hint 리스트 기반)
        is_lefty = any(hint.lower() in pitcher_dir.lower() for hint in lefty_hints)
        side_prefix = "L" if is_lefty else "R"
        target_col = f'{side_prefix}_ELBOW_x'
        
        for file_path in csv_files:
            try:
                # 성능을 위해 필요한 컬럼만 로드 (target_col)
                df = pd.read_csv(file_path)
                
                # 검수 조건: 1. 특정 좌표 전체 결측치(NaN) 이거나 2. 데이터 길이가 10 미만인 경우
                is_unrecognizable = df[target_col].isnull().all()
                is_too_short = len(df) < 10
                
                if is_unrecognizable or is_too_short:
                    # 파일명에서 클립 ID 추출
                    clip_id = os.path.basename(file_path).replace("pitch_data_", "").replace(".csv", "")
                    
                    # PLAYER_NAMES 딕셔너리에서 한글 이름 매핑 (없으면 폴더명 사용)
                    display_name = next(
                        (val for key, val in player_names.items() if key.lower() in pitcher_dir.lower()), 
                        pitcher_dir
                    )
                    
                    bad_data_list.append({
                        "투수": display_name,
                        "클립": clip_id,
                        "사유": "인식 불가" if is_unrecognizable else "데이터 부족"
                    })
            except Exception as e:
                st.error(f"파일 로드 오류 ({file_path}): {e}")
                
    return bad_data_list

# --- Streamlit UI 부분 ---
with tab3:
    st.subheader("🔍 전수 데이터 품질 검수")
    st.info("시스템 내의 모든 투구 데이터를 스캔하여 결측치 및 유효성을 검사합니다.")

    if st.button("🚀 시스템 전수 스캔 시작"):
        with st.spinner("데이터를 분석 중입니다..."):
            # 함수 호출
            bad_results = check_data_quality(pitcher_list, BASE_DIR, LEFTY_HINTS, PLAYER_NAMES)
        
        if bad_results:
            st.warning(f"총 {len(bad_results)}건의 결함 데이터가 발견되었습니다.")
            st.dataframe(pd.DataFrame(bad_results), use_container_width=True)
        else:
            st.success("✅ 모든 데이터가 정상입니다!")
