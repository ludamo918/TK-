import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os
import random
import google.generativeai as genai

# ==========================================
# 0. 全局配置
# ==========================================
st.set_page_config(
    page_title="TK选品分析青春版",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- iOS 极简白昼风 CSS ---
st.markdown("""
<style>
    .stApp { background-color: #F5F5F7; color: #1D1D1F; }
    .glass-card, div[data-testid="metric-container"] {
        background-color: #FFFFFF !important;
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.02);
    }
    .glass-card:hover, div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.08);
    }
    h1, h2, h3, p, span, div {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif !important;
        color: #1D1D1F !important;
    }
    div[data-testid="stMetricValue"] { color: #007AFF !important; }
    .stButton > button {
        background-color: #5856D6 !important;
        color: white !important;
        border-radius: 12px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        box-shadow: 0 4px 10px rgba(88, 86, 214, 0.2);
    }
    .stButton > button:hover { background-color: #4A48C5 !important; }
    .score-badge {
        display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; margin-left: 10px;
    }
    .score-s { background-color: #FFD700; color: #8B4500 !important; } 
    .score-a { background-color: #E5E5EA; color: #333 !important; }   
</style>
""", unsafe_allow_html=True)

# --- 状态管理 ---
if 'selected_product_title' not in st.session_state:
    st.session_state.selected_product_title = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = 'guest' # 默认为访客

# ==========================================
# 🔒 团队密码锁 (双重身份版)
# ==========================================
if 'auth' not in st.session_state: st.session_state.auth = False

def check_password():
    if st.session_state.auth: return True
    
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div class="glass-card" style="text-align: center;">', unsafe_allow_html=True)
        if os.path.exists("avatar.png"):
            img_c1, img_c2, img_c3 = st.columns([1, 1, 1])
            with img_c2: st.image("avatar.png", width=100)
        
        st.markdown("<h2 style='text-align: center; margin-bottom: 20px;'>🔒 团队登录</h2>", unsafe_allow_html=True)
        pwd = st.text_input("请输入访问密码", type="password", label_visibility="collapsed")
        
        # --- 身份判断逻辑 ---
        # 1. 访客密码 (告诉别人的)
        GUEST_PWD = "1997"
        # 2. 管理员密码 (你自己用的，不要告诉别人!)
        ADMIN_PWD = "20261888" 
        
        if pwd == GUEST_PWD: 
            st.session_state.auth = True
            st.session_state.user_role = 'guest' # 标记为访客
            st.rerun()
        elif pwd == ADMIN_PWD:
            st.session_state.auth = True
            st.session_state.user_role = 'admin' # 标记为管理员
            st.rerun()
        elif pwd: 
            st.error("🚫 密码错误")
            
        st.markdown('</div>', unsafe_allow_html=True)
    return False

if not check_password(): st.stop()

# ==========================================
# 1. 核心工具函数
# ==========================================
def clean_currency(val):
    if pd.isna(val): return 0
    s = str(val).strip().lower().replace(',', '')
    multiplier = 1
    if 'k' in s: multiplier = 1000; s = s.replace('k', '')
    if 'w' in s or '万' in s: multiplier = 10000; s = s.replace('w', '').replace('万', '')
    match = re.search(r'(\d+(\.\d+)?)', s)
    if match: return float(match.group(1)) * multiplier
    return 0

def calculate_score(row, max_gmv):
    score_val = (row['GMV'] / max_gmv) * 100
    if score_val >= 50: return "S", "🔥 顶级爆款 (S级)", "score-s"
    elif score_val >= 20: return "A", "🚀 潜力热销 (A级)", "score-a"
    elif score_val >= 5: return "B", "⚖️ 稳健出单 (B级)", "score-a"
    else: return "C", "🌱 起步阶段 (C级)", "score-a"

def basic_optimize_title(original_title):
    remove_list = ['pcs', 'set', 'for', 'women', 'men', 'sale', 'hot', 'new', '2025', 'high quality']
    words = str(original_title).split()
    clean_words = [w for w in words if w.lower() not in remove_list]
    short_title = " ".join(clean_words[:8])
    return f"🔥 {short_title} ✨\n#MustHave #fyp"

def basic_generate_script(title, price):
    return f"**[Hook]**: Stop scrolling! 🛑\n**[Demo]**: Check out {title}!\n**[CTA]**: Only ${price}!"

def get_gemini_response(prompt):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash') 
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

# ==========================================
# 2. 侧边栏与 API 权限控制
# ==========================================
if os.path.exists("avatar.png"):
    c1, c2, c3 = st.sidebar.columns([1, 2, 1])
    with c2: st.image("avatar.png", width=110)
st.sidebar.markdown("<h3 style='text-align: center; margin-top: -10px;'>TK选品分析青春版</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# --- 🚀 智能权限系统 ---
active_api_key = None
is_ai_ready = False

# 1. 只有管理员 (Admin) 才能自动读取后台 Key
if st.session_state.user_role == 'admin':
    try:
        if "GEMINI_API_KEY" in st.secrets:
            active_api_key = st.secrets["GEMINI_API_KEY"]
            st.sidebar.success(f"👑 管理员模式: AI 已激活")
    except:
        pass
else:
    st.sidebar.info("👤 访客模式: 使用 AI 需自填 Key")

# 2. 允许手动输入覆盖 (访客填了自己的Key也能用)
with st.sidebar.expander("🔑 API 设置 (访客专用)", expanded=False):
    manual_key = st.text_input("手动输入 Key", type="password")
    if manual_key:
        active_api_key = manual_key

# 3. 配置 Gemini
if active_api_key:
    try:
        genai.configure(api_key=active_api_key)
        is_ai_ready = True
        # 如果是访客填了Key，也提示就绪
        if st.session_state.user_role != 'admin':
            st.sidebar.success("✅ AI 引擎已就绪 (自定义Key)")
    except Exception as e:
        st.sidebar.error(f"Key 配置失败: {e}")

st.sidebar.markdown("---")

# ==========================================
# 3. 文件上传与数据处理
# ==========================================
uploaded_file = st.sidebar.file_uploader("📂 上传 Kalodata/EchoTik 表格", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: df = pd.read_excel(uploaded_file)
    except: st.error("文件格式错误"); st.stop()

    cols = list(df.columns)
    with st.sidebar.expander("🔧 字段校准", expanded=True):
        guess_name = next((c for c in cols if 'Title' in c or '名称' in c or 'Name' in c), cols[0])
        guess_price = next((c for c in cols if 'Price' in c or '价格' in c), cols[1] if len(cols)>1 else cols[0])
        guess_sales = next((c for c in cols if 'Sales' in c or '销量' in c), cols[2] if len(cols)>2 else cols[0])
        guess_img = next((c for c in cols if 'Image' in c or 'Img' in c or 'Pic' in c or '图' in c or 'Cover' in c), None)

        col_name = st.selectbox("商品标题列", cols, index=cols.index(guess_name))
        col_price = st.selectbox("价格列", cols, index=cols.index(guess_price))
        col_sales = st.selectbox("销量列", cols, index=cols.index(guess_sales))
        col_img = st.selectbox("图片列 (可选)", ["无"] + cols, index=(cols.index(guess_img) + 1) if guess_img else 0)
    
    main_df = df.copy()
    main_df['Clean_Price'] = main_df[col_price].apply(clean_currency)
    main_df['Clean_Sales'] = main_df[col_sales].apply(clean_currency)
    main_df['GMV'] = main_df['Clean_Price'] * main_df['Clean_Sales']
    has_image = col_img != "无"
    if has_image: main_df['Image_Url'] = main_df[col_img].astype(str)

    # 漏斗筛选
    min_p, max_p = int(main_df['Clean_Price'].min()), int(main_df['Clean_Price'].max())
    if min_p == max_p: max_p += 1
    price_range = st.sidebar.slider("💰 价格区间", min_p, max_p, (min_p, max_p))
    sales_min = st.sidebar.number_input("🔥 最低销量", min_value=0, value=100)
    filtered_df = main_df[(main_df['Clean_Price'] >= price_range[0]) & (main_df['Clean_Price'] <= price_range[1]) & (main_df['Clean_Sales'] >= sales_min)]
    max_gmv = filtered_df['GMV'].max() if not filtered_df.empty else 1

    # ==========================================
    # 4. 主界面
    # ==========================================
    st.title("✨ TK选品分析青春版")
    
    # 指标概览
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("总 GMV", f"${filtered_df['GMV'].sum():,.0f}")
    m2.metric("平均客单价", f"${filtered_df['Clean_Price'].mean():.2f}")
    m3.metric("潜力品数", len(filtered_df))
    m4.metric("最高销量", f"{filtered_df['Clean_Sales'].max():,.0f}")
    st.markdown("<br>", unsafe_allow_html=True)

    # 清单
    st.subheader("📋 商品清单")
    display_cols = [col_name, 'Clean_Price', 'Clean_Sales', 'GMV']
    if has_image: display_cols.insert(0, 'Image_Url')
    col_config = {
        col_name: st.column_config.TextColumn("标题", width="medium"),
        "Clean_Price": st.column_config.NumberColumn("售价", format="$%.2f"),
        "Clean_Sales": st.column_config.NumberColumn("销量"),
        "GMV": st.column_config.NumberColumn("GMV", format="$%.0f"),
    }
    if has_image: col_config["Image_Url"] = st.column_config.ImageColumn("主图")
    
    selection = st.dataframe(
        filtered_df.sort_values('GMV', ascending=False)[display_cols],
        column_config=col_config, use_container_width=True, height=400,
        on_select="rerun", selection_mode="single-row"
    )

    # 选中逻辑
    current_product = None
    if selection.selection["rows"]:
        current_product = filtered_df.sort_values('GMV', ascending=False).iloc[selection.selection["rows"][0]]
        st.session_state.selected_product_title = current_product[col_name]
    elif st.session_state.selected_product_title:
        match = filtered_df[filtered_df[col_name] == st.session_state.selected_product_title]
        if not match.empty: current_product = match.iloc[0]

    # 分析室
    if current_product is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        score, score_text, score_css = calculate_score(current_product, max_gmv)
        st.markdown(f"""
        <div class="glass-card analysis-room">
            <h2 style="color: #5856D6 !important; margin:0;">🎯 分析室: {current_product[col_name][:30]}... <span class="score-badge {score_css}">{score_text}</span></h2>
        </div><br>
        """, unsafe_allow_html=True)
        
        c_left, c_right = st.columns([1, 1.5])
        with c_left:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            if has_image and pd.notna(current_product['Image_Url']):
                st.markdown(f'<img src="{current_product["Image_Url"]}" style="width:100%; border-radius:12px;">', unsafe_allow_html=True)
            
            sell_price = current_product['Clean_Price']
            profit = sell_price * 0.3 
            st.metric("预估利润 (30%)", f"${profit:.2f}")
            st.markdown('</div>', unsafe_allow_html=True)

        with c_right:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("🤖 AI 运营助手")
            
            tab1, tab2 = st.tabs(["标题优化", "脚本生成"])
            
            # TAB 1: 标题
            with tab1:
                orig_name = st.text_input("原标题", value=str(current_product[col_name]))
                keywords = st.text_input("关键词", placeholder="MustHave, Gift")
                
                if st.button("🚀 优化标题"):
                    if is_ai_ready and keywords:
                        with st.spinner("Gemini 思考中..."):
                            prompt = f"Act as TikTok SEO expert. Optimize title: {orig_name}. Keywords: {keywords}. English only. Under 100 chars."
                            res = get_gemini_response(prompt)
                            st.session_state['gen_title'] = res.strip()
                            st.success("优化完成")
                    else:
                        st.session_state['gen_title'] = basic_optimize_title(orig_name)
                        if not is_ai_ready: st.caption("💡 提示: 管理员登录或输入Key可开启AI模式")

                if 'gen_title' in st.session_state:
                    st.code(st.session_state['gen_title'], language='text')

            # TAB 2: 脚本
            with tab2:
                if st.button("🎬 生成脚本"):
                    target_name = st.session_state.get('gen_title', orig_name)
                    if is_ai_ready and keywords:
                        with st.spinner("AI 编写中..."):
                            prompt = f"Write a TikTok video script prompt for product: {target_name}. Keywords: {keywords}. Include Visual Style, Hook, Scenes."
                            st.text_area("脚本指令:", value=get_gemini_response(prompt), height=250)
                    else:
                        st.text_area("基础脚本:", value=basic_generate_script(target_name, sell_price), height=150)
                        if not is_ai_ready: st.caption("💡 提示: 普通模式仅提供模板")

            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("👈 请在左侧列表中选择一个商品进行分析")

else:
    st.markdown('<div class="glass-card" style="text-align: center; padding: 60px;"><h2>👈 请上传数据表格</h2></div>', unsafe_allow_html=True)