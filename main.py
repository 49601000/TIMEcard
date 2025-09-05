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
from logic import (
    record_punch,
    save_refresh_token_to_drive,
    load_refresh_token_from_drive,
    get_access_token_from_refresh_token
)

# 初期化
if "access_token" not in st.session_state:
    st.session_state.access_token = None
# イニシャルトークン   
if "initial_access_token" not in st.session_state:
    st.session_state.initial_access_token = None

# 固定情報
staff_list = ["田中", "佐藤", "鈴木", "オプティカル"]
folder_id = "1-3Dc_yKjZQt8kJD_xlRFmuH4RKAxf_Jb"
client_id = st.secrets["web"]["client_id"]
client_secret = st.secrets["web"]["client_secret"]
token_uri = st.secrets["web"]["token_uri"]
redirect_uri = st.secrets["web"]["redirect_uri"]


if st.session_state.initial_access_token:
    saved_refresh_token = load_refresh_token_from_drive(
        access_token=st.session_state.initial_access_token,
        folder_id=folder_id
    )

# タイトル表示
show_title()

# 認証コードの取得
query_params = st.query_params
code = query_params.get("code", [None])[0]

# 初回認証フロー（codeがある場合）
if code:
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
    refresh_token = token_json.get("refresh_token")

    show_auth_status(access_token is not None, token_json)

    if access_token and refresh_token:
        # refresh_token を Drive に保存
        save_refresh_token_to_drive(refresh_token, access_token, folder_id)
    
    # ✅ 初回取得した access_token を session_state に保存
    st.write("🔍 認証コード:", code)
    st.session_state.access_token = access_token
    st.session_state.initial_access_token = access_token

# 自動認証フロー（codeがない場合）
elif st.session_state.access_token is None:
    try:
        # ✅ 初回保存した access_token を使って refresh_token.csv を読み込む
        if st.session_state.initial_access_token:
            saved_refresh_token = load_refresh_token_from_drive(
                access_token=st.session_state.initial_access_token,
                folder_id=folder_id
            )
        else:
            saved_refresh_token = None

        if saved_refresh_token:
            new_access_token = get_access_token_from_refresh_token(
                refresh_token=saved_refresh_token,
                client_id=st.secrets["web"]["client_id"],
                client_secret=st.secrets["web"]["client_secret"],
                token_uri=st.secrets["web"]["token_uri"]
            )
            st.write("🔍 refresh_token:", saved_refresh_token)
            st.write("🔍 client_id:", st.secrets["web"]["client_id"])
            st.write("🔍 client_secret:", st.secrets["web"]["client_secret"])
            st.write("🔍 token_uri:", st.secrets["web"]["token_uri"])
            
            st.session_state.access_token = new_access_token
            st.success("🔄 自動ログインに成功しました")

            st.session_state.access_token = new_access_token
            st.success("🔄 自動ログインに成功しました")
        else:
            show_login_link(client_id, redirect_uri)

    except Exception as e:
        st.error("❌ 自動認証に失敗しました")
        st.write(e)

        # 認証リンクを表示
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            "response_type=code&"
            "scope=https://www.googleapis.com/auth/drive.file&"
            "access_type=offline&"
            "prompt=consent"
        )
        st.markdown(f"[🔐 Google認証を開始する]({auth_url})")


# 認証済みなら打刻UIを表示
if st.session_state.access_token:
    name = user_selector(staff_list)
    punch_in, punch_out = punch_buttons()

    if punch_in and name:
        timestamp, success = record_punch(name, "出勤", st.session_state.access_token, folder_id)
        show_punch_result(name, timestamp, "in" if success else "error")

    if punch_out and name:
        timestamp, success = record_punch(name, "退勤", st.session_state.access_token, folder_id)
        show_punch_result(name, timestamp, "out" if success else "error")
