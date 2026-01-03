import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components
from streamlit_option_menu import option_menu
import urllib.parse
from datetime import datetime, date, timedelta
import pytz
import requests
import plotly.express as px
import time
import random

# --- THƯ VIỆN ĐỊNH DẠNG SHEET ---
from gspread_formatting import *

# ================= CẤU HÌNH HỆ THỐNG =================
st.set_page_config(page_title="PHÒNG NỘI DUNG SỐ & TRUYỀN THÔNG", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")

# --- CSS TÙY CHỈNH: GIAO DIỆN GỌN & FONT CHUẨN ---
st.markdown("""
<style>
    /* Font hệ thống chuẩn cho tiếng Việt */
    * {
        font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    
    /* Chỉnh Sidebar gọn gàng */
    [data-testid="stSidebar"] { padding-top: 1rem; background-color: #f8f9fa; }
    [data-testid="stSidebar"] .block-container { padding-top: 0rem; }
    
    /* Card User Gọn */
    .user-compact {
        background-color: #e8f5e9;
        padding: 8px 12px;
        border-radius: 6px;
        border-left: 4px solid #2e7d32;
        margin-bottom: 5px;
        color: #1b5e20;
        font-weight: 700;
        font-size: 14px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }

    /* Tiêu đề chính */
    .main-header {
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        color: #005bea;
    }
    
    /* Radio button ngày tháng: Không ngắt dòng */
    div[role="radiogroup"] label > div:first-child {
        display: flex; align-items: center; white-space: nowrap !important;
    }
</style>
""", unsafe_allow_html=True)

# --- LIÊN KẾT GOOGLE SHEET ---
SHEET_MAIN = "HeThongQuanLy" 
SHEET_TRUCSO = "VoTrucSo"
LINK_VO_TRUC_SO = "https://docs.google.com/spreadsheets/d/1lsm4FxTPMTmDbc50xq5ldbtCb7PIc-gbk5PMLHdzu7Y/edit?usp=sharing"
LINK_LICH_TONG = "https://docs.google.com/spreadsheets/d/1jqPGEVTA7RfvTnV8rN6FSpRJFWXS7amVIAFQ0QqzXbI/edit?usp=sharing"

def get_vn_time(): return datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))

def get_short_name(full_name):
    if not full_name or full_name == "--" or str(full_name).strip() == "": return "..."
    parts = full_name.strip().split()
    return " ".join(parts[-2:]) if len(parts) >= 2 else full_name

# --- KHO LỜI KHUYÊN ---
ADVICE_LIST = [
    "Chúc bạn một ngày làm việc thật năng suất và hiệu quả!",
    "Hãy nhớ uống đủ nước và vận động nhẹ nhàng để giữ gìn sức khỏe nhé.",
    "Một nụ cười bằng mười thang thuốc bổ, hãy cười nhiều lên nhé!",
    "Tập trung giải quyết việc khó nhất trước, bạn sẽ thấy nhẹ nhõm hơn rất nhiều.",
    "Đừng quên dành ít phút nghỉ ngơi cho đôi mắt sau mỗi giờ làm việc căng thẳng.",
    "Chúc bạn có những ý tưởng đột phá và sáng tạo trong công việc hôm nay.",
    "Sự tỉ mỉ trong từng chi tiết nhỏ sẽ tạo nên chất lượng công việc tuyệt vời.",
    "Hôm nay là một ngày tuyệt vời để hoàn thành các mục tiêu đã đề ra!",
    "Giữ vững đam mê, thành công sẽ luôn theo đuổi bạn."
]

@st.cache_data(ttl=3600)
def get_weather_and_advice():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=21.0285&longitude=105.8542&current_weather=true&timezone=Asia%2FBangkok"
        res = requests.get(url, timeout=2).json()
        temp = res['current_weather']['temperature']; wcode = res['current_weather']['weathercode']
        cond = "Có mây"
        if wcode in [0, 1]: cond = "Nắng đẹp ☀️"
        elif wcode in [2, 3]: cond = "Nhiều mây ☁️"
        elif wcode in [51, 53, 55, 61, 63, 65]: cond = "Có mưa 🌧️"
        elif wcode >= 95: cond = "Giông bão ⛈️"
        advice = random.choice(ADVICE_LIST)
        return f"{temp}°C - {cond}", advice
    except: return "Hà Nội", "Luôn giữ vững đam mê nghề báo bạn nhé!"

# --- CẤU HÌNH ---
ROLES_HEADER = ["LÃNH ĐẠO BAN", "TRỰC THƯ KÝ TÒA SOẠN", "TRỰC QUẢN TRỊ MXH + VIDEO BIÊN TẬP", "TRỰC LỊCH PHÁT SÓNG", "TRỰC THƯ KÝ TÒA SOẠN", "TRỰC SẢN XUẤT VIDEO CLIP, LPS", "TRỰC QUẢN TRỊ CỔNG TTĐT", "TRỰC QUẢN TRỊ APP"]
OPTS_DINH_DANG = ["Bài dịch", "Video biên tập", "Sản phẩm sản xuất"]
OPTS_NEN_TANG = ["Facebook", "Youtube", "TikTok", "Web + App", "Instagram"]
OPTS_STATUS_TRUCSO = ["Chờ xử lý", "Đang biên tập", "Gửi duyệt TCSX", "Yêu cầu sửa (TCSX)", "Gửi duyệt LĐP", "Yêu cầu sửa (LĐP)", "Đã duyệt/Chờ đăng", "Đã đăng", "Hủy"]
OPTS_TRANG_THAI_VIEC = ["Đã giao", "Đang thực hiện", "Chờ duyệt", "Hoàn thành", "Hủy"]
CONTENT_HEADER = ["STT", "NỘI DUNG", "ĐỊNH DẠNG", "NỀN TẢNG", "STATUS", "CHECK", "NGUỒN", "NHÂN SỰ", "Ý KIẾN ĐIỀU CHỈNH", "LINK DUYỆT", "GIỜ ĐĂNG", "NGÀY ĐĂNG", "LINK SẢN PHẨM"]

# --- TỪ ĐIỂN HIỂN THỊ (SỬA LỖI NAME ERROR) ---
VN_COLS_VIEC = {"TenViec": "Tên công việc", "DuAn": "Dự án", "Deadline": "Hạn chót", "NguoiPhuTrach": "Người thực hiện", "TrangThai": "Trạng thái", "LinkBai": "Link SP", "GhiChu": "Ghi chú"}
VN_COLS_TRUCSO = {"STT": "STT", "NỘI DUNG": "Nội dung", "ĐỊNH DẠNG": "Định dạng", "NỀN TẢNG": "Nền tảng", "STATUS": "Trạng thái", "NGUỒN": "Nguồn", "NHÂN SỰ": "Nhân sự", "Ý KIẾN ĐIỀU CHỈNH": "Ý kiến", "LINK DUYỆT": "Link Duyệt", "GIỜ ĐĂNG": "Giờ đăng", "NGÀY ĐĂNG": "Ngày đăng", "LINK SẢN PHẨM": "Link SP"}
VN_COLS_DUAN = {"TenDuAn": "Tên Dự án", "MoTa": "Mô tả", "TrangThai": "Trạng thái", "TruongNhom": "Điều phối"} # Đã thêm dòng này
VN_COLS_LOG = {"ThoiGian": "Thời gian", "NguoiDung": "Người dùng", "HanhDong": "Hành động", "ChiTiet": "Chi tiết"}

# --- BACKEND ---
@st.cache_resource(ttl=3600)
def get_gspread_client_cached():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets: creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        else: creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
        return gspread.authorize(creds)
    except: return None

def ket_noi_sheet(url):
    client = get_gspread_client_cached()
    if not client: return None
    try: return client.open_by_url(url) if "http" in url else client.open(url)
    except: return None

def safe_read_records(wks):
    for i in range(3):
        try: return pd.DataFrame(wks.get_all_records())
        except: time.sleep(1)
    return pd.DataFrame()

def safe_read_values(wks):
    for i in range(3):
        try:
            data = wks.get_all_values()
            if len(data) > 4: return pd.DataFrame(data[4:], columns=data[3])
            return pd.DataFrame(columns=CONTENT_HEADER)
        except: time.sleep(1)
    return pd.DataFrame(columns=CONTENT_HEADER)

@st.cache_data(ttl=600)
def load_all_data():
    try:
        sh = ket_noi_sheet(SHEET_MAIN)
        df_u = safe_read_records(sh.worksheet("TaiKhoan"))
        df_d = safe_read_records(sh.worksheet("DuAn"))
        df_c = safe_read_records(sh.worksheet("CongViec"))
        try: wks_cn = sh.worksheet("ViecCaNhan"); df_cn = safe_read_records(wks_cn)
        except: df_cn = pd.DataFrame()
        try: wks_nk = sh.worksheet("NhatKy"); df_nk = safe_read_records(wks_nk)
        except: df_nk = pd.DataFrame()
        return df_u, df_d, df_c, df_cn, df_nk
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def clear_cache_and_rerun(): st.cache_data.clear(); st.rerun()

def ghi_nhat_ky(sh_main, nguoi, hanh_dong, chi_tiet):
    try: sh_main.worksheet("NhatKy").append_row([get_vn_time().strftime("%H:%M %d/%m/%Y"), nguoi, hanh_dong, chi_tiet])
    except: pass

def check_quyen(current_user, role, row, df_da):
    if role == 'LanhDao': return 2
    if str(row.get('NguoiTao','')).strip() == current_user: return 2
    try:
        leads = str(df_da[df_da['TenDuAn']==row['DuAn']].iloc[0]['TruongNhom'])
        if current_user in leads: return 2
    except: pass
    if current_user in str(row.get('NguoiPhuTrach','')): return 1
    return 0

def lay_nhan_su_tu_lich_phuc_tap(target_date_obj):
    try:
        if "docs.google.com" not in LINK_LICH_TONG: return [], []
        sh_lich = ket_noi_sheet(LINK_LICH_TONG); wks_lich = sh_lich.get_worksheet(0); data = wks_lich.get_all_values()
        target_str = target_date_obj.strftime("%d/%m/%Y")
        found_col_idx = -1; found_row_idx = -1 
        for r_idx, row in enumerate(data):
            for c_idx, cell_val in enumerate(row):
                if target_str in str(cell_val).strip(): found_row_idx = r_idx; found_col_idx = c_idx; break
            if found_row_idx != -1: break
        if found_row_idx == -1: return [], []
        list_tcsx = []; list_btv = []; scan_range = 40; current_row = found_row_idx + 1
        while current_row < len(data) and current_row < found_row_idx + scan_range:
            row_data = data[current_row]
            if len(row_data) > found_col_idx:
                cell_val = str(row_data[found_col_idx]).strip().lower()
                is_working = False; is_tcsx = False
                if "tcsx" in cell_val: is_working = True; is_tcsx = True
                elif "trực số" in cell_val or cell_val == "x": is_working = True
                if is_working:
                    name = ""
                    if len(row_data) > 1: name = row_data[1].strip()
                    if name and name != "--":
                        if is_tcsx: list_tcsx.append(name)
                        else: list_btv.append(name)
            current_row += 1
        return list_tcsx, list_btv
    except: return [], []

def dinh_dang_dep(wks):
    wks.merge_cells('A1:M1')
    format_cell_range(wks, 'A1:M1', CellFormat(backgroundColor=Color(0, 1, 1), textFormat=TextFormat(bold=True, fontSize=14), horizontalAlignment='CENTER', verticalAlignment='MIDDLE'))
    format_cell_range(wks, 'A2:M3', CellFormat(textFormat=TextFormat(bold=True), horizontalAlignment='CENTER', verticalAlignment='MIDDLE', wrapStrategy='WRAP', borders=Borders(top=Border("SOLID"), bottom=Border("SOLID"), left=Border("SOLID"), right=Border("SOLID"))))
    format_cell_range(wks, 'A2:M2', CellFormat(backgroundColor=Color(0.8, 1, 1)))
    format_cell_range(wks, 'A4:M4', CellFormat(backgroundColor=Color(1, 1, 0), textFormat=TextFormat(bold=True), horizontalAlignment='CENTER', verticalAlignment='MIDDLE', wrapStrategy='WRAP', borders=Borders(top=Border("SOLID"), bottom=Border("SOLID"), left=Border("SOLID"), right=Border("SOLID"))))
    set_column_width(wks, 'A', 40); set_column_width(wks, 'B', 300); set_column_width(wks, 'C', 100); set_column_width(wks, 'D', 100)
    set_column_width(wks, 'E', 130); set_column_width(wks, 'F', 50); set_column_width(wks, 'G', 80); set_column_width(wks, 'H', 120)
    set_column_width(wks, 'I', 120); set_column_width(wks, 'J', 100); set_column_width(wks, 'K', 70); set_column_width(wks, 'L', 80); set_column_width(wks, 'M', 100)
    format_cell_range(wks, 'B5:B100', CellFormat(wrapStrategy='WRAP', verticalAlignment='TOP'))

def dinh_dang_dong_moi(wks, row_idx):
    rng = f"A{row_idx}:M{row_idx}"
    format_cell_range(wks, rng, CellFormat(wrapStrategy='WRAP', verticalAlignment='TOP', borders=Borders(top=Border("SOLID"), bottom=Border("SOLID"), left=Border("SOLID"), right=Border("SOLID"))))

# ================= AUTH =================
if 'dang_nhap' not in st.session_state: st.session_state['dang_nhap'] = False; st.session_state['user_info'] = {}
sh_main = ket_noi_sheet(SHEET_MAIN)

df_users, df_duan, df_cv, df_cn, df_log = load_all_data()
list_duan = df_duan['TenDuAn'].tolist() if not df_duan.empty else []
list_nv = df_users['HoTen'].tolist() if not df_users.empty else []

if not st.session_state['dang_nhap']:
    st.markdown("## 🔐 CỔNG ĐĂNG NHẬP")
    with st.form("login"):
        user = st.text_input("Tên đăng nhập"); pwd = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("ĐĂNG NHẬP"):
            if not df_users.empty:
                u_row = df_users[(df_users['TenDangNhap'].astype(str)==user) & (df_users['MatKhau'].astype(str)==pwd)]
                if not u_row.empty:
                    st.session_state['dang_nhap'] = True; st.session_state['user_info'] = u_row.iloc[0].to_dict()
                    ghi_nhat_ky(sh_main, u_row.iloc[0]['HoTen'], "Đăng nhập", "Success"); clear_cache_and_rerun()
                else: st.error("Sai thông tin!")
            else: st.error("Lỗi dữ liệu Tài khoản.")
else:
    u_info = st.session_state['user_info']; curr_name = u_info['HoTen']; curr_username = str(u_info['TenDangNhap']); role = u_info.get('VaiTro', 'NhanVien')
    
    # --- SIDEBAR COMPACT ---
    with st.sidebar:
        st.markdown(f'<div class="user-compact">👤 {curr_name.upper()}</div>', unsafe_allow_html=True)
        if st.button("🔄 LÀM MỚI DỮ LIỆU", type="primary", use_container_width=True): clear_cache_and_rerun()
        
        selected_menu = option_menu(
            None,
            ["Checklist Cá Nhân", "Quản Lý Công Việc", "Quản Lý Dự Án", "Trực Số", "Lịch Làm Việc", "Email", "Dashboard", "Nhật Ký"] if role == 'LanhDao' else ["Checklist Cá Nhân", "Quản Lý Công Việc", "Quản Lý Dự Án", "Trực Số", "Lịch Làm Việc", "Email"],
            icons=["check-square", "list-task", "folder", "pencil-square", "calendar-week", "envelope", "graph-up", "clock-history"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#f8f9fa", "margin-top": "10px"},
                "nav-link": {"font-size": "14px", "margin": "2px", "padding": "10px 12px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#0072ff"},
            }
        )
        
        st.markdown("---")
        w_info, advice = get_weather_and_advice()
        st.caption(f"**{w_info}**")
        st.info(f"💡 {advice}")
        
        with st.expander("🔐 Đổi Mật Khẩu"):
            with st.form("change_pass"):
                old_p = st.text_input("Mật khẩu cũ", type="password"); new_p = st.text_input("Mật khẩu mới", type="password")
                if st.form_submit_button("Lưu"):
                    if old_p == str(u_info['MatKhau']):
                        wks_acc = sh_main.worksheet("TaiKhoan"); cell = wks_acc.find(curr_username)
                        if cell: wks_acc.update_cell(cell.row, 2, new_p); st.session_state['user_info']['MatKhau'] = new_p; st.success("Xong!")
                    else: st.error("Sai MK!")
        
        if st.button("Đăng xuất", use_container_width=True): st.session_state['dang_nhap'] = False; st.rerun()

    # --- MAIN CONTENT ---
    st.markdown('<div class="main-header">🏢 PHÒNG NỘI DUNG SỐ & TRUYỀN THÔNG</div>', unsafe_allow_html=True)
    sh_trucso = ket_noi_sheet(SHEET_TRUCSO)

    # 1. CHECKLIST
    if selected_menu == "Checklist Cá Nhân":
        st.subheader(f"✅ CHECKLIST CỦA: {curr_name.upper()}")
        try: wks_canhan = sh_main.worksheet("ViecCaNhan")
        except: wks_canhan = sh_main.add_worksheet("ViecCaNhan", 1000, 5); wks_canhan.append_row(["User", "TenViec", "Ngay", "TrangThai", "GhiChu"])
        
        c1, c2 = st.columns([1, 3]); view_mode = c1.radio("Xem:", ["Hôm nay", "Tuần này", "Tháng này"], horizontal=True)
        today = date.today(); my_tasks = [t for t in df_cn.to_dict('records') if str(t.get('User')) == curr_name]
        
        filtered = []
        for t in my_tasks:
            try:
                t_date = datetime.strptime(t['Ngay'], "%d/%m/%Y").date()
                if view_mode == "Hôm nay" and t_date == today: filtered.append(t)
                elif view_mode == "Tuần này" and today - timedelta(days=today.weekday()) <= t_date <= today + timedelta(days=6-today.weekday()): filtered.append(t)
                elif view_mode == "Tháng này" and t_date.month == today.month and t_date.year == today.year: filtered.append(t)
            except: pass
        
        if filtered:
            df_v = pd.DataFrame(filtered); df_v['Xong'] = df_v['TrangThai'].apply(lambda x: str(x).upper() == "TRUE")
            edited = st.data_editor(df_v[['TenViec', 'Ngay', 'GhiChu', 'Xong']], column_config={"Xong": st.column_config.CheckboxColumn("Hoàn thành", default=False), "TenViec": st.column_config.TextColumn("Nội dung", width="large"), "Ngay": st.column_config.TextColumn("Ngày", disabled=True), "GhiChu": st.column_config.TextColumn("Ghi chú")}, hide_index=True, key="ed_chk", use_container_width=True)
            if st.button("💾 CẬP NHẬT TRẠNG THÁI"):
                with st.spinner("Đang lưu..."):
                    vals = wks_canhan.get_all_values()
                    for i, r in edited.iterrows():
                        for idx, s_r in enumerate(vals):
                            if idx==0: continue
                            if s_r[0]==curr_name and s_r[1]==r['TenViec'] and s_r[2]==r['Ngay']:
                                wks_canhan.update_cell(idx+1, 4, "TRUE" if r['Xong'] else "FALSE"); wks_canhan.update_cell(idx+1, 5, r['GhiChu']); break
                    st.success("Xong!"); clear_cache_and_rerun()
        else: st.info("Chưa có việc.")
        
        st.divider()
        with st.expander("🛠️ QUẢN LÝ CHI TIẾT (THÊM / SỬA / XÓA)", expanded=False):
            all_df = pd.DataFrame(my_tasks)
            if not all_df.empty:
                all_df['TrangThai'] = all_df['TrangThai'].apply(lambda x: str(x).upper() == "TRUE")
                ed_full = st.data_editor(all_df[['TenViec', 'Ngay', 'TrangThai', 'GhiChu']], column_config={"TrangThai": st.column_config.CheckboxColumn("Xong"), "TenViec": st.column_config.TextColumn("Tên việc", width="large")}, num_rows="dynamic", use_container_width=True, key="ed_full")
                if st.button("💾 LƯU TOÀN BỘ"):
                    with st.spinner("Đang lưu..."):
                        full = wks_canhan.get_all_values(); head = full[0]; others = [r for r in full[1:] if r[0] != curr_name]
                        new_data = [[curr_name, r.get('TenViec'), r.get('Ngay', today.strftime("%d/%m/%Y")), "TRUE" if r.get('TrangThai') else "FALSE", r.get('GhiChu','')] for i, r in ed_full.iterrows() if r.get('TenViec')]
                        wks_canhan.clear(); wks_canhan.update([head] + others + new_data); st.success("Xong!"); clear_cache_and_rerun()
            else:
                ed_new = st.data_editor(pd.DataFrame(columns=['TenViec', 'Ngay', 'TrangThai', 'GhiChu']), num_rows="dynamic", key="ed_new")
                if st.button("LƯU MỚI"):
                    for i, r in ed_new.iterrows(): 
                        if r.get('TenViec'): wks_canhan.append_row([curr_name, r['TenViec'], today.strftime("%d/%m/%Y"), "FALSE", r.get('GhiChu','')])
                    st.success("Xong!"); clear_cache_and_rerun()

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            with st.form("q_add"):
                n_ten = st.text_input("Nội dung"); n_ngay = st.date_input("Ngày", value=today, format="DD/MM/YYYY")
                if st.form_submit_button("THÊM NHANH"):
                    if n_ten: wks_canhan.append_row([curr_name, n_ten, n_ngay.strftime("%d/%m/%Y"), "FALSE", ""]); st.success("Xong!"); clear_cache_and_rerun()
        with c2:
            st.markdown("#### 📥 GẮP TỪ VIỆC CHUNG")
            if not df_cv.empty:
                my_cv = df_cv[df_cv['NguoiPhuTrach'].astype(str).str.contains(curr_name, case=False, na=False)]
                if not my_cv.empty:
                    sel = st.selectbox("Việc được giao:", [f"{r['TenViec']} ({r['Deadline']})" for i, r in my_cv.iterrows()])
                    if st.button("GẮP SANG CHECKLIST"):
                        tn = sel.split(" (")[0]; r = my_cv[my_cv['TenViec']==tn].iloc[0]; dl = today.strftime("%d/%m/%Y")
                        try: dl = r['Deadline'].split(" ")[1]
                        except: pass
                        wks_canhan.append_row([curr_name, tn, dl, "FALSE", "Từ hệ thống"]); st.success("Xong!"); clear_cache_and_rerun()

    # 2. CÔNG VIỆC
    elif selected_menu == "Quản Lý Công Việc":
        st.subheader("📋 QUẢN LÝ CÔNG VIỆC")
        with st.expander("➕ TẠO VIỆC MỚI", expanded=False):
            c1, c2 = st.columns(2)
            ten = c1.text_input("TÊN VIỆC"); da = c1.selectbox("DỰ ÁN", list_duan)
            dl_t = c1.time_input("GIỜ"); dl_d = c1.date_input("NGÀY", format="DD/MM/YYYY")
            nguoi = c2.multiselect("NGƯỜI LÀM", list_nv); ghi = c2.text_area("YÊU CẦU", height=100)
            opt_mail = st.checkbox("Gửi Email", True); tk_mail = st.selectbox("TK Gửi:", range(10), format_func=lambda x:f"TK {x}")
            if st.button("LƯU"):
                with st.spinner("Đang lưu..."):
                    sh_main.worksheet("CongViec").append_row([ten, da, f"{dl_t.strftime('%H:%M')} {dl_d.strftime('%d/%m/%Y')}", ", ".join(nguoi), "Đã giao", "", ghi, curr_name])
                    if opt_mail and nguoi:
                        ms = [m for m in df_users[df_users['HoTen'].isin(nguoi)]['Email'].tolist() if str(m).strip()]
                        if ms: st.markdown(f'<script>window.open("https://mail.google.com/mail/u/{tk_mail}/?view=cm&fs=1&to={",".join(ms)}&su={urllib.parse.quote(ten)}&body={urllib.parse.quote(ghi)}", "_blank");</script>', unsafe_allow_html=True)
                    st.success("Xong!"); clear_cache_and_rerun()
        
        st.divider(); da_f = st.selectbox("LỌC DỰ ÁN:", ["-- TẤT CẢ --"]+list_duan)
        if not df_cv.empty:
            df_d = df_cv[df_cv['DuAn']==da_f] if da_f != "-- TẤT CẢ --" else df_cv
            edits = {f"{r['TenViec']} ({i+2})": {"id":i, "lv":check_quyen(curr_name, role, r, df_duan)} for i, r in df_d.iterrows() if check_quyen(curr_name, role, r, df_duan)>0}
            if edits:
                with st.expander("🛠️ CẬP NHẬT TRẠNG THÁI", expanded=True):
                    s = st.selectbox("CHỌN VIỆC:", list(edits.keys()))
                    if s:
                        rd = df_d.iloc[edits[s]['id']]; dis = (edits[s]['lv']==1)
                        with st.form("fe"):
                            c1, c2 = st.columns(2)
                            et = c1.text_input("TÊN", rd['TenViec'], disabled=dis); en = c1.text_input("NGƯỜI LÀM", rd['NguoiPhuTrach'], disabled=dis)
                            el = c1.text_input("LINK SP", rd.get('LinkBai','')); edl = c2.text_input("DEADLINE", rd['Deadline'], disabled=dis)
                            es = c2.selectbox("TRẠNG THÁI", OPTS_TRANG_THAI_VIEC, index=OPTS_TRANG_THAI_VIEC.index(rd.get('TrangThai','Đã giao')) if rd.get('TrangThai') in OPTS_TRANG_THAI_VIEC else 0)
                            enote = c2.text_area("GHI CHÚ", rd.get('GhiChu',''))
                            if st.form_submit_button("CẬP NHẬT"):
                                w = sh_main.worksheet("CongViec"); cell = w.find(rd['TenViec'])
                                if cell:
                                    r = cell.row; w.update_cell(r,1,et); w.update_cell(r,3,edl); w.update_cell(r,4,en); w.update_cell(r,5,es); w.update_cell(r,6,el); w.update_cell(r,7,enote)
                                    st.success("Xong!"); clear_cache_and_rerun()
            st.dataframe(df_d.drop(columns=['NguoiTao'], errors='ignore').rename(columns=VN_COLS_VIEC), use_container_width=True, hide_index=True)
        else: st.info("Trống.")

    # 3. DỰ ÁN
    elif selected_menu == "Quản Lý Dự Án":
        st.subheader("🗂️ QUẢN LÝ DỰ ÁN")
        if role == 'LanhDao':
            with st.form("nda"):
                n = st.text_input("TÊN"); m = st.text_area("MÔ TẢ"); l = st.multiselect("PHỤ TRÁCH", list_nv)
                if st.form_submit_button("TẠO"): sh_main.worksheet("DuAn").append_row([n, m, "Đang chạy", ",".join(l)]); st.success("Xong!"); clear_cache_and_rerun()
        st.dataframe(df_duan.rename(columns=VN_COLS_DUAN), use_container_width=True)

    # 4. TRỰC SỐ
    elif selected_menu == "Trực Số":
        today = get_vn_time().date(); yest = today - timedelta(days=1); tom = today + timedelta(days=1)
        c1, c2 = st.columns([1, 4])
        with c1: 
            mode = st.radio("CHỌN NGÀY:", [f"Hôm qua ({yest.strftime('%d/%m')})", f"Hôm nay ({today.strftime('%d/%m')})", f"Ngày mai ({tom.strftime('%d/%m')})"], index=1, key="ts_nav")
        if "Hôm qua" in mode: td = yest
        elif "Ngày mai" in mode: td = tom
        else: td = today
        tab_name = td.strftime("%d-%m-%Y"); d_str = td.strftime("%d/%m/%Y")
        
        with c2: st.subheader(f"📝 TRỰC SỐ NGÀY: {tab_name}")
        
        is_admin = (role in ['LanhDao', 'ToChucSanXuat']); use_arc = False
        if is_admin:
            with st.expander("🗄️ TRA CỨU LỊCH SỬ (ARCHIVE)", expanded=False):
                try:
                    all_sheets = sh_trucso.worksheets(); sheet_titles = [s.title for s in all_sheets]
                    date_sheets = [t for t in sheet_titles if len(t.split('-')) == 3]; date_sheets.sort(reverse=True)
                    selected_archive = st.selectbox("CHỌN NGÀY CẦN XEM LẠI:", ["-- Chọn ngày --"] + date_sheets)
                    if selected_archive != "-- Chọn ngày --": tab_name_current = selected_archive; use_archive = True; st.info(f"ĐANG XEM DỮ LIỆU LƯU TRỮ NGÀY: {selected_archive}")
                except: pass

        exists = False
        try: wks_t = sh_trucso.worksheet(tab_name); exists = True
        except: exists = False

        if is_admin and not use_archive:
            with st.expander("⚙️ QUẢN LÝ VỎ / EKIP TRỰC", expanded=not exists):
                if not exists:
                    if td >= today:
                        st.warning("Chưa có sổ trực.")
                        atcsx, abtv = lay_nhan_su_tu_lich_phuc_tap(td); def_r = [""]*8
                        if atcsx: def_r[3] = atcsx[0]
                        random.shuffle(abtv)
                        if len(abtv)>0: def_r[2]=abtv[0]
                        if len(abtv)>1: def_r[6]=abtv[1]
                        if len(abtv)>2: def_r[7]=abtv[2]
                        
                        with st.form("init_vo"):
                            cs = st.columns(3); rv = []
                            for i, rt in enumerate(ROLES_HEADER):
                                with cs[i%3]: 
                                    idx = list_nv.index(def_r[i])+1 if def_r[i] in list_nv else 0
                                    rv.append(st.selectbox(f"**{rt}**", ["--"]+list_nv, index=idx, key=f"c_{i}"))
                            if st.form_submit_button("🚀 TẠO TRỰC SỐ MỚI"):
                                with st.spinner("Đang tạo vỏ..."):
                                    try:
                                        w = sh_trucso.add_worksheet(title=tab_name, rows=100, cols=20)
                                        w.update_cell(1,1,f"TRỰC SỐ {tab_name}"); w.update_cell(2,1,"DANH SÁCH:"); [w.update_cell(2,i+2,v) for i,v in enumerate(ROLES_HEADER)]
                                        w.update_cell(3,1,"NHÂN SỰ:"); [w.update_cell(3,i+2,v if v!="--" else "") for i,v in enumerate(rv)]
                                        w.append_row(CONTENT_HEADER); dinh_dang_dep(w); st.success("ĐÃ TẠO XONG!"); st.rerun()
                                    except Exception as e: st.error(str(e))
                    else: st.error("Không tìm thấy dữ liệu quá khứ.")
                else:
                    st.success("Đã có vỏ.")
                    try:
                        # --- KHÔI PHỤC LOGIC GỬI EMAIL ĐẦY ĐỦ ---
                        r_names = wks_t.row_values(3)[1:] # Lấy danh sách tên
                        clean_names = [n for n in r_names if n and n != "--" and n in list_nv]
                        
                        c_mail, c_zalo = st.columns(2)
                        with c_mail:
                            st.markdown("##### 📧 GỬI EMAIL TRÌNH DUYỆT")
                            tk_gui_vo = st.selectbox("CHỌN TÀI KHOẢN GỬI:", range(10), format_func=lambda x: f"TK {x} (Trên máy này)", key="mail_vo")
                            recipients = list(set([df_users[df_users['HoTen'] == n]['Email'].values[0] for n in clean_names if len(df_users[df_users['HoTen'] == n]['Email'].values) > 0]))
                            
                            name_ld = get_short_name(r_names[0] if len(r_names) > 0 else "")
                            name_tk = get_short_name(r_names[1] if len(r_names) > 1 else "")
                            name_sender = get_short_name(curr_name) 

                            email_sub = f"Trình duyệt Vỏ tin bài NDS Vietnam Today ngày {d_str}"
                            email_body = f"""Kính gửi chị {name_ld}, chị {name_tk}

Nhóm xin gửi các chị vỏ tin bài NDS ngày {d_str} trên các nền tảng.

Link: {LINK_VO_TRUC_SO}

Các chị xem giúp nhóm ạ.

Em xin cảm ơn các chị ạ!

Em {name_sender}"""
                            
                            if recipients:
                                link_mail = f"https://mail.google.com/mail/u/{tk_gui_vo}/?view=cm&fs=1&to={','.join(recipients)}&su={urllib.parse.quote(email_sub)}&body={urllib.parse.quote(email_body)}"
                                st.markdown(f'<a href="{link_mail}" target="_blank" style="background:#EA4335;color:white;padding:10px 15px;text-decoration:none;border-radius:5px;font-weight:bold;display:block;text-align:center;">🚀 SOẠN EMAIL NGAY</a>', unsafe_allow_html=True)
                                st.caption(f"Gửi tới: {', '.join(recipients)}")
                                st.markdown(f'<br><a href="https://mail.google.com/mail/u/{tk_gui_vo}" target="_blank">👉 Kiểm tra hộp thư gửi đi (Check Mail)</a>', unsafe_allow_html=True)
                            else: st.warning("Chưa tìm thấy email của ekip.")

                        with c_zalo:
                            st.markdown("##### 💬 GỬI QUA ZALO")
                            zalo_msg = f"🔔 *THÔNG BÁO LỊCH TRỰC SỐ*\n📅 NGÀY: {tab_name}\n------------------\n"
                            for i, name in enumerate(r_names):
                                if i < len(ROLES_HEADER) and name != "--": zalo_msg += f"🔹 {ROLES_HEADER[i]}: {name}\n"
                            zalo_msg += "------------------\n👉 Mời các anh/chị truy cập hệ thống để nhận nhiệm vụ."
                            st.text_area("NỘI DUNG (COPY):", value=zalo_msg, height=150)
                            st.link_button("🚀 MỞ ZALO WEB", "https://chat.zalo.me/")

                    except Exception as e: st.error(f"Lỗi tạo thông báo: {e}")
                    
                    st.divider()
                    with st.form("ed_vo"):
                        c = st.columns(3); nv = []
                        for i, rt in enumerate(ROLES_HEADER):
                            with c[i%3]: 
                                curr = r_names[i] if i < len(r_names) else ""
                                idx = list_nv.index(curr)+1 if curr in list_nv else 0
                                nv.append(st.selectbox(f"{rt}", ["--"]+list_nv, index=idx, key=f"e_{i}"))
                        if st.form_submit_button("CẬP NHẬT EKIP"):
                            for i, v in enumerate(nv): wks_t.update_cell(3, i+2, v if v!="--" else "")
                            st.success("Xong!"); st.rerun()

        if exists:
            with st.expander("ℹ️ EKIP TRỰC", expanded=True):
                try:
                    rn = wks_t.row_values(3)[1:] # Load lại tên mới nhất
                    rr = wks_t.row_values(2)[1:]
                    c = st.columns(4)
                    for i in range(4):
                        if i < len(rn): c[i].markdown(f"<small style='color:gray'>{rr[i]}</small><br><b>{rn[i]}</b>", unsafe_allow_html=True)
                    st.write("---"); c2 = st.columns(4)
                    for i in range(4):
                        idx = i+4
                        if idx < len(rn): c2[i].markdown(f"<small style='color:gray'>{rr[idx]}</small><br><b>{rn[idx]}</b>", unsafe_allow_html=True)
                except: st.caption("Lỗi đọc ekip.")

            with st.form("add_n"):
                c1, c2 = st.columns([3, 1]); nd = c1.text_area("NỘI DUNG"); dd = c2.selectbox("ĐỊNH DẠNG", OPTS_DINH_DANG)
                c3, c4, c5 = st.columns(3); nt = c3.multiselect("NỀN TẢNG", OPTS_NEN_TANG); stt = c4.selectbox("TRẠNG THÁI", OPTS_STATUS_TRUCSO); ns = c5.multiselect("NHÂN SỰ", list_nv, default=[curr_name] if curr_name in list_nv else None)
                c6, c7, c8 = st.columns(3); ng = c6.text_input("NGUỒN"); gd = c7.time_input("GIỜ", value=None); nda = c8.date_input("NGÀY ĐĂNG", value=datetime.strptime(tab_name, "%d-%m-%Y").date(), format="DD/MM/YYYY")
                c9, c10 = st.columns(2); ld = c9.text_input("LINK DUYỆT"); lsp = c10.text_input("LINK SP"); yk = st.text_input("Ý KIẾN")
                
                if st.form_submit_button("THÊM VÀO VỎ", type="primary"):
                    with st.spinner("Lưu..."):
                        start = len(wks_t.get_all_values()) - 4 + 1
                        for p in (nt if nt else [""]):
                            wks_t.append_row([start, nd, dd, p, stt, "", ng, ", ".join(ns), yk, ld, gd.strftime("%H:%M") if gd else "", nda.strftime("%d/%m/%Y"), lsp])
                            start += 1
                        dinh_dang_dong_moi(wks_t, len(wks_t.get_all_values())); st.success("Xong!"); st.rerun()

            st.divider(); df_c = safe_read_values(wks_t)
            if not df_c.empty:
                with st.expander("🛠️ SỬA DÒNG TIN", expanded=False):
                    s = st.selectbox("CHỌN:", [f"{r['STT']} - {r['NỘI DUNG'][:30]}..." for i, r in df_c.iterrows()])
                    if s:
                        idx = [f"{r['STT']} - {r['NỘI DUNG'][:30]}..." for i, r in df_c.iterrows()].index(s); r = df_c.iloc[idx]
                        with st.form("ed_n"):
                            e_nd = st.text_area("ND", r['NỘI DUNG']); e_st = st.selectbox("TT", OPTS_STATUS_TRUCSO, index=OPTS_STATUS_TRUCSO.index(r['STATUS']) if r['STATUS'] in OPTS_STATUS_TRUCSO else 0)
                            e_ns = st.text_input("NS", r['NHÂN SỰ']); e_ld = st.text_input("LINK DUYỆT", r['LINK DUYỆT']); e_lsp = st.text_input("LINK SP", r['LINK SẢN PHẨM'])
                            if st.form_submit_button("CẬP NHẬT"):
                                row = idx + 5; wks_t.update_cell(row, 2, e_nd); wks_t.update_cell(row, 5, e_st); wks_t.update_cell(row, 8, e_ns); wks_t.update_cell(row, 10, e_ld); wks_t.update_cell(row, 13, e_lsp)
                                st.success("Xong!"); st.rerun()
                st.dataframe(df_c, use_container_width=True, hide_index=True)
            else: st.info("Chưa có tin.")

    # ================= TAB 5: LỊCH LÀM VIỆC =================
    elif selected_menu == "Lịch Làm Việc":
        st.subheader("📅 LỊCH & DEADLINE")
        if not df_cv.empty:
            tl = []
            for i, r in df_cv.iterrows():
                try: 
                    dl = datetime.strptime(r['Deadline'], "%H:%M %d/%m/%Y"); st_t = dl - timedelta(days=2)
                    if role!='LanhDao' and curr_name not in r['NguoiPhuTrach']: continue
                    tl.append({"Task": r['TenViec'], "Start": st_t, "Finish": dl, "Assignee": r['NguoiPhuTrach'], "Status": r['TrangThai']})
                except: continue
            if tl:
                fig = px.timeline(pd.DataFrame(tl), x_start="Start", x_end="Finish", y="Assignee", color="Status"); st.plotly_chart(fig, use_container_width=True)
                st.dataframe(pd.DataFrame(tl)[['Task', 'Finish', 'Status']], use_container_width=True)
        else: st.info("Trống.")

    # ================= TAB 6: EMAIL =================
    elif selected_menu == "Email":
        st.subheader("📧 GỬI EMAIL NỘI BỘ")
        tk = st.selectbox("TK GỬI:", range(10), format_func=lambda x:f"TK {x}")
        to = st.multiselect("ĐẾN:", df_users['Email'].tolist())
        sub = st.text_input("TIÊU ĐỀ"); bod = st.text_area("Nội dung")
        if st.button("GỬI EMAIL"): st.markdown(f'<script>window.open("https://mail.google.com/mail/u/{tk}/?view=cm&fs=1&to={",".join(to)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(bod)}", "_blank");</script>', unsafe_allow_html=True)

    # ================= CÁC TAB LÃNH ĐẠO (DASHBOARD, LOGS) =================
    elif role == 'LanhDao':
        if selected_menu == "Dashboard":
            st.header("📊 DASHBOARD TỔNG QUAN")
            if not df_cv.empty:
                col1, col2 = st.columns(2)
                with col1:
                    status_counts = df_cv['TrangThai'].value_counts().reset_index(); status_counts.columns = ['Trạng thái', 'Số lượng']
                    fig_pie = px.pie(status_counts, values='Số lượng', names='Trạng thái', title='TỶ LỆ TRẠNG THÁI CÔNG VIỆC', hole=0.4); st.plotly_chart(fig_pie, use_container_width=True)
                with col2:
                    all_staff = []; [all_staff.extend([n.strip() for n in s.split(',')]) for s in df_cv['NguoiPhuTrach']]
                    staff_counts = pd.Series(all_staff).value_counts().reset_index(); staff_counts.columns = ['BTV', 'Số việc']
                    fig_bar = px.bar(staff_counts, x='BTV', y='Số việc', title='NĂNG SUẤT NHÂN SỰ', color='BTV'); st.plotly_chart(fig_bar, use_container_width=True)
        elif selected_menu == "Nhật Ký":
            st.subheader("📜 NHẬT KÝ HOẠT ĐỘNG")
            if not df_log.empty: st.dataframe(df_log.iloc[::-1].rename(columns=VN_COLS_LOG), use_container_width=True)