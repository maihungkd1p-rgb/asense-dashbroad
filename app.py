import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Báo Cáo Tự Động - a.SENSE", page_icon="📊", layout="wide")

# CSS Customization (Font Lexend & B&W Theme)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700&display=swap');

* {
    font-family: 'Lexend', sans-serif;
}

/* Minimalist Cards */
div[data-testid="metric-container"] {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    padding: 1rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    border-radius: 8px;
}

/* Tweak alert boxes */
div[data-testid="stAlert"] {
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# --- DATA INGESTION ---
@st.cache_data(ttl=1800) # Cập nhật sau mỗi 30 phút
def load_data():
    current_day = datetime.now().day
    
    # T6 (Tháng Trước)
    df_june = pd.read_csv('DATA_CUSTOMERS_ALL.csv')
    df_june['Ngày'] = pd.to_datetime(df_june['Ngày'], format='%Y-%m-%d', errors='coerce').dt.normalize()
    df_june['Doanh thu'] = pd.to_numeric(df_june['Doanh thu'], errors='coerce').fillna(0)
    df_june['Tháng'] = 'Tháng Trước'
    
    # T7 (Tháng Hiện Tại)
    url = "https://script.google.com/macros/s/AKfycby8qd2tH4gAASBOIYrfJuWwnxF-PduCMgp-WZ0HNpGb5FYMiZj4umFA2SP-kw-Al7qJ/exec"
    res = requests.get(url)
    cust_raw = res.json()["DATA_CUSTOMERS_ECO"]
    df_july = pd.DataFrame(cust_raw[1:], columns=cust_raw[0])
    df_july['Doanh thu'] = pd.to_numeric(df_july['Doanh thu'], errors='coerce').fillna(0)
    df_july['Ngày'] = pd.to_datetime(df_july['Ngày'], errors='coerce', utc=True).dt.tz_convert('Asia/Ho_Chi_Minh').dt.tz_localize(None).dt.normalize()
    df_july['Tháng'] = 'Tháng Hiện Tại'
    
    # Lọc số ngày tương đương nhau (YTD) dựa trên ngày hôm nay
    df_june = df_june[(df_june['Ngày'].dt.day <= current_day) & (df_june['Mã cửa hàng'].isin(['L1 Landmark', 'Solforest']))].copy()
    df_july = df_july[(df_july['Ngày'].dt.day <= current_day) & (df_july['Mã cửa hàng'].isin(['L1 Landmark', 'Solforest']))].copy()
    
    # Category extraction
    def get_category(row):
        if str(row['Nhóm dịch vụ']).upper() == 'RETAIL': return 'Retail'
        note = str(row['Ghi chú']).lower()
        if pd.isna(row['Ghi chú']) or note == 'nan': return 'Khác'
        if any(k in note for k in ['nail', 'nhặt da', 'sơn gel', 'chà gót', 'tạo cầu', 'phá']): return 'Nails & Hand Care'
        if any(k in note for k in ['triệt', 'mép', 'nách']): return 'Triệt lông'
        if any(k in note for k in ['detox']): return 'Detox cổ vai gáy'
        if any(k in note for k in ['mặt nạ', 'tăng sáng', 'da tươi', 'vtm', 'mna', 'mạt nạ']): return 'Chăm sóc da mặt'
        if any(k in note for k in ['gội', 'ex', 'tls', 'sig', 'sạch sâu', 'thanh lọc', 'cân bằng', 'da đàu', '1m', 'tcb']): return 'Gội đầu / Hair Spa'
        return 'Khác'

    df_june['Danh mục'] = df_june.apply(get_category, axis=1)
    df_july['Danh mục'] = df_july.apply(get_category, axis=1)
    
    df_all = pd.concat([df_june, df_july], ignore_index=True)
    df_all['Day'] = df_all['Ngày'].dt.day
    return df_all, current_day

try:
    df_all, current_day = load_data()
except Exception as e:
    st.error(f"Lỗi tải dữ liệu: {e}")
    st.stop()

# --- TOP RAIL FILTERS ---
st.title("📊 BÁO CÁO KINH DOANH VÀ ĐIỂM NGHẼN VẬN HÀNH")

with st.expander("🎛️ BỘ LỌC DỮ LIỆU", expanded=True):
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        selected_stores = st.multiselect("🏪 Cơ Sở", df_all['Mã cửa hàng'].unique(), default=df_all['Mã cửa hàng'].unique())
    with f_col2:
        selected_categories = st.multiselect("📂 Danh Mục", df_all['Danh mục'].unique(), default=df_all['Danh mục'].unique())
    with f_col3:
        selected_nhom_dv = st.multiselect("🏷️ Nhóm Dịch Vụ", df_all['Nhóm dịch vụ'].unique(), default=df_all['Nhóm dịch vụ'].unique())

# Lọc dữ liệu
df_filtered = df_all[
    (df_all['Mã cửa hàng'].isin(selected_stores)) & 
    (df_all['Danh mục'].isin(selected_categories)) & 
    (df_all['Nhóm dịch vụ'].isin(selected_nhom_dv))
]

df_t6 = df_filtered[df_filtered['Tháng'] == 'Tháng Trước']
df_t7 = df_filtered[df_filtered['Tháng'] == 'Tháng Hiện Tại']

# --- NỘI DUNG CHÍNH ---

# Tầng 1: Chỉ số đo lường
st.subheader(f"1️⃣ TỔNG QUAN CHỈ SỐ (So sánh {current_day} ngày đầu tháng)")

col1, col2, col3, col4 = st.columns(4)
rev_t6, rev_t7 = df_t6['Doanh thu'].sum(), df_t7['Doanh thu'].sum()
cust_t6, cust_t7 = df_t6['Khách hàng'].nunique(), df_t7['Khách hàng'].nunique()
turns_t6, turns_t7 = len(df_t6), len(df_t7)
aov_t6 = rev_t6 / turns_t6 if turns_t6 > 0 else 0
aov_t7 = rev_t7 / turns_t7 if turns_t7 > 0 else 0

def get_delta(t6, t7):
    if t6 == 0: return "+N/A"
    return f"{(t7 - t6) / t6 * 100:.1f}%"

col1.metric("Tổng Doanh Thu", f"{rev_t7:,.0f} đ", get_delta(rev_t6, rev_t7))
col2.metric("Số Lượng Khách Hàng", f"{cust_t7}", get_delta(cust_t6, cust_t7))
col3.metric("Số Lượt Phục Vụ", f"{turns_t7}", get_delta(turns_t6, turns_t7))
col4.metric("Giá Trị Trung Bình/Khách", f"{aov_t7:,.0f} đ", get_delta(aov_t6, aov_t7))

st.markdown("---")

# Tầng 2: Góc nhìn chuyên sâu (Insight) & Hành động
st.subheader("2️⃣ ĐIỂM ĐÒN BẨY & HÀNH ĐỘNG ƯU TIÊN")
col_a, col_b = st.columns(2)
# Logic phân tích Realtime
insight_text = "**🔴 VẤN ĐỀ VẬN HÀNH (REALTIME):**\n"
action_text = "**🟢 HÀNH ĐỘNG ƯU TIÊN (REALTIME):**\n"
has_error = False

if cust_t7 > cust_t6 and aov_t7 < aov_t6:
    has_error = True
    insight_text += f"1. **Nghịch lý dòng khách:** Khách tăng nhưng AOV giảm (chỉ còn {aov_t7:,.0f}đ). Dấu hiệu KTV chỉ chốt dịch vụ mồi giá rẻ.\n"
    action_text += f"👉 **Cấp bách:** Thưởng nóng hoa hồng cho KTV Upsale thành công hóa đơn trên {aov_t6:,.0f}đ.\n"
elif cust_t7 < cust_t6 and rev_t7 < rev_t6:
    has_error = True
    insight_text += "1. **Báo động đỏ:** Vừa mất khách, vừa mất doanh thu so với cùng kỳ. Trạng thái kinh doanh đang co hẹp.\n"
    action_text += "👉 **Cấp bách:** Khởi động Telesale gọi điện tặng Voucher 50% cho tập khách chưa quay lại trong 30 ngày.\n"
elif rev_t7 > rev_t6 and aov_t7 > aov_t6:
    insight_text = "**🟢 ĐIỂM SÁNG VẬN HÀNH (REALTIME):**\n"
    insight_text += "1. **Tăng trưởng bền vững:** Doanh thu và AOV đều tăng trưởng ấn tượng.\n"
    action_text += "👉 **Phát huy:** Đổ thêm 20% ngân sách Marketing vào các phễu chiến dịch đang mang lại lượng khách giá trị cao này.\n"
else:
    insight_text = "**🟡 TRẠNG THÁI ỔN ĐỊNH (REALTIME):**\n"
    insight_text += "1. **Chưa có biến động bất thường:** Các chỉ số cơ bản đang đi ngang hoặc biến động nhẹ.\n"
    action_text += "👉 **Hành động:** Duy trì quy trình hiện tại, theo dõi sát sao tỷ lệ Upsale của KTV trong các ca đông khách.\n"

# Kiểm tra số lượt phục vụ
if turns_t7 < turns_t6 and aov_t7 > aov_t6:
    has_error = True
    insight_text += f"2. **Tín hiệu chững:** Số lượt phục vụ giảm mạnh so với cùng kỳ tháng trước ({turns_t7} vs {turns_t6}).\n"
    action_text += "👉 **Phòng ngừa:** Rà soát lại việc xếp ca của KTV, tránh tình trạng khách đến không có người làm phải quay về.\n"

with col_a:
    if has_error:
        st.error(insight_text)
    elif "🟢" in insight_text:
        st.success(insight_text)
    else:
        st.warning(insight_text)
with col_b:
    st.info(action_text)

st.markdown("---")

# Tầng 3: Biểu đồ phân tích (2x2 Grid)
st.subheader("3️⃣ PHÂN TÍCH ĐIỂM NGHẼN (Trực quan hóa)")

c1, c2 = st.columns(2)

with c1:
    daily_rev = df_filtered.groupby(['Tháng', 'Day'])['Doanh thu'].sum().reset_index()
    fig1 = px.line(daily_rev, x='Day', y='Doanh thu', color='Tháng', markers=True, text='Doanh thu',
                   title="So Sánh Doanh Thu Theo Từng Ngày",
                   color_discrete_map={'Tháng Trước': '#94A3B8', 'Tháng Hiện Tại': '#3B82F6'})
    fig1.update_traces(textposition="top center", texttemplate='%{text:.2s}', line=dict(width=3), marker=dict(size=8))
    fig1.update_layout(font_family="Lexend", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig1, use_container_width=True)

with c2:
    cat_rev = df_filtered.groupby(['Tháng', 'Danh mục'])['Doanh thu'].sum().reset_index()
    fig3 = px.bar(cat_rev, x='Danh mục', y='Doanh thu', color='Tháng', barmode='group', text_auto='.2s',
                  title="Doanh Thu Theo Dịch Vụ Trọng Điểm",
                  color_discrete_map={'Tháng Trước': '#94A3B8', 'Tháng Hiện Tại': '#3B82F6'})
    fig3.update_layout(font_family="Lexend", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig3, use_container_width=True)

c3, c4 = st.columns(2)

with c3:
    mix_rev = df_filtered.groupby(['Tháng', 'Nhóm dịch vụ'])['Doanh thu'].sum().reset_index()
    fig2 = px.bar(mix_rev, x='Nhóm dịch vụ', y='Doanh thu', color='Tháng', barmode='group', text_auto='.2s',
                  title="Sự Dịch Chuyển Từ Mua Gói Sang Mua Lẻ",
                  color_discrete_map={'Tháng Trước': '#94A3B8', 'Tháng Hiện Tại': '#3B82F6'})
    fig2.update_layout(font_family="Lexend", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig2, use_container_width=True)

with c4:
    p1, p2 = st.columns(2)
    cat_colors = {
        'Gội đầu / Hair Spa': '#88CCEE',
        'Detox cổ vai gáy': '#CC6677',
        'Chăm sóc da mặt': '#117733',
        'Triệt lông': '#DDCC77',
        'Nails & Hand Care': '#332288',
        'Retail': '#AA4499',
        'Khác': '#44AA99'
    }
    with p1:
        fig_pie_t6 = px.pie(df_t6, values='Doanh thu', names='Danh mục', color='Danh mục', title='Tỷ Trọng (Tháng Trước)', hole=0.4,
                            color_discrete_map=cat_colors)
        fig_pie_t6.update_traces(textposition='inside', textinfo='percent', marker=dict(line=dict(color='#FFFFFF', width=1)))
        fig_pie_t6.update_layout(font_family="Lexend", showlegend=True, legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5), margin=dict(t=30, b=120, l=0, r=0))
        st.plotly_chart(fig_pie_t6, use_container_width=True)
    with p2:
        fig_pie_t7 = px.pie(df_t7, values='Doanh thu', names='Danh mục', color='Danh mục', title='Tỷ Trọng (Tháng Hiện Tại)', hole=0.4,
                            color_discrete_map=cat_colors)
        fig_pie_t7.update_traces(textposition='inside', textinfo='percent', marker=dict(line=dict(color='#FFFFFF', width=1)))
        fig_pie_t7.update_layout(font_family="Lexend", showlegend=True, legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5), margin=dict(t=30, b=120, l=0, r=0))
        st.plotly_chart(fig_pie_t7, use_container_width=True)

st.markdown("---")

# Tầng 4: Bảng dữ liệu
st.subheader("4️⃣ DỮ LIỆU CHI TIẾT")
st.dataframe(df_filtered.sort_values(by='Ngày', ascending=False).astype(str), use_container_width=True)
