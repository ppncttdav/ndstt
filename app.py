import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components
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
st.set_page_config(page_title="PHÒNG NỘI DUNG SỐ & TRUYỀN THÔNG", page_icon="🏢", layout="wide")

# --- TÊN FILE GOOGLE SHEET ---
SHEET_MAIN = "HeThongQuanLy" 
SHEET_TRUCSO = "VoTrucSo"
LINK_VO_TRUC_SO = "https://docs.google.com/spreadsheets/d/1lsm4FxTPMTmDbc50xq5ldbtCb7PIc-gbk5PMLHdzu7Y/edit?usp=sharing"

# 🔥 Dán link file Lịch trực tổng vào đây
LINK_LICH_TONG = "https://docs.google.com/spreadsheets/d/1jqPGEVTA7RfvTnV8rN6FSpRJFWXS7amVIAFQ0QqzXbI/edit?gid=0#gid=0"

# --- CẤU HÌNH THỜI GIAN VN ---
def get_vn_time():
    return datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))

# --- HÀM XỬ LÝ TÊN ---
def get_short_name(full_name):
    if not full_name or full_name == "--" or str(full_name).strip() == "": return "..."
    parts = full_name.strip().split()
    return " ".join(parts[-2:]) if len(parts) >= 2 else full_name

# --- HÀM LẤY THỜI TIẾT ---
@st.cache_data(ttl=3600)
def get_weather_and_advice():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=21.0285&longitude=105.8542&current_weather=true&timezone=Asia%2FBangkok"
        res = requests.get(url, timeout=2).json()
        temp = res['current_weather']['temperature']
        wcode = res['current_weather']['weathercode']
        condition = "CÓ MÂY"; advice = "CHÚC BẠN MỘT NGÀY LÀM VIỆC NĂNG SUẤT!"
        if wcode in [0, 1]: condition = "NẮNG ĐẸP ☀️"; advice = "TRỜI ĐẸP! GIỮ NĂNG LƯỢNG TÍCH CỰC NHÉ."
        elif wcode in [2, 3]: condition = "NHIỀU MÂY ☁️"; advice = "THỜI TIẾT DỊU MÁT, TẬP TRUNG CAO ĐỘ NÀO!"
        elif wcode in [51, 53, 55, 61, 63, 65]: condition = "CÓ MƯA 🌧️"; advice = "TRỜI MƯA, ĐƯỜNG TRƠN. CÁC BTV ĐI LẠI CẨN THẬN!"
        elif wcode >= 95: condition = "GIÔNG BÃO ⛈️"; advice = "THỜI TIẾT XẤU. HẠN CHẾ RA NGOÀI."
        return f"{temp}°C - {condition}", advice
    except: return "--°C", "LUÔN GIỮ VỮNG ĐAM MÊ NGHỀ BÁO NHÉ!"

# --- 1. DANH SÁCH CHỨC DANH ---
ROLES_HEADER = [
    "LÃNH ĐẠO BAN", "TRỰC THƯ KÝ TÒA SOẠN", "TRỰC QUẢN TRỊ MXH + VIDEO BIÊN TẬP",
    "TRỰC LỊCH PHÁT SÓNG", "TRỰC THƯ KÝ TÒA SOẠN", "TRỰC SẢN XUẤT VIDEO CLIP, LPS",
    "TRỰC QUẢN TRỊ CỔNG TTĐT", "TRỰC QUẢN TRỊ APP"
]

# --- 2. CÁC TÙY CHỌN ---
OPTS_DINH_DANG = ["Bài dịch", "Video biên tập", "Sản phẩm sản xuất"]
OPTS_NEN_TANG = ["Facebook", "Youtube", "TikTok", "Web + App", "Instagram"]
OPTS_STATUS_TRUCSO = ["Chờ xử lý", "Đang biên tập", "Gửi duyệt TCSX", "Yêu cầu sửa (TCSX)", "Gửi duyệt LĐP", "Yêu cầu sửa (LĐP)", "Đã duyệt/Chờ đăng", "Đã đăng", "Hủy"]
OPTS_TRANG_THAI_VIEC = ["Đã giao", "Đang thực hiện", "Chờ duyệt", "Hoàn thành", "Hủy"]

# --- 3. TIÊU ĐỀ CỘT ---
CONTENT_HEADER = ["STT", "NỘI DUNG", "ĐỊNH DẠNG", "NỀN TẢNG", "STATUS", "CHECK", "NGUỒN", "NHÂN SỰ", "Ý KIẾN ĐIỀU CHỈNH", "LINK DUYỆT", "GIỜ ĐĂNG", "NGÀY ĐĂNG", "LINK SẢN PHẨM"]

# --- TỪ ĐIỂN HIỂN THỊ ---
VN_COLS_VIEC = {"TenViec": "Tên công việc", "DuAn": "Dự án", "Deadline": "Hạn chót", "NguoiPhuTrach": "Người thực hiện", "TrangThai": "Trạng thái", "LinkBai": "Link SP", "GhiChu": "Ghi chú"}
VN_COLS_TRUCSO = {"STT": "STT", "NỘI DUNG": "Nội dung", "ĐỊNH DẠNG": "Định dạng", "NỀN TẢNG": "Nền tảng", "STATUS": "Trạng thái", "NGUỒN": "Nguồn", "NHÂN SỰ": "Nhân sự", "Ý KIẾN ĐIỀU CHỈNH": "Ý kiến", "LINK DUYỆT": "Link Duyệt", "GIỜ ĐĂNG": "Giờ đăng", "NGÀY ĐĂNG": "Ngày đăng", "LINK SẢN PHẨM": "Link SP"}
VN_COLS_DUAN = {"TenDuAn": "Tên Dự án", "MoTa": "Mô tả", "TrangThai": "Trạng thái", "TruongNhom": "Điều phối"}
VN_COLS_LOG = {"ThoiGian": "Thời gian", "NguoiDung": "Người dùng", "HanhDong": "Hành động", "ChiTiet": "Chi tiết"}

# ================= 1. BACKEND =================
@st.cache_resource(ttl=3600)
def get_gspread_client_cached():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets: creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        else: creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
        return gspread.authorize(creds)
    except Exception as e: st.error(f"🔴 Lỗi chứng thực: {e}"); return None

def ket_noi_sheet(sheet_name_or_url):
    client = get_gspread_client_cached()
    if not client: return None
    try:
        if "http" in sheet_name_or_url: return client.open_by_url(sheet_name_or_url)
        else: return client.open(sheet_name_or_url)
    except Exception as e: st.error(f"🔴 Lỗi kết nối sheet: {e}"); st.stop()

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

def lay_nhan_su_tu_lich_phuc_tap(target_date_obj):
    try:
        if "docs.google.com" not in LINK_LICH_TONG: return [], []
        sh_lich = ket_noi_sheet(LINK_LICH_TONG)
        wks_lich = sh_lich.get_worksheet(0)
        data = wks_lich.get_all_values()
        target_str = target_date_obj.strftime("%d/%m/%Y")
        
        found_col_idx = -1; found_row_idx = -1 
        for r_idx, row in enumerate(data):
            for c_idx, cell_val in enumerate(row):
                if target_str in str(cell_val).strip(): found_row_idx = r_idx; found_col_idx = c_idx; break
            if found_row_idx != -1: break
            
        if found_row_idx == -1: return [], []

        list_tcsx = []; list_btv = []
        scan_range = 40; current_row = found_row_idx + 1
        
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

# --- HÀM TẢI DỮ LIỆU CHUNG ---
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

def clear_cache_and_rerun():
    st.cache_data.clear()
    st.rerun()

def ghi_nhat_ky(sh_main, nguoi_dung, hanh_dong, chi_tiet):
    try: sh_main.worksheet("NhatKy").append_row([get_vn_time().strftime("%H:%M %d/%m/%Y"), nguoi_dung, hanh_dong, chi_tiet])
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

# --- FORMATTING ---
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

# ================= 2. AUTH =================
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
    
    with st.sidebar:
        st.success(f"XIN CHÀO: **{curr_name.upper()}**\n\nCHÚC BẠN MỘT NGÀY LÀM VIỆC VUI VẺ! ❤️")
        weather_info, advice_msg = get_weather_and_advice()
        st.markdown(f"---\n**🌤️ HÀ NỘI:** {weather_info}\n\n💡 **LỜI KHUYÊN:** {advice_msg}\n---")
        with st.expander("🔐 ĐỔI MẬT KHẨU"):
            with st.form("change_pass_form"):
                old_p = st.text_input("MẬT KHẨU CŨ", type="password"); new_p = st.text_input("MẬT KHẨU MỚI", type="password"); cfm_p = st.text_input("NHẬP LẠI", type="password")
                if st.form_submit_button("LƯU"):
                    if old_p != str(u_info['MatKhau']): st.error("Sai mật khẩu cũ!")
                    elif new_p != cfm_p: st.error("Mật khẩu không khớp!")
                    elif not new_p: st.error("Không để trống!")
                    else:
                        wks_acc = sh_main.worksheet("TaiKhoan"); cell = wks_acc.find(curr_username)
                        if cell: 
                            wks_acc.update_cell(cell.row, 2, new_p); st.session_state['user_info']['MatKhau'] = new_p; 
                            st.success("Xong!"); clear_cache_and_rerun()
        if st.button("🔄 LÀM MỚI DỮ LIỆU"): clear_cache_and_rerun()
        if st.button("ĐĂNG XUẤT"): st.session_state['dang_nhap'] = False; st.rerun()

    st.title("🏢 PHÒNG NỘI DUNG SỐ & TRUYỀN THÔNG")
    sh_trucso = ket_noi_sheet(SHEET_TRUCSO)
    
    # --- ĐỔI THỨ TỰ: TRỰC SỐ LÊN ĐẦU ---
    list_tabs = ["📝 TRỰC SỐ", "✅ CHECKLIST CÁ NHÂN", "📋 QUẢN LÝ CÔNG VIỆC", "🗂️ QUẢN LÝ DỰ ÁN", "📅 LỊCH LÀM VIỆC", "📧 EMAIL"]
    if role == 'LanhDao': list_tabs.extend(["📊 DASHBOARD", "📜 NHẬT KÝ"])
    tabs = st.tabs(list_tabs)

    # ================= TAB 0: TRỰC SỐ (CHUYỂN TỪ DƯỚI LÊN) =================
    with tabs[0]:
        today_vn = get_vn_time().date()
        yest_vn = today_vn - timedelta(days=1); tom_vn = today_vn + timedelta(days=1)
        c_nav1, c_nav2 = st.columns([1, 4])
        with c_nav1:
            lbl_yest = f"HÔM QUA ({yest_vn.strftime('%d/%m')})"; lbl_today = f"HÔM NAY ({today_vn.strftime('%d/%m')})"; lbl_tom = f"NGÀY MAI ({tom_vn.strftime('%d/%m')})"
            mode_view = st.radio("CHỌN NGÀY LÀM VIỆC:", [lbl_yest, lbl_today, lbl_tom], index=1, horizontal=False)
        
        if mode_view == lbl_yest: target_date = yest_vn
        elif mode_view == lbl_tom: target_date = tom_vn
        else: target_date = today_vn
        tab_name_current = target_date.strftime("%d-%m-%Y"); date_str_display = target_date.strftime("%d/%m/%Y")
        
        with c_nav2: st.header(f"📝 TRỰC SỐ NGÀY: {tab_name_current}")

        is_shift_admin = (role in ['LanhDao', 'ToChucSanXuat']); use_archive = False
        if is_shift_admin:
            with st.expander("🗄️ KHO LƯU TRỮ VỎ BẢN TIN (TRA CỨU LỊCH SỬ)", expanded=False):
                try:
                    all_sheets = sh_trucso.worksheets(); sheet_titles = [s.title for s in all_sheets]
                    date_sheets = [t for t in sheet_titles if len(t.split('-')) == 3]; date_sheets.sort(reverse=True)
                    selected_archive = st.selectbox("CHỌN NGÀY CẦN XEM LẠI:", ["-- Chọn ngày --"] + date_sheets)
                    if selected_archive != "-- Chọn ngày --": tab_name_current = selected_archive; use_archive = True; st.info(f"ĐANG XEM DỮ LIỆU LƯU TRỮ NGÀY: {selected_archive}")
                except: st.error("Lỗi tải danh sách lưu trữ.")

        tab_exists = False
        try: wks_today = sh_trucso.worksheet(tab_name_current); tab_exists = True
        except gspread.WorksheetNotFound: tab_exists = False

        if is_shift_admin and not use_archive:
            with st.expander("⚙️ QUẢN LÝ VỎ / EKIP TRỰC (DÀNH CHO QUẢN TRỊ)", expanded=not tab_exists):
                if not tab_exists:
                    if target_date >= today_vn:
                        st.warning(f"CHƯA CÓ SỔ TRỰC NGÀY {tab_name_current}.")
                        
                        # --- TỰ ĐỘNG LẤY TÊN TỪ LỊCH ---
                        auto_tcsx, auto_btv = lay_nhan_su_tu_lich_phuc_tap(target_date)
                        default_roster = [""] * len(ROLES_HEADER)
                        
                        if auto_tcsx: default_roster[3] = auto_tcsx[0]
                        random.shuffle(auto_btv)
                        if len(auto_btv) > 0: default_roster[2] = auto_btv[0] 
                        if len(auto_btv) > 1: default_roster[6] = auto_btv[1] 
                        if len(auto_btv) > 2: default_roster[7] = auto_btv[2] 

                        with st.form("init_roster"):
                            cols = st.columns(3); roster_vals = []
                            for i, r_t in enumerate(ROLES_HEADER):
                                with cols[i%3]: 
                                    def_idx = 0
                                    if default_roster[i] in list_nv:
                                        def_idx = list_nv.index(default_roster[i]) + 1
                                    
                                    val = st.selectbox(f"**{r_t}**", ["--"]+list_nv, index=def_idx, key=f"cr_{i}")
                                    roster_vals.append(val if val != "--" else "")
                            
                            if st.form_submit_button("🚀 TẠO TRỰC SỐ MỚI"):
                                with st.spinner("Đang tạo vỏ..."):
                                    try:
                                        w = sh_trucso.add_worksheet(title=tab_name_current, rows=100, cols=20)
                                        w.update_cell(1, 1, f"TRỰC SỐ VIETNAM TODAY {tab_name_current}")
                                        w.update_cell(2, 1, "DANH SÁCH TRỰC:")
                                        for i, v in enumerate(ROLES_HEADER): w.update_cell(2, i+2, v)
                                        w.update_cell(3, 1, "NHÂN SỰ:")
                                        for i, v in enumerate(roster_vals): w.update_cell(3, i+2, v)
                                        w.append_row(CONTENT_HEADER); dinh_dang_dep(w); st.success("ĐÃ TẠO XONG!"); st.rerun()
                                    except Exception as e: st.error(str(e))
                    else: st.error("KHÔNG TÌM THẤY DỮ LIỆU CỦA NGÀY HÔM QUA (CHƯA ĐƯỢC TẠO).")
                else:
                    st.success("ĐÃ CÓ VỎ TRỰC."); st.subheader("📢 GỬI THÔNG BÁO CA TRỰC")
                    try:
                        r_names = wks_today.row_values(3)[1:]
                        name_ld = get_short_name(r_names[0] if len(r_names) > 0 else "")
                        name_tk = get_short_name(r_names[1] if len(r_names) > 1 else "")
                        name_lps = get_short_name(r_names[3] if len(r_names) > 3 else "")
                        c_mail, c_zalo = st.columns(2)
                        with c_mail:
                            st.markdown("##### 📧 GỬI EMAIL TRÌNH DUYỆT")
                            tk_gui_vo = st.selectbox("CHỌN TÀI KHOẢN GỬI:", range(10), format_func=lambda x: f"TK {x} (Trên máy này)", key="mail_vo")
                            recipients = list(set([df_users[df_users['HoTen'] == n]['Email'].values[0] for n in r_names if n and n != "--" and len(df_users[df_users['HoTen'] == n]['Email'].values) > 0]))
                            email_sub = f"Trình duyệt Vỏ tin bài NDS Vietnam Today ngày {date_str_display}"
                            email_body = f"""Kính gửi chị {name_ld}, chị {name_tk}\n\nNhóm xin gửi các chị vỏ tin bài NDS ngày {date_str_display} trên các nền tảng.\n\nLink: {LINK_VO_TRUC_SO}\n\nCác chị xem giúp nhóm ạ.\n\nEm xin cảm ơn các chị ạ!\n\nEm {name_lps}"""
                            if recipients:
                                link_mail = f"https://mail.google.com/mail/u/{tk_gui_vo}/?view=cm&fs=1&to={','.join(recipients)}&su={urllib.parse.quote(email_sub)}&body={urllib.parse.quote(email_body)}"
                                st.markdown(f'<a href="{link_mail}" target="_blank" style="background:#EA4335;color:white;padding:10px 15px;text-decoration:none;border-radius:5px;font-weight:bold;display:block;text-align:center;">🚀 SOẠN EMAIL NGAY</a>', unsafe_allow_html=True)
                                st.caption(f"Gửi tới: {', '.join(recipients)}")
                            else: st.warning("Chưa tìm thấy email nào.")
                        with c_zalo:
                            st.markdown("##### 💬 GỬI QUA ZALO"); zalo_msg = f"🔔 *THÔNG BÁO LỊCH TRỰC SỐ*\n📅 NGÀY: {tab_name_current}\n------------------\n"
                            for i, name in enumerate(r_names):
                                if i < len(ROLES_HEADER) and name != "--": zalo_msg += f"🔹 {ROLES_HEADER[i]}: {name}\n"
                            zalo_msg += "------------------\n👉 Mời các anh/chị truy cập hệ thống để nhận nhiệm vụ."
                            st.text_area("NỘI DUNG (COPY):", value=zalo_msg, height=150); st.link_button("🚀 MỞ ZALO WEB", "https://chat.zalo.me/")
                    except Exception as e: st.error(f"Lỗi tạo thông báo: {e}")
                    st.divider()
                    tab_edit_vo, tab_del_vo = st.tabs(["SỬA EKIP TRỰC", "XÓA SỔ"])
                    with tab_edit_vo:
                        curr_names = wks_today.row_values(3)[1:]
                        while len(curr_names) < len(ROLES_HEADER): curr_names.append("")
                        with st.form("edit_roster_form"):
                            new_roster_vals = []
                            cols = st.columns(3)
                            for i, r_t in enumerate(ROLES_HEADER):
                                with cols[i%3]: val = st.selectbox(f"**{r_t}**", ["--"]+list_nv, index=list_nv.index(curr_names[i]) if curr_names[i] in list_nv else 0, key=f"ed_{i}"); new_roster_vals.append(val if val != "--" else "")
                            if st.form_submit_button("CẬP NHẬT EKIP"):
                                with st.spinner("Đang cập nhật..."):
                                    for i, v in enumerate(new_roster_vals): wks_today.update_cell(3, i+2, v)
                                    st.success("ĐÃ CẬP NHẬT!"); st.rerun()
                    with tab_del_vo:
                        st.error("⚠️ HÀNH ĐỘNG NÀY SẼ XÓA TOÀN BỘ DỮ LIỆU NGÀY NÀY!")
                        if st.button("XÁC NHẬN XÓA SỔ"): 
                            with st.spinner("Đang xóa..."):
                                sh_trucso.del_worksheet(wks_today); st.success("ĐÃ XÓA!"); st.rerun()

        if tab_exists:
            with st.expander("ℹ️ XEM EKIP TRỰC", expanded=True):
                try:
                    r_names = wks_today.row_values(3)[1:]
                    r_roles = wks_today.row_values(2)[1:]
                    if r_names:
                        c1, c2, c3, c4 = st.columns(4); cols_1 = [c1, c2, c3, c4]
                        for i in range(4):
                            if i < len(r_names):
                                with cols_1[i]: st.markdown(f"<p style='color:gray; font-size:12px; margin-bottom:0px;'>{r_roles[i]}</p>", unsafe_allow_html=True); st.markdown(f"<p style='color:#31333F; font-size:15px; font-weight:bold;'>{r_names[i]}</p>", unsafe_allow_html=True)
                        st.write("---")
                        c5, c6, c7, c8 = st.columns(4); cols_2 = [c5, c6, c7, c8]
                        for i in range(4):
                            idx = i + 4
                            if idx < len(r_names):
                                with cols_2[i]: st.markdown(f"<p style='color:gray; font-size:12px; margin-bottom:0px;'>{r_roles[idx]}</p>", unsafe_allow_html=True); st.markdown(f"<p style='color:#31333F; font-size:15px; font-weight:bold;'>{r_names[idx]}</p>", unsafe_allow_html=True)
                except: st.caption("Lỗi đọc ekip.")

            st.markdown("### ➕ THÊM TIN BÀI / ĐẦU MỤC")
            with st.form("add_news_form"):
                c1, c2 = st.columns([3, 1])
                ts_noidung = c1.text_area("NỘI DUNG", placeholder="Nhập nội dung...")
                ts_dinhdang = c2.selectbox("ĐỊNH DẠNG", OPTS_DINH_DANG)
                c3, c4, c5 = st.columns(3)
                ts_nentang = c3.multiselect("NỀN TẢNG (TÁCH DÒNG)", OPTS_NEN_TANG)
                ts_status = c4.selectbox("TRẠNG THÁI", OPTS_STATUS_TRUCSO)
                ts_nhansu = c5.multiselect("BTV THỰC HIỆN", list_nv, default=[curr_name] if curr_name in list_nv else None)
                c6, c7, c8 = st.columns(3)
                ts_nguon = c6.text_input("NGUỒN")
                ts_giodang = c7.time_input("GIỜ ĐĂNG (DK)", value=None)
                ts_ngaydang = c8.date_input("NGÀY ĐĂNG", value=datetime.strptime(tab_name_current, "%d-%m-%Y").date(), format="DD/MM/YYYY")
                c9, c10 = st.columns(2)
                ts_linkduyet = c9.text_input("LINK DUYỆT"); ts_linksp = c10.text_input("LINK SẢN PHẨM"); ts_ykien = st.text_input("Ý KIẾN / GHI CHÚ")

                if st.form_submit_button("LƯU VÀO SỔ", type="primary"):
                    with st.spinner("Đang lưu..."):
                        try:
                            all_rows = wks_today.get_all_values(); start_stt = max(0, len(all_rows) - 4) + 1
                            plats = ts_nentang if ts_nentang else [""]
                            for p in plats:
                                row = [start_stt, ts_noidung, ts_dinhdang, p, ts_status, "", ts_nguon, ", ".join(ts_nhansu), ts_ykien, ts_linkduyet, ts_giodang.strftime("%H:%M") if ts_giodang else "", ts_ngaydang.strftime("%d/%m/%Y"), ts_linksp]
                                wks_today.append_row(row); last_row_idx = len(wks_today.get_all_values()); dinh_dang_dong_moi(wks_today, last_row_idx); start_stt += 1
                            st.success("ĐÃ LƯU!"); st.rerun()
                        except Exception as e: st.error(f"Lỗi: {e}")

            st.divider()
            st.markdown("##### 📋 DANH SÁCH TIN BÀI")
            df_content = safe_read_values(wks_today)
            if not df_content.empty:
                with st.expander("🛠️ CẬP NHẬT / CHỈNH SỬA DÒNG TIN", expanded=False):
                    st.info("ℹ️ QUY TRÌNH: Chờ xử lý -> Đang biên tập -> Gửi duyệt TCSX -> Yêu cầu sửa -> Gửi duyệt LĐP -> Đã duyệt -> Đã đăng")
                    edit_opts = [f"{r['STT']} - {r['NỘI DUNG'][:30]}... ({r['NỀN TẢNG']})" for i, r in df_content.iterrows()]
                    sel_news = st.selectbox("CHỌN DÒNG TIN CẦN SỬA:", edit_opts)
                    if sel_news:
                        idx_news = edit_opts.index(sel_news); r_news = df_content.iloc[idx_news]
                        with st.form("edit_news_form"):
                            ec1, ec2 = st.columns([3, 1])
                            e_nd = ec1.text_area("NỘI DUNG", value=r_news['NỘI DUNG'])
                            try: idx_dd = OPTS_DINH_DANG.index(r_news['ĐỊNH DẠNG'])
                            except: idx_dd = 0
                            e_dd = ec2.selectbox("ĐỊNH DẠNG", OPTS_DINH_DANG, index=idx_dd)
                            try: idx_st = OPTS_STATUS_TRUCSO.index(r_news['STATUS'])
                            except: idx_st = 0
                            e_st = ec2.selectbox("TRẠNG THÁI", OPTS_STATUS_TRUCSO, index=idx_st)
                            ec3, ec4 = st.columns(2)
                            e_nt = ec3.text_input("NỀN TẢNG", value=r_news['NỀN TẢNG'])
                            e_ns = ec4.text_input("BTV THỰC HIỆN", value=r_news['NHÂN SỰ'])
                            ec5, ec6, ec7 = st.columns(3)
                            e_ld = ec5.text_input("LINK DUYỆT", value=r_news['LINK DUYỆT'])
                            try: curr_d_val = datetime.strptime(r_news['NGÀY ĐĂNG'], "%d/%m/%Y").date()
                            except: curr_d_val = datetime.now().date()
                            e_ndang = ec6.date_input("NGÀY ĐĂNG", value=curr_d_val, format="DD/MM/YYYY")
                            e_lsp = ec7.text_input("LINK SẢN PHẨM", value=r_news['LINK SẢN PHẨM'])
                            e_yk = st.text_input("Ý KIẾN (GHI CHÚ SỬA/DUYỆT)", value=r_news['Ý KIẾN ĐIỀU CHỈNH'])
                            if st.form_submit_button("CẬP NHẬT DÒNG TIN"):
                                with st.spinner("Đang cập nhật..."):
                                    r_sh = idx_news + 5 
                                    wks_today.update_cell(r_sh, 2, e_nd); wks_today.update_cell(r_sh, 3, e_dd)
                                    wks_today.update_cell(r_sh, 4, e_nt); wks_today.update_cell(r_sh, 5, e_st)
                                    wks_today.update_cell(r_sh, 8, e_ns); wks_today.update_cell(r_sh, 9, e_yk)
                                    wks_today.update_cell(r_sh, 10, e_ld); wks_today.update_cell(r_sh, 12, e_ndang.strftime("%d/%m/%Y"))
                                    wks_today.update_cell(r_sh, 13, e_lsp)
                                    st.success("ĐÃ CẬP NHẬT!"); st.rerun()
                st.dataframe(df_content, use_container_width=True, hide_index=True, column_config={"LINK DUYỆT": st.column_config.LinkColumn(display_text="Xem"),"LINK SẢN PHẨM": st.column_config.LinkColumn(display_text="Link"),})
            else: st.info("CHƯA CÓ TIN BÀI NÀO.")

    # ================= TAB 1: CHECKLIST CÁ NHÂN =================
    with tabs[1]:
        st.header(f"📝 CHECKLIST CỦA: {curr_name.upper()}")
        try: wks_canhan = sh_main.worksheet("ViecCaNhan")
        except: 
            wks_canhan = sh_main.add_worksheet("ViecCaNhan", 1000, 5)
            wks_canhan.append_row(["User", "TenViec", "Ngay", "TrangThai", "GhiChu"])
        
        col_view, col_date = st.columns([1, 2])
        view_mode = col_view.radio("Xem theo:", ["Hôm nay", "Tuần này", "Tháng này"], horizontal=True)
        today = date.today()
        my_tasks = [t for t in df_cn.to_dict('records') if str(t.get('User')) == curr_name]
        
        filtered_tasks = []
        for t in my_tasks:
            try:
                t_date = datetime.strptime(t['Ngay'], "%d/%m/%Y").date()
                if view_mode == "Hôm nay" and t_date == today: filtered_tasks.append(t)
                elif view_mode == "Tuần này" and today - timedelta(days=today.weekday()) <= t_date <= today + timedelta(days=6-today.weekday()): filtered_tasks.append(t)
                elif view_mode == "Tháng này" and t_date.month == today.month and t_date.year == today.year: filtered_tasks.append(t)
            except: pass
        
        if filtered_tasks:
            df_my_view = pd.DataFrame(filtered_tasks)
            df_my_view['Xong'] = df_my_view['TrangThai'].apply(lambda x: True if str(x).upper() == "TRUE" else False)
            edited_df = st.data_editor(
                df_my_view[['TenViec', 'Ngay', 'GhiChu', 'Xong']],
                column_config={
                    "Xong": st.column_config.CheckboxColumn("Hoàn thành", default=False),
                    "TenViec": st.column_config.TextColumn("Nội dung công việc", width="medium"),
                    "Ngay": st.column_config.TextColumn("Ngày", disabled=True),
                    "GhiChu": st.column_config.TextColumn("Ghi chú"),
                }, hide_index=True, key="editor_checklist"
            )
            
            if st.button("💾 CẬP NHẬT CHECKLIST"):
                with st.spinner("Đang lưu..."):
                    try:
                        all_values = wks_canhan.get_all_values()
                        for i, row in edited_df.iterrows():
                            for idx, sheet_row in enumerate(all_values):
                                if idx == 0: continue
                                if sheet_row[0] == curr_name and sheet_row[1] == row['TenViec'] and sheet_row[2] == row['Ngay']:
                                    wks_canhan.update_cell(idx + 1, 4, "TRUE" if row['Xong'] else "FALSE")
                                    wks_canhan.update_cell(idx + 1, 5, row['GhiChu'])
                                    break
                        st.success("Đã cập nhật!"); clear_cache_and_rerun()
                    except Exception as e: st.error(f"Lỗi: {e}")
        else: st.info(f"Bạn chưa có việc cá nhân nào trong {view_mode.lower()}.")

        st.divider()
        c_add1, c_add2 = st.columns(2)
        with c_add1:
            st.markdown("#### ➕ TỰ TẠO VIỆC")
            with st.form("new_personal_task"):
                n_ten = st.text_input("Nội dung"); n_ngay = st.date_input("Ngày", value=today, format="DD/MM/YYYY"); n_ghichu = st.text_input("Ghi chú")
                if st.form_submit_button("THÊM"):
                    if n_ten:
                        with st.spinner("Đang thêm..."):
                            wks_canhan.append_row([curr_name, n_ten, n_ngay.strftime("%d/%m/%Y"), "FALSE", n_ghichu])
                            st.success("Xong!"); clear_cache_and_rerun()
        with c_add2:
            st.markdown("#### 📥 LẤY TỪ VIỆC CHUNG")
            if not df_cv.empty:
                my_tasks_cv = df_cv[df_cv['NguoiPhuTrach'].astype(str).str.contains(curr_name, case=False, na=False)]
                if not my_tasks_cv.empty:
                    opts = [f"{r['TenViec']} ({r['Deadline']})" for i, r in my_tasks_cv.iterrows()]
                    sel = st.selectbox("Chọn việc:", opts)
                    if st.button("CHUYỂN SANG CHECKLIST"):
                        with st.spinner("Đang chuyển..."):
                            t_name = sel.split(" (")[0]
                            row = my_tasks_cv[my_tasks_cv['TenViec'] == t_name].iloc[0]
                            try: dl = row['Deadline'].split(" ")[1]
                            except: dl = today.strftime("%d/%m/%Y")
                            try: wks_canhan = sh_main.worksheet("ViecCaNhan")
                            except: wks_canhan = sh_main.add_worksheet("ViecCaNhan", 1000, 5); wks_canhan.append_row(["User", "TenViec", "Ngay", "TrangThai", "GhiChu"])
                            wks_canhan.append_row([curr_name, t_name, dl, "FALSE", "Từ hệ thống chung"]); st.success("Xong!"); clear_cache_and_rerun()

    # ================= TAB 2: CÔNG VIỆC CHUNG =================
    with tabs[2]:
        st.caption("QUẢN LÝ TIẾN ĐỘ DỰ ÁN TOÀN PHÒNG.")
        with st.expander("➕ TẠO ĐẦU VIỆC MỚI", expanded=False):
            c1, c2 = st.columns(2)
            tv_ten = c1.text_input("TÊN ĐẦU VIỆC"); tv_duan = c1.selectbox("DỰ ÁN", list_duan)
            now_vn = get_vn_time()
            tv_time = c1.time_input("GIỜ DEADLINE", value=now_vn.time()); tv_date = c1.date_input("NGÀY DEADLINE", value=now_vn.date(), format="DD/MM/YYYY")
            tv_nguoi = c2.multiselect("BTV THỰC HIỆN", list_nv); tv_ghichu = c2.text_area("YÊU CẦU", height=100)
            
            ct1, ct2 = st.columns([2,1])
            tk_gui = ct1.selectbox("GỬI TỪ GMAIL:", range(10), format_func=lambda x: f"TK {x}")
            ct2.markdown(f'<br><a href="https://mail.google.com/mail/u/{tk_gui}" target="_blank">Check Mail</a>', unsafe_allow_html=True)
            opt_nv = st.checkbox("Gửi Email cho BTV", True)
            
            if st.button("💾 LƯU & GỬI EMAIL"):
                with st.spinner("Đang lưu..."):
                    try:
                        dl_fmt = f"{tv_time.strftime('%H:%M')} {tv_date.strftime('%d/%m/%Y')}"
                        sh_main.worksheet("CongViec").append_row([tv_ten, tv_duan, dl_fmt, ", ".join(tv_nguoi), "Đã giao", "", tv_ghichu, curr_name])
                        ghi_nhat_ky(sh_main, curr_name, "Tạo việc", tv_ten); st.success("Xong!")
                        if opt_nv and tv_nguoi:
                            mails = df_users[df_users['HoTen'].isin(tv_nguoi)]['Email'].tolist()
                            mails = [m for m in mails if str(m).strip()]
                            if mails: st.markdown(f'<a href="https://mail.google.com/mail/u/{tk_gui}/?view=cm&fs=1&to={",".join(mails)}&su={urllib.parse.quote(tv_ten)}&body={urllib.parse.quote(tv_ghichu)}" target="_blank">📧 Gửi BTV</a>', unsafe_allow_html=True)
                        clear_cache_and_rerun()
                    except Exception as e: st.error(str(e))

        st.divider()
        da_filter = st.selectbox("LỌC DỰ ÁN:", ["-- TẤT CẢ --"]+list_duan)
        if not df_cv.empty:
            df_display = df_cv.copy()
            if da_filter != "-- TẤT CẢ --": df_display = df_display[df_display['DuAn']==da_filter]
            edits = {f"{r['TenViec']} ({i+2})": {"id": i, "lv": check_quyen(curr_name, role, r, df_duan)} for i, r in df_display.iterrows() if check_quyen(curr_name, role, r, df_duan)>0}
            if edits:
                with st.expander("🛠️ CẬP NHẬT TRẠNG THÁI", expanded=True):
                    s_task = st.selectbox("CHỌN ĐẦU VIỆC:", list(edits.keys()))
                    if s_task:
                        row_idx = edits[s_task]['id']; lv = edits[s_task]['lv']; r_dat = df_display.iloc[row_idx]
                        dis = (lv == 1)
                        with st.form("f_edit"):
                            ce1, ce2 = st.columns(2)
                            e_ten = ce1.text_input("TÊN VIỆC", r_dat['TenViec'], disabled=dis)
                            e_ng = ce1.text_input("BTV THỰC HIỆN", r_dat['NguoiPhuTrach'], disabled=dis)
                            e_lk = ce1.text_input("LINK SẢN PHẨM", r_dat.get('LinkBai',''))
                            e_dl = ce2.text_input("DEADLINE", r_dat.get('Deadline',''), disabled=dis)
                            e_st = ce2.selectbox("TRẠNG THÁI", OPTS_TRANG_THAI_VIEC, index=OPTS_TRANG_THAI_VIEC.index(r_dat.get('TrangThai','Đã giao')) if r_dat.get('TrangThai') in OPTS_TRANG_THAI_VIEC else 0)
                            e_nt = ce2.text_area("GHI CHÚ", r_dat.get('GhiChu',''))
                            if st.form_submit_button("CẬP NHẬT"):
                                with st.spinner("Đang cập nhật..."):
                                    w = sh_main.worksheet("CongViec")
                                    cell = w.find(r_dat['TenViec']) 
                                    if cell:
                                        rn = cell.row
                                        w.update_cell(rn,1,e_ten); w.update_cell(rn,3,e_dl); w.update_cell(rn,4,e_ng)
                                        w.update_cell(rn,5,e_st); w.update_cell(rn,6,e_lk); w.update_cell(rn,7,e_nt)
                                        st.success("ĐÃ CẬP NHẬT!"); clear_cache_and_rerun()
            st.dataframe(df_display.drop(columns=['NguoiTao'], errors='ignore').rename(columns=VN_COLS_VIEC), use_container_width=True, hide_index=True)
        else: st.info("CHƯA CÓ CÔNG VIỆC NÀO.")

    # ================= TAB 3: DỰ ÁN =================
    with tabs[3]:
        if role == 'LanhDao':
            with st.form("new_da"):
                d_n = st.text_input("TÊN DỰ ÁN"); d_m = st.text_area("MÔ TẢ"); d_l = st.multiselect("PHỤ TRÁCH", list_nv)
                if st.form_submit_button("TẠO DỰ ÁN"): 
                    with st.spinner("Đang tạo..."):
                        sh_main.worksheet("DuAn").append_row([d_n, d_m, "Đang chạy", ",".join(d_l)]); st.success("Xong!"); clear_cache_and_rerun()
        st.dataframe(df_duan.rename(columns=VN_COLS_DUAN), use_container_width=True)

    # ================= TAB 5: LỊCH LÀM VIỆC =================
    with tabs[4]:
        st.header("📅 LỊCH LÀM VIỆC & DEADLINE")
        if not df_cv.empty:
            task_list = []
            for i, r in df_cv.iterrows():
                try:
                    dl_str = r['Deadline']; dl_dt = datetime.strptime(dl_str, "%H:%M %d/%m/%Y")
                    start_dt = dl_dt - timedelta(days=2) 
                    if role != 'LanhDao' and curr_name not in r['NguoiPhuTrach']: continue
                    task_list.append({"Task": r['TenViec'], "Start": start_dt, "Finish": dl_dt, "Assignee": r['NguoiPhuTrach'], "Status": r['TrangThai'], "Project": r['DuAn']})
                except: continue
            if task_list:
                df_gantt = pd.DataFrame(task_list)
                fig = px.timeline(df_gantt, x_start="Start", x_end="Finish", y="Assignee", color="Status", hover_data=["Task", "Project"], title="TIMELINE CÔNG VIỆC (DỰ KIẾN)", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
                st.divider()
                st.dataframe(df_gantt[['Task', 'Finish', 'Assignee', 'Status']], use_container_width=True)
            else: st.info("KHÔNG CÓ DỮ LIỆU.")
        else: st.info("CHƯA CÓ CÔNG VIỆC NÀO.")

    # ================= TAB 6: EMAIL =================
    with tabs[5]:
        tk = st.selectbox("TK GỬI:", range(10), format_func=lambda x:f"TK {x}")
        to = st.multiselect("ĐẾN:", df_users['Email'].tolist())
        sub = st.text_input("TIÊU ĐỀ"); bod = st.text_area("Nội dung")
        if st.button("GỬI EMAIL"): st.markdown(f'<script>window.open("https://mail.google.com/mail/u/{tk}/?view=cm&fs=1&to={",".join(to)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(bod)}", "_blank");</script>', unsafe_allow_html=True)

    # ================= CÁC TAB LÃNH ĐẠO (DASHBOARD, LOGS) =================
    if role == 'LanhDao':
        with tabs[6]:
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
            if tab_exists and not df_content.empty:
                st.divider(); st.subheader(f"THỐNG KÊ TIN BÀI NGÀY {tab_name_current}"); c3, c4 = st.columns(2)
                with c3:
                    plat_counts = df_content['NỀN TẢNG'].value_counts().reset_index(); plat_counts.columns = ['Nền tảng', 'Số lượng']
                    fig_plat = px.bar(plat_counts, x='Số lượng', y='Nền tảng', orientation='h', title='PHÂN BỐ NỀN TẢNG'); st.plotly_chart(fig_plat, use_container_width=True)
                with c4:
                    st_counts = df_content['STATUS'].value_counts().reset_index(); st_counts.columns = ['Status', 'Count']
                    fig_st = px.pie(st_counts, values='Count', names='Status', title='TIẾN ĐỘ TIN BÀI'); st.plotly_chart(fig_st, use_container_width=True)
        with tabs[7]:
            if not df_log.empty: st.dataframe(df_log.iloc[::-1].rename(columns=VN_COLS_LOG), use_container_width=True)