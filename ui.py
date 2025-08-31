import streamlit as st

def user_selector(staff_list):
    selected = st.selectbox("スタッフを選択", staff_list)
    custom = st.text_input("スタッフ名を直接入力（任意）")
    return custom if custom else selected

def punch_buttons():
    col1, col2 = st.columns(2)
    with col1:
        punch_in = st.button("出勤")
    with col2:
        punch_out = st.button("退勤")
    return punch_in, punch_out
