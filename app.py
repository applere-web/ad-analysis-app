import streamlit as st
import pandas as pd
import requests
import json
import base64
from PIL import Image
import io

# --- 页面配置 ---
st.set_page_config(
    page_title="Shopee/TikTok/Lazada 广告分析 V3.0",
    page_icon="🛒",
    layout="wide"
)

# --- 侧边栏 ---
st.sidebar.title("🔧 设置中心")
api_key = st.sidebar.text_input("请输入 Google Gemini API Key:", type="password")
st.sidebar.markdown("---")
st.sidebar.info("V3.0 更新：\n1. 自动识别 Shopee 报表格式\n2. 自动跳过顶部的店铺信息行\n3. 针对 GMV Max 和 Bidding Manual 进行优化")

# --- 核心函数：连接 AI ---
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

# --- 核心函数：智能读取 Shopee 报表 ---
def load_shopee_data(uploaded_file):
    try:
        # 1. 先把文件读进来，不设表头，看前20行
        if uploaded_file.name.endswith('.csv'):
            # 尝试多种编码，防止印尼语/中文乱码
            try:
                df_temp = pd.read_csv(uploaded_file, header=None, nrows=20, encoding='utf-8')
            except:
                uploaded_file.seek(0)
                df_temp = pd.read_csv(uploaded_file, header=None, nrows=20, encoding='latin1')
        else:
            df_temp = pd.read_excel(uploaded_file, header=None, nrows=20)
        
        # 2. 寻找真正的表头行
        # 我们找包含 'Nama Iklan' (广告名) 或 'Status' (状态) 的那一行
        header_row_index = -1
        for i, row in df_temp.iterrows():
            row_str = row.astype(str).values.tolist()
            # 只要这一行里同时出现了 "Status" 或者 "Nama Iklan" 或者 "Ad Name"，就认为是表头
            if any("Nama Iklan" in str(x) for x in row_str) or any("Ad Name" in str(x) for x in row_str):
                header_row_index = i
                break
        
        # 3. 如果没找到，就默认第0行；如果找到了，就从那一行重新读取
        uploaded_file.seek(0) # 回到文件开头
        
        if header_row_index != -1:
            st.toast(f"✅ 已自动识别表头在第 {header_row_index + 1} 行，正在裁切数据...", icon="✂️")
            if uploaded_file.name.endswith('.csv'):
                try:
                    df = pd.read_csv(uploaded_file, header=header_row_index, encoding='utf-8')
                except:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, header=header_row_index, encoding='latin1')
            else:
                df = pd.read_excel(uploaded_file, header=header_row_index)
        else:
            st.warning("⚠️ 未能自动定位表头，尝试标准读取...")
            if uploaded_file.name.endswith('.csv'):
                 df = pd.read_csv(uploaded_file)
            else:
                 df = pd.read_excel(uploaded_file)

        return df

    except Exception as e:
        return None

# --- 主页面 ---
st.title("🛒 Shopee/Lazada 智能广告报表分析")
st.caption("专为 Shopee 印尼/马来/台湾站点优化 | 自动识别 GMV Max 与 ROI")

# --- 模块 1: 数据上传 ---
st.header("1. 上传报表 (Excel/CSV)")
uploaded_file = st.file_uploader("请直接上传 Shopee 导出的原始文件 (无需删除前几行)", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    df = load_shopee_data(uploaded_file)
    
    if df is None:
        st.error("❌ 文件读取失败。请确保文件是 Excel (.xlsx) 或 CSV 格式。")
    else:
        # 数据清洗：删除完全为空的列
        df = df.dropna(how='all', axis=1)
        
        st.success(f"✅ 读取成功！有效数据共 {len(df)} 条。")
        st.write("### 📊 数据预览 (已自动修正表头)")
        st.dataframe(df.head(5))

        # --- 模块 2: AI 分析 ---
        st.header("2. AI 深度分析")
        
        analysis_mode = st.selectbox("选择分析维度", 
            ["综合诊断：哪些要停？哪些要加码？", 
             "GMV Max 效果专项分析", 
             "Bidding Manual (手动出价) 关键词优化", 
             "高 ROI (Efektivitas) 逆推模式"])
        
        if st.button("🚀 开始 AI 运算"):
            with st.spinner("AI 正在分析您的广告花费(Biaya)、销售额(Omzet)和ROI(Efektivitas)..."):
                
                # 数据截取与转换
                full_data_str = df.head(3000).to_csv(index=False)
                
                prompt = f"""
                角色：Shopee/Lazada 顶级电商运营专家。
                任务：分析用户上传的广告数据。
                分析目标：{analysis_mode}
                
                **重要：字段对应关系 (Shopee Indonesia)**
                - Nama Iklan = 广告名称/产品名
                - Status = 状态
                - Mode Bidding = 出价模式 (GMV Max / Manual)
                - Dilihat = 浏览量 (Impressions)
                - Jumlah Klik = 点击量 (Clicks)
                - Persentas Klik = 点击率 (CTR)
                - Biaya = 花费 (Cost)
                - Omzet Penjualan = 销售额 (GMV)
                - Efektivitas = 投产比 (ROI/ROAS)
                - Produk Terjual = 销量
                
                这是用户的数据样本 (CSV格式):
                ```csv
                {full_data_str}
                ```
                
                请给出极其具体的**操作建议**：
                1. **红黑榜**：列出表现最好的 3 个广告 (ROI/Efektivitas 最高)，和表现最差的 3 个广告 (光花钱不出单)。
                2. **诊断分析**：
                   - 针对 **GMV Max** 的广告，效果如何？如果不理想，建议是调预算还是关停？
                   - 针对 **Manual Bidding** 的广告，点击率低是因为图片还是关键词？
                3. **未来动作**：具体说明哪个 ID 需要【听/暂停】，哪个 ID 需要【增加预算】。
                4. **趋势逆推**：如果把浪费在差广告上的钱挪给好广告，预估下周销售额增长多少？
                
                请用**中文**回答，重点突出，不要讲大道理，直接给操作指令。
                """
                
                response_text = get_gemini_response(prompt)
                st.markdown("### 🧠 运营策略建议")
                st.markdown(response_text)

st.markdown("---")

# --- 模块 3: 图片分析 ---
st.header("3. 广告图诊断")
uploaded_img = st.file_uploader("上传广告图", type=['png', 'jpg', 'jpeg'])
if uploaded_img and st.button("👁️ 分析图片"):
    with st.spinner("AI 正在看图..."):
        res = get_gemini_response("这张图作为Shopee/Lazada的主图，点击率会高吗？给分0-10。有什么缺点？怎么改更吸引人？", Image.open(uploaded_img))
        st.markdown(res)
