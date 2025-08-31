import streamlit as st
import requests
import json
from ui import (
    show_title,
    user_selector,
    punch_buttons,
    show_auth_status,
    show_punch_result,
    show_login_link
)
from logic import record_punch

# スタッフリストとDriveフォルダID（必要に応じて変更）
staff_list = ["田中", "佐藤", "鈴木", "オプティカル"]
folder_id = "1-3Dc_yKjZQt8kJD_xlRFmuH4RKAxf_Jb"

# タイトル表示
show_title()

# 認証コードの取得（安全な方法）
query_params = st.query_params
code = query_params.get("code", [None])[0]
access_token = None

# 認証処理
if code:
    client_id = st.secrets["web"]["client_id"]
    client_secret = st.secrets["web"]["client_secret"]
    redirect_uri = "https://timecard-xvsby8ih4cxk6npxpyjmnf.streamlit.app/"
    token_uri = st.secrets["web"]["token_uri"]

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

    show_auth_status(access_token is not None, token_json)

# 認証済みなら打刻UIを表示
if access_token:
    name = user_selector(staff_list)
    punch_in, punch_out = punch_buttons()

    if punch_in and name:
        timestamp, success = record_punch(name, "出勤", access_token, folder_id)
        show_punch_result(name, timestamp, "in" if success else "error")

    if punch_out and name:
        timestamp, success = record_punch(name, "退勤", access_token, folder_id)
        show_punch_result(name, timestamp, "out" if success else "error")

# 未認証ならログインリンクを表示
else:
    client_id = st.secrets["web"]["client_id"]
    redirect_uri = "https://timecard-xvsby8ih4cxk6npxpyjmnf.streamlit.app/"
    show_login_link(client_id, redirect_uri)
