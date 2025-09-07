import streamlit as st

def show_title():
    """アプリのタイトルを表示"""
    st.title("🕒 タイムカード打刻")

def user_selector(staff_list):
    selected = st.selectbox("スタッフを選択", staff_list)
    custom = st.text_input("スタッフ名を直接入力（任意）")
    return custom if custom else selected

def punch_buttons():
    """出勤・退勤ボタンの表示と状態取得"""
    col1, col2 = st.columns(2)
    with col1:
        punch_in = st.button("✅ 出勤")
    with col2:
        punch_out = st.button("🏁 退勤")
    return punch_in, punch_out

def show_auth_status(success, token_json=None):
    """Google認証の成否を表示"""
    if success:
        st.success("✅ Google認証に成功しました")
    else:
        st.error("❌ 認証失敗")
        if token_json:
            st.subheader("🔍 認証レスポンス詳細")
            st.write(token_json)

def show_punch_result(name, timestamp, status):
    """打刻結果の表示（出勤・退勤・失敗）"""
    if status == "in":
        st.success(f"✅ {name} さんが {timestamp} に出勤しました")
    elif status == "out":
        st.warning(f"✅ {name} さんが {timestamp} に退勤しました")
    else:
        st.error("❌ 打刻の保存に失敗しました")

def show_login_link(client_id, redirect_uri, scope="https://www.googleapis.com/auth/drive.file"):
    """Google OAuth 認証リンクの表示"""
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    st.markdown(f"[🔐 Googleでログイン]({auth_url})")

def show_main_ui_if_authenticated(staff_list=None):
    """
    認証済みなら打刻UIを表示。未認証なら警告とログインリンクを表示。
    staff_list を渡さない場合はデフォルトリストを使用。
    """
    if "access_token" in st.session_state and st.session_state.access_token:
        show_title()
        if staff_list is None:
            staff_list = ["山田", "佐藤", "鈴木", "田中"]
        name = user_selector(staff_list)
        punch_in, punch_out = punch_buttons()
        return name, punch_in, punch_out
    else:
        st.warning("⚠️ access_token が未取得のため、打刻UIは表示されません")
        if "client_id" in st.session_state and "redirect_uri" in st.session_state:
            show_login_link(st.session_state.client_id, st.session_state.redirect_uri)
        return None, None, None

