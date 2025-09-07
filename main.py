import streamlit as st
import requests
import json
from datetime import datetime
from ui import (
    show_title,
    user_selector,
    punch_buttons,
    show_auth_status,
    show_punch_result,
    show_login_link
)
from utils.auth_utis import (
    save_refresh_token_to_drive,
    load_refresh_token_from_drive,
    get_access_token_from_refresh_token,
    restore_access_token_if_needed
)
from logicMod import (
    record_punch,
    check_file_exists
)
# 🧩 Step 0: セッションステート初期化
if "code_used" not in st.session_state:
    st.session_state.code_used = False
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "initial_access_token" not in st.session_state:
    st.session_state.initial_access_token = None
    

# 📦 Step 1: 固定情報の取得
staff_list = ["田中", "佐藤", "鈴木", "オプティカル"]
folder_id = "1-3Dc_yKjZQt8kJD_xlRFmuH4RKAxf_Jb"
client_id = st.secrets["web"]["client_id"]
client_secret = st.secrets["web"]["client_secret"]
token_uri = st.secrets["web"]["token_uri"]
redirect_uri = st.secrets["web"]["redirect_uri"]

#st.write("📦 client_id:", client_id)
#st.write("🔐 client_secret:", client_secret[:4] + "••••••••")
#st.write("🌐 token_uri:", token_uri)
#st.write("↩️ redirect_uri:", redirect_uri)
#st.write("📁 folder_id:", folder_id)

restore_access_token_if_needed(client_id, client_secret, token_uri, folder_id)

# 🖼️ タイトル表示
show_title()

# 🔍 Step 2: 認証コードの取得
if "code_used" not in st.session_state:
    st.session_state.code_used = False
#st.write("🔍 全クエリパラメータ:", st.query_params)  # ← ここに入れる！
query_params = st.query_params
code = query_params.get("code")

if isinstance(code, list):
    code = code[0]

#st.write("🔍 認証コード:", code)

# 🚪 Step 3: 初回認証フロー（codeがある場合）
if code and not st.session_state.code_used:
    st.write("🚪 Step 3: 認証コードあり → access_token を取得します")

    token_data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    token_response = requests.post(token_uri, data=token_data)
    #st.write("🧾 トークンレスポンス:", token_response.text)  # ← Googleのレスポンスを確認

    token_json = token_response.json()
    access_token = token_json.get("access_token")
    refresh_token = token_json.get("refresh_token")

    show_auth_status(access_token is not None, token_json)

    #st.write("🔑 access_token:", access_token)
    #st.write("🔁 refresh_token:", refresh_token)

    if access_token and refresh_token:
        save_refresh_token_to_drive(refresh_token, access_token, folder_id)
        st.success("✅ refresh_token を Drive に保存しました")

    st.session_state.access_token = access_token
    st.session_state.initial_access_token = access_token
    st.session_state.code_used = True  # ✅ 再利用防止フラグ

    st.success("✅ access_token をセッションに保存しました")

    # ✅ 認証コードをURLから消す
    st.markdown("""
    <script>
      const url = new URL(window.location);
      url.searchParams.delete("code");
      window.history.replaceState({}, '', url);
    </script>
    """, unsafe_allow_html=True)

# 🔄 Step 4: 自動認証フロー（codeがない場合）
if st.session_state.access_token is None:
    st.write("🔄 Step 4: code がない → 自動認証フロー開始")

    try:
        # ✅ Step 4.1: refresh_token.csv を読み込み
        if st.session_state.initial_access_token:
            st.write("📥 Step 4.1: initial_access_token あり → refresh_token.csv を読み込みます")
            saved_refresh_token = load_refresh_token_from_drive(
                access_token=st.session_state.initial_access_token,
                folder_id=folder_id
            )
            st.write("📄 Step 4.2: refresh_token 読み込み結果:", saved_refresh_token)
        else:
            st.warning("⚠️ Step 4.1: initial_access_token が未設定です")
            saved_refresh_token = None

        # ✅ Step 4.3: refresh_token があれば access_token を再取得
        if saved_refresh_token:
            st.write("🚀 Step 4.3: access_token を再取得します")
            new_access_token = get_access_token_from_refresh_token(
                refresh_token=saved_refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                token_uri=token_uri
            )
            st.write("🔑 Step 4.4: 新しい access_token:", new_access_token)

            if new_access_token:
                st.session_state.access_token = new_access_token
                st.success("✅ Step 4.5: 自動ログインに成功しました")
            else:
                st.warning("⚠️ Step 4.4: access_token の取得に失敗しました")
                show_login_link(client_id, redirect_uri)  # ← ここで再ログインリンク表示
                show_auth_status(False, token_json={"error": "invalid_grant", "error_description": "Bad Request"})
                
        else:
            st.warning("⚠️ Step 4.3: refresh_token が取得できませんでした")
            show_login_link(client_id, redirect_uri)

    except Exception as e:
        st.error("❌ Step 4.X: 自動認証に失敗しました")
        st.write(e)

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
        
# 🔄 Step 5-1: セッション復元処理（access_token がなければ Drive から復元）
restore_access_token_if_needed(client_id, client_secret, token_uri, folder_id)

# 🕒 Step 5-2: access_token がある → 打刻UIを表示
if st.session_state.access_token:
    st.write("🕒 Step 5: access_token がある → 打刻UIを表示します")
    name = user_selector(staff_list)
    punch_in, punch_out = punch_buttons()

    if punch_in and name:
        timestamp, success, filename = record_punch(name, "出勤", st.session_state.access_token, folder_id)
        show_punch_result(name, timestamp, "in" if success else "error")
        check_file_exists(filename, st.session_state.access_token, folder_id)
        #エラーチェック
        st.write({
            "folder_id": folder_id,
            "filename": filename,
            "timestamp": timestamp,
            "success": success
        })

    if punch_out and name:
        timestamp, success, filename = record_punch(name, "退勤", st.session_state.access_token, folder_id)
        show_punch_result(name, timestamp, "out" if success else "error")
else:
    st.warning("⚠️ access_token が未取得のため、打刻UIは表示されません")
