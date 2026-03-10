import pandas as pd
import os

csv_path = r'C:\Users\kccistc\Documents\github\AI_Pitching_analysis_system\UIUX\app\services\data\Anwoojin.csv'
df = pd.read_csv(csv_path)

print("📂 CSV 컬럼 목록:", df.columns.tolist())
print("\n📂 상위 5줄 데이터:")
print(df.head())