import streamlit as st
from ui import user_selector, punch_buttons
from logic import record_punch

staff_list = ["田中", "佐藤", "鈴木", "オプティカル"]

st.title("🕒 タイムカード打刻")

# ユーザー選択
name = user_selector(staff_list)

# 打刻ボタン
punch_in, punch_out = punch_buttons()

# 打刻処理
if punch_in:
    time = record_punch(name, "出勤", access_token)
    st.success(f"{name} さんが {time} に出勤しました")

if punch_out:
    time = record_punch(name, "退勤", access_token)
    st.warning(f"{name} さんが {time} に退勤しました")
