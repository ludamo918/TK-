import streamlit as st
import pandas as pd
import plotly.express as px
import re
from collections import Counter

# ==========================================
# 0. 全局配置与安全锁
# ==========================================
st.set_page_config(
    page_title="TK 跨境数据指挥台 (兼容版)",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 美化
st.markdown("""
<style>
    .stApp { background-color: #f4f6f9; }
    .metric-card {
        background-color: white; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;
    }
    /* 修复老版本表格字体 */
    .stDataFrame { font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# 简易密码锁
if 'auth' not in st.session_state: st.session_state.auth = False
def check_password():
    if st.session_state.auth: return True
    pwd = st.text_input("🔐 请输入团队访问密码", type="password")
    if pwd == "888888": # 修改密码
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
    ignore = ['pcs', 'set', 'for', 'with', 'and', 'new', 'hot', 'sale', 'women', 'men']
    words = [w for w in title.split() if w.lower() not in ignore and len(w)>2]
    keyword = " ".join(words[:4]) # 取前4个词，提高搜索成功率
    return f"https://s.1688.com/selloffer/offer_search.htm?keywords={keyword}"

# ==========================================
# 2. 侧边栏：数据中心与筛选器
# ==========================================
st.sidebar.header("📂 数据装载舱")
uploaded_file = st.sidebar.file_uploader("上传 Kalodata/EchoTik 导出表", type=["xlsx", "csv"])

if uploaded_file:
    # A. 读取数据
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: df = pd.read_excel(uploaded_file)
    except: st.error("文件格式错误"); st.stop()

    # B. 字段校准
    cols = list(df.columns)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔧 字段校准")
    
    guess_name = next((c for c in cols if 'Title' in c or '名称' in c or 'Name' in c), cols[0])
    guess_price = next((c for c in cols if 'Price' in c or '价格' in c), cols[1] if len(cols)>1 else cols[0])
    guess_sales = next((c for c in cols if 'Sales' in c or '销量' in c), cols[2] if len(cols)>2 else cols[0])

    col_name = st.sidebar.selectbox("商品标题列", cols, index=cols.index(guess_name))
    col_price = st.sidebar.selectbox("价格列 (Price)", cols, index=cols.index(guess_price))
    col_sales = st.sidebar.selectbox("销量列 (Sales)", cols, index=cols.index(guess_sales))
    
    # C. 数据清洗
    main_df = df.copy()
    main_df['Clean_Price'] = main_df[col_price].apply(clean_currency)
    main_df['Clean_Sales'] = main_df[col_sales].apply(clean_currency)
    main_df['GMV'] = main_df['Clean_Price'] * main_df['Clean_Sales']
    main_df['1688_Link'] = main_df[col_name].apply(generate_1688_link)

    # D. 漏斗筛选
    st.sidebar.markdown("---")
    st.sidebar.subheader("🌪️ 选品漏斗")
    
    min_price, max_price = int(main_df['Clean_Price'].min()), int(main_df['Clean_Price'].max())
    # 防止滑块报错：如果最大最小值一样，手动处理
    if min_price == max_price: max_price += 1
    
    price_range = st.sidebar.slider("💰 价格区间 (USD)", min_price, max_price, (min_price, max_price))
    sales_min = st.sidebar.number_input("🔥 最低销量筛选", min_value=0, value=100)

    filtered_df = main_df[
        (main_df['Clean_Price'] >= price_range[0]) & 
        (main_df['Clean_Price'] <= price_range[1]) &
        (main_df['Clean_Sales'] >= sales_min)
    ]

    # ==========================================
    # 3. 主界面
    # ==========================================
    st.title("🛳️ TK 跨境选品指挥台 (兼容版)")
    st.markdown(f"**数据源:** {uploaded_file.name} | **筛选后剩余:** {len(filtered_df)} 款商品")

    # [区域 1] 宏观指标
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("筛选池总 GMV", f"${filtered_df['GMV'].sum():,.0f}")
    m2.metric("平均客单价", f"${filtered_df['Clean_Price'].mean():.2f}")
    m3.metric("潜力爆款数", len(filtered_df))
    m4.metric("最高单品销量", f"{filtered_df['Clean_Sales'].max():,.0f}")

    st.divider()

    # [区域 2] 蓝海象限图
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("🔭 市场象限图 (寻找右上角)")
        if not filtered_df.empty:
            fig = px.scatter(
                filtered_df, 
                x='Clean_Price', 
                y='Clean_Sales',
                size='GMV', 
                color='Clean_Price',
                hover_name=col_name,
                log_y=True,
                template="plotly_white",
                color_continuous_scale="RdBu_r"
            )
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("暂无数据，请调整筛选条件")

    with c2:
        st.subheader("💡 标题热词云")
        all_titles = " ".join(filtered_df[col_name].astype(str).tolist()).lower()
        ignore_words = ['for', 'and', 'with', 'the', 'pcs', 'set', 'new', 'hot', 'color', 'size', 'women']
        words = re.findall(r'\b\w+\b', all_titles)
        clean_words = [w for w in words if w not in ignore_words and len(w)>2 and not w.isdigit()]
        
        if clean_words:
            top_words = Counter(clean_words).most_common(10)
            w_df = pd.DataFrame(top_words, columns=['Word', 'Count'])
            fig_bar = px.bar(w_df, x='Count', y='Word', orientation='h', color='Count')
            fig_bar.update_layout(yaxis={'autorange': 'reversed'}, height=450)
            st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # [区域 3] 选品清单 & 深度分析
    st.subheader("📋 爆品清单与分析")
    
    # 替换掉报错的交互表格，改用更稳定的“下拉选择”模式
    display_df = filtered_df.sort_values('GMV', ascending=False)
    
    # 1. 提供一个下拉框让用户选品
    product_list = display_df[col_name].tolist()
    if product_list:
        selected_prod = st.selectbox("🔍 在此处搜索或选择商品进行分析：", product_list)
        
        # 找到选中的那一行数据
        row = display_df[display_df[col_name] == selected_prod].iloc[0]
        
        # 展示选中商品的详情卡片
        st.info(f"正在分析：**{row[col_name]}**")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("单价", f"${row['Clean_Price']}")
        col_b.metric("销量", f"{int(row['Clean_Sales'])}")
        col_c.markdown(f"👉 [**点击跳转 1688 找同款**]({row['1688_Link']})")
    
    # 2. 展示静态大表格
    st.markdown("---")
    st.dataframe(
        display_df[[col_name, 'Clean_Price', 'Clean_Sales', 'GMV', '1688_Link']],
        column_config={
            col_name: "商品标题",
            "Clean_Price": st.column_config.NumberColumn("售价($)", format="$%.2f"),
            "Clean_Sales": st.column_config.NumberColumn("销量", format="%d"),
            "GMV": st.column_config.NumberColumn("GMV($)", format="$%.0f"),
            "1688_Link": st.column_config.LinkColumn("供应链", display_text="找同款")
        },
        use_container_width=True,
        height=500
    )

else:
    st.info("👈 请在左侧上传数据文件")