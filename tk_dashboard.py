import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os
from collections import Counter

# ==========================================
# 0. 全局配置与 iOS 风格
# ==========================================
st.set_page_config(
    page_title="TK选品分析青春版 (Pro)",
    page_icon="🦄", # 换个独角兽图标，代表独特性
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS 美化 (保持 V15 的高颜值) ---
st.markdown("""
<style>
    .stApp { background-color: #F5F5F7; color: #1D1D1F; }
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
    h1, h2, h3, p, span, div {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif !important;
        color: #1D1D1F !important;
    }
    div[data-testid="stMetricValue"] { color: #007AFF !important; }
    section[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E5E5EA; }
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
    .highlight-card { border: 2px solid #5856D6 !important; background-color: #FBFBFF !important; }
    
    /* 新增：利润计算器的样式 */
    .profit-box {
        background-color: #F2F2F7;
        padding: 15px;
        border-radius: 12px;
        margin-top: 10px;
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
# 2. 侧边栏配置
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
    with st.sidebar.expander("🔧 字段校准 (展开设置)", expanded=False):
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
    # 3. 主界面
    # ==========================================
    st.title("🦄 TK选品分析 (差异化竞争版)")
    st.caption("🚀 比普通数据网站多想一步：不仅看数据，更看利润与落地。")

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

    # 图表区
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        c1, c2 = st.columns([7, 3])
        with c1:
            st.subheader("📊 畅销品销量排行 (Top 50)")
            if not filtered_df.empty:
                chart_df = filtered_df.sort_values('Clean_Sales', ascending=False).head(50).copy()
                chart_df['Short_Name'] = chart_df[col_name].astype(str).apply(lambda x: x[:15] + '..' if len(x)>15 else x)
                fig = px.bar(
                    chart_df, x='Short_Name', y='Clean_Sales', color='Clean_Price', 
                    hover_name=col_name, template="plotly_white", color_continuous_scale="Viridis",
                    labels={'Clean_Sales': '销量', 'Short_Name': '商品', 'Clean_Price': '售价($)'}
                )
                fig.update_layout(height=400, margin=dict(l=20,r=20,t=30,b=50), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font={'color': '#1D1D1F'}, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("暂无数据")
        with c2:
            st.subheader("💡 标题热词云")
            all_titles = " ".join(filtered_df[col_name].astype(str).tolist()).lower()
            ignore_words = ['for', 'and', 'with', 'the', 'pcs', 'set', 'new', 'hot', 'color', 'size', 'high', 'women']
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
    st.subheader("📋 精品清单")
    display_cols = [col_name, 'Clean_Price', 'Clean_Sales', 'GMV']
    if has_image: display_cols.insert(0, 'Image_Url')
    display_df = filtered_df.sort_values('GMV', ascending=False).reset_index(drop=True)
    
    col_config = {
        col_name: st.column_config.TextColumn("商品标题", width="medium"),
        "Clean_Price": st.column_config.NumberColumn("售价($)", format="$%.2f"),
        "Clean_Sales": st.column_config.NumberColumn("销量", format="%d"),
        "GMV": st.column_config.NumberColumn("GMV($)", format="$%.0f"),
    }
    if has_image: col_config["Image_Url"] = st.column_config.ImageColumn("主图")

    selection = st.dataframe(
        display_df[display_cols], column_config=col_config,
        use_container_width=True, height=400, on_select="rerun", selection_mode="single-row"
    )

    # 选品逻辑
    current_product = None
    if selection.selection["rows"]:
        selected_index = selection.selection["rows"][0]
        current_product = display_df.iloc[selected_index]
    elif st.session_state.selected_product_title:
        match = display_df[display_df[col_name] == st.session_state.selected_product_title]
        if not match.empty: current_product = match.iloc[0]

    # --- 差异化核心：单品战术分析室 ---
    if current_product is not None:
        price = current_product['Clean_Price']
        p_words = [w for w in re.findall(r'\b\w+\b', current_product[col_name].lower()) if len(w)>2]
        
        # 1. 蓝海雷达计算
        # 逻辑：如果(销量/价格)比值很高，说明需求大；这里简单模拟一个“机会分”
        opportunity_score = min(100, int((current_product['Clean_Sales'] / (price + 1)) * 0.5))
        if opportunity_score > 80: radar_label = "🌊 超级蓝海 (闭眼冲)"
        elif opportunity_score > 50: radar_label = "🛶 稳健增长 (可跟卖)"
        else: radar_label = "🔥 红海血战 (需谨慎)"

        big_img_html = ""
        if has_image and pd.notna(current_product['Image_Url']) and current_product['Image_Url'].startswith('http'):
            big_img_html = f'<div style="flex: 0 0 150px;"><img src="{current_product["Image_Url"]}" style="width:100%; border-radius:12px; border:1px solid #eee;"></div>'

        st.markdown(f"""
        <div class="glass-card highlight-card">
            <h2 style="color: #5856D6 !important; margin-top:0;">🎯 单品战术分析室</h2>
            <div style="display: flex; gap: 20px; align-items: flex-start;">
                {big_img_html}
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 10px 0;">{current_product[col_name]}</h3>
                    <div style="margin-bottom: 10px;">
                        <span style="background: #E5E5EA; color: #333; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold;">{radar_label}</span>
                        <span style="background: #FFD60A; color: #333; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; margin-left: 10px;">机会分: {opportunity_score}</span>
                    </div>
                </div>
            </div>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
        """, unsafe_allow_html=True)

        # 2. 交互式利润计算器 (Profit Hacker)
        c_calc, c_ai = st.columns([1, 1])
        
        with c_calc:
            st.markdown("#### 💰 利润模拟器 (Profit Simulator)")
            st.caption("拖动滑块，算算你这一单到底赚多少？")
            
            # 模拟输入
            cost_cny = st.slider("1. 1688 采购价 (¥)", 0.0, float(price)*7*0.8, float(price)*7*0.2)
            ship_usd = st.slider("2. 头程运费 ($)", 0.0, 10.0, 3.0)
            ads_roas = st.slider("3. 预期投流 ROAS", 1.0, 10.0, 3.0)
            
            # 实时计算
            exchange_rate = 7.2
            cost_usd = cost_cny / exchange_rate
            platform_fee = price * 0.05 # 假设5%佣金
            ads_cost = price / ads_roas if ads_roas > 0 else 0
            
            net_profit = price - cost_usd - ship_usd - platform_fee - ads_cost
            margin = (net_profit / price) * 100 if price > 0 else 0
            
            # 结果展示
            if net_profit > 0:
                color = "#34C759" # Green
                res_text = f"✅ 预估净赚: ${net_profit:.2f} ({margin:.1f}%)"
            else:
                color = "#FF3B30" # Red
                res_text = f"🛑 预估亏损: ${net_profit:.2f} ({margin:.1f}%)"
            
            st.markdown(f"""
            <div style="background-color: {color}20; padding: 15px; border-radius: 10px; border: 1px solid {color};">
                <h3 style="color: {color} !important; margin:0; text-align: center;">{res_text}</h3>
            </div>
            """, unsafe_allow_html=True)

        # 3. AI 脚本生成器 (AI Prompt)
        with c_ai:
            st.markdown("#### 🧠 AI 爆款脚本生成 (Prompt)")
            st.caption("一键复制下方指令给 ChatGPT，生成视频脚本：")
            
            keywords = ', '.join(p_words[:5])
            prompt_text = f"""
Act as a TikTok E-commerce Expert. 
Product: "{current_product[col_name]}"
Keywords: {keywords}
Price: ${price}

Task: Write 3 viral TikTok video hooks and a short script structure for this product. 
Target Audience: Young US buyers.
Tone: User-generated content (UGC), authentic, emotional.
Length: 15-30 seconds.
            """
            st.code(prompt_text, language="text")
            st.info("👆 点击右上角复制，发送给 AI 即可生成脚本。")

        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.info("👆 点击上方【Top 3 按钮】或【表格中的图片/行】，在此处查看深度单品分析。")
else:
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 60px;">
        <h2 style="color: #1D1D1F !important;">👈 请在左侧上传数据表格</h2>
        <p style="color: #86868b !important; font-size: 18px;">开启您的 iOS 极简风选品之旅</p>
    </div>
    """, unsafe_allow_html=True)