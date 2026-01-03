import streamlit as st
import subprocess
import sys

# 1. 强制安装库 (防止 ModuleNotFoundError)
try:
    import google.generativeai as genai
except ImportError:
    st.warning("正在安装 AI 库，请稍候...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai"])
    import google.generativeai as genai
    st.rerun()

st.title("🛠️ Gemini API 诊断器")

# 2. 读取 Key 的逻辑
api_key = None

# A. 尝试从 Secrets 读取
try:
    if "GEMINI_API_KEY" in st.secrets:
        secret_key = st.secrets["GEMINI_API_KEY"]
        st.success(f"✅ 从 Secrets 检测到 Key: {secret_key[:5]}... (格式正确)")
        api_key = secret_key
    else:
        st.error("❌ Secrets 里没有找到 GEMINI_API_KEY，请检查是否保存或格式是否正确（有无双引号）。")
except Exception as e:
    st.error(f"❌ 读取 Secrets 出错: {e}")

# B. 手动输入覆盖
st.write("---")
manual_key = st.text_input("或者在这里手动输入 Key 测试:", type="password")
if manual_key:
    api_key = manual_key.strip() # 自动去除空格

# 3. 发起测试
if st.button("开始测试连接"):
    if not api_key:
        st.warning("没有可用的 Key，请先配置 Secrets 或手动输入。")
        st.stop()
    
    st.info(f"正在使用 Key: {api_key[:5]}... 尝试连接 Google...")
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Hello, reply 'OK' if you can hear me.")
        
        st.balloons()
        st.success("🎉 连接成功！API 是好的！")
        st.write(f"🤖 AI 回复: {response.text}")
        st.caption("现在你可以把代码换回原来的选品系统了，记得 Secrets 必须保持带引号的状态！")
        
    except Exception as e:
        st.error("🔥 连接失败！原因如下：")
        st.code(str(e))
        st.markdown("""
        **常见错误排查：**
        1. `InvalidArgument`: Key 输错了，或者复制多了空格。
        2. `PermissionDenied`: 这个 Key 被禁用了，或者 Google Cloud 项目没开通。
        3. `404 Not Found`: 模型名称写错了 (代码里用的是 gemini-1.5-flash)。
        """)