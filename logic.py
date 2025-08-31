import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
from urllib.parse import urlencode

# 認証情報を Secrets から取得
client_id = st.secrets["web"]["client_id"]
client_secret = st.secrets["web"]["client_secret"]
auth_uri = st.secrets["web"]["auth_uri"]
token_uri = st.secrets["web"]["token_uri"]

# Streamlit Cloud のリダイレクトURI（Google Cloud Consoleに登録済み）
redirect_uri = "https://<your-app>.streamlit.app"  # ← 実際のURLに置き換えてください

# Google Drive API のスコープ
scope = "https://www.googleapis.com/auth/drive.file"

# 認証URLの生成
params = {
    "client_id": client_id,
    "redirect_uri": redirect_uri,
    "response_type": "code",
    "scope": scope,
    "access_type": "offline",
    "prompt": "consent"
}
auth_url = f"{auth_uri}?{urlencode(params)}"
st.markdown(f"[🔐 Googleでログイン]({auth_url})")

# 認証コードの取得
query_params = st.experimental_get_query_params()
access_token = None

if "code" in query_params:
    code = query_params["code"][0]
    token_data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    token_response = requests.post(token_uri, data=token_data)
    token_json = token_response.json()
    access_token = token_json.get("access_token")

    if access_token:
        st.success("✅ 認証成功！")
    else:
        st.error("❌ 認証失敗")
        st.write(token_json)

# Google Drive にCSVをアップロードする関数
def upload_to_drive(access_token, filename, csv_data):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    metadata = {
        "name": filename,
        "mimeType": "application/vnd.google-apps.spreadsheet"
    }
    files = {
        "data": ("metadata", json.dumps(metadata), "application/json"),
        "file": ("file", csv_data, "text/csv")
    }
    response = requests.post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
        headers=headers,
        files=files
    )
    return response.status_code in [200, 201]

# 打刻処理
def record_punch(name, mode, access_token):
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    year = now.strftime("%Y")
    filename = f"{year}_timecard.csv"

    new_record = pd.DataFrame([{
        "名前": name,
        "モード": mode,
        "時刻": timestamp
    }])
    csv_data = new_record.to_csv(index=False).encode("utf-8")

    st.write(f"🕒 打刻時刻: {timestamp}")
    st.write(f"👤 名前: {name}, モード: {mode}")
    st.write(f"📤 Google Driveにアップロード中...")

    if upload_to_drive(access_token, filename, csv_data):
        st.success("✅ Google Driveに保存完了")
    else:
        st.error("❌ Google Driveへの保存に失敗しました")

    return timestamp

# UI：名前とモードの入力
if access_token:
    st.subheader("📝 打刻フォーム")
    name = st.text_input("名前を入力")
    mode = st.selectbox("モードを選択", ["出勤", "退勤"])

    if st.button("打刻する") and name and mode:
        record_punch(name, mode, access_token)
