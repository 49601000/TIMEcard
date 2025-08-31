from datetime import datetime
import pandas as pd
import os

def record_punch(name, mode, filepath="data/records.csv"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_record = {"名前": name, "モード": mode, "時刻": now}

    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
    else:
        df = pd.DataFrame([new_record])

    df.to_csv(filepath, index=False)
    return now
