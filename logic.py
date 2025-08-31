import pandas as pd
from datetime import datetime
import os
import streamlit as st
def record_punch(name, mode):
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    year = now.strftime("%Y")

    base_dir = r"C:\Users\info\OneDrive\3_マトイコーヒー\アルバイト_給与関係\TIMECARD"
    filename = f"{year}_timecard.csv"
    filepath = os.path.join(base_dir, filename)

    st.write(f"📁 保存先パス: {filepath}")
    st.write(f"🕒 打刻時刻: {timestamp}")
    st.write(f"👤 名前: {name}, モード: {mode}")

    new_record = pd.DataFrame([{
        "名前": name,
        "モード": mode,
        "時刻": timestamp
    }])

    if os.path.exists(filepath):
        st.write("📄 既存ファイルを読み込み中...")
        existing = pd.read_csv(filepath)
        updated = pd.concat([existing, new_record], ignore_index=True)
    else:
        st.write("📄 新規ファイルを作成します")
        updated = new_record

    os.makedirs(base_dir, exist_ok=True)
    updated.to_csv(filepath, index=False)
    st.write("✅ CSV保存完了")

    return timestamp
