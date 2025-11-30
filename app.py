import streamlit as st
import pandas as pd
import requests
import json
import base64
from PIL import Image
import io
import time

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="电商广告 AI 决策系统 V6.1 (自动寻路版)",
    page_icon="🛍️",
    layout="wide"
)

# --- 2. 侧边栏设置 ---
st.sidebar.title("🔧 系统设置")
api_key = st.sidebar.text_input("请输入 Google Gemini API Key:", type="password")
st.sidebar.markdown("---")
st.sidebar.success("✅ V6.1 升级：\n- 自动修复 404 连接错误\n- 自动切换 AI 模型线路\n- 保留所有 V6.0 功能")

# --- 3. 核心功能：连接 AI (增加自动重试机制) ---
def get_gemini_response(prompt, image=None):
    if not api_key:
        return "⚠️ 请先在侧边栏输入 API Key"

    # 备选模型列表：如果第一个报错，自动试下一个
    models_to_try = [
        "gemini-1.5-flash", 
        "gemini-1.5-flash-latest", 
        "gemini-1.5-flash-001",
        "gemini-pro"  # 最后的保底
    ]

    # 准备图片数据 (如果有)
    image_part = None
    if image:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        image_part = {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": img_str
            }
        }

    last_error = ""

    # --- 循环尝试连接 ---
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        
        contents_parts = [{"text": prompt}]
        if image_part:
            contents_parts.append(image_part)

        payload = {"contents": [{"parts": contents_parts}]}

        try:
            # 发送请求
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            
            # 如果成功 (200)，直接返回结果，结束循环
            if response.status_code == 200:
                result = response.json()
                try:
                    return result['candidates'][0]['content']['parts'][0]['text']
                except:
                    return f"AI 回复解析异常 ({model_name}): {result}"
            
            # 如果是 404 (找不到模型) 或 503 (过载)，记录错误并尝试下一个
            else:
                last_error = f"模型 {model_name} 连接失败 ({response.status_code})。正在尝试备用线路..."
                continue # 跳到下一次循环

        except Exception as e:
            last_error = f"网络错误: {str(e)}"
            continue

    # 如果所有模型都试完了还是不行
    return f"❌ 所有 AI 线路均无法连接。最后一次错误: {last_error}\n请检查 API Key 是否有效，或 Google 服务是否在维护。"

# --- 4. 核心功能：强力文件读取 (Shopee 专用修复) ---
def load_data_robust(uploaded_file):
    uploaded_file.seek(0)
    df = None
    read_method = ""

    # 策略 A: .xlsx (openpyxl)
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        read_method = "openpyxl"
    except:
        uploaded_file.seek(0)
    
    # 策略 B: .xls (xlrd)
    if df is None:
        try:
            df = pd.read_excel(uploaded_file, engine='xlrd')
            read_method = "xlrd"
        except:
            uploaded_file.seek(0)

    # 策略 C: CSV
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
st.title("🛒 全平台电商广告 AI 决策系统")
st.caption("版本: V6.1 (Auto-Switch Model) | 状态: 稳定")

# ================= 模块 1: 报表分析 =================
st.header("1. 广告报表分析")
uploaded_file = st.file_uploader("支持 Shopee/TikTok/Lazada 报表", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    df, method = load_data_robust(uploaded_file)
    
    if df is None:
        st.error(f"❌ 读取失败: {method}")
    else:
        st.success(f"✅ 读取成功 ({method}) | 数据行数: {len(df)}")
        st.dataframe(df.head(3))

        st.subheader("🤖 选择 AI 运算模式")
        analysis_mode = st.selectbox(
            "请选择分析方向：",
            [
                "综合诊断 (红黑榜 + 启停建议)",
                "GMV Max 专项分析 (预算分配)",
                "手动出价 (Manual Bidding) 优化",
                "逆推模式：提高投产比 (ROI)",
                "未来趋势预测"
            ]
        )

        if st.button("🚀 开始 AI 运算"):
            with st.spinner("正在连接 Google AI (自动尝试最佳线路)..."):
                data_preview = df.head(3000).to_csv(index=False)
                
                prompt = f"""
                角色：资深电商数据科学家。
                任务：分析广告数据（Shopee/Lazada/TikTok）。
                模式：{analysis_mode}
                
                **Shopee 印尼/马来字段字典:**
                - Nama Iklan = 广告名称
                - Status = 状态
                - Mode Bidding = 出价模式 (GMV Max / Manual)
                - Biaya = 花费
                - Omzet Penjualan = 销售额
                - Efektivitas = ROI
                - Jumlah Klik = 点击量
                - Persentas Klik = CTR
                
                数据:
                {data_preview}
                
                请输出：
                1. **决策建议**：3个最好(继续投) 和 3个最差(暂停)的广告ID。
                2. **深度洞察**：
                   - GMV Max 效果如何？ROI 达标吗？
                   - 花费高但 0 转化的是哪些？
                3. **行动指令**：针对“{analysis_mode}”的具体操作。
                4. **预测**：下周趋势预估。
                
                请用中文回答。
                """
                
                response = get_gemini_response(prompt)
                st.markdown("### 🧠 AI 分析结论")
                st.markdown(response)

st.markdown("---")

# ================= 模块 2: 图片分析 =================
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
