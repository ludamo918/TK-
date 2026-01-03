import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os
import random
import subprocess
import sys

# ==========================================
# 0. 强制配置：环境、代理、自动安装库
# ==========================================
# 1. 强制设置代理 (根据你的实际情况，这里默认写了 7890，如不同请修改)
# 如果你是 v2rayN 请改为 10809
if "HTTP_PROXY" not in os.environ:
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"

# 2. 自动安装/检查 Google 库 (防止报错)
try:
    import google.generativeai as genai
except ImportError:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "google-generativeai"])
        import google.generativeai as genai
    except: pass

st.set_page_config(
    page_title="TK选品分析青春版",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS 样式美化 ---
st.markdown("""
<style>
    .stApp { background-color: #F5F5F7; color: #1D1D1F; }
    .glass-card { background-color: #FFFFFF; border-radius: 18px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); margin-bottom: 20px; border: 1px solid rgba(0,0,0,0.02); }
    .glass-card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.08); transition: all 0.2s ease; }
    
    /* 按钮样式 */
    .stButton > button { background-color: #5856D6; color: white; border-radius: 12px; border: none; padding: 10px 24px; font-weight: 600; }
    .stButton > button:hover { background-color: #4A48C5; }
    
    /* 标签样式 */
    .score-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; margin-left: 10px; }
    .score-s { background-color: #FFD700; color: #8B4500; } 
    .score-a { background-color: #E5E5EA; color: #333; }
</style>
""", unsafe_allow_html=True)

# --- 状态管理 ---
if 'selected_product_title' not in st.session_state: st.session_state.selected_product_title = None
if 'user_role' not in st.session_state: st.session_state.user_role = 'guest'
if 'auth' not in st.session_state: st.session_state.auth = False

# ==========================================
# 🔒 双重账号安全锁 (核心保护)
# ==========================================
def check_password():
    if st.session_state.auth: return True
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br><div class='glass-card' style='text-align:center'>", unsafe_allow_html=True)
        if os.path.exists("avatar.png"): st.image("avatar.png", width=80)
        st.markdown("<h2>🔒 团队登录</h2>", unsafe_allow_html=True)
        
        pwd = st.text_input("请输入访问密码", type="password")
        
        # --- 身份验证逻辑 ---
        if pwd == "1997": 
            # 访客模式：无法自动获取 Key
            st.session_state.auth = True
            st.session_state.user_role = 'guest'
            st.rerun()
        elif pwd == "20261888":
            # 管理员模式：自动获取 Secrets Key
            st.session_state.auth = True
            st.session_state.user_role = 'admin'
            st.rerun()
        elif pwd: 
            st.error("🚫 密码错误")
            
        st.markdown("</div>", unsafe_allow_html=True)
    return False

if not check_password(): st.stop()

# ==========================================
# 1. 核心工具函数
# ==========================================
def clean_currency(val):
    if pd.isna(val): return 0
    s = str(val).strip().lower().replace(',', '')
    match = re.search(r'(\d+(\.\d+)?)', s)
    return float(match.group(1)) if match else 0

def calculate_score(row, max_gmv):
    val = (row['GMV'] / max_gmv) * 100
    if val >= 50: return "S", "🔥 顶级爆款 (S级)", "score-s"
    elif val >= 20: return "A", "🚀 潜力热销 (A级)", "score-a"
    else: return "B", "⚖️ 稳健出单 (B级)", "score-a"

# --- Gemini AI 调用核心 ---
def get_gemini_response(prompt, api_key):
    try:
        # 配置 API (使用 REST 协议以兼容代理)
        genai.configure(api_key=api_key, transport='rest')
        
        # 使用最新的 Flash 模型
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

# ==========================================
# 2. 侧边栏 & Key 管理
# ==========================================
st.sidebar.image("avatar.png", width=110) if os.path.exists("avatar.png") else None
st.sidebar.title("TK选品分析")
st.sidebar.markdown("---")

# --- Key 智能加载逻辑 ---
active_api_key = None
is_admin = (st.session_state.user_role == 'admin')

# 1. 如果是管理员，尝试从 Secrets 自动读取
if is_admin:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            active_api_key = st.secrets["GEMINI_API_KEY"]
            st.sidebar.success(f"👑 管理员已登录 (Key已自动加载)")
    except: pass
else:
    st.sidebar.info("👤 访客模式 (AI需自填Key)")

# 2. 手动输入框 (访客必填，管理员可覆盖)
with st.sidebar.expander("🔑 API Key 设置", expanded=not active_api_key):
    manual = st.text_input("输入Key (以AIza开头)", type="password")
    if manual: active_api_key = manual.strip().replace('"', '')

# 显示状态
if active_api_key:
    # 简单的验证
    if not is_admin and not manual:
        pass # 访客没填Key
    else:
        st.sidebar.success("✅ AI 引擎已就绪")
else:
    st.sidebar.warning("⚠️ 未连接 AI")

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("📂 上传表格", type=["xlsx", "csv"])

# ==========================================
# 3. 主程序
# ==========================================
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    except: st.error("文件错误"); st.stop()

    # 字段映射
    cols = list(df.columns)
    col_name = cols[0] # 默认第一列为标题
    col_price = next((c for c in cols if 'Price' in c or '价格' in c), cols[1])
    col_sales = next((c for c in cols if 'Sales' in c or '销量' in c), cols[2])
    col_img = next((c for c in cols if 'Image' in c or 'Img' in c), None)

    # 数据清洗
    main_df = df.copy()
    main_df['Clean_Price'] = main_df[col_price].apply(clean_currency)
    main_df['Clean_Sales'] = main_df[col_sales].apply(clean_currency)
    main_df['GMV'] = main_df['Clean_Price'] * main_df['Clean_Sales']
    if col_img: main_df['Image_Url'] = main_df[col_img].astype(str)
    
    # 全局筛选
    filtered_df = main_df
    max_gmv = filtered_df['GMV'].max() if not filtered_df.empty else 1

    st.title("✨ TK选品分析青春版")
    
    # 1. 宏观指标
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总 GMV", f"${filtered_df['GMV'].sum():,.0f}")
    c2.metric("平均价格", f"${filtered_df['Clean_Price'].mean():.2f}")
    c3.metric("商品数", len(filtered_df))
    c4.metric("最高销量", f"{filtered_df['Clean_Sales'].max():,.0f}")
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 🔥 Top 3 推荐 (保留旧版好功能)
    st.subheader("🔥 今日 Top 3 爆款")
    top3 = filtered_df.sort_values('GMV', ascending=False).head(3)
    if len(top3) >= 3:
        cols_top = st.columns(3)
        for i, col in enumerate(cols_top):
            row = top3.iloc[i]
            with col:
                # 渲染卡片
                st.markdown(f"""<div class='glass-card' style='text-align:center'>
                    <div style='font-size:24px; margin-bottom:5px'>{'🥇🥈🥉'[i]}</div>
                    <div style='color:#5856D6; font-weight:bold; font-size:18px'>${row['GMV']:,.0f}</div>
                    <div style='color:#666; font-size:12px; margin-bottom:10px'>销量: {row['Clean_Sales']:,.0f}</div>
                    <div style='height:40px; overflow:hidden; font-size:14px; line-height:1.4'>{row[col_name][:40]}...</div>
                </div>""", unsafe_allow_html=True)
                # 按钮在卡片下方
                if st.button(f"🔍 分析这款", key=f"top_btn_{i}", use_container_width=True):
                    st.session_state.selected_product_title = row[col_name]
                    st.rerun()

    # 3. 柱状图 (可点击)
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📊 销量排行 (点击柱子跳转)")
        chart_df = filtered_df.sort_values('Clean_Sales', ascending=False).head(20)
        chart_df['ShortName'] = chart_df[col_name].apply(lambda x: str(x)[:15] + '..')
        
        fig = px.bar(chart_df, x='ShortName', y='Clean_Sales', hover_name=col_name, color='Clean_Price')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350)
        
        # 开启点击事件
        event = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
        if event and event['selection']['points']:
            idx = event['selection']['points'][0]['point_index']
            clicked_title = chart_df.iloc[idx][col_name]
            st.session_state.selected_product_title = clicked_title
            st.rerun() # 立即刷新
        st.markdown('</div>', unsafe_allow_html=True)

    # 4. 商品清单
    st.subheader("📋 商品清单")
    selection = st.dataframe(
        filtered_df[[col_name, 'Clean_Price', 'Clean_Sales', 'GMV']], 
        use_container_width=True, 
        on_select="rerun", 
        selection_mode="single-row"
    )
    
    # 选中逻辑处理
    current_product = None
    if selection.selection["rows"]:
        idx = selection.selection["rows"][0]
        current_product = filtered_df.iloc[idx]
        st.session_state.selected_product_title = current_product[col_name]
    elif st.session_state.selected_product_title:
        match = filtered_df[filtered_df[col_name] == st.session_state.selected_product_title]
        if not match.empty: current_product = match.iloc[0]

    # 5. 🎯 分析室 (核心功能区)
    st.markdown("<div id='analysis_target'></div>", unsafe_allow_html=True)
    if current_product is not None:
        st.markdown("---")
        score, score_text, score_css = calculate_score(current_product, max_gmv)
        
        # 标题栏
        st.markdown(f"""
        <div class="glass-card analysis-room">
            <h2 style="color: #5856D6; margin:0;">🎯 分析室: {str(current_product[col_name])[:30]}... 
            <span class="score-badge {score_css}">{score_text}</span></h2>
        </div><br>
        """, unsafe_allow_html=True)

        c_left, c_mid, c_right = st.columns([1, 1.2, 1.4]) # 调整比例给右侧更多空间
        
        with c_left:
            # 图片区
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            if col_img and pd.notna(current_product['Image_Url']):
                st.image(current_product['Image_Url'], use_container_width=True)
            else: st.info("暂无图片")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with c_mid:
            # 💰 利润模拟器 (保留手动输入)
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("💰 利润模拟器")
            sell = float(current_product['Clean_Price'])
            st.metric("零售价 (Price)", f"${sell:.2f}")
            
            cost = st.number_input("进货成本 ($)", value=sell*0.3, step=1.0)
            ship = st.number_input("头程运费 ($)", value=3.0, step=0.5)
            fee = sell * 0.05
            
            profit = sell - cost - ship - fee
            margin = (profit/sell)*100 if sell>0 else 0
            
            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.metric("预估净赚", f"${profit:.2f}", delta_color="normal" if profit>0 else "inverse")
            c2.metric("利润率", f"{margin:.1f}%")
            st.caption(f"*已扣除 5% 佣金: ${fee:.2f}")
            st.markdown('</div>', unsafe_allow_html=True)

        with c_right:
            # 🤖 AI 运营助手 (升级版 3大功能)
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("🤖 AI 运营助手")
            
            # 选项卡
            tab1, tab2 = st.tabs(["文案优化", "视频脚本"])
            
            # --- Tab 1: 标题 & 描述 ---
            with tab1:
                # 1. 基础信息
                orig_title = str(current_product[col_name])
                keywords = st.text_input("核心关键词 (Keywords)", placeholder="MustHave, Gift for her")
                
                # 功能 1: 生成标题
                if st.button("🚀 1. 生成爆款标题"):
                    if active_api_key and keywords:
                        with st.spinner("Gemini 正在思考..."):
                            prompt = f"""
                            Act as a TikTok Shop SEO Expert.
                            Task: Create a viral product title based on the original name and keywords.
                            Original Name: {orig_title}
                            Keywords: {keywords}
                            Requirements: English only, under 100 chars, emotive and catchy.
                            Output: Just the title.
                            """
                            res = get_gemini_response(prompt, active_api_key)
                            st.session_state['gen_title'] = res.strip()
                            st.success("标题优化完成")
                    else:
                        st.warning("⚠️ 请输入关键词，并确保 Key 已连接")

                # 显示生成的新标题
                if 'gen_title' in st.session_state:
                    st.info(f"**新标题:** {st.session_state['gen_title']}")
                    
                    st.markdown("---")
                    # 功能 2: 生成描述 (基于新标题)
                    if st.button("📝 2. 生成300字英文描述"):
                        if active_api_key:
                            with st.spinner("Gemini 正在撰写..."):
                                desc_prompt = f"""
                                Act as a Copywriter. 
                                Task: Write a 300-word product description for TikTok Shop.
                                Product: {st.session_state['gen_title']}
                                Keywords: {keywords}
                                Tone: Exciting, Persuasive, addressing pain points.
                                Format: Pure English text, short paragraphs.
                                """
                                st.session_state['gen_desc'] = get_gemini_response(desc_prompt, active_api_key)
                        else:
                            st.error("请检查 Key 连接")
                    
                    if 'gen_desc' in st.session_state:
                        st.text_area("生成结果:", value=st.session_state['gen_desc'], height=200)

            # --- Tab 2: 视频脚本 ---
            with tab2:
                # 功能 3: 脚本生成
                st.caption("基于关键词生成 AI 视频提示词")
                if st.button("🎬 3. 生成脚本提示词"):
                    target = st.session_state.get('gen_title', orig_title)
                    if active_api_key and keywords:
                        with st.spinner("正在编写剧本..."):
                            script_prompt = f"""
                            Act as a Viral Video Director.
                            Task: Create a video script prompt for AI video generators (like Sora/Runway).
                            Product: {target}
                            Keywords: {keywords}
                            Output Format:
                            - Visual Style: (e.g. Cinematic, UGC)
                            - Hook: (First 3 seconds visual)
                            - Key Scenes: (3-4 bullet points)
                            - AI Prompt: (Detailed prompt block for generation)
                            """
                            script_res = get_gemini_response(script_prompt, active_api_key)
                            st.text_area("脚本指令:", value=script_res, height=300)
                    else:
                        st.warning("请确保已有标题/关键词且 Key 已连接")

            st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 60px;">
        <h2 style="color: #1D1D1F !important;">👈 请在左侧上传数据表格</h2>
        <p style="color: #86868b !important; font-size: 18px;">开启您的 iOS 极简风选品之旅</p>
    </div>
    """, unsafe_allow_html=True)