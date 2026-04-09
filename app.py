import streamlit as st
import json
import datetime
import requests
from datetime import timedelta
from pathlib import Path
import time

DATA_FILE = Path("user_data.json")

# ================== 微信配置（从 Secrets 读取） ==================
WECHAT_APPID = st.secrets["WECHAT_APPID"]
WECHAT_SECRET = st.secrets["WECHAT_SECRET"]
WECHAT_OPENID = st.secrets["WECHAT_OPENID"]
WECHAT_TEMPLATE_ID = st.secrets["WECHAT_TEMPLATE_ID"]

def get_wechat_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APPID}&secret={WECHAT_SECRET}"
    try:
        res = requests.get(url, timeout=10)
        return res.json().get("access_token")
    except:
        return None

def send_wechat_template(msg_type, phone, content, time_str):
    token = get_wechat_access_token()
    if not token:
        return
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    
    data = {
        "touser": WECHAT_OPENID,
        "template_id": WECHAT_TEMPLATE_ID,
        "data": {
            "type": {"value": "付款申请" if msg_type == "pay" else "用户建议"},
            "phone": {"value": phone},
            "content": {"value": content},
            "time": {"value": time_str}
        }
    }
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"推送失败：{e}")

# ================== 登录状态 ==================
if "login_phone" not in st.session_state:
    st.session_state.login_phone = None

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
st.set_page_config(page_title="AI文案生成器", layout="centered")
st.title("✨ AI小红书爆款文案生成器")
current_phone = st.session_state.login_phone

# 登录注册
tab1, tab2 = st.sidebar.tabs(["登录", "注册"])
with tab1:
    phone_login = st.text_input("手机号", key="phone_login")
    pwd_login = st.text_input("密码", type="password", key="pwd_login")
    if st.button("登录", key="btn_login"):
        if phone_login in data["users"] and data["users"][phone_login]["pwd"] == pwd_login:
            st.session_state.login_phone = phone_login
            st.success("登录成功")
            st.rerun()
        else:
            st.error("账号或密码错误")

with tab2:
    phone_reg = st.text_input("手机号", key="phone_reg")
    pwd_reg = st.text_input("密码", type="password", key="pwd_reg")
    if st.button("注册", key="btn_reg"):
        if len(phone_reg) == 11 and phone_reg.isdigit() and phone_reg not in data["users"]:
            data["users"][phone_reg] = {"pwd": pwd_reg,"free_count": 0,"is_paid": False,"expire_time": None}
            save_data(data)
            st.success("注册成功")
        else:
            st.warning("手机号无效或已注册")

if not current_phone:
    st.warning("👈 请先登录")
    st.stop()

user = data["users"][current_phone]

# ====================== AI 模型配置（从Secrets读取） ======================
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
DEEPSEEK_URL = "https://api.deepseek.com/v1"
# =========================================================

# 检查过期
def check_expire():
    if user["expire_time"]:
        now = datetime.datetime.now()
        exp = datetime.datetime.strptime(user["expire_time"], "%Y-%m-%d %H:%M:%S")
        if now > exp:
            user["is_paid"] = False
            user["expire_time"] = None
            save_data(data)
check_expire()

# ================== 业务逻辑 ==================
FREE_TRIAL_LIMIT = 3
WECHAT_QR = "wechat.jpg"
can_use = user["is_paid"] or user["free_count"] < FREE_TRIAL_LIMIT

st.subheader(f"你好：{current_phone}")
product = st.text_input("产品名称", key="product")
desc = st.text_area("产品描述", key="desc")
keywords = st.text_input("关键词", key="keywords")
style = st.selectbox(
    "风格",
    ["闺蜜风","学霸风","真实测评","干货种草风","热门爆款风","避坑吐槽风"],
    key="style"
)

if not user["is_paid"]:
    if user["free_count"] < FREE_TRIAL_LIMIT:
        st.success(f"免费剩余：{FREE_TRIAL_LIMIT - user['free_count']} 次")
    else:
        st.markdown("## 🔒 免费次数用完")
        st.markdown("# 💰 9.9元/30天")
        st.image(WECHAT_QR, width=300)
        st.warning("付款时一定要备注手机号，否则作废！管理员会在5分钟之内通过，若5分钟后仍无法使用，请刷新网页。")

        if st.button("✅ 我已支付", key="btn_pay"):
            apply_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data["pay_applies"].append({"phone": current_phone, "apply_time": apply_time})
            save_data(data)
            send_wechat_template("pay", current_phone, "用户申请开通会员", apply_time)
            st.success("已提交！管理员会尽快处理")

else:
    st.success(f"✅ 会员已开通\n到期：{user['expire_time']}")

if can_use and st.button("🔥 生成文案", key="btn_generate"):
    if not product:
        st.warning("请输入产品名")
    else:
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_URL
            )

            prompt = f"""
            请你生成一篇优质小红书文案，风格：{style}
            产品：{product}
            产品描述：{desc}
            关键词：{keywords}

            要求：
            1. 口语化、吸引人
            2. 适合小红书平台
            3. 带表情符号
            4. 结构清晰、段落简短
            5. 直接输出文案，不要多余解释
            """

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1024
            )

            result = response.choices[0].message.content
            st.success("✅ 文案生成成功！")
            st.markdown("---")
            st.write(result)

            if not user["is_paid"]:
                user["free_count"] += 1
                save_data(data)

        except Exception as e:
            st.error(f"生成失败：{str(e)}")

# 建议提交
st.divider()
st.subheader("💬 建议反馈")
suggest_content = st.text_area("输入你的建议", key="suggest_content")
if st.button("📩 提交建议", key="btn_suggest"):
    if suggest_content.strip():
        sug_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["suggestions"].append({
            "phone": current_phone,
            "content": suggest_content,
            "time": sug_time,
            "read": False
        })
        save_data(data)
        send_wechat_template("suggest", current_phone, suggest_content, sug_time)
        st.success("✅ 提交成功！感谢你的反馈")