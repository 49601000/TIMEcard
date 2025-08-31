import pandas as pd
from datetime import datetime
import os

def record_punch(name, mode):
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    year = now.strftime("%Y")

    # 保存先のOneDriveパス（必要に応じて環境変数化も可）
    base_dir = r"C:\Users\info\OneDrive\3_マトイコーヒー\アルバイト_給与関係\TIMECARD"
    filename = f"{year}_timecard.csv"
    filepath = os.path.join(base_dir, filename)

    # 新しいレコード
    new_record = pd.DataFrame([{
        "名前": name,
        "モード": mode,
        "時刻": timestamp
    }])

    # ファイルが存在すれば追記、なければ新規作成
    if os.path.exists(filepath):
        existing = pd.read_csv(filepath)
        updated = pd.concat([existing, new_record], ignore_index=True)
    else:
        updated = new_record

    # 保存
    updated.to_csv(filepath, index=False)
    return timestamp
