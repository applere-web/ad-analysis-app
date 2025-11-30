import streamlit as st
import pandas as pd
import requests
import json
import base64
from PIL import Image
import io

# --- 页面配置 ---
st.set_page_config(
    page_title="电商广告AI智能分析系统 V1.0 (云端版)",
    page_icon="🚀",
    layout="wide"
)

# --- 侧边栏 ---
st.sidebar.title("🔧 系统设置")
st.sidebar.info("版本: V1.0 (通用连接版)")
api_key = st.sidebar.text_input("请输入 Google Gemini API Key:", type="password")
st.sidebar.markdown("---")

# --- 核心函数：通过 HTTP 直接连接 Gemini (不依赖 SDK) ---
def get_gemini_response(prompt, image=None):
    if not api_key:
        return "⚠️ 请先在左侧输入 API Key"

    # API 接口地址
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    
    # 准备发送给 AI 的内容
    contents_parts = [{"text": prompt}]

    # 如果有图片，把图片转换成 AI 能看懂的代码 (Base64)
    if image:
        buffered = io.BytesIO()
        # 统一转为 JPEG 以压缩体积
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        image_data = {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": img_str
            }
        }
        contents_parts.append(image_data)

    payload = {
        "contents": [{
            "parts": contents_parts
        }]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            result = response.json()
            # 提取 AI 回复的文字
            try:
                return result['candidates'][0]['content']['parts'][0]['text']
            except:
                return f"AI 回复结构异常: {result}"
        else:
            return f"❌ 连接失败 (代码 {response.status_code}): {response.text}"
            
    except Exception as e:
        return f"❌ 网络请求错误: {str(e)}"

# --- 主页面 ---
st.title("🚀 多平台电商广告 AI 决策系统")
st.markdown("""
本系统支持 **Shopee, TikTok, Lazada** 数据分析。
直接连接 Google 算力，无需安装复杂环境。
""")

# --- 模块 1: 数据上传 ---
st.header("1. 上传广告数据 (Excel/CSV)")
uploaded_file = st.file_uploader("支持含关键词、GMV Max等数据的报表", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.write("### 📊 数据预览")
        st.dataframe(df.head())

        # 统计
        col1, col2, col3 = st.columns(3)
        col1.metric("总行数", len(df))
        col2.metric("特征列数", len(df.columns))
        possible_gmv = [col for col in df.columns if 'GMV' in col or 'Sales' in col or '销售' in col]
        if possible_gmv:
            total_gmv = df[possible_gmv[0]].sum()
            col3.metric("预估总 GMV", f"{total_gmv:,.2f}")

        # --- 模块 2: AI 分析 ---
        st.header("2. AI 深度运算与策略逆推")
        
        analysis_type = st.selectbox("选择分析模式", 
            ["全盘诊断与趋势预测", "逆推：高ROI广告特征分析", "预测：下阶段广告投放建议", "关键词效能分析"])
        
        if st.button("开始 AI 运算"):
            with st.spinner("AI 正在读取数据、进行逻辑推理与未来模拟..."):
                # 取前 50 行数据作为样本 (避免请求过大)
                data_preview = df.head(50).to_csv(index=False)
                
                prompt = f"""
                角色：你是一个顶级的电商数据科学家。
                任务：分析以下广告数据（Shopee/TikTok/Lazada）。
                分析目标：{analysis_type}
                
                请执行：
                1. **运算与分析**：找出表现最好和最差的广告。
                2. **推理**：解释原因。
                3. **建议**：明确指出哪个广告ID需要【继续投放】，哪个需要【停止】。
                4. **模拟逆推**：预测未来趋势。
                
                数据样本：
                {data_preview}
                """
                
                result = get_gemini_response(prompt)
                st.markdown("### 🤖 AI 分析报告")
                st.markdown(result)

    except Exception as e:
        st.error(f"文件读取失败: {e}")

st.markdown("---")

# --- 模块 3: 图片分析 ---
st.header("3. 广告素材(图片) 视觉诊断")
uploaded_image = st.file_uploader("上传广告图片", type=['png', 'jpg', 'jpeg'])

if uploaded_image is not None:
    image = Image.open(uploaded_image)
    st.image(image, caption='上传的广告素材', width=300)
    
    img_prompt = st.text_input("您可以输入特定问题:", value="分析这张电商广告图。它的优点是什么？缺点是什么？预测点击率会高吗？为何？给出优化建议。")
    
    if st.button("分析图片"):
        with st.spinner("AI 正在观看图片并进行视觉推理..."):
            img_result = get_gemini_response(img_prompt, image)
            st.markdown("### 👁️ 视觉分析结果")
            st.markdown(img_result)

st.markdown("---")
st.caption("Powered by Streamlit & Google Gemini 1.5 Flash (REST API Mode)")
