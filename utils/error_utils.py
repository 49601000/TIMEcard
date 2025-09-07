import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
from io import StringIO, BytesIO
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials

# 🧩 エラー処理
def log_error_to_drive(error_message, access_token, folder_id):
    try:
        creds = Credentials(token=access_token)
        service = build("drive", "v3", credentials=creds)

        filename = "エラーLOG.csv"
        query = f"name='{filename}' and '{folder_id}' in parents"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])

        # 新しいログ行
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row = pd.DataFrame([{"日付（時刻）": timestamp, "エラー内容": error_message}])

        if files:
            file_id = files[0]["id"]
            request = service.files().get_media(fileId=file_id)
            fh = BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.seek(0)

            existing_df = pd.read_csv(fh)
            combined_df = pd.concat([existing_df, new_row], ignore_index=True)
        else:
            combined_df = new_row

        updated_csv = combined_df.to_csv(index=False).encode("utf-8")
        media = MediaIoBaseUpload(BytesIO(updated_csv), mimetype="text/csv")

        if files:
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            metadata = {
                "name": filename,
                "parents": [folder_id],
                "mimeType": "text/csv"
            }
            service.files().create(body=metadata, media_body=media, fields="id").execute()

    except Exception as e:
        st.error("❌ エラーログ保存に失敗しました")
        st.write("📋 詳細:", str(e))
