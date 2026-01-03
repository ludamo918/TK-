import streamlit as st
import pandas as pd
import plotly.express as px
import re
from collections import Counter
import os

# ==========================================
# 0. 全局配置与安全锁
# ==========================================
st.set_page_config(
    page_title="TK选品分析青春版",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- iOS 极简风 CSS ---
st.markdown("""
<style>
    /* 全局字体与背景 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .stApp {
        background-color: #F2F2F7; /* iOS 浅灰背景 */
    }
    
    /* 卡片式设计 (Metric & Containers) */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        border-radius: 16px; /* 大圆角 */
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); /* 柔和阴影 */
        border: none;
    }
    
    /* 侧边栏美化 */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid rgba(0,0,0,0.05);
    }
    
    /* 按钮美化 (iOS 风格) */
    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* 表格美化 */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    /* 标题微调 */
    h1, h2, h3 {
        font-weight: 600;
        color: #1C1C1E;
    }
</style>
""", unsafe_allow_html=True)

# 简易密码锁
if 'auth' not in st.session_state: st.session_state.auth = False
def check_password():
    if st.session_state.auth: return True
    # 使用 columns 居中放置密码框
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><br><h2 style='text-align: center;'>🔒 访客验证</h2>", unsafe_allow_html=True)
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
# 2. 侧边栏：个人中心与数据装载
# ==========================================
# 显示头像 (如果存在)
if os.path.exists("avatar.png"):
    c1, c2, c3 = st.sidebar.columns([1, 2, 1])
    with c2:
        st.image("avatar.png", width=120, output_format="PNG")
st.sidebar.markdown("<h3 style='text-align: center;'>TK选品分析青春版</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")

st.sidebar.header("📂 数据装载舱")
uploaded_file = st.sidebar.file_uploader("上传 Kalodata/EchoTik 导出表", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: df = pd.read_excel(uploaded_file)
    except: st.error("文件格式错误"); st.stop()

    # 字段校准
    cols = list(df.columns)
    with st.sidebar.expander("🔧 字段校准 (点此展开)", expanded=False):
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
    # 3. 主界面
    # ==========================================
    st.title("⚡ TK选品分析青春版")
    st.caption(f"数据源: {uploaded_file.name} | 已筛选精品: {len(filtered_df)} 款")

    # 宏观指标卡片
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("筛选池总 GMV", f"${filtered_df['GMV'].sum():,.0f}")
    m2.metric("平均客单价", f"${filtered_df['Clean_Price'].mean():.2f}")
    m3.metric("潜力爆款数", len(filtered_df))
    m4.metric("最高单品销量", f"{filtered_df['Clean_Sales'].max():,.0f}")

    st.markdown("<br>", unsafe_allow_html=True) # 增加间距

    # 图表区 (卡片化容器)
    with st.container():
        c1, c2 = st.columns([7, 3])
        with c1:
            st.subheader("🔭 蓝海象限图 (寻找右上角)")
            if not filtered_df.empty:
                fig = px.scatter(
                    filtered_df, x='Clean_Price', y='Clean_Sales', size='GMV', 
                    color='Clean_Price', hover_name=col_name, log_y=True,
                    template="plotly_white", color_continuous_scale="Blues"
                )
                fig.update_layout(height=450, margin=dict(l=20, r=20, t=30, b=20),
                                  plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("暂无数据，请调整筛选条件")

        with c2:
            st.subheader("💡 标题热词云")
            all_titles = " ".join(filtered_df[col_name].astype(str).tolist()).lower()
            ignore_words = ['for', 'and', 'with', 'the', 'pcs', 'set', 'new', 'hot', 'color', 'size', 'women', 'high']
            words = re.findall(r'\b\w+\b', all_titles)
            clean_words = [w for w in words if w not in ignore_words and len(w)>2 and not w.isdigit()]
            if clean_words:
                w_df = pd.DataFrame(Counter(clean_words).most_common(10), columns=['Word', 'Count'])
                fig_bar = px.bar(w_df, x='Count', y='Word', orientation='h', color='Count', color_continuous_scale="Greens")
                fig_bar.update_layout(yaxis={'autorange': 'reversed'}, height=450, margin=dict(l=20, r=20, t=30, b=20),
                                      plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 交互式清单区
    st.subheader("📋 精品清单 (点击行查看详情)")
    display_df = filtered_df.sort_values('GMV', ascending=False).reset_index(drop=True)
    
    # 高性能交互表格 (PC端专属)
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
        on_select="rerun", # 开启点击交互
        selection_mode="single-row" # 单行选择
    )

    # 选中后的详情弹窗
    if selection.selection["rows"]:
        selected_index = selection.selection["rows"][0]
        row = display_df.iloc[selected_index]
        
        with st.container():
            st.info(f"🎯 已选中：**{row[col_name]}**")
            c_a, c_b, c_c = st.columns(3)
            c_a.metric("售价", f"${row['Clean_Price']:.2f}")
            c_b.metric("预估 GMV", f"${row['GMV']:,.0f}")
            # 醒目的 iOS 风格按钮
            c_c.markdown(f"""
                <a href="{row['1688_Link']}" target="_blank" style="text-decoration: none;">
                    <div style="background-color: #007AFF; color: white; padding: 12px 24px; border-radius: 12px; text-align: center; font-weight: 600; box-shadow: 0 4px 12px rgba(0,122,255,0.3);">
                        🚀 跳转 1688 找同款
                    </div>
                </a>
            """, unsafe_allow_html=True)
    else:
        st.caption("👆 点击表格中的任意一行，在此处查看详情和 1688 链接。")

else:
    # 空状态引导页
    st.info("👈 请在左侧上传您的选品数据表格，开始探索。")