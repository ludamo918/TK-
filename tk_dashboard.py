import streamlit as st
import pandas as pd
import plotly.express as px
import re
from collections import Counter

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="TK 爆款收割机 (单品狙击版)",
    page_icon="🎯",
    layout="wide"
)

# --- 2. 状态管理 (实现点击跳转的核心) ---
if 'selected_product_name' not in st.session_state:
    st.session_state['selected_product_name'] = None

# --- 3. 细腻 UI CSS ---
st.markdown("""
<style>
    /* 全局背景：极淡蓝灰，护眼高级 */
    .stApp { background-color: #f0f2f5; font-family: 'PingFang SC', sans-serif; }
    
    /* 侧边栏 */
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e1e4e8; }
    
    /* 指标卡片 */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* 🏆 推荐卡片 (交互核心) */
    .rec-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e1e4e8;
        border-top: 4px solid #3b82f6; /* 顶部蓝条 */
        box-shadow: 0 4px 6px rgba(0,0,0,0.03);
        height: 100%;
        transition: 0.3s;
    }
    .rec-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px rgba(0,0,0,0.1);
    }
    .rank-tag {
        background: #e6f7ff; color: #1890ff; 
        padding: 2px 8px; border-radius: 4px; 
        font-size: 12px; font-weight: bold;
        display: inline-block; margin-bottom: 10px;
    }
    .prod-title {
        font-size: 15px; font-weight: 600; color: #333;
        height: 45px; overflow: hidden; margin-bottom: 10px;
    }
    .prod-data {
        font-size: 22px; font-weight: 800; color: #1f1f1f;
    }
    
    /* 🎯 单品分析室 (详情页) */
    .detail-box {
        background: #ffffff;
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 30px;
        margin: 20px 0;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.1);
        animation: fadeIn 0.5s;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>
""", unsafe_allow_html=True)

# --- 4. 工具函数 ---
def clean_number(val):
    if pd.isna(val): return 0
    s = str(val).strip()
    s = re.sub(r'[¥$£,，]', '', s)
    multiplier = 1
    if '万' in s: multiplier = 10000; s = s.replace('万', '')
    if 'w' in s.lower(): multiplier = 10000; s = s.replace('w', '').replace('W', '')
    if 'k' in s.lower(): multiplier = 1000; s = s.replace('k', '').replace('K', '')
    match = re.search(r'(\d+(\.\d+)?)', s)
    if match: return float(match.group(1)) * multiplier
    return 0

def get_keywords(text):
    # 提取单个标题的关键词
    stop_words = ['for', 'and', 'with', 'the', 'in', 'of', 'a', 'to', 'pcs', 'set', 'new', 'hot']
    words = re.findall(r'\b\w+\b', str(text).lower())
    return [w for w in words if w not in stop_words and len(w) > 2 and not w.isdigit()]

# --- 5. 侧边栏 ---
st.sidebar.title("📂 数据工作台")
uploaded_file = st.sidebar.file_uploader("1. 上传表格 (Excel/CSV)", type=["xlsx", "csv"])

st.sidebar.markdown("---")
st.sidebar.caption("🔧 列名校准 (如数据不对请调整)")
# 占位符，等数据加载后再填充
col_placeholder = st.sidebar.empty()

# --- 6. 主逻辑 ---
if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error("文件读取失败")
        st.stop()

    cols = list(df.columns)
    
    # 在侧边栏填充下拉框
    with col_placeholder.container():
        idx_name = next((i for i, c in enumerate(cols) if 'name' in str(c).lower() or '标题' in str(c)), 0)
        idx_price = next((i for i, c in enumerate(cols) if 'price' in str(c).lower() or '价' in str(c)), 1 if len(cols)>1 else 0)
        idx_sales = next((i for i, c in enumerate(cols) if 'sales' in str(c).lower() or '量' in str(c)), 2 if len(cols)>2 else 0)

        col_name = st.selectbox("标题列", cols, index=idx_name)
        col_price = st.selectbox("价格列", cols, index=idx_price)
        col_sales = st.selectbox("销量列", cols, index=idx_sales)

    # 数据处理
    clean_df = df[[col_name, col_price, col_sales]].copy()
    clean_df.columns = ['Name', 'Raw_Price', 'Raw_Sales']
    clean_df['Price'] = clean_df['Raw_Price'].apply(clean_number)
    clean_df['Sales'] = clean_df['Raw_Sales'].apply(clean_number)
    clean_df['Revenue'] = clean_df['Price'] * clean_df['Sales']
    
    # 过滤无效数据并计算评分
    final_df = clean_df[clean_df['Price'] > 0].reset_index(drop=True)
    max_rev = final_df['Revenue'].max() if final_df['Revenue'].max() > 0 else 1
    final_df['Score'] = (final_df['Revenue'] / max_rev) * 100
    
    # 排序
    top_products = final_df.sort_values('Score', ascending=False).head(3).reset_index(drop=True)

    # --- 界面展示 ---
    
    st.title("🚀 TK 爆款收割机")
    
    # 1. 基础大盘
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("市场总规模 (GMV)", f"${final_df['Revenue'].sum():,.0f}")
    k2.metric("总销量", f"{final_df['Sales'].sum():,.0f}")
    k3.metric("爆品数量", f"{len(final_df)}")
    k4.metric("平均客单价", f"${final_df['Price'].mean():.2f}")
    
    st.divider()

    # 2. 智能推荐区 (Top 3)
    st.subheader("🏆 必上爆款 Top 3 (点击按钮深度分析)")
    
    c1, c2, c3 = st.columns(3)
    for i, col in enumerate([c1, c2, c3]):
        if i < len(top_products):
            row = top_products.iloc[i]
            with col:
                st.markdown(f"""
                <div class="rec-card">
                    <span class="rank-tag">TOP {i+1} 推荐</span>
                    <div class="prod-title">{row['Name'][:40]}...</div>
                    <div class="prod-data">${row['Revenue']:,.0f}</div>
                    <div style="color:#666; font-size:12px; margin-bottom:15px;">
                        销量: {int(row['Sales'])} | 单价: ${row['Price']:.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 核心交互按钮
                if st.button(f"🔍 深度分析这款", key=f"btn_top_{i}", use_container_width=True):
                    st.session_state['selected_product_name'] = row['Name']
                    st.rerun()

    # --- 3. 单品分析室 (只有选中了才显示) ---
    if st.session_state['selected_product_name']:
        # 查找对应数据
        target_df = final_df[final_df['Name'] == st.session_state['selected_product_name']]
        
        if not target_df.empty:
            target_row = target_df.iloc[0]
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class="detail-box">
                <h2 style="color:#3b82f6; margin-bottom:0;">🎯 单品战术分析室</h2>
                <p style="color:#666;">当前锁定商品数据</p>
                <h3 style="margin-top:10px;">{target_row['Name']}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # 单品详情布局
            col_d1, col_d2 = st.columns([1, 2])
            
            with col_d1:
                st.info("📊 核心数据指标")
                st.metric("该商品总成交额", f"${target_row['Revenue']:,.0f}")
                st.metric("该商品总销量", f"{int(target_row['Sales'])}")
                st.metric("商品单价", f"${target_row['Price']:.2f}")
                
            with col_d2:
                st.success("🔑 专属关键词拆解 (标题里包含的高频词)")
                # 拆解标题关键词
                words = get_keywords(target_row['Name'])
                if words:
                    # 统计词频
                    word_counts = Counter(words).most_common(10)
                    kw_df = pd.DataFrame(word_counts, columns=['关键词', '频率'])
                    
                    fig = px.bar(kw_df, x='频率', y='关键词', orientation='h', height=250)
                    fig.update_layout(yaxis={'autorange': 'reversed'}, margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("标题太短，无法提取更多关键词")
            
            # 复制区域
            st.markdown("👇 **一键复制标题去上架：**")
            st.code(target_row['Name'], language="text")
            
            if st.button("❌ 关闭分析室，查看其他"):
                st.session_state['selected_product_name'] = None
                st.rerun()
            
            st.divider()

    # 4. 完整数据表 (也支持点击)
    st.subheader("📋 所有商品清单 (点击表格行也能分析)")
    
    # 交互式表格
    selection = st.dataframe(
        final_df[['Name', 'Price', 'Sales', 'Revenue']],
        column_config={
            "Name": st.column_config.TextColumn("商品标题", width="large"),
            "Price": st.column_config.NumberColumn("单价", format="$%.2f"),
            "Revenue": st.column_config.NumberColumn("GMV", format="$%.0f"),
        },
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    # 表格点击逻辑
    if selection.selection.rows:
        idx = selection.selection.rows[0]
        selected_name_from_table = final_df.iloc[idx]['Name']
        # 如果跟当前选的不一样，则更新并刷新
        if selected_name_from_table != st.session_state['selected_product_name']:
            st.session_state['selected_product_name'] = selected_name_from_table
            st.rerun()

else:
    st.info("👈 请在左侧上传你的数据文件")