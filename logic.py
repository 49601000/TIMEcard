import pandas as pd
import requests
import json
from datetime import datetime

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


def record_punch(name, mode, access_token, folder_id=None):
    """
    打刻処理の統合関数：データ生成 → CSV化 → Driveアップロード
    """
    filename, timestamp, df = generate_punch_record(name, mode)
    csv_data = df.to_csv(index=False).encode("utf-8")

    success = upload_to_drive(access_token, filename, csv_data, folder_id)
    return timestamp, success
