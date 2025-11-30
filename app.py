import streamlit as st
import pandas as pd
import requests
import json
import base64
from PIL import Image
import io

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="电商广告 AI 决策系统 V6.0 (全功能版)",
    page_icon="🛍️",
    layout="wide"
)

# --- 2. 侧边栏设置 ---
st.sidebar.title("🔧 系统设置")
api_key = st.sidebar.text_input("请输入 Google Gemini API Key:", type="password")
st.sidebar.markdown("---")
st.sidebar.success("✅ 功能状态：\n- 强力文件读取: Ready\n- GMV Max 分析: Ready\n- 图片视觉诊断: Ready\n- 智能表头识别: Ready")

# --- 3. 核心功能：连接 AI (REST API 模式 - 最稳定) ---
def get_gemini_response(prompt, image=None):
    if not api_key:
        return "⚠️ 请先在侧边栏输入 API Key"

    # 使用 Gemini 1.5 Flash 模型
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    contents_parts = [{"text": prompt}]

    # 如果有图片，处理图片数据
    if image:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        contents_parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": img_str
            }
        })

    payload = {"contents": [{"parts": contents_parts}]}

    try:
        # 发送请求，设置 60秒超时防止卡死
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if response.status_code == 200:
            result = response.json()
            try:
                return result['candidates'][0]['content']['parts'][0]['text']
            except:
                return f"AI 回复解析异常: {result}"
        else:
            return f"❌ AI 请求失败 (代码 {response.status_code}): {response.text}"
    except Exception as e:
        return f"❌ 网络连接错误: {str(e)}"

# --- 4. 核心功能：强力文件读取 (集成自动表头识别 + 旧版Excel支持) ---
def load_data_robust(uploaded_file):
    # 重置文件指针
    uploaded_file.seek(0)
    df = None
    read_method = ""

    # 策略 A: 尝试作为 .xlsx (新版 Excel)
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        read_method = "openpyxl"
    except:
        uploaded_file.seek(0)
    
    # 策略 B: 尝试作为 .xls (旧版 Excel - 专门修复您遇到的问题)
    if df is None:
        try:
            df = pd.read_excel(uploaded_file, engine='xlrd')
            read_method = "xlrd"
        except:
            uploaded_file.seek(0)

    # 策略 C: 尝试作为 CSV (多种编码)
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

    # --- 智能表头清洗 (针对 Shopee) ---
    # 无论上面用哪种方法读出来，如果第一行是店铺名，我们需要往下找 "Nama Iklan"
    if df is not None:
        try:
            # 转换成字符串列表方便搜索
            cols_str = " ".join([str(c) for c in df.columns])
            # 如果表头里没有 'Status' 或 'Nama'，说明表头没对齐
            if "Status" not in cols_str and "Nama" not in cols_str:
                for i in range(min(30, len(df))): # 往下搜 30 行
                    row_values = " ".join(df.iloc[i].astype(str).values)
                    # 只要发现这一行有 Status, Nama Iklan, Ad Name, SKU 等关键词
                    if "Status" in row_values or "Nama" in row_values or "Iklan" in row_values:
                        df.columns = df.iloc[i] # 把这行变表头
                        df = df.iloc[i+1:]      # 截取这行下面的数据
                        df = df.reset_index(drop=True)
                        read_method += " + AutoHeader"
                        break
        except Exception as e:
            return None, f"表头清洗失败: {str(e)}"
            
        return df, read_method

    return None, "所有读取方法均失败 (Unknown Format)"

# --- 5. 主界面构建 ---
st.title("🛒 全平台电商广告 AI 决策系统")
st.caption("架构版本: V6.0 | 包含: 数据运算 + 视觉分析 + 策略逆推")

# ================= 模块 1: 数据上传与分析 =================
st.header("1. 广告报表分析")
uploaded_file = st.file_uploader("支持 Shopee/TikTok/Lazada 报表 (xls, xlsx, csv)", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    df, method = load_data_robust(uploaded_file)
    
    if df is None:
        st.error(f"❌ 读取失败: {method}")
        st.info("建议：请将文件另存为 .xlsx 格式后重新上传。")
    else:
        st.success(f"✅ 读取成功 ({method}) | 数据行数: {len(df)}")
        
        # 数据预览
        st.write("### 📊 数据预览")
        st.dataframe(df.head(3))

        # 策略选择区
        st.subheader("🤖 选择 AI 运算模式")
        analysis_mode = st.selectbox(
            "请选择您想要 AI 分析的方向：",
            [
                "综合诊断 (红黑榜 + 启停建议)",
                "GMV Max 专项分析 (预算分配与效果评估)",
                "手动出价 (Manual Bidding) 关键词优化",
                "逆推模式：如何提高投产比 (ROI/Efektivitas)",
                "未来趋势预测 (下阶段流量模拟)"
            ]
        )

        if st.button("🚀 开始 AI 运算"):
            with st.spinner("AI 正在连接谷歌大脑，进行逻辑推理与数据运算..."):
                # 截取数据文本 (保留前3000行，通常包含核心头部数据)
                data_preview = df.head(3000).to_csv(index=False)
                
                # 精心设计的 Prompt (包含印尼语映射)
                prompt = f"""
                角色：资深电商数据科学家。
                用户任务：分析以下广告数据（平台：Shopee/Lazada/TikTok）。
                分析模式：{analysis_mode}
                
                **关键字段字典 (请务必基于此理解数据):**
                - Nama Iklan / Ad Name = 广告/产品名称
                - Status = 广告状态
                - Mode Bidding / Bid Type = 出价模式 (GMV Max 或 Manual)
                - Biaya / Cost = 花费
                - Omzet Penjualan / GMV = 销售额
                - Efektivitas / ROI = 投产比
                - Jumlah Klik / Clicks = 点击量
                - Persentas Klik / CTR = 点击率
                
                数据内容 (CSV格式):
                {data_preview}
                
                请输出分析报告：
                1. **决策建议**：直接列出 3 个表现最好的广告ID (继续投/加码)，和 3 个表现最差的广告ID (建议暂停/听)。
                2. **深度洞察**：
                   - 针对 GMV Max 广告，它的 ROI 是否及格？
                   - 针对 Manual Bidding，点击率低是因为什么？
                3. **行动指令**：根据我的“{analysis_mode}”需求，告诉我下一步具体做什么？
                4. **模拟预测**：如果按您的建议调整，预估下周的 ROI 变化趋势。
                
                要求：使用中文回答，逻辑清晰，数据支撑。
                """
                
                # 调用 AI
                response = get_gemini_response(prompt)
                st.markdown("### 🧠 AI 分析结论")
                st.markdown(response)

st.markdown("---")

# ================= 模块 2: 图片视觉分析 =================
st.header("2. 广告素材视觉诊断")
st.info("功能：上传广告图，AI 将模拟用户视角，预测点击率并给出修改建议。")

uploaded_image = st.file_uploader("上传广告素材图片", type=['png', 'jpg', 'jpeg'])

if uploaded_image is not None:
    image = Image.open(uploaded_image)
    st.image(image, caption='待分析素材', width=300)
    
    img_prompt = st.text_input("您可以输入具体问题 (或保持默认):", value="这张图作为电商广告，点击率(CTR)会高吗？满分10分打几分？最大的缺点是什么？")
    
    if st.button("👁️ 开始视觉分析"):
        with st.spinner("AI 正在观看图片..."):
            img_result = get_gemini_response(img_prompt, image)
            st.markdown("### 💡 视觉优化建议")
            st.markdown(img_result)

# --- 底部版权 ---
st.markdown("---")
st.caption("Powered by Streamlit & Google Gemini 1.5 Flash | Architecture V6.0")
