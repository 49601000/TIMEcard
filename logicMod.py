import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
from io import StringIO, BytesIO
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials

# 🔐 1. refresh_token を Drive に保存（上書き対応）
def save_refresh_token_to_drive(refresh_token, access_token, folder_id):
    try:
        creds = Credentials(token=access_token)
        service = build("drive", "v3", credentials=creds)

        query = f"'{folder_id}' in parents and name='refresh_token.csv'"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])

        csv_content = f"refresh_token\n{refresh_token}"
        media = MediaIoBaseUpload(StringIO(csv_content), mimetype="text/csv")

        if files:
            file_id = files[0]["id"]
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {
                "name": "refresh_token.csv",
                "parents": [folder_id],
                "mimeType": "application/vnd.google-apps.spreadsheet"
            }
            service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    except Exception as e:
        print("❌ refresh_token 保存失敗:", e)

# 📥 2. Driveから refresh_token.csv を読み込む
def load_refresh_token_from_drive(access_token, folder_id):
    try:
        creds = Credentials(token=access_token)
        service = build("drive", "v3", credentials=creds)

        query = f"'{folder_id}' in parents and name='refresh_token.csv'"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])

        if not files:
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
        return df["refresh_token"].iloc[0]
    except Exception as e:
        print("❌ refresh_token 読み込み失敗:", e)
        return None

# 🔄 3. refresh_token から access_token を再取得
def get_access_token_from_refresh_token(refresh_token, client_id, client_secret, token_uri):
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
        return token_json.get("access_token")
    except Exception as e:
        print("❌ access_token 再取得失敗:", e)
        return None

# 4. セッション初期化時にaccess_tokenを復元する処理
def restore_access_token_if_needed(client_id, client_secret, token_uri, folder_id):
    if "access_token" not in st.session_state:
        st.info("🔄 セッション復元中...")

        # Drive から refresh_token を読み込む
        refresh_token = load_refresh_token_from_drive(access_token="", folder_id=folder_id)
        if not refresh_token:
            st.warning("⚠️ refresh_token が見つかりません。再ログインが必要です。")
            return

        # refresh_token から access_token を再取得
        access_token = get_access_token_from_refresh_token(refresh_token, client_id, client_secret, token_uri)
        if access_token:
            st.session_state.access_token = access_token
            st.success("✅ access_token を復元しました")
        else:
            st.error("❌ access_token の復元に失敗しました。再認証してください。")

# 🕒 5. 打刻データの生成
def generate_punch_record(name, mode):
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    year = now.strftime("%Y")
    filename = f"{year}_timecard.csv"

    record_df = pd.DataFrame([{
        "名前": name,
        "モード": mode,
        "時刻": timestamp
    }])

    return filename, timestamp, record_df

# 📁 6. フォルダの存在確認と自動作成
def ensure_folder_exists(folder_name, access_token):
    creds = Credentials(token=access_token)
    service = build("drive", "v3", credentials=creds)

    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name, parents)").execute()
    files = results.get("files", [])



    if files:
        return files[0]["id"]
    else:
        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        folder = service.files().create(body=metadata, fields="id").execute()
        st.write("📁 新規フォルダを作成しました:", folder)
        return folder.get("id")

def upload_to_drive(access_token, filename, new_csv_data, folder_id=None):
    try:
        st.write("📁 upload_to_drive に渡された folder_id:", folder_id)
        creds = Credentials(token=access_token)
        service = build("drive", "v3", credentials=creds)

        query = f"name='{filename}'"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])

        if files:
            file_id = files[0]["id"]

            # 🔍 既存ファイルの親フォルダ確認
            file_metadata = service.files().get(fileId=file_id, fields="id, name, parents").execute()
            current_parents = file_metadata.get("parents", [])

            # 🔽 既存CSVをダウンロード
            request = service.files().get_media(fileId=file_id)
            fh = BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.seek(0)

            # 🔄 CSVを結合
            existing_df = pd.read_csv(fh)
            new_df = pd.read_csv(BytesIO(new_csv_data))
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            updated_csv = combined_df.to_csv(index=False).encode("utf-8")
            media = MediaIoBaseUpload(BytesIO(updated_csv), mimetype="text/csv")

            # 🛠 ファイル内容更新＋フォルダ移動（必要なら）
            update_response = service.files().update(
                fileId=file_id,
                media_body=media,
                addParents=folder_id if folder_id else None,
                removeParents=",".join(current_parents) if folder_id else None
            ).execute()

            st.write("✅ ファイル更新完了:", update_response)
            st.write("📁 フォルダ移動: 旧 →", current_parents, "→ 新 →", folder_id)
            return True, filename

        else:
            # 🆕 新規ファイル作成
            media = MediaIoBaseUpload(BytesIO(new_csv_data), mimetype="text/csv")
            metadata = {
                "name": filename,
                "mimeType": "text/csv"
            }
            if folder_id:
                metadata["parents"] = [folder_id]

            response = service.files().create(
                body=metadata,
                media_body=media,
                fields="id, name, parents, webViewLink"
            ).execute()

            st.write("📄 作成されたファイル情報:", response)
            st.write("📁 保存先フォルダID:", response.get("parents"))
            st.write("🔗 ファイルリンク:", response.get("webViewLink"))
            return True, filename

    except Exception as e:
        st.error("❌ CSVアップロード失敗")
        st.write("エラー内容:", str(e))
        return False

# 🧩 8. 打刻処理の統合関数（フォルダ自動作成付き）
def record_punch(name, mode, access_token, folder_name=None):
    folder_id = None
    if folder_name:
        folder_id = ensure_folder_exists(folder_name, access_token)

    filename, timestamp, df = generate_punch_record(name, mode)
    csv_data = df.to_csv(index=False).encode("utf-8")
    success, filename = upload_to_drive(access_token, filename, csv_data, folder_id)
    return timestamp, success, filename  

# 🧩 ex. ファイルの存在を確認
def check_file_exists(filename, access_token, folder_id=None):
    creds = Credentials(token=access_token)
    service = build("drive", "v3", credentials=creds)

    # 🔍 クエリ構築（folder_id の有無で分岐）
    if folder_id:
        query = f"name='{filename}' and mimeType='text/csv' and '{folder_id}' in parents"
    else:
        query = f"name='{filename}' and mimeType='text/csv'"

    st.write("🔍 検索クエリ:", query)  # ← デバッグ用に表示

    results = service.files().list(q=query, fields="files(id, name, parents)").execute()
    files = results.get("files", [])

    if files:
        st.success(f"✅ ファイル '{filename}' は Drive に存在します")
        st.write("📁 検出されたファイル情報:", files)
        return True
    else:
        st.warning(f"⚠️ ファイル '{filename}' は Drive に存在しません")
        return False
