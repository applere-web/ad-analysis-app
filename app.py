import streamlit as st
import pandas as pd
import requests
import json
import base64
from PIL import Image
import io

# --- 页面配置 ---
st.set_page_config(
    page_title="电商广告 AI 决策系统 V5.0 (旗舰版)",
    page_icon="🚀",
    layout="wide"
)

# --- 侧边栏设置 ---
st.sidebar.title("🔧 系统设置")
api_key = st.sidebar.text_input("请输入 Google Gemini API Key:", type="password")
st.sidebar.info("V5.0 特性：\n✅ 强力修复文件读取 (含 xls/xlsx/csv)\n✅ 包含 GMV Max 专项分析\n✅ 包含图片视觉诊断\n✅ 包含 ROI 逆推模拟")

# --- 核心 1: 连接 AI (稳定版) ---
def get_gemini_response(prompt, image=None):
    if not api_key:
        return "⚠️ 请先在侧边栏输入 API Key"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    contents_parts = [{"text": prompt}]

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

# --- 核心 2: 强力文件读取 (保留 V4.0 的能力) ---
def load_data_robust(uploaded_file):
    error_log = []
    
    # 0. 预处理
    uploaded_file.seek(0)

    # 尝试 1: 标准 Excel (.xlsx)
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        return df, "Success: openpyxl"
    except:
        uploaded_file.seek(0)

    # 尝试 2: 旧版 Excel (.xls) - 关键修复
    try:
        df = pd.read_excel(uploaded_file, engine='xlrd')
        return df, "Success: xlrd"
    except:
        uploaded_file.seek(0)

    # 尝试 3: 标准 CSV
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
        return df, "Success: csv_utf8"
    except:
        uploaded_file.seek(0)
        
    # 尝试 4: 乱码 CSV
    try:
        df = pd.read_csv(uploaded_file, encoding='latin1')
        return df, "Success: csv_latin1"
    except:
        uploaded_file.seek(0)
    
    # 尝试 5: 自动寻找表头 (针对 Shopee 报表)
    try:
        # 先盲读
        if uploaded_file.name.endswith('.csv'):
             df = pd.read_csv(uploaded_file, on_bad_lines='skip', encoding='latin1')
        else:
             df = pd.read_excel(uploaded_file)
        
        # 暴力搜索包含 'Nama' 或 'Status' 的行
        for i in range(min(20, len(df))):
            row_text = " ".join(df.iloc[i].astype(str).values)
            if "Nama" in row_text or "Status" in row_text or "Iklan" in row_text:
                df.columns = df.iloc[i] # 设为表头
                df = df.iloc[i+1:] # 截取
                df = df.reset_index(drop=True)
                return df, f"Success: Auto-Header found at row {i}"
    except Exception as e:
        error_log.append(str(e))

    return None, "所有读取方法均失败"

# --- 主页面 UI ---
st.title("🚀 多平台电商广告 AI 决策系统 (V5.0)")
st.caption("集成：数据清洗 + 策略逆推 + 视觉诊断 + GMV Max 深度分析")

# ================= 模块 1: 数据上传 (功能回归) =================
st.header("1. 广告数据分析")
uploaded_file = st.file_uploader("支持 Shopee/TikTok/Lazada 报表 (xls, xlsx, csv)", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    # 调用强力读取函数
    df, status_msg = load_data_robust(uploaded_file)
    
    if df is None:
        st.error("❌ 文件读取失败，请检查文件是否损坏。")
    else:
        # 数据清洗：简单的表头修正 (双重保险)
        cols = [str(c) for c in df.columns]
        if "Status" not in cols and "Nama Iklan" not in cols:
             # 如果还没对齐，再试一次
             st.toast("正在微调表头格式...", icon="🔧")
             for idx, row in df.iterrows():
                 if "Status" in str(row.values) or "Nama" in str(row.values):
                     df.columns = row.values
                     df = df.iloc[idx+1:]
                     break
        
        st.success(f"✅ 读取成功！有效数据 {len(df)} 行")
        st.dataframe(df.head(3)) # 只展示前3行

        # --- 功能回归：策略选择 ---
        st.subheader("🤖 选择 AI 分析策略")
        analysis_mode = st.selectbox("请选择分析模式 (功能全开)", 
            [
                "综合诊断 (红黑榜 + 启停建议)", 
                "GMV Max 专项分析 (预算分配建议)", 
                "手动出价 (Bidding Manual) 关键词优化", 
                "ROI 逆推模式 (如何提高投产比)",
                "未来趋势预测 (下周流量模拟)"
            ]
        )
        
        if st.button("🚀 开始 AI 运算"):
            with st.spinner("AI 正在全盘扫描数据、计算 ROI、比对 GMV Max 效果..."):
                # 准备数据 (截取前3000行以防超时，足够分析)
                data_str = df.head(3000).to_csv(index=False)
                
                # 能够读懂 Shopee 印尼语的 Prompt
                prompt = f"""
                角色：顶级电商数据分析师。
                任务：分析这份电商广告数据。
                模式：{analysis_mode}
                
                **关键字段字典 (Shopee ID -> 中文):**
                - Nama Iklan: 广告名
                - Status: 状态
                - Mode Bidding: 出价模式 (关注 GMV Max vs Manual)
                - Biaya: 花费 (Cost)
                - Omzet Penjualan: 销售额 (GMV)
                - Efektivitas: 投产比 (ROI)
                - Jumlah Klik: 点击量
                - Persentas Klik: 点击率 (CTR)
                
                数据内容:
                {data_str}
                
                请输出分析报告：
                1. **核心结论**：直接告诉我哪些广告表现好(保留)，哪些表现差(关停)。
                2. **数据洞察**：
                   - 如果是 GMV Max，它的 ROI 达标了吗？
                   - 花费最高但没有转化的广告是哪个？
                3. **行动指南**：针对我的 {analysis_mode} 需求，给出具体操作步骤 (比如：调整出价、更换素材、停止投放)。
                4. **未来预测**：基于当前趋势，预测下周表现。
                
                请用清晰的中文回答，多用数据支撑。
                """
                
                res = get_gemini_response(prompt)
                st.markdown("### 📊 AI 分析报告")
                st.markdown(res)

st.markdown("---")

# ================= 模块 2: 图片分析 (功能回归) =================
st.header("2. 广告素材视觉诊断")
st.info("上传广告图，AI 将模拟用户眼球追踪，预测点击率。")

uploaded_img = st.file_uploader("上传广告图片", type=['png', 'jpg', 'jpeg'])
if uploaded_img:
    image = Image.open(uploaded_img)
    st.image(image, caption='待分析素材', width=300)
    
    img_prompt = st.text_input("想问 AI 什么？", value="这张图作为电商广告，点击率(CTR)会高吗？满分10分打几分？最大的缺点是什么？")
    
    if st.button("👁️ 开始视觉分析"):
        with st.spinner("AI 正在进行视觉推理..."):
            img_res = get_gemini_response(img_prompt, image)
            st.markdown("### 💡 视觉优化建议")
            st.markdown(img_res)

# --- 底部 ---
st.markdown("---")
st.caption("架构: Streamlit + Python + Google Gemini | V5.0 Ultimate")
