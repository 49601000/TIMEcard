import streamlit as st
from ui import user_selector, punch_buttons
from logic import record_punch

staff_list = ["田中", "佐藤", "鈴木", "オプティカル"]

st.title("🕒 タイムカード打刻")

# 認証コードの取得
query_params = st.query_params
code = query_params.get("code", [None])[0]  # ← 安全なアクセス方法

if "code" in query_params:
    # トークン取得処理（client_id などは st.secrets から取得）
    import requests
    import json

    client_id = st.secrets["web"]["client_id"]
    client_secret = st.secrets["web"]["client_secret"]
    redirect_uri = "https://timecard-xvsby8ih4cxk6npxpyjmnf.streamlit.app/"
    token_uri = st.secrets["web"]["token_uri"]

    token_data = {
        "code": query_params["code"][0],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    token_response = requests.post(token_uri, data=token_data)
    token_json = token_response.json()
    access_token = token_json.get("access_token")

    if access_token:
        st.success("✅ Google認証に成功しました")
    else:
        st.error("❌ 認証失敗")
        st.write(token_json)
