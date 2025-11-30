import streamlit as st
import pandas as pd
import requests
import json
import base64
from PIL import Image
import io

# --- 页面配置 ---
st.set_page_config(page_title="Shopee 广告分析 V4.0 (兼容版)", page_icon="🛡️", layout="wide")

# --- 侧边栏 ---
st.sidebar.title("🔧 设置")
api_key = st.sidebar.text_input("Google Gemini API Key:", type="password")

# --- 核心函数：连接 AI ---
def get_gemini_response(prompt, image=None):
    if not api_key: return "⚠️ 请先输入 API Key"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    contents_parts = [{"text": prompt}]
    if image:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        contents_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_str}})
    payload = {"contents": [{"parts": contents_parts}]}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"Request Failed: {str(e)}"

# --- 核心函数：万能文件读取 (带调试信息) ---
def load_data_brute_force(uploaded_file):
    error_log = []
    df = None
    
    # 0. 预处理：指针归零
    uploaded_file.seek(0)
    file_type = uploaded_file.name.split('.')[-1].lower()

    # 尝试 1: 标准 Excel (.xlsx) - openpyxl
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        return df, "Success: openpyxl"
    except Exception as e:
        error_log.append(f"xlsx尝试失败: {str(e)}")
        uploaded_file.seek(0)

    # 尝试 2: 旧版 Excel (.xls) - xlrd
    try:
        df = pd.read_excel(uploaded_file, engine='xlrd')
        return df, "Success: xlrd"
    except Exception as e:
        error_log.append(f"xls尝试失败: {str(e)}")
        uploaded_file.seek(0)

    # 尝试 3: 标准 CSV (utf-8)
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
        return df, "Success: csv_utf8"
    except Exception as e:
        error_log.append(f"csv_utf8尝试失败: {str(e)}")
        uploaded_file.seek(0)
        
    # 尝试 4: 常见乱码 CSV (latin1/gbk)
    try:
        df = pd.read_csv(uploaded_file, encoding='latin1')
        return df, "Success: csv_latin1"
    except Exception as e:
        error_log.append(f"csv_latin1尝试失败: {str(e)}")
        uploaded_file.seek(0)
    
    # 尝试 5: 如果是 Shopee 这种带前几行废话的，尝试跳过前6行读取
    try:
        df = pd.read_excel(uploaded_file) # 让pandas自动猜
        # 寻找表头
        for i in range(10):
            # 检查这一行是否包含 'Status' 或 'Nama'
            row_values = df.iloc[i].astype(str).values
            if any("Status" in v or "Nama" in v for v in row_values):
                df.columns = df.iloc[i] # 设为表头
                df = df.iloc[i+1:] # 截取下面的数据
                return df, f"Success: Auto-Header found at row {i}"
    except Exception as e:
        error_log.append(f"自动寻找表头失败: {str(e)}")

    return None, "\n".join(error_log)

# --- 主页面 ---
st.title("🛡️ 广告文件强力修复版 (V4.0)")

uploaded_file = st.file_uploader("上传文件 (支持 xls, xlsx, csv)", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    # 1. 读取文件
    df, status_msg = load_data_brute_force(uploaded_file)
    
    if df is None:
        st.error("❌ 文件彻底读取失败！")
        with st.expander("查看详细错误原因 (发给工程师)"):
            st.code(status_msg)
        st.info("💡 建议：打开 Excel 文件，点击【文件】->【另存为】-> 选择【Excel 工作簿 (*.xlsx)】，然后上传新文件。")
    else:
        # 2. 简单的表头清洗 (防止读出来的表头不准)
        # 如果第一列是 "店铺名称" 这种废话，我们再做一次清理
        st.success("✅ 读取成功！")
        
        # 再次确认表头：如果现在的列名里没有 'Status'，我们去前几行找找
        cols_str = " ".join([str(c) for c in df.columns])
        if "Status" not in cols_str and "Nama" not in cols_str:
            st.warning("⚠️ 检测到表头可能未对齐，正在尝试自动修正...")
            # 暴力找表头逻辑
            for idx, row in df.iterrows():
                row_text = " ".join(row.astype(str).values)
                if "Status" in row_text or "Nama Iklan" in row_text:
                    df.columns = row.values
                    df = df.iloc[idx+1:]
                    break

        st.dataframe(df.head())
        
        # --- AI 分析部分 ---
        if st.button("开始 AI 分析"):
            with st.spinner("AI 正在思考..."):
                # 安全截取数据
                data_str = df.head(2000).to_csv(index=False)
                prompt = f"""
                分析这份 Shopee 广告数据。
                字段说明：Nama Iklan(商品), Biaya(花费), Omzet(销售额), Efektivitas(ROI).
                
                数据：
                {data_str}
                
                请给出：
                1. 表现最好的3个广告（高ROI）。
                2. 表现最差的3个广告（亏损）。
                3. 针对 GMV Max 和 Manual Bidding 的优化建议。
                """
                res = get_gemini_response(prompt)
                st.markdown(res)
