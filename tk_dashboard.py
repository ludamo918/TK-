import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os
from openai import OpenAI

# ==========================================
# 0. 全局配置
# ==========================================
st.set_page_config(page_title="TK选品 (DeepSeek Pro版)", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# --- CSS 样式 ---
st.markdown("""
<style>
    .stApp { background-color: #F5F5F7; color: #1D1D1F; }
    .glass-card { background-color: #FFFFFF !important; border-radius: 18px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); border: 1px solid rgba(0,0,0,0.02); }
    h1, h2, h3, p, span, div { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif !important; color: #1D1D1F !important; }
    .stButton > button { background-color: #5856D6 !important; color: white !important; border-radius: 12px; border: none; padding: 10px 24px; font-weight: 600; }
    .stButton > button:hover { background-color: #4A48C5 !important; }
    .analysis-room { border: 2px solid #5856D6 !important; background-color: #fff !important; animation: pulse 1s ease-in-out; }
    .score-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; margin-left: 10px; }
    .score-s { background-color: #FFD700; color: #8B4500 !important; } 
    .score-a { background-color: #E5E5EA; color: #333 !important; }
    /* 优化代码块显示，方便复制 */
    .stCodeBlock { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# --- 状态管理 ---
if 'selected_product_title' not in st.session_state: st.session_state.selected_product_title = None
if 'user_role' not in st.session_state: st.session_state.user_role = 'guest'
if 'gen_keywords' not in st.session_state: st.session_state.gen_keywords = "" # 新增：存储关键词
if 'gen_title' not in st.session_state: st.session_state.gen_title = ""
if 'gen_desc' not in st.session_state: st.session_state.gen_desc = ""

# ==========================================
# 🔒 团队密码锁
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
        if pwd == "1997": 
            st.session_state.auth = True; st.session_state.user_role = 'guest'; st.rerun()
        elif pwd == "20261888":
            st.session_state.auth = True; st.session_state.user_role = 'admin'; st.rerun()
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

def calculate_score(row, max_gmv):
    score_val = (row['GMV'] / max_gmv) * 100
    if score_val >= 50: return "S", "🔥 顶级爆款 (S级)", "score-s"
    elif score_val >= 20: return "A", "🚀 潜力热销 (A级)", "score-a"
    elif score_val >= 5: return "B", "⚖️ 稳健出单 (B级)", "score-a"
    else: return "C", "🌱 起步阶段 (C级)", "score-a"

# 🔥 DeepSeek 流式生成函数 (支持自定义温度)
def stream_ai_response(client, prompt, placeholder_obj, temp=1.3):
    try:
        stream = client.chat.completions.create(
            model="deepseek-chat", # 这里使用的是 V3 模型，性价比最高
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            temperature=temp 
        )
        full_text = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_text += content
                placeholder_obj.markdown(full_text + "▌") 
        placeholder_obj.markdown(full_text)
        return full_text
    except Exception as e:
        err_str = str(e)
        if "Insufficient Balance" in err_str or "402" in err_str:
            err_msg = "❌ 余额不足 (Error 402): 请去 DeepSeek 官网充值 (只需几块钱)。"
        else:
            err_msg = f"❌ AI 请求失败: {err_str}"
        placeholder_obj.error(err_msg)
        return err_msg

# ==========================================
# 2. 侧边栏与 API
# ==========================================
if os.path.exists("avatar.png"):
    c1, c2, c3 = st.sidebar.columns([1, 2, 1])
    with c2: st.image("avatar.png", width=110)
st.sidebar.markdown("<h3 style='text-align: center; margin-top: -10px;'>TK选品 (DeepSeek Pro)</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")

client = None
active_api_key = None
is_ai_ready = False

# 管理员自动读 Secrets
if st.session_state.user_role == 'admin':
    try:
        if "DEEPSEEK_API_KEY" in st.secrets:
            active_api_key = st.secrets["DEEPSEEK_API_KEY"]
            st.sidebar.success(f"👑 管理员模式: DeepSeek 已激活")
    except: pass
else:
    st.sidebar.info("👤 访客模式: 请输入 DeepSeek Key")

with st.sidebar.expander("🔑 API 设置 (访客专用)", expanded=False):
    manual_key = st.text_input("请输入 DeepSeek API Key", type="password")
    if manual_key: active_api_key = manual_key

# 🔥 新增：AI 创造力控制
ai_temp = st.sidebar.slider("🌡️ AI 脑洞/创造力 (Temperature)", 0.5, 1.8, 1.3, step=0.1, help="数值越大越有创意，数值越小越严谨")

if active_api_key:
    try:
        client = OpenAI(api_key=active_api_key, base_url="https://api.deepseek.com")
        is_ai_ready = True
        if st.session_state.user_role != 'admin':
            st.sidebar.success("✅ DeepSeek V3 引擎就绪")
    except Exception as e:
        st.sidebar.error(f"Key 错误: {e}")

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

    min_p, max_p = int(main_df['Clean_Price'].min()), int(main_df['Clean_Price'].max())
    if min_p == max_p: max_p += 1
    price_range = st.sidebar.slider("💰 价格区间", min_p, max_p, (min_p, max_p))
    sales_min = st.sidebar.number_input("🔥 最低销量", min_value=0, value=100)
    filtered_df = main_df[(main_df['Clean_Price'] >= price_range[0]) & (main_df['Clean_Price'] <= price_range[1]) & (main_df['Clean_Sales'] >= sales_min)]
    max_gmv = filtered_df['GMV'].max() if not filtered_df.empty else 1

    # ==========================================
    # 4. 主界面
    # ==========================================
    st.title("🚀 TK选品分析 (DeepSeek Pro)")
    
    m1, m2, m3, m4 = st.columns(4)
    avg_price = filtered_df['Clean_Price'].mean()
    m1.metric("筛选池总 GMV", f"${filtered_df['GMV'].sum():,.0f}")
    m2.metric("平均客单价", f"${avg_price:.2f}")
    m3.metric("潜力爆款数", len(filtered_df))
    m4.metric("最高单品销量", f"{filtered_df['Clean_Sales'].max():,.0f}")
    st.markdown("<br>", unsafe_allow_html=True)

    # Top 3
    st.subheader("🔥 Top 3 推荐")
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
                    # 清空之前的缓存，保证新产品重新生成
                    st.session_state.gen_keywords = ""
                    st.session_state.gen_title = ""
                    st.session_state.gen_desc = ""
                    st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

    # List
    display_cols = [col_name, 'Clean_Price', 'Clean_Sales', 'GMV']
    if has_image: display_cols.insert(0, 'Image_Url')
    col_config = {
        col_name: st.column_config.TextColumn("标题", width="medium"),
        "Clean_Price": st.column_config.NumberColumn("售价", format="$%.2f"),
        "Clean_Sales": st.column_config.NumberColumn("销量"),
        "GMV": st.column_config.NumberColumn("GMV", format="$%.0f"),
    }
    if has_image: col_config["Image_Url"] = st.column_config.ImageColumn("主图", help="点击放大")

    st.subheader("📋 商品清单 (点击选择)")
    selection = st.dataframe(
        filtered_df.sort_values('GMV', ascending=False)[display_cols],
        column_config=col_config, use_container_width=True, height=300,
        on_select="rerun", selection_mode="single-row"
    )

    current_product = None
    if selection.selection["rows"]:
        current_product = filtered_df.sort_values('GMV', ascending=False).iloc[selection.selection["rows"][0]]
        # 如果切换了产品，清空缓存
        if st.session_state.selected_product_title != current_product[col_name]:
            st.session_state.gen_keywords = ""
            st.session_state.gen_title = ""
            st.session_state.gen_desc = ""
        st.session_state.selected_product_title = current_product[col_name]
    elif st.session_state.selected_product_title:
        match = filtered_df[filtered_df[col_name] == st.session_state.selected_product_title]
        if not match.empty: current_product = match.iloc[0]

    # Analysis Room
    st.markdown("<div id='analysis_target'></div>", unsafe_allow_html=True)
    if current_product is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        score, score_text, score_css = calculate_score(current_product, max_gmv)
        st.markdown(f"""<div class="glass-card analysis-room"><h2 style="color: #5856D6 !important; margin:0;">🎯 分析室: {current_product[col_name][:30]}... <span class="score-badge {score_css}">{score_text}</span></h2></div><br>""", unsafe_allow_html=True)
        
        c_left, c_mid, c_right = st.columns([1, 1.2, 1.2])
        
        with c_left:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            if has_image and pd.notna(current_product['Image_Url']):
                st.markdown(f'<img src="{current_product["Image_Url"]}" style="width:100%; border-radius:12px; max-height:250px; object-fit:contain;">', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c_mid:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("💰 利润模拟器")
            sell_price = current_product['Clean_Price']
            st.metric("零售价", f"${sell_price:.2f}")
            cost_price = st.number_input("进货成本", value=float(sell_price)*0.2, step=1.0)
            ship_cost = st.number_input("头程运费", value=3.0, step=0.5)
            platform_fee = sell_price * 0.05 
            profit = sell_price - cost_price - ship_cost - platform_fee
            margin = (profit / sell_price) * 100 if sell_price > 0 else 0
            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.metric("预估净赚", f"${profit:.2f}")
            c2.metric("利润率", f"{margin:.1f}%")
            st.markdown('</div>', unsafe_allow_html=True)

        with c_right:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("🤖 AI 运营助手 (V3)")
            
            tab1, tab2 = st.tabs(["核心文案 (SEO & 卖点)", "视频脚本"])
            
            with tab1:
                orig_name = str(current_product[col_name])
                st.caption(f"原标题: {orig_name[:50]}...")
                
                # --- 步骤 0: 关键词提取 ---
                if st.button("🔍 0. 智能提炼关键词 (One-Click)"):
                    if is_ai_ready:
                        prompt_kw = f"As a TikTok SEO expert, extract 5-8 high-traffic, relevant English keywords from this product title: '{orig_name}'. Output ONLY the keywords separated by commas, no other text."
                        placeholder_kw = st.empty()
                        res = stream_ai_response(client, prompt_kw, placeholder_kw, temp=1.0)
                        st.session_state.gen_keywords = res
                    else: st.warning("请检查 API Key")
                
                # 显示关键词 (代码块格式方便复制)
                keywords_in = st.text_input("关键词 (可手动修改)", value=st.session_state.gen_keywords, placeholder="点击上方按钮自动生成...")
                if st.session_state.gen_keywords:
                    st.caption("👇 点击右上角复制按钮：")
                    st.code(st.session_state.gen_keywords, language="text")

                st.markdown("---")
                
                # --- 步骤 1: 标题生成 ---
                if st.button("🚀 1. 生成裂变 SEO 标题"):
                    if is_ai_ready and keywords_in:
                        # 优化后的 Prompt
                        prompt_title = f"""
                        Act as a TikTok Shop copywriter. Create ONE optimized product title based on: "{orig_name}".
                        Target Keywords: {keywords_in}.
                        Rules:
                        1. Length: Keep it between 40-80 characters (Mobile optimized).
                        2. Structure: [Adjective/Hook] + [Core Product Name] + [Benefit/Feature] + [Emoji].
                        3. Goal: High Click-Through Rate (CTR) and SEO friendly.
                        4. Output ONLY the title, no explanations.
                        """
                        placeholder_t = st.empty() 
                        st.session_state.gen_title = stream_ai_response(client, prompt_title, placeholder_t, temp=ai_temp)
                    elif not keywords_in: st.warning("请先提取或输入关键词！")
                    else: st.warning("API 未连接")
                
                if st.session_state.gen_title:
                    st.info(f"结果: {st.session_state.gen_title}")

                st.markdown("---")
                
                # --- 步骤 2: 描述生成 ---
                if st.button("📝 2. 生成高转化描述 (不凑字数)"):
                    if is_ai_ready and st.session_state.gen_title:
                        # 优化后的描述 Prompt - 黄金法则
                        prompt_desc = f"""
                        Write a high-converting TikTok Shop product description for: "{st.session_state.gen_title}".
                        Keywords: {keywords_in}.
                        Structure (Strictly follow this):
                        1. **Hook**: A short, punchy sentence to grab attention.
                        2. **Pain Point & Solution**: Relate to a user problem and how this solves it.
                        3. **Key Features**: 3-4 bullet points highlighting benefits (not just specs).
                        4. **CTA**: Clear Call to Action (e.g., "Grab yours now!").
                        Tone: Authentic, Exciting, Viral. English only. 
                        Length: Concise, about 150-250 words. Do not write fluff.
                        """
                        placeholder_d = st.empty()
                        st.session_state.gen_desc = stream_ai_response(client, prompt_desc, placeholder_d, temp=ai_temp)
                    elif not st.session_state.gen_title: st.warning("请先生成标题！")

            with tab2:
                # 3. 脚本生成
                if st.button("🎬 生成爆款脚本"):
                    if is_ai_ready and keywords_in:
                        target = st.session_state.gen_title if st.session_state.gen_title else orig_name
                        prompt_script = f"Write a TikTok video script for: {target}. Keywords: {keywords_in}. Style: User Generated Content (UGC) feel. Include: Visual Hook (0-3s), Problem Agitation, Product Demo, Social Proof, CTA."
                        placeholder_s = st.empty()
                        stream_ai_response(client, prompt_script, placeholder_s, temp=ai_temp)
                    else: st.warning("请先设置关键词")

            st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown('<div class="glass-card" style="text-align: center; padding: 60px;"><h2>👈 请上传数据表格</h2></div>', unsafe_allow_html=True)