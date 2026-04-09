import streamlit as st
import json
import datetime
from datetime import timedelta
from pathlib import Path
import time

# 🔥 必须放在第一行！
st.set_page_config(page_title="AI文案生成器", layout="centered")

DATA_FILE = Path("user_data.json")

# 🔐 密钥配置（保持不变）
WECHAT_APPID = st.secrets["WECHAT_APPID"]
WECHAT_SECRET = st.secrets["WECHAT_SECRET"]
WECHAT_OPENID = st.secrets["WECHAT_OPENID"]
WECHAT_TEMPLATE_ID = st.secrets["WECHAT_TEMPLATE_ID"]
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

DEEPSEEK_URL = "https://api.deepseek.com/v1"

# ==============================================
# 🔄 通用数据函数
# ==============================================
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 补全缺失字段
        if "users" not in data: data["users"] = {}
        if "pay_applies" not in data: data["pay_applies"] = []
        if "suggestions" not in data: data["suggestions"] = []
        return data
    return {"users": {}, "pay_applies": [], "suggestions": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ==============================================
# 📌 页面导航（必须放在变量定义之后）
# ==============================================
st.sidebar.title("📌 功能菜单")
page = st.sidebar.radio("选择页面", ["用户端", "管理员后台"])

# ==============================================
# 🔐 页面1：用户端（核心修复）
# ==============================================
if page == "用户端":
    st.title("✨ AI小红书爆款文案生成器")

    # 🔥 初始化登录状态（保证变量一定存在）
    if "login_phone" not in st.session_state:
        st.session_state.login_phone = None
    current_phone = st.session_state.login_phone

    # ================= 未登录状态 =================
    if not current_phone:
        tab1, tab2 = st.tabs(["🔑 登录", "📝 注册"])
        
        with tab1:
            # 🔥 必须加 key，否则状态会乱
            phone_login = st.text_input("手机号", key="login_phone_input")
            pwd_login = st.text_input("密码", type="password", key="login_pwd_input")
            
            if st.button("🚀 登录", key="main_login_btn"):
                if not phone_login or not pwd_login:
                    st.warning("请填写手机号和密码")
                elif phone_login in data["users"] and data["users"][phone_login]["pwd"] == pwd_login:
                    st.session_state.login_phone = phone_login  # 写入会话
                    st.success("✅ 登录成功！")
                    time.sleep(0.3)
                    st.rerun()  # 强制刷新进入主页
                else:
                    st.error("❌ 手机号或密码错误")

        with tab2:
            phone_reg = st.text_input("手机号", key="reg_phone_input")
            pwd_reg = st.text_input("密码", type="password", key="reg_pwd_input")
            
            if st.button("📝 注册", key="main_reg_btn"):
                if len(phone_reg) != 11 or not phone_reg.isdigit():
                    st.warning("❌ 请输入11位有效手机号")
                elif phone_reg in data["users"]:
                    st.warning("❌ 该手机号已注册")
                else:
                    # 注册新用户
                    data["users"][phone_reg] = {
                        "pwd": pwd_reg,
                        "free_count": 0,
                        "is_paid": False,
                        "expire_time": None
                    }
                    save_data(data)
                    st.success("✅ 注册成功！请登录")
        # 🔥 停止渲染后续内容（必须放在 tab 外！）
        st.stop()

    # ================= 已登录状态 =================
    user = data["users"][current_phone]

    # 🔍 检查会员过期
    def check_expire():
        if user["expire_time"]:
            now = datetime.datetime.now()
            exp = datetime.datetime.strptime(user["expire_time"], "%Y-%m-%d %H:%M:%S")
            if now > exp:
                user["is_paid"] = False
                user["expire_time"] = None
                save_data(data)
    check_expire()

    FREE_TRIAL_LIMIT = 3
    WECHAT_QR = "wechat.jpg"
    can_use = user["is_paid"] or user["free_count"] < FREE_TRIAL_LIMIT

    # 📋 主界面
    st.subheader(f"👋 欢迎使用：{current_phone}")
    
    # 🔄 退出登录按钮
    if st.button("🚪 退出登录", key="user_logout_btn"):
        st.session_state.login_phone = None
        st.rerun()

    st.divider()
    
    # 📝 文案生成
    product = st.text_input("🏷️ 产品名称", key="prod_name")
    desc = st.text_area("📄 产品描述", key="prod_desc")
    keywords = st.text_input("🔑 关键词", key="prod_key")
    style = st.selectbox("🎨 文案风格", [
        "闺蜜风", "学霸风", "真实测评",
        "干货种草风", "热门爆款风", "避坑吐槽风"
    ], key="prod_style")

    # 💰 付费逻辑
    if not user["is_paid"]:
        if user["free_count"] < FREE_TRIAL_LIMIT:
            st.info(f"🎁 免费剩余次数：{FREE_TRIAL_LIMIT - user['free_count']} 次")
        else:
            st.markdown("---")
            st.markdown("## 🔒 免费次数已用完")
            st.markdown("# 💳 9.9元 / 30天")
            st.image(WECHAT_QR, width=250)
            st.warning("💡 付款后请备注手机号，5分钟内开通！")
            if st.button("✅ 我已支付", key="pay_btn"):
                t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["pay_applies"].append({"phone": current_phone, "apply_time": t})
                save_data(data)
                st.success("📝 提交成功！等待管理员审核")

    # 🚀 生成按钮
    if can_use and st.button("🔥 生成文案", key="gen_btn"):
        if not product:
            st.warning("❌ 请填写产品名称")
        else:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_URL)
                prompt = f"""生成小红书文案，风格：{style}
产品：{product}
描述：{desc}
关键词：{keywords}
要求：口语化、带Emoji、段落简短、直接输出文案内容，不要多余解释"""
                res = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}]
                )
                st.markdown("---")
                st.success("✅ 生成成功！")
                st.write(res.choices[0].message.content)
                
                # 扣免费次数
                if not user["is_paid"]:
                    user["free_count"] += 1
                    save_data(data)
            except Exception as e:
                st.error(f"❌ 生成失败：{str(e)}")

    st.divider()
    
    # 💬 建议反馈（核心修复：加 key）
    st.subheader("💬 意见反馈")
    suggest_content = st.text_area("👇 输入你的建议", key="suggest_area")
    
    # 🔥 修复：加一个唯一 key，防止跳转
    if st.button("📩 提交建议", key="submit_sug_btn"):
        if not suggest_content.strip():
            st.warning("❌ 建议内容不能为空")
        else:
            t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data["suggestions"].append({
                "phone": current_phone,
                "content": suggest_content,
                "time": t,
                "read": False
            })
            save_data(data)
            st.success("💾 建议提交成功！管理员会尽快查看")

# ==============================================
# 🔐 页面2：管理员后台
# ==============================================
elif page == "管理员后台":
    st.title("🔑 管理员后台")

    # 初始化状态
    if "admin_logged" not in st.session_state:
        st.session_state.admin_logged = False

    # ================= 管理员登录 =================
    if not st.session_state.admin_logged:
        admin_pwd = st.text_input("🔑 管理员密码", type="password", key="admin_pwd_input")
        if st.button("🚀 进入后台", key="admin_login_btn"):
            if admin_pwd == ADMIN_PASSWORD:
                st.session_state.admin_logged = True
                st.success("✅ 管理员登录成功！")
                time.sleep(0.3)
                st.rerun()
            else:
                st.error("❌ 管理员密码错误")
        st.stop()

    # ================= 管理员操作区 =================
    st.success("✅ 已登录管理员后台")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 刷新数据", key="admin_refresh"):
            st.rerun()
    with col2:
        if st.button("🚪 退出后台", key="admin_logout_btn"):
            st.session_state.admin_logged = False
            st.rerun()

    st.divider()

    # 📥 待审核付款
    st.subheader("📥 待审核付款申请")
    if not data["pay_applies"]:
        st.info("暂无付款申请")
    else:
        for i, item in enumerate(data["pay_applies"]):
            st.markdown(f"**👤 用户：**{item['phone']}  \n**⏰ 申请时间：**{item['apply_time']}")
            c_a, c_b = st.columns(2)
            with c_a:
                if st.button(f"✅ 同意开通", key=f"agree_{i}"):
                    if item["phone"] in data["users"]:
                        u = data["users"][item["phone"]]
                        u["is_paid"] = True
                        u["expire_time"] = (datetime.datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
                        data["pay_applies"].pop(i)
                        save_data(data)
                        st.success("✅ 已开通会员！")
                        st.rerun()
            with c_b:
                if st.button(f"❌ 拒绝申请", key=f"reject_{i}"):
                    data["pay_applies"].pop(i)
                    save_data(data)
                    st.warning("❌ 已拒绝申请")
                    st.rerun()
            st.divider()

    # 💬 用户建议（核心修复：修复过滤逻辑）
    st.subheader("💬 用户建议反馈")
    sug_filter = st.radio("筛选状态", ["全部", "未读", "已读"], horizontal=True, key="sug_filter")
    
    # 🔥 修复：正确过滤数据
    suggestions = data["suggestions"]
    filtered_sugs = suggestions
    if sug_filter == "未读":
        filtered_sugs = [s for s in suggestions if not s.get("read", False)]
    elif sug_filter == "已读":
        filtered_sugs = [s for s in suggestions if s.get("read", False)]

    if not filtered_sugs:
        st.info("暂无建议数据")
    else:
        for idx, sug in enumerate(filtered_sugs):
            # 🔥 修复：通过索引找真实数据，避免找不到
            real_idx = data["suggestions"].index(sug)
            status_text = "🔴 未读" if not sug.get("read") else "🟢 已读"
            
            st.markdown(f"""
**👤 来自：**{sug['phone']} | **📅 时间：**{sug['time']} | **{status_text}**
> 💬 内容：{sug['content']}
            """)
            
            # 标为已读按钮
            if not sug.get("read") and st.button("✅ 标为已读", key=f"mark_read_{idx}"):
                data["suggestions"][real_idx]["read"] = True
                save_data(data)
                st.rerun()
            st.divider()

    # 👥 用户列表
    st.subheader("👥 所有用户")
    user_filter = st.radio("筛选用户", ["全部", "已付款", "未付款"], horizontal=True, key="user_filter")
    
    users = data["users"]
    show_users = users
    if user_filter == "已付款":
        show_users = {k:v for k,v in users.items() if v.get("is_paid")}
    elif user_filter == "未付款":
        show_users = {k:v for k,v in users.items() if not v.get("is_paid")}
    
    st.json(show_users, expanded=True)
