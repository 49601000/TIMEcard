import pandas as pd
import requests
import json
from datetime import datetime
from io import StringIO
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials

#リフレッシュトークンの処理
def save_refresh_token_to_drive(refresh_token, access_token, folder_id):
    """refresh_token を Drive に保存（CSV形式）"""
    creds = Credentials(token=access_token)
    service = build("drive", "v3", credentials=creds)

    csv_content = f"refresh_token\n{refresh_token}"
    media = MediaIoBaseUpload(StringIO(csv_content), mimetype="text/csv")

    file_metadata = {
        "name": "refresh_token.csv",
        "parents": [folder_id],
        "mimeType": "application/vnd.google-apps.spreadsheet"
    }

    service.files().create(body=file_metadata, media_body=media, fields="id").execute()

def load_refresh_token_from_drive(access_token, folder_id):
    """Driveから refresh_token.csv を読み込む"""
    creds = Credentials(token=access_token)
    service = build("drive", "v3", credentials=creds)

    # ファイル検索
    query = f"'{folder_id}' in parents and name='refresh_token.csv'"
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])

    if not files:
        return None

    file_id = files[0]["id"]
    request = service.files().get_media(fileId=file_id)
    fh = StringIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()

    fh.seek(0)
    df = pd.read_csv(fh)
    return df["refresh_token"].iloc[0]

def get_access_token_from_refresh_token(refresh_token, client_id, client_secret, token_uri):
    """refresh_token を使って access_token を再取得"""
    refresh_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    response = requests.post(token_uri, data=refresh_data)
    token_json = response.json()
    return token_json.get("access_token")

#ここまで#####################################################

#1. 打刻データの生成
def generate_punch_record(name, mode):
    """
    打刻データを生成し、ファイル名・時刻・DataFrameを返す
    """
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

#2. Google Driveへのアップロード処理
def upload_to_drive(access_token, filename, csv_data, folder_id=None):
    """
    Google Drive にCSVをアップロードする
    """
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    metadata = {
        "name": filename,
        "mimeType": "application/vnd.google-apps.spreadsheet"
    }

    if folder_id:
        metadata["parents"] = [folder_id]

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

#3. 打刻処理の統合関数（UIなし）
def record_punch(name, mode, access_token, folder_id=None):
    """
    打刻処理の統合関数：データ生成 → CSV化 → Driveアップロード
    """
    filename, timestamp, df = generate_punch_record(name, mode)
    csv_data = df.to_csv(index=False).encode("utf-8")

    success = upload_to_drive(access_token, filename, csv_data, folder_id)
    return timestamp, success
