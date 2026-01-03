import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os
from collections import Counter

# ==========================================
# 0. 全局配置与 iOS 白昼风格
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
    /* 1. 全局背景 */
    .stApp { background-color: #F5F5F7; color: #1D1D1F; }
    
    /* 2. 纯白悬浮卡片 */
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

    /* 3. 字体适配 */
    h1, h2, h3, p, span, div {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif !important;
        color: #1D1D1F !important;
    }
    div[data-testid="stMetricValue"] { color: #007AFF !important; }
    
    /* 4. 侧边栏 */
    section[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E5E5EA; }
    
    /* 5. 按钮美化 */
    .stButton > button {
        background-color: #5856D6 !important; /* iOS 紫色 */
        color: white !important;
        border-radius: 12px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        box-shadow: 0 4px 10px rgba(88, 86, 214, 0.2);
    }
    .stButton > button:hover { background-color: #4A48C5 !important; }
    
    /* 6. 选中行高亮 */
    .highlight-card {
        border: 2px solid #5856D6 !important;
        background-color: #FBFBFF !important;
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

# ==========================================
# 2. 侧边栏
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
    with st.sidebar.expander("🔧 字段校准 (含图片列)", expanded=True): # 默认展开方便确认图片列
        guess_name = next((c for c in cols if 'Title' in c or '名称' in c or 'Name' in c), cols[0])
        guess_price = next((c for c in cols if 'Price' in c or '价格' in c), cols[1] if len(cols)>1 else cols[0])
        guess_sales = next((c for c in cols if 'Sales' in c or '销量' in c), cols[2] if len(cols)>2 else cols[0])
        # 自动猜测图片列
        guess_img = next((c for c in cols if 'Image' in c or 'Img' in c or 'Pic' in c or '图' in c or 'Cover' in c), None)

        col_name = st.selectbox("商品标题列", cols, index=cols.index(guess_name))
        col_price = st.selectbox("价格列 (Price)", cols, index=cols.index(guess_price))
        col_sales = st.selectbox("销量列 (Sales)", cols, index=cols.index(guess_sales))
        # 新增图片列选择
        col_img = st.selectbox("图片链接列 (可选)", ["无"] + cols, index=(cols.index(guess_img) + 1) if guess_img else 0)
    
    main_df = df.copy()
    main_df['Clean_Price'] = main_df[col_price].apply(clean_currency)
    main_df['Clean_Sales'] = main_df[col_sales].apply(clean_currency)
    main_df['GMV'] = main_df['Clean_Price'] * main_df['Clean_Sales']
    
    # 如果选了图片列，处理一下
    has_image = col_img != "无"
    if has_image:
        main_df['Image_Url'] = main_df[col_img].astype(str)

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
    st.title("✨ TK选品分析青春版")

    # 宏观指标
    m1, m2, m3, m4 = st.columns(4)
    avg_price = filtered_df['Clean_Price'].mean()
    m1.metric("筛选池总 GMV", f"${filtered_df['GMV'].sum():,.0f}")
    m2.metric("平均客单价", f"${avg_price:.2f}")
    m3.metric("潜力爆款数", len(filtered_df))
    m4.metric("最高单品销量", f"{filtered_df['Clean_Sales'].max():,.0f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Top 3 推荐
    st.subheader("🔥 今日 Top 3 推荐")
    top_3_df = filtered_df.sort_values('GMV', ascending=False).head(3)
    
    if len(top_3_df) >= 3:
        t1, t2, t3 = st.columns(3)
        for i, (col, icon) in enumerate(zip([t1, t2, t3], ["🥇", "🥈", "🥉"])):
            row = top_3_df.iloc[i]
            short_title = (row[col_name][:35] + '...') if len(row[col_name]) > 35 else row[col_name]
            # 尝试获取图片显示在卡片里
            img_html = ""
            if has_image and pd.notna(row['Image_Url']) and row['Image_Url'].startswith('http'):
                img_html = f'<img src="{row["Image_Url"]}" style="width:100%; height:120px; object-fit:cover; border-radius:8px; margin-bottom:10px;">'
            
            with col:
                st.markdown(f"""
                <div class="glass-card" style="text-align: center;">
                    {img_html}
                    <h3 style="color:#5856D6 !important; margin:0;">{icon} GMV: ${row['GMV']:,.0f}</h3>
                    <p style="font-weight: 600; height: 45px; overflow: hidden; margin-top: 10px;">{short_title}</p>
                    <p style="color: #666; font-size: 14px;">售价: ${row['Clean_Price']:.2f}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"🔍 深度分析 {i+1}", key=f"btn_top_{i}", use_container_width=True):
                    st.session_state.selected_product_title = row[col_name]
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 图表区 (柱状图替换象限图)
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        c1, c2 = st.columns([7, 3])
        with c1:
            st.subheader("📊 畅销品销量排行 (Top 50)")
            if not filtered_df.empty:
                # 准备数据：取 Top 50 销量，按销量排序
                chart_df = filtered_df.sort_values('Clean_Sales', ascending=False).head(50).copy()
                # 截断标题防止X轴太乱
                chart_df['Short_Name'] = chart_df[col_name].astype(str).apply(lambda x: x[:15] + '..' if len(x)>15 else x)
                
                fig = px.bar(
                    chart_df, 
                    x='Short_Name', 
                    y='Clean_Sales', 
                    color='Clean_Price', # 颜色区分价格
                    hover_name=col_name,
                    title=None,
                    template="plotly_white", 
                    color_continuous_scale="Viridis", # 颜色鲜艳一点
                    labels={'Clean_Sales': '销量', 'Short_Name': '商品', 'Clean_Price': '售价($)'}
                )
                fig.update_layout(
                    height=400, 
                    margin=dict(l=20,r=20,t=30,b=50), 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    font={'color': '#1D1D1F'},
                    xaxis_tickangle=-45 # X轴标签倾斜
                )
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("暂无数据")
        with c2:
            st.subheader("💡 标题热词云")
            all_titles = " ".join(filtered_df[col_name].astype(str).tolist()).lower()
            ignore_words = ['for', 'and', 'with', 'the', 'pcs', 'set', 'new', 'hot', 'color', 'size', 'high']
            words = re.findall(r'\b\w+\b', all_titles)
            clean_words = [w for w in words if w not in ignore_words and len(w)>2 and not w.isdigit()]
            if clean_words:
                w_df = pd.DataFrame(Counter(clean_words).most_common(10), columns=['Word', 'Count'])
                fig_bar = px.bar(w_df, x='Count', y='Word', orientation='h', color='Count', color_continuous_scale="Purples")
                fig_bar.update_layout(yaxis={'autorange': 'reversed'}, height=400, margin=dict(l=0,r=0,t=30,b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False, font={'color': '#1D1D1F'})
                st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 列表与交互
    st.subheader("📋 精品清单 (点击表格行查看分析)")
    
    # 准备表格数据
    display_cols = [col_name, 'Clean_Price', 'Clean_Sales', 'GMV']
    if has_image:
        display_cols.insert(0, 'Image_Url') # 把图片放第一列

    display_df = filtered_df.sort_values('GMV', ascending=False).reset_index(drop=True)
    
    # 动态构建列配置
    col_config = {
        col_name: st.column_config.TextColumn("商品标题", width="medium"),
        "Clean_Price": st.column_config.NumberColumn("售价($)", format="$%.2f"),
        "Clean_Sales": st.column_config.NumberColumn("销量", format="%d"),
        "GMV": st.column_config.NumberColumn("GMV($)", format="$%.0f"),
    }
    
    # 如果有图片，配置图片列
    if has_image:
        col_config["Image_Url"] = st.column_config.ImageColumn("主图", help="商品主图预览")

    # 表格交互
    selection = st.dataframe(
        display_df[display_cols],
        column_config=col_config,
        use_container_width=True,
        height=400, # 表格稍微高一点展示图片
        on_select="rerun",
        selection_mode="single-row"
    )

    # 逻辑：表格点击优先
    current_product = None
    if selection.selection["rows"]:
        selected_index = selection.selection["rows"][0]
        current_product = display_df.iloc[selected_index]
    elif st.session_state.selected_product_title:
        match = display_df[display_df[col_name] == st.session_state.selected_product_title]
        if not match.empty:
            current_product = match.iloc[0]

    # 深度分析卡片
    if current_product is not None:
        price_diff = current_product['Clean_Price'] - avg_price
        price_status = "🔴 高于均价" if price_diff > 0 else "🟢 低于均价"
        price_pct = abs(price_diff / avg_price) * 100
        p_words = [w for w in re.findall(r'\b\w+\b', current_product[col_name].lower()) if len(w)>2]
        
        # 获取大图
        big_img_html = ""
        if has_image and pd.notna(current_product['Image_Url']) and current_product['Image_Url'].startswith('http'):
            big_img_html = f'<div style="flex: 0 0 150px;"><img src="{current_product["Image_Url"]}" style="width:100%; border-radius:12px; border:1px solid #eee;"></div>'

        st.markdown(f"""
        <div class="glass-card highlight-card">
            <h2 style="color: #5856D6 !important; margin-top:0;">🎯 单品战术分析室</h2>
            <div style="display: flex; gap: 20px; align-items: flex-start;">
                {big_img_html}
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 15px 0;">{current_product[col_name]}</h3>
                    <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 20px;">
                        <div>
                            <p style="font-size: 14px; color: #666; margin:0;">💰 销售表现</p>
                            <p style="font-size: 24px; font-weight: bold; margin:0;">GMV: ${current_product['GMV']:,.0f}</p>
                            <p style="margin:0;">销量: {int(current_product['Clean_Sales'])} 单</p>
                        </div>
                        <div>
                            <p style="font-size: 14px; color: #666; margin:0;">📊 价格定位</p>
                            <p style="font-size: 24px; font-weight: bold; margin:0;">${current_product['Clean_Price']:.2f}</p>
                            <p style="margin:0;">{price_status} {price_pct:.1f}%</p>
                        </div>
                    </div>
                </div>
            </div>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="font-size: 14px; color: #666;">🔑 核心关键词提取</p>
            <p style="background: #F2F2F7; padding: 12px; border-radius: 8px; margin:0; font-family: monospace;">
                {', '.join(p_words[:8])}
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("👆 点击上方【Top 3 按钮】或【表格中的图片/行】，在此处查看深度单品分析。")

else:
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 60px;">
        <h2 style="color: #1D1D1F !important;">👈 请在左侧上传数据表格</h2>
        <p style="color: #86868b !important; font-size: 18px;">开启您的 iOS 极简风选品之旅</p>
    </div>
    """, unsafe_allow_html=True)