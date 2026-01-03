import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os
import random
import subprocess
import sys

# ==========================================
# 🔌 网络修复补丁 (必须放在最前面)
# ==========================================
# 强制让 Python 通过你的梯子访问网络
# ⚠️ 注意：如果你用的是 Clash，端口通常是 7890
# ⚠️ 注意：如果你用的是 V2Ray/Shadowsocks，端口可能是 10809
proxy_url = "http://127.0.0.1:7890"  
os.environ["http_proxy"] = proxy_url
os.environ["https_proxy"] = proxy_url

# === 🛠️ 强制安装补丁 (专治 ModuleNotFoundError) ===
try:
    import google.generativeai as genai
except ImportError:
    # 如果找不到库，就强制安装
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai"])
    import google.generativeai as genai

# ==========================================
# 0. 全局配置
# ==========================================
st.set_page_config(
    page_title="TK选品分析青春版 (v2.5)",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- iOS 极简白昼风 CSS (保留原样) ---
st.markdown("""
<style>
    .stApp { background-color: #F5F5F7; color: #1D1D1F; }
    
    /* 卡片通用样式 */
    .glass-card, div[data-testid="metric-container"] {
        background-color: #FFFFFF !important;
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.02);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover, div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.08);
    }

    /* 字体与颜色 */
    h1, h2, h3, p, span, div {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif !important;
        color: #1D1D1F !important;
    }
    div[data-testid="stMetricValue"] { color: #007AFF !important; }
    
    /* 侧边栏 */
    section[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E5E5EA; }
    
    /* 按钮美化 (紫色系) */
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
    
    /* 分析室高亮样式 */
    .analysis-room {
        border: 2px solid #5856D6 !important;
        background-color: #fff !important;
        animation: pulse 1s ease-in-out;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(88, 86, 214, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(88, 86, 214, 0); }
        100% { box-shadow: 0 0 0 0 rgba(88, 86, 214, 0); }
    }
    
    /* 评分标签 */
    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
        margin-left: 10px;
    }
    .score-s { background-color: #FFD700; color: #8B4500 !important; } 
    .score-a { background-color: #E5E5EA; color: #333 !important; }   
</style>
""", unsafe_allow_html=True)

# --- 状态管理 ---
if 'selected_product_title' not in st.session_state:
    st.session_state.selected_product_title = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = 'guest'

# ==========================================
# 🔒 团队密码锁 (双重身份版) - 保留原样
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
        
        # --- 身份判断 ---
        GUEST_PWD = "1997"
        ADMIN_PWD = "20261888" # 管理员密码
        
        if pwd == GUEST_PWD: 
            st.session_state.auth = True
            st.session_state.user_role = 'guest'
            st.rerun()
        elif pwd == ADMIN_PWD:
            st.session_state.auth = True
            st.session_state.user_role = 'admin'
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
    remove_list = ['pcs', 'set', 'for', 'women', 'men', 'sale', 'hot', 'new', '2025']
    words = str(original_title).split()
    clean_words = [w for w in words if w.lower() not in remove_list]
    short_title = " ".join(clean_words[:8])
    return f"🔥 {short_title} ✨ #MustHave"

def basic_generate_script(title, price):
    return f"**[Hook]**: Stop scrolling! 🛑\n**[Demo]**: Check out {title}!\n**[CTA]**: Only ${price}!"

def get_gemini_response(prompt):
    try:
        # 🔥 修改点：这里改成了你指定的 'gemini-2.5'
        # 如果你用的是中转API，确保他们支持这个模型名称
        model = genai.GenerativeModel('gemini-2.5') 
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

# ==========================================
# 2. 侧边栏与 API
# ==========================================
if os.path.exists("avatar.png"):
    c1, c2, c3 = st.sidebar.columns([1, 2, 1])
    with c2: st.image("avatar.png", width=110)
st.sidebar.markdown("<h3 style='text-align: center; margin-top: -10px;'>TK选品分析青春版</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# --- 🚀 智能权限系统 ---
active_api_key = None
is_ai_ready = False

# 管理员自动读 Secrets
if st.session_state.user_role == 'admin':
    try:
        if "GEMINI_API_KEY" in st.secrets:
            active_api_key = st.secrets["GEMINI_API_KEY"]
            st.sidebar.success(f"👑 管理员模式: AI 已激活")
    except: pass
else:
    st.sidebar.info("👤 访客模式: 使用 AI 需自填 Key")

# 手动输入覆盖
with st.sidebar.expander("🔑 API 设置 (访客专用)", expanded=False):
    manual_key = st.text_input("手动输入 Key", type="password")
    if manual_key: active_api_key = manual_key

# 配置 Gemini
if active_api_key:
    try:
        genai.configure(api_key=active_api_key)
        is_ai_ready = True
        if st.session_state.user_role != 'admin':
            st.sidebar.success("✅ AI 引擎已就绪 (v2.5)")
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
    st.title("✨ TK选品分析青春版 (AI v2.5)")
    
    # 1. 宏观指标
    m1, m2, m3, m4 = st.columns(4)
    avg_price = filtered_df['Clean_Price'].mean()
    m1.metric("筛选池总 GMV", f"${filtered_df['GMV'].sum():,.0f}")
    m2.metric("平均客单价", f"${avg_price:.2f}")
    m3.metric("潜力爆款数", len(filtered_df))
    m4.metric("最高单品销量", f"{filtered_df['Clean_Sales'].max():,.0f}")
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 🔥 Top 3 推荐
    st.subheader("🔥 今日 Top 3 推荐")
    top_3_df = filtered_df.sort_values('GMV', ascending=False).head(3)
    if len(top_3_df) >= 3:
        t1, t2, t3 = st.columns(3)
        for i, (col, icon) in enumerate(zip([t1, t2, t3], ["🥇", "🥈", "🥉"])):
            row = top_3_df.iloc[i]
            img_html = ""
            if has_image and pd.notna(row['Image_Url']) and row['Image_Url'].startswith('http'):
                img_html = f'<img src="{row["Image_Url"]}" style="width:100%; height:120px; object-fit:cover; border-radius:8px; margin-bottom:10px;">'
            
            with col:
                st.markdown(f"""
                <div class="glass-card" style="text-align: center;">
                    {img_html}
                    <h3 style="color:#5856D6 !important; margin:0;">{icon} GMV: ${row['GMV']:,.0f}</h3>
                    <p style="font-weight: 600; height: 45px; overflow: hidden; margin-top: 10px;">{(row[col_name][:35] + '...')}</p>
                    <p style="color: #666; font-size: 14px;">售价: ${row['Clean_Price']:.2f}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"🔍 分析这款", key=f"btn_top_{i}", use_container_width=True):
                    st.session_state.selected_product_title = row[col_name]
                    st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

    # 3. 📊 交互式柱状图
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📊 畅销品销量排行 (点击柱子查看分析)")
        if not filtered_df.empty:
            chart_df = filtered_df.sort_values('Clean_Sales', ascending=False).head(50).copy()
            chart_df['Short_Name'] = chart_df[col_name].astype(str).apply(lambda x: x[:15] + '..' if len(x)>15 else x)
            
            fig = px.bar(
                chart_df, x='Short_Name', y='Clean_Sales', color='Clean_Price',
                hover_name=col_name, template="plotly_white", color_continuous_scale="Viridis",
            )
            fig.update_layout(
                height=400, margin=dict(l=20,r=20,t=30,b=50), 
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font={'color': '#1D1D1F'}, xaxis_tickangle=-45
            )
            # 关键：开启点击事件
            selected_points = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
            if selected_points and selected_points['selection']['points']:
                point_idx = selected_points['selection']['points'][0]['point_index']
                clicked_product = chart_df.iloc[point_idx][col_name]
                st.session_state.selected_product_title = clicked_product
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # 4. 商品清单
    st.subheader("📋 所有商品清单 (点击行 -> 自动跳转分析室)")
    display_cols = [col_name, 'Clean_Price', 'Clean_Sales', 'GMV']
    if has_image: display_cols.insert(0, 'Image_Url')
    
    col_config = {
        col_name: st.column_config.TextColumn("标题", width="medium"),
        "Clean_Price": st.column_config.NumberColumn("售价", format="$%.2f"),
        "Clean_Sales": st.column_config.NumberColumn("销量"),
        "GMV": st.column_config.NumberColumn("GMV", format="$%.0f"),
    }
    if has_image: col_config["Image_Url"] = st.column_config.ImageColumn("主图", help="点击放大")

    selection = st.dataframe(
        filtered_df.sort_values('GMV', ascending=False)[display_cols],
        column_config=col_config, use_container_width=True, height=400,
        on_select="rerun", selection_mode="single-row"
    )

    # 选中逻辑 (兼容图表点击和表格点击)
    current_product = None
    if selection.selection["rows"]:
        current_product = filtered_df.sort_values('GMV', ascending=False).iloc[selection.selection["rows"][0]]
        st.session_state.selected_product_title = current_product[col_name]
    elif st.session_state.selected_product_title:
        match = filtered_df[filtered_df[col_name] == st.session_state.selected_product_title]
        if not match.empty: current_product = match.iloc[0]

    # 5. 🎯 单品分析室
    st.markdown("<div id='analysis_target'></div>", unsafe_allow_html=True)
    if current_product is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        score, score_text, score_css = calculate_score(current_product, max_gmv)
        st.markdown(f"""
        <div class="glass-card analysis-room">
            <h2 style="color: #5856D6 !important; margin:0;">🎯 分析室: {current_product[col_name][:30]}... <span class="score-badge {score_css}">{score_text}</span></h2>
        </div><br>
        """, unsafe_allow_html=True)
        
        c_left, c_mid, c_right = st.columns([1, 1.2, 1.2])
        
        with c_left:
            # 图片
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            if has_image and pd.notna(current_product['Image_Url']):
                st.markdown(f'<img src="{current_product["Image_Url"]}" style="width:100%; border-radius:12px; max-height:250px; object-fit:contain;">', unsafe_allow_html=True)
            else: st.info("暂无图片")
            st.markdown('</div>', unsafe_allow_html=True)

        with c_mid:
            # 💰 利润模拟器 (已修复)
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("💰 利润模拟器")
            sell_price = current_product['Clean_Price']
            st.metric("零售价 (Price)", f"${sell_price:.2f}")
            
            cost_price = st.number_input("进货成本 ($)", value=float(sell_price)*0.2, step=1.0)
            ship_cost = st.number_input("头程运费 ($)", value=3.0, step=0.5)
            platform_fee = sell_price * 0.05 
            
            profit = sell_price - cost_price - ship_cost - platform_fee
            margin = (profit / sell_price) * 100 if sell_price > 0 else 0
            
            st.markdown("---")
            c_p1, c_p2 = st.columns(2)
            c_p1.metric("预估净赚", f"${profit:.2f}", delta_color="normal" if profit>0 else "inverse")
            c_p2.metric("利润率", f"{margin:.1f}%")
            st.caption(f"*已扣除约 5% 佣金 (${platform_fee:.2f})")
            st.markdown('</div>', unsafe_allow_html=True)

        with c_right:
            # 🤖 AI 运营助手
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("🤖 AI 运营助手")
            
            tab1, tab2 = st.tabs(["文案优化 (标题&描述)", "视频脚本"])
            
            # === TAB 1: 标题 + 描述 ===
            with tab1:
                orig_name = st.text_input("原标题", value=str(current_product[col_name]))
                keywords = st.text_input("关键词", placeholder="MustHave, Gift", key="kw_in")
                
                # 功能 1: 标题优化
                if st.button("🚀 1. 生成爆款标题"):
                    if is_ai_ready and keywords:
                        with st.spinner("Gemini 优化中..."):
                            prompt = f"Act as TikTok SEO expert. Optimize title: {orig_name}. Keywords: {keywords}. English only. Under 100 chars."
                            res = get_gemini_response(prompt)
                            st.session_state['gen_title'] = res.strip()
                            st.success("优化完成")
                    else:
                        st.session_state['gen_title'] = basic_optimize_title(orig_name)
                        if not is_ai_ready: st.caption("提示: 普通模式生成")

                if 'gen_title' in st.session_state:
                    st.info(f"新标题: {st.session_state['gen_title']}")
                    
                    # 功能 2: 描述生成 (基于新标题)
                    st.markdown("---")
                    if st.button("📝 2. 生成300字描述"):
                        if is_ai_ready and keywords:
                            with st.spinner("AI 撰写中..."):
                                d_prompt = f"Write a 300-word product description for {st.session_state['gen_title']}. Keywords: {keywords}. Tone: Exciting. Format: Plain text."
                                st.session_state['gen_desc'] = get_gemini_response(d_prompt)
                        else:
                            st.warning("普通模式无法生成长文，请登录管理员或输入Key")
                    
                    if 'gen_desc' in st.session_state:
                        st.text_area("英文描述:", value=st.session_state['gen_desc'], height=150)

            # === TAB 2: 脚本 ===
            with tab2:
                # 功能 3: 脚本生成
                if st.button("🎬 3. 生成视频脚本"):
                    target_name = st.session_state.get('gen_title', orig_name)
                    if is_ai_ready and keywords:
                        with st.spinner("AI 编写中..."):
                            prompt = f"Write a TikTok video script prompt for: {target_name}. Keywords: {keywords}. Include Visual Style, Hook, Scenes."
                            st.text_area("脚本指令:", value=get_gemini_response(prompt), height=250)
                    else:
                        st.text_area("基础脚本:", value=basic_generate_script(target_name, sell_price), height=150)
                        if not is_ai_ready: st.caption("提示: 普通模式生成")

            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("👈 请点击【上方图表】、【Top3推荐】或【商品清单】中的任意一项，开启深度分析与算账。")

else:
    st.markdown('<div class="glass-card" style="text-align: center; padding: 60px;"><h2>👈 请上传数据表格</h2></div>', unsafe_allow_html=True)