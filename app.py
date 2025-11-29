import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io

# --- 页面配置 ---
st.set_page_config(
    page_title="电商广告AI智能分析系统 V1.0",
    page_icon="🚀",
    layout="wide"
)

# --- 侧边栏：设置与登录 ---
st.sidebar.title("🔧 系统设置")
st.sidebar.info("版本: V1.0 (基础架构版)")

api_key = st.sidebar.text_input("请输入 Google Gemini API Key:", type="password")
st.sidebar.markdown("---")

# --- AI 配置函数 ---
def get_ai_response(prompt, image=None):
    if not api_key:
        return "⚠️ 请先在左侧输入 API Key"
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        if image:
            response = model.generate_content([prompt, image])
        else:
            response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ AI 连接错误: {str(e)}"

# --- 主页面 ---
st.title("🚀 多平台电商广告 AI 决策系统")
st.markdown("""
本系统支持 **Shopee, TikTok, Lazada** 数据分析。
具备能力：**运算、推理、预测、逆推、图片分析**。
""")

# --- 模块 1: 数据上传与处理 ---
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

        # 数据统计简报
        col1, col2, col3 = st.columns(3)
        col1.metric("总行数", len(df))
        col2.metric("列数 (特征)", len(df.columns))
        # 尝试自动识别 GMV 或 销售额 列
        possible_gmv = [col for col in df.columns if 'GMV' in col or 'Sales' in col or '销售' in col]
        if possible_gmv:
            total_gmv = df[possible_gmv[0]].sum()
            col3.metric("预估总 GMV", f"{total_gmv:,.2f}")

        # --- 模块 2: AI 深度分析 (纯文本/表格) ---
        st.header("2. AI 深度运算与策略逆推")
        
        analysis_type = st.selectbox("选择分析模式", 
            ["全盘诊断与趋势预测", "逆推：高ROI广告特征分析", "预测：下阶段广告投放建议", "关键词效能分析"])
        
        if st.button("开始 AI 运算"):
            with st.spinner("AI 正在读取数据、进行逻辑推理与未来模拟..."):
                # 将数据转换为字符串喂给 AI (限制前100行以防过大，Gemini Flash处理能力很强但为了速度做截取)
                # 如果数据量巨大，通常做法是传统计数据，这里为了演示直接传Raw Data片段
                data_preview = df.to_csv(index=False)
                
                prompt = f"""
                你是一个顶级的电商数据科学家。请分析以下广告数据（来自Shopee/TikTok/Lazada）。
                
                分析目标：{analysis_type}
                
                请执行以下任务：
                1. **运算与分析**：找出表现最好和最差的广告。
                2. **推理**：解释为什么这些广告表现好（是因为点击率、转化率还是客单价？）。
                3. **建议**：明确指出哪个广告ID需要【继续投放/加码】，哪个需要【立即停止/听】。
                4. **模拟逆推**：如果我们将预算集中在表现好的广告上，预估未来趋势会怎样？
                
                数据内容如下：
                {data_preview[:30000]} 
                (注意：这是数据的一部分)
                """
                
                result = get_ai_response(prompt)
                st.markdown("### 🤖 AI 分析报告")
                st.markdown(result)

    except Exception as e:
        st.error(f"文件读取失败: {e}")

st.markdown("---")

# --- 模块 3: 图片视觉分析 ---
st.header("3. 广告素材(图片) 视觉诊断")
st.info("上传广告图，AI 将分析其吸引力、点击欲望(CTR)预测，并给出改进建议。")

uploaded_image = st.file_uploader("上传广告图片", type=['png', 'jpg', 'jpeg'])

if uploaded_image is not None:
    image = Image.open(uploaded_image)
    st.image(image, caption='上传的广告素材', width=300)
    
    img_prompt = st.text_input("您可以输入特定问题 (例如：这张图适合TikTok吗？)", value="分析这张电商广告图。它的优点是什么？缺点是什么？预测点击率会高吗？为何？给出优化建议。")
    
    if st.button("分析图片"):
        with st.spinner("AI 正在观看图片并进行视觉推理..."):
            img_result = get_ai_response(img_prompt, image)
            st.markdown("### 👁️ 视觉分析结果")
            st.markdown(img_result)

# --- 底部 ---
st.markdown("---")
st.caption("Powered by Streamlit & Google Gemini 1.5 Flash | Free Architecture")
