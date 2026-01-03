import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os

# ==========================================
# 0. 全局配置与终极 iOS 美化
# ==========================================
st.set_page_config(
    page_title="TK选品分析青春版",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 终极 iOS 原生质感 CSS (核心美化代码) ---
st.markdown("""
<style>
    /* 1. 全局背景：苹果动态光影壁纸 */
    .stApp {
        background: url("https://images.unsplash.com/photo-1557683316-973673baf926?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D") no-repeat center center fixed;
        background-size: cover;
    }
    /* 修复Streamlit默认的白色遮罩 */
    .main .block-container {
        background: rgba(255, 255, 255, 0) !important;
    }

    /* 2. 毛玻璃卡片容器 (Frosted Glass Container) */
    .glass-card, div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.75) !important; /* 半透明白 */
        backdrop-filter: blur(20px) saturate(180%); /* 核心：毛玻璃模糊特效 */
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border-radius: 20px; /* 超大圆角 */
        border: 1px solid rgba(255, 255, 255, 0.3); /* 增加质感边框 */
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07); /* 柔和且深邃的阴影 */
        padding: 20px;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); /* 苹果原生物理动画曲线 */
    }
    
    /* 3. 微动效：鼠标悬停 */
    .glass-card:hover, div[data-testid="metric-container"]:hover {
        transform: translateY(-3px) scale(1.01); /* 轻微上浮和放大 */
        box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.6);
    }

    /* 4. Top 3 推荐卡片特别样式 */
    .top-card {
        text-align: center;
        padding: 24px !important;
        background: rgba(255, 255, 255, 0.85) !important; /* 稍微不透明一点，更突出 */
    }
    .top-card h3 { color: #007AFF !important; font-weight: 700; } /* 苹果蓝 */
    
    /* 5. 侧边栏美化 */
    section[data-testid="stSidebar"] {
        background-color: rgba(242, 242, 247, 0.9) !important; /* iOS 侧边栏米白色 */
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(0,0,0,0.05);
    }

    /* 6. 字体与标题 */
    html, body, [class*="css"], h1, h2, h3 {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        color: #1D1D1F !important; /* 苹果深灰黑 */
    }
    h1 { font-weight: 700; letter-spacing: -0.5px; }

    /* 7. 按钮美化 */
    .stButton > button {
        background-color: #007AFF !important; /* 苹果蓝 */
        color: white !important;
        border-radius: 14px;
        font-weight: 600;
        border: none;
        padding: 10px 20px;
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
    }
    .stButton > button:hover { background-color: #0062cc !important; }
    
</style>
""", unsafe_allow_html=True)

# 简易密码锁
if 'auth' not in st.session_state: st.session_state.auth = False
def check_password():
    if st.session_state.auth: return True
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><br><div class='glass-card'><h2 style='text-align: center;'>🔒 访客验证</h2></div>", unsafe_allow_html=True)
        pwd = st.text_input("请输入团队访问密码", type="password", label_visibility="collapsed")
        if pwd == "1997": # 修改密码
            st.session_state.auth = True
            st.rerun()
        elif pwd: st.error("密码错误")
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

def generate_1688_link(title):
    if not isinstance(title, str): return "#"
    ignore = ['pcs', 'set', 'for', 'with', 'and', 'new', 'hot', 'sale', 'women', 'men', 'color']
    words = [w for w in title.split() if w.lower() not in ignore and len(w)>2]
    keyword = " ".join(words[:4])
    return f"https://s.1688.com/selloffer/offer_search.htm?keywords={keyword}"

# ==========================================
# 2. 侧边栏配置
# ==========================================
# 显示头像
if os.path.exists("avatar.png"):
    c1, c2, c3 = st.sidebar.columns([1, 2, 1])
    with c2:
        st.image("avatar.png", width=110)
st.sidebar.markdown("<h3 style='text-align: center; margin-top: -10px;'>TK选品分析青春版</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader("📂 上传 Kalodata/EchoTik 表格", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: df = pd.read_excel(uploaded_file)
    except: st.error("文件格式错误"); st.stop()

    # 字段校准
    cols = list(df.columns)
    with st.sidebar.expander("🔧 字段校准 (默认折叠)", expanded=False):
        guess_name = next((c for c in cols if 'Title' in c or '名称' in c or 'Name' in c), cols[0])
        guess_price = next((c for c in cols if 'Price' in c or '价格' in c), cols[1] if len(cols)>1 else cols[0])
        guess_sales = next((c for c in cols if 'Sales' in c or '销量' in c), cols[2] if len(cols)>2 else cols[0])
        col_name = st.selectbox("商品标题列", cols, index=cols.index(guess_name))
        col_price = st.selectbox("价格列 (Price)", cols, index=cols.index(guess_price))
        col_sales = st.selectbox("销量列 (Sales)", cols, index=cols.index(guess_sales))
    
    # 数据清洗
    main_df = df.copy()
    main_df['Clean_Price'] = main_df[col_price].apply(clean_currency)
    main_df['Clean_Sales'] = main_df[col_sales].apply(clean_currency)
    main_df['GMV'] = main_df['Clean_Price'] * main_df['Clean_Sales']
    main_df['1688_Link'] = main_df[col_name].apply(generate_1688_link)

    # 漏斗筛选
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
    # 3. 主界面：iOS 风格仪表盘
    # ==========================================
    st.title("🍎 TK选品分析青春版")

    # [板块 1] 宏观指标 (毛玻璃卡片)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("筛选池总 GMV", f"${filtered_df['GMV'].sum():,.0f}")
    m2.metric("平均客单价", f"${filtered_df['Clean_Price'].mean():.2f}")
    m3.metric("潜力爆款数", len(filtered_df))
    m4.metric("最高单品销量", f"{filtered_df['Clean_Sales'].max():,.0f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # [板块 2] Top 3 爆品推荐 (回归！iOS 小组件风格)
    st.subheader("🔥 今日 Top 3 爆品推荐")
    top_3_df = filtered_df.sort_values('GMV', ascending=False).head(3)
    
    if len(top_3_df) >= 3:
        t1, t2, t3 = st.columns(3)
        # 使用自定义 HTML 构建带毛玻璃效果的卡片
        for i, (col, icon) in enumerate(zip([t1, t2, t3], ["🥇", "🥈", "🥉"])):
            row = top_3_df.iloc[i]
            short_title = (row[col_name][:35] + '...') if len(row[col_name]) > 35 else row[col_name]
            with col:
                st.markdown(f"""
                <div class="glass-card top-card">
                    <h3>{icon} GMV: ${row['GMV']:,.0f}</h3>
                    <p style="font-weight: 600; height: 50px; overflow: hidden;">{short_title}</p>
                    <p>售价: ${row['Clean_Price']:.2f} | 销量: {int(row['Clean_Sales'])}</p>
                    <a href="{row['1688_Link']}" target="_blank">
                        <button style="background-color: #007AFF; color: white; border: none; padding: 8px 16px; border-radius: 12px; cursor: pointer; font-weight: 600;">
                            🚀 1688 找货
                        </button>
                    </a>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("数据不足，无法生成 Top 3 推荐，请上传更多数据。")

    st.markdown("<br>", unsafe_allow_html=True)

    # [板块 3] 图表分析区 (包裹在毛玻璃容器中)
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True) # 开始容器
        c1, c2 = st.columns([7, 3])
        with c1:
            st.subheader("🔭 蓝海象限图")
            if not filtered_df.empty:
                fig = px.scatter(
                    filtered_df, x='Clean_Price', y='Clean_Sales', size='GMV', 
                    color='Clean_Price', hover_name=col_name, log_y=True,
                    template="plotly_white", color_continuous_scale="Blues"
                )
                # 让图表背景透明，透出毛玻璃
                fig.update_layout(height=400, margin=dict(l=20,r=20,t=30,b=20), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("暂无数据")
        with c2:
            st.subheader("💡 标题热词云")
            all_titles = " ".join(filtered_df[col_name].astype(str).tolist()).lower()
            ignore_words = ['for', 'and', 'with', 'the', 'pcs', 'set', 'new', 'hot', 'color', 'size']
            words = re.findall(r'\b\w+\b', all_titles)
            clean_words = [w for w in words if w not in ignore_words and len(w)>2 and not w.isdigit()]
            if clean_words:
                w_df = pd.DataFrame(Counter(clean_words).most_common(10), columns=['Word', 'Count'])
                fig_bar = px.bar(w_df, x='Count', y='Word', orientation='h', color='Count', color_continuous_scale="Greens")
                fig_bar.update_layout(yaxis={'autorange': 'reversed'}, height=400, margin=dict(l=0,r=0,t=30,b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True) # 结束容器

    st.markdown("<br>", unsafe_allow_html=True)

    # [板块 4] 交互式清单
    st.subheader("📋 精品清单 (点击查看详情)")
    display_df = filtered_df.sort_values('GMV', ascending=False).reset_index(drop=True)
    
    selection = st.dataframe(
        display_df[[col_name, 'Clean_Price', 'Clean_Sales', 'GMV']],
        column_config={
            col_name: st.column_config.TextColumn("商品标题", width="large"),
            "Clean_Price": st.column_config.NumberColumn("售价($)", format="$%.2f"),
            "Clean_Sales": st.column_config.NumberColumn("销量", format="%d"),
            "GMV": st.column_config.NumberColumn("GMV($)", format="$%.0f"),
        },
        use_container_width=True,
        height=400,
        on_select="rerun",
        selection_mode="single-row"
    )

    if selection.selection["rows"]:
        selected_index = selection.selection["rows"][0]
        row = display_df.iloc[selected_index]
        # 详情弹窗也用毛玻璃包裹
        st.markdown(f"""
        <div class="glass-card" style="background: rgba(0,122,255,0.1) !important; border: 1px solid #007AFF;">
            <h3 style="margin-top: 0;">🎯 已选中：{row[col_name]}</h3>
            <p><b>售价:</b> ${row['Clean_Price']:.2f} | <b>预估 GMV:</b> ${row['GMV']:,.0f}</p>
            <a href="{row['1688_Link']}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #007AFF; color: white; padding: 12px 24px; border-radius: 12px; text-align: center; font-weight: 600; box-shadow: 0 4px 12px rgba(0,122,255,0.3);">
                    🚀 跳转 1688 找同款
                </div>
            </a>
        </div>
        """, unsafe_allow_html=True)

else:
    # 空状态页 (带背景的毛玻璃卡片)
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 50px;">
        <h2>👈 请在左侧上传数据表格</h2>
        <p style="color: #666;">开启您的 iOS 风格跨境选品之旅</p>
    </div>
    """, unsafe_allow_html=True)