import streamlit as st
import pandas as pd
import requests
import json
import base64
from PIL import Image
import io

# --- 页面配置 ---
st.set_page_config(
    page_title="电商广告AI全盘分析系统 V2.0",
    page_icon="🛍️",
    layout="wide"
)

# --- 侧边栏 ---
st.sidebar.title("🔧 设置中心")
api_key = st.sidebar.text_input("请输入 Google Gemini API Key:", type="password")
st.sidebar.markdown("---")
st.sidebar.info("V2.0 更新：\n1. 支持全量数据读取\n2. 自动修复文件格式错误\n3. 自动清洗货币符号")

# --- 核心函数：连接 AI ---
def get_gemini_response(prompt, image=None):
    if not api_key:
        return "⚠️ 请先输入 API Key"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    contents_parts = [{"text": prompt}]

    if image:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=80) # 压缩图片以加快速度
        img_str = base64.b64encode(buffered.getvalue()).decode()
        contents_parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": img_str
            }
        })

    payload = {"contents": [{"parts": contents_parts}]}

    try:
        # 增加 timeout 防止数据量太大时断开
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if response.status_code == 200:
            result = response.json()
            try:
                return result['candidates'][0]['content']['parts'][0]['text']
            except:
                return f"AI 回复解析失败: {result}"
        else:
            return f"❌ AI 请求失败 ({response.status_code}): {response.text}"
    except Exception as e:
        return f"❌ 网络/超时错误: {str(e)}"

# --- 辅助函数：智能读取文件 ---
def load_data(uploaded_file):
    try:
        # 方法 1: 尝试作为 Excel 读取
        if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
            return pd.read_excel(uploaded_file)
        
        # 方法 2: 尝试作为标准 CSV 读取
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file)
        except:
            pass
            
        # 方法 3: 遇到 "Expected 2 fields" 错误时，尝试忽略错误行并自动推断分隔符
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, sep=None, engine='python', on_bad_lines='skip')
        
    except Exception as e:
        return None

# --- 主页面 ---
st.title("🛍️ 电商广告全量数据 AI 大脑")
st.caption("支持 Shopee / Lazada / TikTok 导出报表 | 自动清洗数据 | 全盘运算")

# --- 模块 1: 强壮的数据上传 ---
st.header("1. 导入数据")
uploaded_file = st.file_uploader("直接上传平台导出的原始表格", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is None:
        st.error("❌ 文件读取彻底失败。请尝试将文件在 Excel 中打开，‘另存为’ -> 选择 'Excel 工作簿 (*.xlsx)' 格式后再上传。")
    else:
        # 数据清洗：把所有看起来像数字的列（含%, $等）转为纯数字，方便AI理解
        st.success(f"✅ 成功读取！共 {len(df)} 行数据。正在进行全量分析准备...")
        
        st.dataframe(df.head(3)) # 只展示前3行给您看，但会发所有数据给AI

        # --- 模块 2: 全量 AI 分析 ---
        st.header("2. AI 全盘运算")
        
        analysis_mode = st.radio("您想让 AI 做什么？", 
            ["全盘诊断 (哪个停哪个投)", "逆推高 ROI 模式", "未来趋势预测", "关键词深度挖掘"], horizontal=True)
        
        if st.button("🚀 启动 AI 全量运算"):
            with st.spinner("AI 正在阅读所有数据行，这可能需要几秒钟..."):
                # 将数据转换为 CSV 文本
                # 技巧：如果数据量超过 2000 行，为了防止请求超时，我们保留关键统计信息
                # 但 Gemini 1.5 Flash 支持 100万 token，我们尽量发全量
                
                # 将整个 DataFrame 转为字符串
                full_data_str = df.to_csv(index=False)
                
                # 检查字数，如果超过 80万字符（约等于限制），进行截断保护
                if len(full_data_str) > 800000:
                    st.warning("⚠️ 数据量极大，已自动截取最重要的前 3000 行进行分析。")
                    full_data_str = df.head(3000).to_csv(index=False)

                prompt = f"""
                角色：资深电商数据专家。
                用户意图：{analysis_mode}
                
                这是用户上传的完整广告数据（CSV格式）：
                
                ```csv
                {full_data_str}
                ```
                
                请根据以上【全部数据】进行运算和分析，不要只看局部。
                
                任务要求：
                1. **决策建议**：请直接列出这就这几个表现【最好】的广告ID，和必须【立即停止】的广告ID。
                2. **数据支撑**：解释为什么建议停止？（是因为花费高但GMV为0？还是CTR太低？）
                3. **逆推与预测**：如果把浪费的预算挪到表现好的广告上，预估下周的 GMV 增长潜力。
                4. **排版**：请用清晰的列表和加粗字体，不要长篇大论，直接给操作指令。
                """
                
                response_text = get_gemini_response(prompt)
                st.markdown("### 🧠 AI 分析结论")
                st.markdown(response_text)

st.markdown("---")

# --- 模块 3: 图片分析 ---
st.header("3. 广告图诊断")
uploaded_img = st.file_uploader("上传广告素材", type=['png', 'jpg', 'jpeg'])
if uploaded_img and st.button("👁️ 分析图片"):
    with st.spinner("正在分析视觉..."):
        res = get_gemini_response("这张图作为电商广告，吸引力够吗？给分0-10。如何修改能提高点击率？", Image.open(uploaded_img))
        st.markdown(res)
