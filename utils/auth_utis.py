import streamlit as st
import pandas as pd
import requests
import json
import base64
from datetime import datetime
from io import StringIO, BytesIO
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from utils.error_utils import log_error_to_drive

# 🔐 1. refresh_token を Drive に保存（上書き対応）
def save_refresh_token_to_drive(refresh_token, access_token, folder_id):
    try:
        creds = Credentials(token=access_token)
        service = build("drive", "v3", credentials=creds)

        query = f"'{folder_id}' in parents and name='refresh_token.csv'"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])

        # 🔐 Base64で暗号化
        encoded_token = base64.b64encode(refresh_token.encode("utf-8")).decode("utf-8")
        csv_content = f"refresh_token\n{encoded_token}"
        media = MediaIoBaseUpload(StringIO(csv_content), mimetype="text/csv")

        if files:
            file_id = files[0]["id"]
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {
                "name": "refresh_token.csv",
                "parents": [folder_id],
                "mimeType": "text/csv"
            }
            service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    except Exception as e:
        st.error("❌ エラーをlogに保存しました")
        log_error_to_drive(str(e), access_token, "1ID1-LS6_kU5l7h1VRHR9RaAAZyUkIHIt")


# 📥 2. Driveから refresh_token.csv を読み込む
def load_refresh_token_from_drive(access_token, folder_id):
    try:
        creds = Credentials(token=access_token)
        service = build("drive", "v3", credentials=creds)

        query = f"'{folder_id}' in parents and name='refresh_token.csv'"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])

        if not files:
            log_error_to_drive("refresh_token.csv が Drive に存在しません", access_token, folder_id)
            return None

        file_id = files[0]["id"]
        request = service.files().get_media(fileId=file_id)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        
        df = pd.read_csv(fh)
        
        # 🔓 Base64復号処理
        encoded_token = df["refresh_token"].iloc[0]
        decoded_token = base64.b64decode(encoded_token.encode("utf-8")).decode("utf-8")
        return decoded_token
        
    except Exception as e:
        st.error("❌ エラーをlogに保存しました")
        log_error_to_drive(str(e), access_token, "1ID1-LS6_kU5l7h1VRHR9RaAAZyUkIHIt")
        return None

# 🔄 3. refresh_token から access_token を再取得
def get_access_token_from_refresh_token(refresh_token, client_id, client_secret, token_uri, folder_id=None):
    try:
        refresh_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        response = requests.post(token_uri, data=refresh_data)
        response.raise_for_status()
        token_json = response.json()

        access_token = token_json.get("access_token")
        expires_in = token_json.get("expires_in")  # 秒数（例：3600）

        if access_token and expires_in:
            from pytz import timezone
            expires_at = datetime.now(timezone("Asia/Tokyo")) + pd.to_timedelta(expires_in, unit="s")
            return access_token, expires_at
        else:
            st.warning("⚠️ トークンレスポンスに access_token または expires_in が含まれていません")
            st.write("🧾 レスポンス内容:", token_json)
            return None, None

    except Exception as e:
        st.error("❌ 認証に失敗しました。再ログインしてください。")
        st.write("🧾 エラー詳細:", str(e))

        if folder_id:
            log_error_to_drive(str(e), "", folder_id)

        # UI操作は関数外で行う方が安全
        return None, None


# 4. セッション初期化時にaccess_tokenを復元する処理
def restore_access_token_if_needed(client_id, client_secret, token_uri, folder_id):
    from pytz import timezone
    now = datetime.now(timezone("Asia/Tokyo"))

    # 🔍 状態確認ログ
    #st.write("🧭 restore_access_token_if_needed: access_token =", st.session_state.get("access_token"))
    #st.write("🧭 restore_access_token_if_needed: expires_at =", st.session_state.get("expires_at"))
    #st.write("🧭 restore_access_token_if_needed: initial_access_token =", st.session_state.get("initial_access_token"))

    # ✅ トークンが未設定 or 有効期限切れなら復元を試みる
    if (
        "access_token" not in st.session_state
        or "expires_at" not in st.session_state
        or st.session_state.expires_at is None
        or st.session_state.expires_at <= now
    ):
        #st.info("🔄 セッション復元中...")

        # ✅ initial_access_token を使って Drive から refresh_token を取得
        initial_token = st.session_state.get("initial_access_token")
        if not initial_token:
            #st.info("⚠️ initial_access_token が未設定です。Driveからの復元はできません。")
            return

        refresh_token = load_refresh_token_from_drive(access_token=initial_token, folder_id=folder_id)
        if not refresh_token:
            st.warning("⚠️ refresh_token が見つかりません。再ログインが必要です。")
            log_error_to_drive("Driveからrefresh_tokenが取得できませんでした", "", folder_id)
            return

        # ✅ refresh_token から access_token を再取得
        access_token, expires_at = get_access_token_from_refresh_token(
            refresh_token, client_id, client_secret, token_uri, folder_id
        )

        if access_token:
            st.session_state.access_token = access_token
            st.session_state.expires_at = expires_at
            st.success("✅ access_token を復元しました")
        else:
            st.error("❌ access_token の復元に失敗しました。再認証してください。")
            log_error_to_drive("access_token の復元に失敗しました（トークン取得失敗）", "", folder_id)
    else:
        st.write("✅ access_token はまだ有効です（復元不要）")
