import streamlit as st
import pandas as pd
import requests
import json
import base64
from PIL import Image
import io

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="电商广告 AI 决策系统 V7.0 (终极修正)",
    page_icon="🛍️",
    layout="wide"
)

# --- 2. 侧边栏 (增加 Key 状态检查) ---
st.sidebar.title("🔧 系统设置")
# 自动去除首尾空格 (.strip)，防止复制错误
raw_api_key = st.sidebar.text_input("请输入 Google Gemini API Key:", type="password")
api_key = raw_api_key.strip() if raw_api_key else ""

if api_key:
    if not api_key.startswith("AIza"):
        st.sidebar.error("⚠️ Key 格式看起来不对 (通常以 AIza 开头)")
    else:
        st.sidebar.success("✅ Key 格式正确，准备连接")

st.sidebar.markdown("---")
st.sidebar.info("V7.0 特性：\n- 自动清除 Key 空格\n- 包含 Shopee 表头自动识别\n- 包含 GMV Max & ROI 分析\n- 包含图片分析")

# --- 3. 核心功能：连接 AI (增强型轮询) ---
def get_gemini_response(prompt, image=None):
    if not api_key:
        return "⚠️ 请先在侧边栏输入 API Key"

    # 这里的顺序非常重要：先试最强最快的，再试最老最稳的
    models_to_try = [
        "gemini-1.5-flash",          # 首选：最新、免费、快
        "gemini-1.5-flash-latest",   # 备选别名
        "gemini-pro",                # 保底：上一代模型 (通常最稳)
        "gemini-1.0-pro"             # 最后的保底
    ]

    # 图片处理
    image_part = None
    if image:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        image_part = {"inline_data": {"mime_type": "image/jpeg", "data": img_str}}

    last_error_msg = ""

    # 循环尝试连接
    for model_name in models_to_try:
        # 注意：这里统一使用 v1beta，因为它是目前最通用的
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        
        contents_parts = [{"text": prompt}]
        if image_part:
            contents_parts.append(image_part)

        payload = {"contents": [{"parts": contents_parts}]}

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                try:
                    return result['candidates'][0]['content']['parts'][0]['text']
                except:
                    return f"AI 回复解析异常: {result}"
            else:
                # 记录错误，但不立即停止，继续试下一个模型
                error_info = response.json() if response.content else response.text
                last_error_msg = f"模型 {model_name} 返回 {response.status_code}: {error_info}"
                continue 

        except Exception as e:
            last_error_msg = f"网络连接错误: {str(e)}"
            continue

    # 如果循环结束还没返回，说明全挂了
    return f"❌ 连接彻底失败。\n\n最后一次错误日志: {last_error_msg}\n\n💡 建议方案：\n1. 您的 Key 可能无效，请去 Google AI Studio 重新生成一个。\n2. 确保您没有在受限国家(如中国内地)且未开代理。"

# --- 4. 核心功能：强力文件读取 (Shopee 专用) ---
def load_data_robust(uploaded_file):
    uploaded_file.seek(0)
    df = None
    read_method = ""

    # 1. 新版 Excel
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        read_method = "openpyxl"
    except:
        uploaded_file.seek(0)
    
    # 2. 旧版 Excel (您需要的关键功能)
    if df is None:
        try:
            df = pd.read_excel(uploaded_file, engine='xlrd')
            read_method = "xlrd"
        except:
            uploaded_file.seek(0)

    # 3. CSV
    if df is None:
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8')
            read_method = "csv_utf8"
        except:
            uploaded_file.seek(0)
            try:
                df = pd.read_csv(uploaded_file, encoding='latin1', on_bad_lines='skip')
                read_method = "csv_latin1"
            except:
                pass

    # --- 智能表头识别 (Shopee) ---
    if df is not None:
        try:
            cols_str = " ".join([str(c) for c in df.columns])
            if "Status" not in cols_str and "Nama" not in cols_str:
                for i in range(min(30, len(df))): 
                    row_values = " ".join(df.iloc[i].astype(str).values)
                    if "Status" in row_values or "Nama" in row_values or "Iklan" in row_values:
                        df.columns = df.iloc[i] 
                        df = df.iloc[i+1:]      
                        df = df.reset_index(drop=True)
                        read_method += " + AutoHeader"
                        break
        except Exception as e:
            return None, f"表头清洗失败: {str(e)}"
            
        return df, read_method

    return None, "所有读取方法均失败"

# --- 5. 主界面 ---
st.title("🛒 全平台电商广告 AI 决策系统 V7.0")

# ================= 模块 1: 报表分析 (保留所有功能) =================
st.header("1. 广告报表分析")
uploaded_file = st.file_uploader("支持 Shopee/TikTok/Lazada 报表", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    df, method = load_data_robust(uploaded_file)
    
    if df is None:
        st.error(f"❌ 读取失败: {method}")
    else:
        st.success(f"✅ 读取成功 ({method}) | 数据量: {len(df)} 行")
        st.dataframe(df.head(3))

        st.subheader("🤖 AI 运算模式")
        analysis_mode = st.selectbox(
            "选择分析策略：",
            [
                "综合诊断 (红黑榜 + 启停建议)",
                "GMV Max 专项分析 (预算优化)",
                "手动出价 (Manual Bidding) 优化",
                "逆推模式：提高投产比 (ROI)",
                "未来趋势预测"
            ]
        )

        if st.button("🚀 开始 AI 运算"):
            with st.spinner("正在连接 Google AI (自动尝试多条线路)..."):
                # 截取数据
                data_preview = df.head(3000).to_csv(index=False)
                
                prompt = f"""
                角色：电商数据专家。
                任务：分析广告数据。
                模式：{analysis_mode}
                
                **Shopee 印尼/马来字段字典:**
                - Nama Iklan = 广告名称
                - Status = 状态
                - Mode Bidding = 出价模式 (GMV Max / Manual)
                - Biaya = 花费
                - Omzet Penjualan = 销售额
                - Efektivitas = ROI
                - Jumlah Klik = 点击量
                
                数据:
                {data_preview}
                
                请输出中文报告：
                1. **决策建议**：3个最好(继续投) 和 3个最差(暂停)的广告ID。
                2. **深度洞察**：
                   - GMV Max 效果如何？
                   - 花费高但 0 转化的是哪些？
                3. **行动指令**：针对“{analysis_mode}”的具体操作。
                4. **预测**：下周趋势。
                """
                
                response = get_gemini_response(prompt)
                st.markdown("### 🧠 AI 分析结论")
                st.markdown(response)

st.markdown("---")

# ================= 模块 2: 图片分析 (保留功能) =================
st.header("2. 广告素材视觉诊断")
uploaded_image = st.file_uploader("上传广告素材", type=['png', 'jpg', 'jpeg'])

if uploaded_image is not None:
    image = Image.open(uploaded_image)
    st.image(image, caption='素材预览', width=300)
    
    img_prompt = st.text_input("问题:", value="这张图点击率会高吗？满分10分打几分？有什么缺点？")
    
    if st.button("👁️ 开始视觉分析"):
        with st.spinner("AI 正在分析视觉..."):
            img_result = get_gemini_response(img_prompt, image)
            st.markdown("### 💡 视觉优化建议")
            st.markdown(img_result)
