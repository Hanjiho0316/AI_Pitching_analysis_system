####
## 좌투 우투 변경용 코드
####
import pandas as pd
import os
import glob

# ==============================
# 경로 설정
# ==============================
TARGET_DIR = r"C:\Users\kccistc\Desktop\workspace\project\2022eomsangbaek"

# 서로 값을 바꿀 관절 키워드 목록
BODY_PARTS = ['SHOULDER', 'ELBOW', 'WRIST', 'HIP', 'KNEE', 'ANKLE']

def swap_only_values_inplace(file_path):
    # 1. 데이터 읽기
    df = pd.read_csv(file_path)
    
    # 2. 복사본 생성 (원본 값을 참조하기 위함)
    temp_df = df.copy()
    
    # 3. L과 R 키워드가 들어간 컬럼값만 교체
    for part in BODY_PARTS:
        # 접미사별로 순환 (x, y, z, vis)
        for suffix in ['_x', '_y', '_z', '_vis']:
            l_col = f"L_{part}{suffix}"
            r_col = f"R_{part}{suffix}"
            
            # 해당 컬럼이 데이터에 존재하는지 확인 후 교체
            if l_col in df.columns and r_col in df.columns:
                # L컬럼에는 원래 R에 있던 값을 넣음
                df[l_col] = temp_df[r_col]
                # R컬럼에는 원래 L에 있던 값을 넣음
                df[r_col] = temp_df[l_col]
                
    # 4. 원본 파일에 덮어쓰기 (NOSE 등 다른 컬럼은 변경 없음)
    df.to_csv(file_path, index=False)

# ==============================
# 실행부
# ==============================
csv_files = glob.glob(os.path.join(TARGET_DIR, "*.csv"))

if not csv_files:
    print("파일을 찾을 수 없습니다.")
else:
    for file_path in csv_files:
        swap_only_values_inplace(file_path)
        print(f"값 교체 완료: {os.path.basename(file_path)}")

print("\n--- 지정된 관절의 L/R 값 교체가 완료되었습니다. ---")
