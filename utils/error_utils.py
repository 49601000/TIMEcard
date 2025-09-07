import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from pytz import timezone
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials

#エラー収集
def log_error_to_drive(error_message, access_token, folder_id):
    try:
        creds = Credentials(token=access_token)
        service = build("drive", "v3", credentials=creds)

        filename = "エラーLOG.csv"
        query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name, parents)").execute()
        files = results.get("files", [])

        # 🕒 JSTでタイムスタンプ
        timestamp = datetime.now(timezone("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")

        # 🧼 エラー内容をCSV安全化（改行・カンマ対策）
        safe_message = error_message.replace("\n", " ").replace(",", "、")
        new_row = pd.DataFrame([{"日付（時刻）": timestamp, "エラー内容": safe_message}])

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
            response = service.files().update(
                fileId=file_id,
                media_body=media,
                fields="id, name, parents, webViewLink"
            ).execute()
        else:
            metadata = {
                "name": filename,
                "parents": [folder_id],
                "mimeType": "text/csv"
            }
            response = service.files().create(
                body=metadata,
                media_body=media,
                fields="id, name, parents, webViewLink"
            ).execute()

        st.success("✅ エラーログを保存しました")
        st.write("🔗 ログファイル:", response.get("webViewLink"))

    except Exception as e:
        st.error("❌ エラーログ保存に失敗しました")
        st.write("📋 詳細:", str(e))
