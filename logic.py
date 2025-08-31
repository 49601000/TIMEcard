import pandas as pd
import requests
import json
from datetime import datetime
from io import StringIO, BytesIO
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials

# 1. refresh_token を Drive に保存（上書き対応）
def save_refresh_token_to_drive(refresh_token, access_token, folder_id):
    try:
        creds = Credentials(token=access_token)
        service = build("drive", "v3", credentials=creds)

        # 既存ファイル検索
        query = f"'{folder_id}' in parents and name='refresh_token.csv'"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])

        csv_content = f"refresh_token\n{refresh_token}"
        media = MediaIoBaseUpload(StringIO(csv_content), mimetype="text/csv")

        if files:
            # 上書き
            file_id = files[0]["id"]
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            # 新規作成
            file_metadata = {
                "name": "refresh_token.csv",
                "parents": [folder_id],
                "mimeType": "application/vnd.google-apps.spreadsheet"
            }
            service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    except Exception as e:
        print("❌ refresh_token 保存失敗:", e)

# 2. Driveから refresh_token.csv を読み込む
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

# 3. refresh_token から access_token を再取得
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

# 4. 打刻データの生成
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

# 5. Google Drive にCSVを追記保存
def upload_to_drive(access_token, filename, new_csv_data, folder_id=None):
    try:
        creds = Credentials(token=access_token)
        service = build("drive", "v3", credentials=creds)

        # ファイル検索
        query = f"name='{filename}'"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])

        if files:
            # 既存ファイルに追記
            file_id = files[0]["id"]
            request = service.files().get_media(fileId=file_id)
            fh = BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

            fh.seek(0)
            existing_df = pd.read_csv(fh)
            new_df = pd.read_csv(BytesIO(new_csv_data))
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)

            updated_csv = combined_df.to_csv(index=False).encode("utf-8")
            media = MediaIoBaseUpload(BytesIO(updated_csv), mimetype="text/csv")
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            # 新規作成
            media = MediaIoBaseUpload(BytesIO(new_csv_data), mimetype="text/csv")
            metadata = {
                "name": filename,
                "mimeType": "application/vnd.google-apps.spreadsheet"
            }
            if folder_id:
                metadata["parents"] = [folder_id]

            service.files().create(body=metadata, media_body=media, fields="id").execute()

        return True
    except Exception as e:
        print("❌ CSVアップロード失敗:", e)
        return False

# 6. 打刻処理の統合関数
def record_punch(name, mode, access_token, folder_id=None):
    filename, timestamp, df = generate_punch_record(name, mode)
    csv_data = df.to_csv(index=False).encode("utf-8")
    success = upload_to_drive(access_token, filename, csv_data, folder_id)
    return timestamp, success
