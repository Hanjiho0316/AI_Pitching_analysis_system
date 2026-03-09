import streamlit as st
import pandas as pd
import numpy as np
import math
import os
import glob
import matplotlib.pyplot as plt

# ==========================================
# 📋 0. 데이터 설정 및 한글 이름 매핑
# ==========================================
PLAYER_NAMES = {
    "2013Leejaehak": "이재학", "2014Hanhyunhee": "한현희", "2014Yunsungwhan": "윤성환",
    "2015Clayton": "클레이튼 커쇼", "2015Eric_hacker": "에릭 해커", "2015Josangwoo": "조상우",
    "2015Youheekwan": "유희관", "2016Andrewmiller": "앤드류 밀러", "2016Dustinnipurt": "더스틴 니퍼트",
    "2016Limchangmin": "임창민", "2017Brooks": "브룩스 레일리", "2017Merrillkelly": "메릴 켈리",
    "2017Ryan": "라이언 피어밴드", "2017Yanghyunjong": "양현종", "2018Henrysosa": "헨리 소사",
    "2018Kimtaehoon": "김태훈", "2018Parkjonghoon": "박종훈", "2020Baejaesung": "배제성",
    "2020Guchangmo": "구창모", "2020Sohyungjun": "소형준", "2021Baekjunghyun": "백정현",
    "2021Goyoungpo": "고영표", "2021Kimjaeyoon": "김재윤", "2022Anwoojin": "안우진",
    "2022Guseungmin": "구승민", "2022Wilmerfont": "윌머 폰트", "2023Ericpaddy": "에릭 페디",
    "2023Kawkbin": "곽빈", "2023Moondongju": "문동주", "2023Nagyunan": "나균안",
}

# 좌완 투수 판별을 위한 키워드
LEFTY_HINTS = ["2015Clayton", "2016Andrewmiller", "2017Brooks", "2017Ryan", "2017Yanghyunjong", "2018Kimtaehoon", "2020Guchangmo", "2021Baekjunghyun", "2015Youheekwan"]

# ==========================================
# 📐 1. 핵심 분석 알고리즘
# ==========================================
def calculate_angle(x1, y1, x2, y2, x3, y3):
    if pd.isna([x1, y1, x2, y2, x3, y3]).any(): return np.nan
    angle = math.degrees(math.atan2(y3 - y2, x3 - x2) - math.atan2(y1 - y2, x1 - x2))
    angle = abs(angle)
    if angle > 180: angle = 360 - angle
    return angle

def get_line_angle(x1, y1, x2, y2):
    if pd.isna([x1, y1, x2, y2]).any(): return np.nan
    return math.degrees(math.atan2(y2 - y1, x2 - x1))

def calculate_similarity(s1, s2):
    min_len = min(len(s1), len(s2))
    if min_len < 10: return 0
    corr = np.corrcoef(s1[:min_len], s2[:min_len])[0, 1]
    return max(0, corr * 100) if not np.isnan(corr) else 0

# ==========================================
# 💎 2. UX/UI 디자인 (CSS)
# ==========================================
st.set_page_config(layout="wide", page_title="AI Pitching Lab Pro", page_icon="⚾")
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif; }
    .main { background-color: #fcfcfc; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .stVideo { border-radius: 12px; overflow: hidden; border: 1px solid #cbd5e1; }
    .recommend-card { background-color: #f1f5f9; padding: 20px; border-radius: 15px; border-left: 5px solid #38bdf8; margin-bottom: 10px; }
    h1 { color: #1e293b; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

st.title("🔬 AI PITCHING PRO ANALYTICS")
st.markdown("<p style='color:#64748b; font-size: 1.1rem;'>상하체 분리, 보폭 및 부상 위험도 정밀 분석 시스템</p>", unsafe_allow_html=True)
st.write("---")

tab1, tab2, tab3 = st.tabs(["🎯 정밀 분석 스튜디오", "🤝 선수 폼 비교", "🧹 데이터 검수 센터"])

BASE_DIR = "pitch_clips"

# ---------------------------------------------------------
# 🎯 TAB 1: 정밀 분석 스튜디오 (X-Factor, Stride, AI 추천)
# ---------------------------------------------------------
with tab1:
    pitcher_list = [f for f in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, f))] if os.path.exists(BASE_DIR) else []
    
    if not pitcher_list:
        st.error("🚨 데이터를 찾을 수 없습니다. 경로를 확인하세요.")
    else:
        with st.sidebar:
            st.markdown("### 🛠️ CONTROL PANEL")
            # 한글 이름 매핑 사전 구축
            display_to_origin = {}
            for folder in pitcher_list:
                kor = next((v for k, v in PLAYER_NAMES.items() if k.lower() in folder.lower()), folder)
                display_to_origin[kor] = folder
            
            selected_display = st.selectbox("분석 대상 선택", list(display_to_origin.keys()))
            selected_origin = display_to_origin[selected_display]
            TEST_DIR = os.path.join(BASE_DIR, selected_origin)
            csv_paths = sorted(glob.glob(os.path.join(TEST_DIR, "pitch_data_*.csv")))
            
            if csv_paths:
                clip_opts = [os.path.basename(f).replace("pitch_data_", "").replace(".csv", "") for f in csv_paths]
                selected_clip = st.select_slider("시퀀스 선택", options=clip_opts)

        if csv_paths:
            df = pd.read_csv(os.path.join(TEST_DIR, f"pitch_data_{selected_clip}.csv"))
            is_l = any(h.lower() in selected_origin.lower() for h in LEFTY_HINTS)
            arm = "L" if is_l else "R"

            # 📏 바이오메카닉스 계산
            # 1. 팔꿈치 각도
            df['elbow_ang'] = df.apply(lambda r: calculate_angle(r[f'{arm}_SHOULDER_x'], r[f'{arm}_SHOULDER_y'], r[f'{arm}_ELBOW_x'], r[f'{arm}_ELBOW_y'], r[f'{arm}_WRIST_x'], r[f'{arm}_WRIST_y']), axis=1)
            min_elbow = df['elbow_ang'].min()
            
            # 2. X-Factor (상하체 꼬임)
            df['shoulder_ang'] = df.apply(lambda r: get_line_angle(r['L_SHOULDER_x'], r['L_SHOULDER_y'], r['R_SHOULDER_x'], r['R_SHOULDER_y']), axis=1)
            df['hip_ang'] = df.apply(lambda r: get_line_angle(r['L_HIP_x'], r['L_HIP_y'], r['R_HIP_x'], r['R_HIP_y']), axis=1)
            df['x_factor'] = abs(df['shoulder_ang'] - df['hip_ang'])
            max_xfactor = df['x_factor'].max()

            # 3. 보폭 (Stride)
            df['stride'] = np.sqrt((df['L_ANKLE_x'] - df['R_ANKLE_x'])**2 + (df['L_ANKLE_y'] - df['R_ANKLE_y'])**2)
            max_stride = df['stride'].max()

            # 4. 부상 위험도 점수화
            risk_score = 0
            if min_elbow < 65: risk_score += 40
            if max_xfactor > 55: risk_score += 20
            risk_status = "🚨 고위험" if risk_score >= 50 else "⚠️ 주의" if risk_score >= 30 else "✅ 안전"

            # --- UI 레이아웃 ---
            st.subheader(f"📋 {selected_display} 선수 바이오메카닉스 리포트")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("종합 부상 위험도", risk_status)
            c2.metric("최대 X-Factor", f"{int(max_xfactor)}°")
            c3.metric("최소 팔꿈치 각도", f"{int(min_elbow)}°")
            c4.metric("최대 보폭 지수", f"{round(max_stride, 2)}")

            st.write("---")
            v_col, f_col = st.columns([1.2, 1])
            with v_col:
                st.video(os.path.join(TEST_DIR, f"pitch_skele_{selected_clip}.mp4"))
            
            with f_col:
                st.markdown("#### 💡 AI 분석 피드백")
                st.info(f"**상하체 분리:** 최대 {int(max_xfactor)}°의 꼬임을 형성하고 있습니다.")
                st.info(f"**보폭 분석:** 하체 보폭 지수는 {round(max_stride, 2)}로 측정되었습니다.")
                if min_elbow < 65: st.error("🚨 팔꿈치 각도가 너무 좁아 부상 위험이 높습니다.")
                else: st.success("✅ 안정적인 팔꿈치 궤적을 유지하고 있습니다.")
                
                # 리포트 다운로드
                report_csv = df[['elbow_ang', 'x_factor', 'stride']].to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 정밀 분석 데이터(CSV) 저장", report_csv, f"{selected_display}_Report.csv", "text/csv")

            # AI 도플갱어 추천
            st.write("---")
            if st.button("🚀 나랑 가장 닮은 프로 선수 찾기"):
                matches = []
                curr_angles = df['elbow_ang'].dropna().tolist()
                for other in pitcher_list:
                    if other == selected_origin: continue
                    other_csvs = glob.glob(os.path.join(BASE_DIR, other, "pitch_data_*.csv"))
                    if not other_csvs: continue
                    t_df = pd.read_csv(other_csvs[0])
                    t_isl = any(h.lower() in other.lower() for h in LEFTY_HINTS)
                    t_arm = "L" if t_isl else "R"
                    t_angs = t_df.apply(lambda r: calculate_angle(r[f'{t_arm}_SHOULDER_x'], r[f'{t_arm}_SHOULDER_y'], r[f'{t_arm}_ELBOW_x'], r[f'{t_arm}_ELBOW_y'], r[f'{t_arm}_WRIST_x'], r[f'{t_arm}_WRIST_y']), axis=1).dropna().tolist()
                    score = calculate_similarity(curr_angles, t_angs)
                    o_kor = next((v for k, v in PLAYER_NAMES.items() if k.lower() in other.lower()), other)
                    matches.append({"name": o_kor, "score": score})
                
                matches = sorted(matches, key=lambda x: x['score'], reverse=True)[:3]
                rc1, rc2, rc3 = st.columns(3)
                for i, res in enumerate(matches):
                    with [rc1, rc2, rc3][i]:
                        st.markdown(f"""<div class="recommend-card"><h4>TOP {i+1} Match</h4><h2 style='color:#0ea5e9;'>{res['name']}</h2><p>유사도: <b>{int(res['score'])}%</b></p></div>""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 🤝 TAB 2: 선수 폼 비교 (1:1 Side-by-Side)
# ---------------------------------------------------------
with tab2:
    st.subheader("🤝 선수 간 투구 메커니즘 1:1 비교")
    if len(pitcher_list) >= 2:
        names = list(display_to_origin.keys())
        cc1, cc2 = st.columns(2)
        with cc1:
            p1_d = st.selectbox("선수 A 선택", names, key="p1")
            p1_o = display_to_origin[p1_d]
            p1_c = st.selectbox("A 시퀀스", [os.path.basename(f).replace("pitch_data_", "").replace(".csv", "") for f in glob.glob(os.path.join(BASE_DIR, p1_o, "pitch_data_*.csv"))], key="p1c")
        with cc2:
            p2_d = st.selectbox("선수 B 선택", names, key="p2", index=1 if len(names)>1 else 0)
            p2_o = display_to_origin[p2_d]
            p2_c = st.selectbox("B 시퀀스", [os.path.basename(f).replace("pitch_data_", "").replace(".csv", "") for f in glob.glob(os.path.join(BASE_DIR, p2_o, "pitch_data_*.csv"))], key="p2c")

        if p1_c and p2_c:
            def get_data(p, c):
                d = pd.read_csv(os.path.join(BASE_DIR, p, f"pitch_data_{c}.csv"))
                isl = any(h.lower() in p.lower() for h in LEFTY_HINTS)
                arm_s = "L" if isl else "R"
                ang = d.apply(lambda r: calculate_angle(r[f'{arm_s}_SHOULDER_x'], r[f'{arm_s}_SHOULDER_y'], r[f'{arm_s}_ELBOW_x'], r[f'{arm_s}_ELBOW_y'], r[f'{arm_s}_WRIST_x'], r[f'{arm_s}_WRIST_y']), axis=1).dropna().tolist()
                return ang, os.path.join(BASE_DIR, p, f"pitch_skele_{c}.mp4")

            d1, v1 = get_data(p1_o, p1_c)
            d2, v2 = get_data(p2_o, p2_c)
            st.metric("투구 메커니즘 유사도", f"{int(calculate_similarity(d1, d2))}%")
            vc1, vc2 = st.columns(2)
            vc1.video(v1); vc2.video(v2)
            
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.plot(d1, label=p1_d, color='#38bdf8', linewidth=2)
            ax.plot(d2, label=p2_d, color='#fb7185', linewidth=2)
            ax.set_ylabel("Angle (°)"); ax.legend(); st.pyplot(fig)

# ---------------------------------------------------------
# 🧹 TAB 3: 데이터 검수 센터 (초강력 검수 모드)
# ---------------------------------------------------------
with tab3:
    st.subheader("🧹 전수 데이터 품질 검수 (강화 모드)")
    st.write("뼈대가 아예 없거나, 중간에 단 1프레임이라도 깜빡거리고 사라지는 불량 파일들을 모두 찾아냅니다.")
    
    if st.button("🚨 강력한 불량 데이터 스캔 시작"):
        bad_list = []
        bar = st.progress(0)
        
        for i, p in enumerate(pitcher_list):
            csvs = glob.glob(os.path.join(BASE_DIR, p, "pitch_data_*.csv"))
            for c in csvs:
                d = pd.read_csv(c)
                isl = any(h.lower() in p.lower() for h in LEFTY_HINTS)
                side = "L" if isl else "R"
                
                # 💡 [핵심] 검수 기준 초강력 업그레이드!
                total_frames = len(d)
                # 팔꿈치 좌표가 하나라도 비어있는(NaN) 프레임의 개수
                missing_frames = d[f'{side}_ELBOW_x'].isnull().sum()
                
                # 불량 사유 판별
                reason = ""
                if total_frames < 15:
                    reason = f"너무 짧은 영상 ({total_frames}프레임)"
                elif missing_frames > 0:
                    reason = f"중간에 뼈대 사라짐 ({missing_frames}프레임 누락)"
                
                # 불량 사유가 하나라도 있다면 리스트에 추가
                if reason:
                    c_id = os.path.basename(c).replace("pitch_data_", "").replace(".csv", "")
                    # 한글 이름 찾기
                    k_name = p
                    for key, val in PLAYER_NAMES.items():
                        if key.lower() in p.lower(): 
                            k_name = val
                            break
                    bad_list.append({"투수": k_name, "클립": c_id, "사유": reason})
                    
            bar.progress((i + 1) / len(pitcher_list))
        
        if bad_list:
            st.error(f"🚨 총 {len(bad_list)}개의 불량 데이터를 찾아냈습니다!")
            st.dataframe(bad_list, use_container_width=True)
            st.info("💡 위 리스트에 나온 번호들을 마저 폴더에서 지워주세요! (뼈대가 끊기면 분석 그래프가 망가집니다)")
        else: 
            st.success("🎉 완벽합니다! 뼈대가 끊기는 데이터가 하나도 없이 100% 깨끗합니다!")
