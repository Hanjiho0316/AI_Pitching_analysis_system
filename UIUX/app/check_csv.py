import pandas as pd
import os

csv_dir = r'C:\Users\kccistc\Documents\github\AI_Pitching_analysis_system\UIUX\app\services\data'
print("📊 CSV 데이터 건강 검진 시작...")

for file in os.listdir(csv_dir):
    if file.endswith('.csv'):
        df = pd.read_csv(os.path.join(csv_dir, file))
        first_col = df.iloc[:, 0]
        # 데이터가 모두 0이거나 비어있는지 체크
        if first_col.sum() == 0:
            status = "❌ 데이터 없음 (전부 0)"
        elif len(df) < 10:
            status = "⚠️ 데이터 너무 짧음"
        else:
            status = f"✅ 정상 (데이터 {len(df)}줄)"
        
        print(f"[{file:<20}] {status}")