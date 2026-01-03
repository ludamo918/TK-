import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os
import random
import subprocess
import sys

# ==========================================
# 0. 强制安装库 & 环境配置
# ==========================================
try:
    import google.generativeai as genai
except ImportError:
    try:
        # 强制安装最新版
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "google-generativeai"])
        import google.generativeai as genai
    except: pass

st.set_page_config(
    page_title="TK选品分析青春版",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS 样式 ---
st.markdown("""
<style>
    .stApp { background-color: #F5F5F7; color: #1D1D1F; }
    .glass-card { background-color: #FFFFFF; border-radius: 18px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); margin-bottom: 20px; }
    .stButton > button { background-color: #5856D6; color: white; border-radius: 12px; border: none; padding: 10px 24px; }
    .stButton > button:hover { background-color: #4A48C5; }
    .score-s { background-color: #FFD700; color: #8B4500; padding: 4px 12px; border-radius: 20px; font-weight: bold; } 
    .score-a { background-color: #E5E5EA; color: #333; padding: 4px 12px; border-radius: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 状态初始化 ---
if 'selected_product_title' not in st.session_state: st.session_state.selected_product_title = None
if 'user_role' not in st.session_state: st.session_state.user_role = 'guest'
if 'auth' not in st.session_state: st.session_state.auth = False

# ==========================================
# 🔒 登录逻辑
# ==========================================
def check_password():
    if st.session_state.auth: return True
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br><div class='glass-card' style='text-align:center'>", unsafe_allow_html=True)
        st.markdown("<h2>🔒 团队登录</h2>", unsafe_allow_html=True)
        pwd = st.text_input("请输入访问密码", type="password")
        if pwd == "1997": 
            st.session_state.auth = True; st.session_state.user_role = 'guest'; st.rerun()
        elif pwd == "boss888":
            st.session_state.auth = True; st.session_state.user_role = 'admin'; st.rerun()
        elif pwd: st.error("密码错误")
        st.markdown("</div>", unsafe_allow_html=True)
    return False
if not check_password(): st.stop()

# ==========================================
# 1. 核心逻辑与 API
# ==========================================
def clean_currency(val):
    if pd.isna(val): return 0
    s = str(val).strip().lower().replace(',','').replace('k','000')
    match = re.search(r'(\d+(\.\d+)?)', s)
    return float(match.group(1)) if match else 0

def get_gemini_response(prompt, api_key):
    # 强制设置代理 (防止掉线)
    if "GEMINI_PROXY" in st.session_state and st.session_state["GEMINI_PROXY"]:
        p = st.session_state["GEMINI_PROXY"]
        os.environ["HTTP_PROXY"] = p
        os.environ["HTTPS_PROXY"] = p
    
    try:
        # 配置 API (使用 transport='rest' 提高代理兼容性)
        genai.configure(api_key=api_key, transport='rest')
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ 连接失败: {e}\n(请检查左侧代理端口是否填写正确)"

# ==========================================
# 2. 侧边栏配置
# ==========================================
st.sidebar.title("TK选品分析")

# --- 🌍 网络代理 (关键修复) ---
with st.sidebar.expander("🌍 网络修复 (必填)", expanded=True):
    st.caption("如果你在中国，必须填入VPN端口号")
    proxy_port = st.text_input("代理端口 (例如 7890 或 10809)", key="proxy_input")
    
    if proxy_port:
        proxy_url = f"http://127.0.0.1:{proxy_port}"
        st.session_state["GEMINI_PROXY"] = proxy_url
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        st.success(f"已连接代理: {proxy_port}")
    else:
        st.warning("⚠️ 未填端口，AI 可能会断连")

# --- 🔑 Key 管理 ---
active_key = None
# 1. 尝试从 Secrets 读取
if st.session_state.user_role == 'admin':
    try:
        if "GEMINI_API_KEY" in st.secrets: active_key = st.secrets["GEMINI_API_KEY"]
    except: pass
# 2. 手动覆盖
manual_key = st.sidebar.text_input("API Key (可选)", type="password")
if manual_key: active_key = manual_key.strip().replace('"','')

if active_key: st.sidebar.success("✅ Key 已就绪")
else: st.sidebar.warning("⚠️ 缺 Key")

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("📂 上传表格", type=["xlsx", "csv"])

# ==========================================
# 3. 主程序逻辑
# ==========================================
if uploaded_file:
    # 极简读取逻辑
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    except: st.error("文件错误"); st.stop()
    
    # 默认选第一列为标题，自动找价格销量
    cols = list(df.columns)
    col_name = cols[0]
    col_price = next((c for c in cols if 'Price' in c or '价格' in c), cols[1])
    col_sales = next((c for c in cols if 'Sales' in c or '销量' in c), cols[2])
    col_img = next((c for c in cols if 'Image' in c or 'Img' in c), None)

    # 数据清洗
    main_df = df.copy()
    main_df['Clean_Price'] = main_df[col_price].apply(clean_currency)
    main_df['Clean_Sales'] = main_df[col_sales].apply(clean_currency)
    main_df['GMV'] = main_df['Clean_Price'] * main_df['Clean_Sales']
    if col_img: main_df['Image_Url'] = main_df[col_img].astype(str)

    # 布局
    st.title("✨ 选品分析仪表盘")
    
    # 商品列表
    st.subheader("📋 商品清单")
    selection = st.dataframe(
        main_df.sort_values('GMV', ascending=False),
        use_container_width=True, 
        on_select="rerun", selection_mode="single-row"
    )

    # 选中逻辑
    current_product = None
    if selection.selection["rows"]:
        current_product = main_df.sort_values('GMV', ascending=False).iloc[selection.selection["rows"][0]]
    
    # 分析室
    if current_product is not None:
        st.markdown("---")
        st.header(f"🎯 分析: {current_product[col_name]}")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            if col_img and pd.notna(current_product['Image_Url']):
                st.image(current_product['Image_Url'], width=300)
            
            # 利润计算器
            st.subheader("💰 利润计算")
            sell = current_product['Clean_Price']
            cost = st.number_input("成本", value=sell*0.3)
            profit = sell - cost
            st.metric("预估利润", f"${profit:.2f}")

        with c2:
            st.subheader("🤖 AI 助手")
            
            # 这里的 active_key 传进去
            if st.button("🚀 生成标题"):
                if active_key and proxy_port:
                    with st.spinner("AI 正在连接..."):
                        prompt = f"Optimize title for TikTok: {current_product[col_name]}"
                        res = get_gemini_response(prompt, active_key)
                        st.info(res)
                else:
                    st.error("请确保已填入 Key 和 代理端口！")
                    
            if st.button("📝 生成描述"):
                if active_key and proxy_port:
                    with st.spinner("AI 正在撰写..."):
                        prompt = f"Write description for: {current_product[col_name]}"
                        res = get_gemini_response(prompt, active_key)
                        st.text_area("结果", res, height=200)
                else:
                    st.error("请确保已填入 Key 和 代理端口！")

else:
    st.info("👈 请先上传表格")