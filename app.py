import streamlit as st
import json
import datetime
from datetime import timedelta
from pathlib import Path
import time
import requests

st.set_page_config(page_title="AI文案生成器", layout="centered")

DATA_FILE = Path("user_data.json")

WECHAT_APPID = st.secrets["WECHAT_APPID"]
WECHAT_SECRET = st.secrets["WECHAT_SECRET"]
WECHAT_OPENID = st.secrets["WECHAT_OPENID"]
WECHAT_TEMPLATE_ID = st.secrets["WECHAT_TEMPLATE_ID"]
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

# 👇 你自己的微信推送接口（我帮你写好了）
PUSH_URL = "https://api.xbxin.com/push"
PUSH_TOKEN = "7af72391-0e4f-4523-bded-e91010a461a4"

DEEPSEEK_URL = "https://api.deepseek.com/v1"

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "users" not in data: data["users"] = {}
        if "pay_applies" not in data: data["pay_applies"] = []
        if "suggestions" not in data: data["suggestions"] = []
        return data
    return {"users": {}, "pay_applies": [], "suggestions": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_wechat_notify(phone):
    try:
        content = f"用户【{phone}】已提交付款申请，请尽快处理"
        requests.post(PUSH_URL, json={
            "token": PUSH_TOKEN,
            "title": "💰 新付款申请",
            "content": content
        })
    except:
        pass

data = load_data()

st.sidebar.title("📌 菜单")
page = st.sidebar.radio("选择页面", ["用户端", "管理员后台"])

# ==========================
# 用户端
# ==========================
if page == "用户端":
    st.title("✨ AI小红书爆款文案生成器")

    if "login_phone" not in st.session_state:
        st.session_state.login_phone = None
    current_phone = st.session_state.login_phone

    if not current_phone:
        tab1, tab2 = st.tabs(["登录", "注册"])
        with tab1:
            phone_login = st.text_input("手机号", key="login_phone")
            pwd_login = st.text_input("密码", type="password", key="login_pwd")
            if st.button("登录"):
                if phone_login in data["users"] and data["users"][phone_login]["pwd"] == pwd_login:
                    st.session_state.login_phone = phone_login
                    st.rerun()
                else:
                    st.error("账号或密码错误")
        with tab2:
            phone_reg = st.text_input("手机号", key="reg_phone")
            pwd_reg = st.text_input("密码", type="password", key="reg_pwd")
            if st.button("注册"):
                if len(phone_reg) == 11 and phone_reg not in data["users"]:
                    data["users"][phone_reg] = {
                        "pwd": pwd_reg, "free_count": 0,
                        "is_paid": False, "expire_time": None
                    }
                    save_data(data)
                    st.success("注册成功")
                else:
                    st.warning("无效或已注册")
        st.stop()

    user = data["users"][current_phone]

    # 检查过期
    if user["expire_time"]:
        try:
            now = datetime.datetime.now()
            exp = datetime.datetime.strptime(user["expire_time"], "%Y-%m-%d %H:%M:%S")
            if now > exp:
                user["is_paid"] = False
                user["expire_time"] = None
                save_data(data)
        except:
            pass

    # ======================
    # 🔥 显示到期时间（你要的！）
    # ======================
    st.subheader(f"你好：{current_phone}")
    if user["is_paid"] and user["expire_time"]:
        st.success(f"✅ 会员状态：已开通\n⏳ 到期时间：{user['expire_time']}")
    else:
        st.info("当前状态：免费版")

    FREE_TRIAL_LIMIT = 3
    can_use = user["is_paid"] or user["free_count"] < FREE_TRIAL_LIMIT

    product = st.text_input("产品名称", key="p")
    desc = st.text_area("产品描述", key="d")
    keywords = st.text_input("关键词", key="k")
    style = st.selectbox("风格", ["闺蜜风","学霸风","真实测评","干货种草风","热门爆款风","避坑吐槽风"], key="s")

    if not user["is_paid"]:
        if user["free_count"] < FREE_TRIAL_LIMIT:
            st.success(f"免费剩余：{FREE_TRIAL_LIMIT - user['free_count']} 次")
        else:
            st.markdown("## 🔒 免费次数用完")
            st.markdown("# 💰 9.9元/30天")
            st.image("wechat.jpg", width=300)
            st.warning("付款备注手机号！")

            # ==========================================
            # 🔥 提交付款 + 微信推送（你要的！）
            # ==========================================
            if st.button("✅ 我已支付，申请开通"):
                t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["pay_applies"].append({"phone": current_phone, "apply_time": t})
                save_data(data)
                send_wechat_notify(current_phone)  # 👈 微信提醒
                st.success("提交成功！我会收到微信提醒，马上处理！")

    if can_use and st.button("🔥 生成文案"):
        if not product:
            st.warning("请输入产品名")
        else:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_URL)
                prompt = f"""生成小红书文案，风格：{style}
产品：{product}
描述：{desc}
关键词：{keywords}
要求口语化、带表情、段落简短"""
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.success("生成成功！")
                st.write(res.choices[0].message.content)
                if not user["is_paid"]:
                    user["free_count"] += 1
                    save_data(data)
            except Exception as e:
                st.error(f"错误：{e}")

    st.divider()
    st.subheader("💬 建议反馈")
    suggest_content = st.text_area("输入建议", key="suggest")
    if st.button("📩 提交建议"):
        if suggest_content.strip():
            t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data["suggestions"].append({
                "phone": current_phone, "content": suggest_content, "time": t, "read": False
            })
            save_data(data)
            st.success("提交成功！")

# ==========================
# 管理员端
# ==========================
elif page == "管理员后台":
    st.title("🔑 管理员后台")

    if "admin_logged" not in st.session_state:
        st.session_state.admin_logged = False

    if not st.session_state.admin_logged:
        pwd = st.text_input("管理员密码", type="password", key="admin_pwd")
        if st.button("登录"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_logged = True
                st.rerun()
            else:
                st.error("密码错误")
        st.stop()

    st.success("✅ 已登录")
    if st.button("🔄 刷新数据"):
        st.rerun()
    if st.button("🚪 退出"):
        st.session_state.admin_logged = False
        st.rerun()

    st.subheader("📥 待审核付款")
    if data["pay_applies"]:
        for i, item in enumerate(data["pay_applies"]):
            st.markdown(f"**{item['phone']}**　{item['apply_time']}")
            c1, c2 = st.columns(2)
            if c1.button(f"同意✅ {i}", key=f"a{i}"):
                if item["phone"] in data["users"]:
                    u = data["users"][item["phone"]]
                    u["is_paid"] = True
                    u["expire_time"] = (datetime.datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
                data["pay_applies"].pop(i)
                save_data(data)
                st.rerun()
            if c2.button(f"拒绝❌ {i}", key=f"r{i}"):
                data["pay_applies"].pop(i)
                save_data(data)
                st.rerun()
            st.divider()
    else:
        st.info("暂无申请")

    st.subheader("💬 用户建议")
    sf = st.radio("筛选", ["全部","未读","已读"], horizontal=1, key="sf")
    sl = data["suggestions"]
    fl = sl
    if sf == "未读": fl = [x for x in sl if not x.get("read")]
    if sf == "已读": fl = [x for x in sl if x.get("read")]
    for idx, s in enumerate(fl):
        st.markdown(f"**{s['phone']}**　{s['time']}　{'🔴未读'if not s.get('read')else'🟢已读'}")
        st.write(f"> {s['content']}")
        if st.button("标为已读", key=f"mr{idx}"):
            sl[sl.index(s)]["read"]=True
            save_data(data)
            st.rerun()
        st.divider()

    st.subheader("👥 用户列表")
    ft = st.radio("筛选", ["全部","已付款","未付款"], horizontal=1, key="uf")
    ul = data["users"]
    show = ul
    if ft == "已付款": show={k:v for k,v in ul.items() if v.get("is_paid")}
    if ft == "未付款": show={k:v for k,v in ul.items() if not v.get("is_paid")}
    st.write(show)
