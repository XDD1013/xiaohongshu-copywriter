import streamlit as st
import json
import datetime
from datetime import timedelta
from pathlib import Path
import time

DATA_FILE = Path("user_data.json")
# 管理员密码从 Secrets 读取，不暴露在代码中
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

# 登录状态
if "admin_logged" not in st.session_state:
    st.session_state.admin_logged = False

st.set_page_config(page_title="管理员后台", layout="centered")
st.title("🔑 管理员后台")

# ======================
# 登录逻辑
# ======================
if not st.session_state.admin_logged:
    pwd = st.text_input("管理员密码", type="password")
    if st.button("登录"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_logged = True
            st.success("✅ 登录成功")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()

# ======================
# 已登录界面
# ======================
st.success("✅ 已登录（刷新不掉线）")

if st.button("🔄 刷新数据（查看新申请/建议）"):
    st.rerun()

if st.button("🚪 退出登录"):
    st.session_state.admin_logged = False
    st.rerun()

# ======================
# 数据加载
# ======================
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "users" not in data: data["users"] = {}
        if "pay_applies" not in data: data["pay_applies"] = []
        if "suggestions" not in data: data["suggestions"] = []
        return data
    return {"users": {},"pay_applies": [],"suggestions": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ======================
# 待审核付款申请
# ======================
st.subheader("📥 待审核付款申请")
if not data.get("pay_applies"):
    st.info("暂无付款申请")
else:
    for idx, item in enumerate(data["pay_applies"]):
        phone = item.get("phone", "未知")
        apply_time = item.get("apply_time", "未知")
        st.markdown(f"**手机号：{phone}**  \n申请时间：{apply_time}")
        col1, col2 = st.columns(2)
        if col1.button(f"同意✅ {idx}", key=f"ok_{idx}"):
            if phone in data["users"]:
                user = data["users"][phone]
                user["is_paid"] = True
                expire = datetime.datetime.now() + timedelta(days=30)
                user["expire_time"] = expire.strftime("%Y-%m-%d %H:%M:%S")
            data["pay_applies"].pop(idx)
            save_data(data)
            st.rerun()
        if col2.button(f"拒绝❌ {idx}", key=f"no_{idx}"):
            data["pay_applies"].pop(idx)
            save_data(data)
            st.rerun()
        st.divider()

# ======================
# 用户建议反馈
# ======================
st.subheader("💬 用户建议反馈")
sug_filter = st.radio("筛选建议", ["全部建议", "未读", "已读"], horizontal=True)
suggestions = data.get("suggestions", [])

if not suggestions:
    st.info("暂无用户建议")
else:
    filtered = []
    if sug_filter == "全部建议": filtered = suggestions
    elif sug_filter == "未读": filtered = [s for s in suggestions if not s.get("read")]
    elif sug_filter == "已读": filtered = [s for s in suggestions if s.get("read")]

    for idx, sug in enumerate(filtered):
        real_idx = data["suggestions"].index(sug)
        status = "🔴 未读" if not sug.get("read") else "🟢 已读"
        st.markdown(f"""**手机号：{sug.get('phone', '未知')}**  \n**时间：{sug.get('time', '未知')} | {status}**  \n> {sug.get('content', '无内容')}""")
        col_a, col_b = st.columns(2)
        if not sug.get("read") and col_a.button(f"标为已读 {idx}", key=f"read_{idx}"):
            data["suggestions"][real_idx]["read"] = True
            save_data(data)
            st.rerun()
        if col_b.button(f"🗑️ 删除 {idx}", key=f"del_{idx}"):
            data["suggestions"].pop(real_idx)
            save_data(data)
            st.rerun()
        st.divider()

# ======================
# 用户管理
# ======================
st.subheader("👥 用户管理")
filter_opt = st.radio("筛选用户", ["全部", "已付款", "未付款"], horizontal=True)
users = data.get("users", {})
filtered_users = {}
if filter_opt == "全部": filtered_users = users
elif filter_opt == "已付款": filtered_users = {k: v for k, v in users.items() if v.get("is_paid")}
elif filter_opt == "未付款": filtered_users = {k: v for k, v in users.items() if not v.get("is_paid")}
st.dataframe(filtered_users)