import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os
import random
from collections import Counter

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
    
    /* AI 生成结果框 */
    .ai-box {
        background-color: #F2F2F7;
        padding: 15px;
        border-radius: 12px;
        border-left: 4px solid #5856D6;
        margin-top: 10px;
        font-family: monospace;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# --- 状态管理 ---
if 'selected_product_title' not in st.session_state:
    st.session_state.selected_product_title = None

# 密码锁
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
        pwd = st.text_input("请输入团队访问密码", type="password", label_visibility="collapsed")
        if pwd == "1997": 
            st.session_state.auth = True
            st.rerun()
        elif pwd: st.error("🚫 密码错误")
        st.markdown('</div>', unsafe_allow_html=True)
    return False
if not check_password(): st.stop()

# ==========================================
# 1. 核心工具函数 (含 AI 模拟)
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

def optimize_title(original_title):
    """模拟 AI 优化标题"""
    remove_list = ['pcs', 'set', 'for', 'women', 'men', 'sale', 'hot', 'new', '2025', 'high quality']
    words = original_title.split()
    clean_words = [w for w in words if w.lower() not in remove_list]
    
    # 截取核心词
    short_title = " ".join(clean_words[:8])
    
    # 随机添加 Emoji 和标签
    emojis = ['🔥', '✨', '💖', '🎁', '🚀', '⭐']
    tags = ['#TikTokMadeMeBuyIt', '#fyp', '#Trending', '#MustHave']
    
    return f"{random.choice(emojis)} {short_title} {random.choice(emojis)}\n\n{random.choice(tags)} {random.choice(tags)}"

def generate_script(title, price):
    """模拟 AI 生成脚本"""
    hooks = [
        "Stop scrolling! You need to see this! 🛑",
        "This product literally changed my life! 😱",
        "Best find on TikTok Shop under $50! 🔥"
    ]
    pain_points = [
        "Tired of boring gifts? This is the perfect solution.",
        "Struggling with messy hair? This fixes it in seconds.",
        "Want to look stylish without breaking the bank?"
    ]
    cta = [
        f"Grab yours now for only ${price:.2f}!",
        "Click the yellow basket below before it sells out! 👇",
        "Limited stock available, hurry up! 🏃💨"
    ]
    
    return f"""
    **[0-3s Hook]**: {random.choice(hooks)}
    
    **[3-15s Demo]**: {random.choice(pain_points)} Look at this details... (Show product close-up). It's super high quality and easy to use.
    
    **[15s+ CTA]**: {random.choice(cta)}
    """

# ==========================================
# 2. 数据处理
# ==========================================
if os.path.exists("avatar.png"):
    c1, c2, c3 = st.sidebar.columns([1, 2, 1])
    with c2: st.image("avatar.png", width=110)
st.sidebar.markdown("<h3 style='text-align: center; margin-top: -10px;'>TK选品分析青春版</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader("📂 上传 Kalodata/EchoTik 表格", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: df = pd.read_excel(uploaded_file)
    except: st.error("文件格式错误"); st.stop()

    cols = list(df.columns)
    with st.sidebar.expander("🔧 字段校准 (含图片列)", expanded=True):
        guess_name = next((c for c in cols if 'Title' in c or '名称' in c or 'Name' in c), cols[0])
        guess_price = next((c for c in cols if 'Price' in c or '价格' in c), cols[1] if len(cols)>1 else cols[0])
        guess_sales = next((c for c in cols if 'Sales' in c or '销量' in c), cols[2] if len(cols)>2 else cols[0])
        guess_img = next((c for c in cols if 'Image' in c or 'Img' in c or 'Pic' in c or '图' in c or 'Cover' in c), None)

        col_name = st.selectbox("商品标题列", cols, index=cols.index(guess_name))
        col_price = st.selectbox("价格列 (Price)", cols, index=cols.index(guess_price))
        col_sales = st.selectbox("销量列 (Sales)", cols, index=cols.index(guess_sales))
        col_img = st.selectbox("图片链接列 (可选)", ["无"] + cols, index=(cols.index(guess_img) + 1) if guess_img else 0)
    
    main_df = df.copy()
    main_df['Clean_Price'] = main_df[col_price].apply(clean_currency)
    main_df['Clean_Sales'] = main_df[col_sales].apply(clean_currency)
    main_df['GMV'] = main_df['Clean_Price'] * main_df['Clean_Sales']
    
    has_image = col_img != "无"
    if has_image: main_df['Image_Url'] = main_df[col_img].astype(str)

    st.sidebar.subheader("🌪️ 选品漏斗")
    min_p, max_p = int(main_df['Clean_Price'].min()), int(main_df['Clean_Price'].max())
    if min_p == max_p: max_p += 1
    price_range = st.sidebar.slider("💰 价格区间 ($)", min_p, max_p, (min_p, max_p))
    sales_min = st.sidebar.number_input("🔥 最低销量", min_value=0, value=100)

    filtered_df = main_df[
        (main_df['Clean_Price'] >= price_range[0]) & 
        (main_df['Clean_Price'] <= price_range[1]) &
        (main_df['Clean_Sales'] >= sales_min)
    ]

    # ==========================================
    # 3. 主界面布局
    # ==========================================
    st.title("✨ TK选品分析青春版")

    # 1. 宏观指标
    m1, m2, m3, m4 = st.columns(4)
    avg_price = filtered_df['Clean_Price'].mean()
    m1.metric("筛选池总 GMV", f"${filtered_df['GMV'].sum():,.0f}")
    m2.metric("平均客单价", f"${avg_price:.2f}")
    m3.metric("潜力爆款数", len(filtered_df))
    m4.metric("最高单品销量", f"{filtered_df['Clean_Sales'].max():,.0f}")
    st.markdown("<br>", unsafe_allow_html=True)

# 2. Top 3 推荐 (点击触发)
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

    # 3. 柱状图 (支持点击！)
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
            # 开启点击事件
            selected_points = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
            
            # 处理图表点击逻辑
            if selected_points and selected_points['selection']['points']:
                # 获取点击的索引
                point_idx = selected_points['selection']['points'][0]['point_index']
                # 从 chart_df 里找到对应的商品名
                clicked_product = chart_df.iloc[point_idx][col_name]
                st.session_state.selected_product_title = clicked_product
                
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. 精品清单 (点击跳转)
    st.subheader("📋 所有商品清单 (点击行 -> 自动跳转分析室)")
    display_cols = [col_name, 'Clean_Price', 'Clean_Sales', 'GMV']
    if has_image: display_cols.insert(0, 'Image_Url')
    
    col_config = {
        col_name: st.column_config.TextColumn("商品标题", width="medium"),
        "Clean_Price": st.column_config.NumberColumn("售价($)", format="$%.2f"),
        "Clean_Sales": st.column_config.NumberColumn("销量", format="%d"),
        "GMV": st.column_config.NumberColumn("GMV($)", format="$%.0f"),
    }
    if has_image: col_config["Image_Url"] = st.column_config.ImageColumn("主图")

    selection = st.dataframe(
        filtered_df.sort_values('GMV', ascending=False)[display_cols],
        column_config=col_config, use_container_width=True, height=400,
        on_select="rerun", selection_mode="single-row"
    )

    # 5. 统一处理选品逻辑
    current_product = None
    
    # 优先级：表格点击 > 图表点击 > 按钮点击 > 历史状态
    if selection.selection["rows"]:
        selected_index = selection.selection["rows"][0]
        # 重新定位回原始 dataframe
        sorted_df = filtered_df.sort_values('GMV', ascending=False)
        current_product = sorted_df.iloc[selected_index]
        # 更新状态以便刷新后保持
        st.session_state.selected_product_title = current_product[col_name]
    elif st.session_state.selected_product_title:
        match = filtered_df[filtered_df[col_name] == st.session_state.selected_product_title]
        if not match.empty:
            current_product = match.iloc[0]

    # 6. 单品战术分析室 (AI 增强版)
    # 创建一个锚点，虽然Streamlit不能强制滚动，但视觉上放在最后是合理的
    st.markdown("<div id='analysis_target'></div>", unsafe_allow_html=True)
    
    if current_product is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="glass-card analysis-room">
            <h2 style="color: #5856D6 !important; margin-top:0;">🎯 单品战术分析室</h2>
            <p style="color: #666;">已锁定商品：{current_product[col_name]}</p>
        </div>
        """, unsafe_allow_html=True)
        
        c_left, c_right = st.columns([1, 1.5])
        
        with c_left:
            # 左侧：高清大图 + 核心数据
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            if has_image and pd.notna(current_product['Image_Url']):
                st.markdown(f'<img src="{current_product["Image_Url"]}" style="width:100%; border-radius:12px; margin-bottom:15px;">', unsafe_allow_html=True)
            
            st.metric("💰 预估 GMV", f"${current_product['GMV']:,.0f}")
            col_a, col_b = st.columns(2)
            col_a.metric("售价", f"${current_product['Clean_Price']:.2f}")
            col_b.metric("销量", f"{int(current_product['Clean_Sales'])}")
            st.markdown('</div>', unsafe_allow_html=True)

        with c_right:
            # 右侧：AI 运营工具箱
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("🤖 AI 运营工具箱")
            
            tab1, tab2 = st.tabs(["✨ 标题优化", "📹 脚本生成"])
            
            with tab1:
                st.markdown("**原始标题：**")
                st.caption(current_product[col_name])
                if st.button("🚀 一键生成 TK 爆款标题"):
                    optimized = optimize_title(current_product[col_name])
                    st.markdown(f"""
                    <div class="ai-box">
                    {optimized.replace(chr(10), '<br>')}
                    </div>
                    """, unsafe_allow_html=True)
                    st.success("已优化！符合 TikTok 搜索习惯")

            with tab2:
                st.markdown("**适用场景：** 短视频带货 / 直播话术")
                if st.button("🎥 生成 3 段式脚本"):
                    script = generate_script(current_product[col_name], current_product['Clean_Price'])
                    st.markdown(f"""
                    <div class="ai-box">
                    {script.replace(chr(10), '<br>')}
                    </div>
                    """, unsafe_allow_html=True)
                    st.success("脚本结构：黄金3秒 + 痛点 + 促单")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
    else:
        # 空状态占位
        st.info("👇 请点击【上方图表】或【商品清单】中的任意一项，深度分析室将在此处自动展开。")

else:
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 60px;">
        <h2 style="color: #1D1D1F !important;">👈 请在左侧上传数据表格</h2>
        <p style="color: #86868b !important; font-size: 18px;">开启您的 iOS 极简风选品之旅</p>
    </div>
    """, unsafe_allow_html=True)