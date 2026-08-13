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
import re
import io

# --- THƯ VIỆN ĐỊNH DẠNG SHEET ---
from gspread_formatting import *

# ================= CẤU HÌNH HỆ THỐNG =================
st.set_page_config(page_title="PHÒNG NỘI DUNG SỐ & TRUYỀN THÔNG", page_icon="🏢", layout="wide")

SHEET_MAIN = "HeThongQuanLy" 
SHEET_TRUCSO = "VoTrucSo"
LINK_VO_TRUC_SO = "https://docs.google.com/spreadsheets/d/1WYfdY8OIVWPD-N5xZD36B3v7MV_XFjHXj_v9UZXK0ZI/edit?gid=1107365160#gid=1107365160"
LINK_LICH_TONG = "https://docs.google.com/spreadsheets/d/1jqPGEVTA7RfvTnV8rN6FSpRJFWXS7amVIAFQ0QqzXbI/edit?gid=0#gid=0"

def get_vn_time():
    return datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))

def get_short_name(full_name):
    if not full_name or full_name == "--" or str(full_name).strip() == "": return "..."
    parts = full_name.strip().split()
    return " ".join(parts[-2:]) if len(parts) >= 2 else full_name

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

ROLES_HEADER = [
    "LÃNH ĐẠO BAN", "TRỰC THƯ KÝ TÒA SOẠN", "TRỰC QUẢN TRỊ MXH + VIDEO BIÊN TẬP",
    "TRỰC LỊCH PHÁT SÓNG", "TRỰC THƯ KÝ TÒA SOẠN", "TRỰC SẢN XUẤT VIDEO CLIP, LPS",
    "TRỰC QUẢN TRỊ CỔNG TTĐT", "TRỰC QUẢN TRỊ APP"
]

OPTS_DINH_DANG = ["Bài dịch", "Video biên tập", "Sản phẩm sản xuất"]
OPTS_NEN_TANG = ["Facebook", "Youtube", "TikTok", "Web + App", "Instagram"]
OPTS_STATUS_TRUCSO = ["Chờ xử lý", "Đang biên tập", "Gửi duyệt TCSX", "Yêu cầu sửa (TCSX)", "Gửi duyệt LĐP", "Yêu cầu sửa (LĐP)", "Đã duyệt/Chờ đăng", "Đã đăng", "Scheduled", "Posted", "Hủy"]
OPTS_TRANG_THAI_VIEC = ["Đã giao", "Đang thực hiện", "Chờ duyệt", "Hoàn thành", "Hủy"]

CONTENT_HEADER = ["STT", "NỘI DUNG", "ĐỊNH DẠNG", "NỀN TẢNG", "STATUS", "CHECK", "NGUỒN", "NHÂN SỰ", "TCSX", "LĐP", "GIỜ ĐĂNG", "NGÀY ĐĂNG", "LINK SẢN PHẨM", "LINK DUYỆT"]

VN_COLS_VIEC = {"TenViec": "Tên công việc", "DuAn": "Dự án", "Deadline": "Hạn chót", "NguoiPhuTrach": "Người thực hiện", "TrangThai": "Trạng thái", "LinkBai": "Link SP", "GhiChu": "Ghi chú"}
VN_COLS_DUAN = {"TenDuAn": "Tên Dự án", "MoTa": "Mô tả", "TrangThai": "Trạng thái", "TruongNhom": "Điều phối"}
VN_COLS_LOG = {"ThoiGian": "Thời gian", "NguoiDung": "Người dùng", "HanhDong": "Hành động", "ChiTiet": "Chi tiết"}

# ================= 1. BACKEND & XỬ LÝ DỮ LIỆU =================
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
    except: st.stop()

@st.cache_data(ttl=1800)
def load_tai_khoan():
    try:
        sh = ket_noi_sheet(SHEET_MAIN)
        for _ in range(2):
            try: return pd.DataFrame(sh.worksheet("TaiKhoan").get_all_records())
            except: time.sleep(0.2)
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def load_du_lieu_app():
    try:
        sh = ket_noi_sheet(SHEET_MAIN)
        df_d = pd.DataFrame(sh.worksheet("DuAn").get_all_records())
        df_c = pd.DataFrame(sh.worksheet("CongViec").get_all_records())
        try: df_cn = pd.DataFrame(sh.worksheet("ViecCaNhan").get_all_records())
        except: df_cn = pd.DataFrame()
        try: df_nk = pd.DataFrame(sh.worksheet("NhatKy").get_all_records())
        except: df_nk = pd.DataFrame()
        return df_d, df_c, df_cn, df_nk
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# HÀM LẤY DỮ LIỆU REAL-TIME TỪ SHEET (Cập nhật cực nhanh mỗi 10s)
@st.cache_data(ttl=10, show_spinner=False)
def fetch_realtime_sheet(date_str):
    try:
        client = get_gspread_client_cached()
        if not client: return pd.DataFrame(columns=CONTENT_HEADER)
        sh = client.open_by_url(LINK_VO_TRUC_SO)
        wks = sh.worksheet(date_str)
        data = wks.get_all_values()
        if len(data) > 4: return pd.DataFrame(data[4:], columns=data[3])
    except: pass
    return pd.DataFrame(columns=CONTENT_HEADER)

def clear_cache_and_rerun(): st.cache_data.clear(); st.rerun()

def ghi_nhat_ky(sh_main, nguoi_dung, hanh_dong, chi_tiet):
    try: sh_main.worksheet("NhatKy").append_row([get_vn_time().strftime("%H:%M %d/%m/%Y"), nguoi_dung, hanh_dong, chi_tiet])
    except: pass

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

def split_text_link(merged_text):
    if pd.isna(merged_text) or not str(merged_text).strip(): return "", ""
    text = str(merged_text)
    urls = re.findall(r'(https?://[^\s]+|drive\.google\.com[^\s]+)', text)
    if urls:
        link = urls[-1]
        caption = text.replace(link, "").strip()
        caption = re.sub(r'\n+$', '', caption).strip()
        return caption, link
    return text, ""

def merge_text_link(caption, link):
    caption = str(caption).strip(); link = str(link).strip()
    if caption and link: return f"{caption}\n\n{link}"
    if caption: return caption
    if link: return link
    return ""

def build_appended_comment(history_text, new_text, is_ok_checked):
    parts = []
    if is_ok_checked: parts.append("OK")
    if new_text.strip(): parts.append(new_text.strip())
    added_str = " - ".join(parts)
    if not added_str: return history_text 
    if history_text.strip(): return f"{history_text.strip()}\n{added_str}" 
    return added_str

def normalize_btv_names(name_str):
    if pd.isna(name_str) or str(name_str).strip() == "": return "Chưa phân công"
    clean_str = re.sub(r'\(.*?\)', '', str(name_str))
    clean_str = re.sub(r'\[.*?\]', '', clean_str)
    parts = re.split(r'[,;]', clean_str)
    normalized_parts = []
    for p in parts:
        p = p.strip().title()
        if p: normalized_parts.append(p)
    if not normalized_parts: return "Chưa phân công"
    return ", ".join(list(dict.fromkeys(normalized_parts)))

def get_smart_status(group_df):
    tcsx_cmts = " ".join(group_df['TCSX'].replace('', pd.NA).dropna().astype(str).tolist()).lower()
    ldp_cmts = " ".join(group_df['LĐP'].replace('', pd.NA).dropna().astype(str).tolist()).lower()
    all_cmts = tcsx_cmts + " " + ldp_cmts
    
    first_row = group_df.iloc[0]
    status = str(first_row.get('STATUS', '')).lower()
    link_duyet = str(first_row.get('LINK DUYỆT', ''))
    has_link = len(link_duyet) > 5
    
    tcsx_ok = re.search(r'\bok\b|\bokie\b|\bokay\b', tcsx_cmts)
    ldp_ok = re.search(r'\bok\b|\bokie\b|\bokay\b', ldp_cmts)
    
    btv_keywords = ["đã sửa", "đã update", "upd", "đã chỉnh", "đã thay", "e đã", "em đã", "đã xong", "đã bổ sung", "đã cắt"]
    btv_fixed = any(kw in all_cmts for kw in btv_keywords)
    
    neutral_phrases = ["đã xem", "xem rồi", "good", "được", "tks", "cảm ơn", "ok", "okie"]
    negative_keywords = ["sửa", "lỗi", "thiếu", "chưa", "sai", "thêm", "đừng", "sao lại", "cắt", "nhạy cảm", "giật", "không", "ko", "nếu"]
    
    tcsx_is_pure_neutral = any(p in tcsx_cmts for p in neutral_phrases) and not any(w in tcsx_cmts for w in negative_keywords)
    ldp_is_pure_neutral = any(p in ldp_cmts for p in neutral_phrases) and not any(w in ldp_cmts for w in negative_keywords)
    
    # Chuỗi ưu tiên đã chỉnh sửa
    if ldp_ok or "đã duyệt" in status or "đã đăng" in status or "posted" in status: return "✅ Đã duyệt"
    if btv_fixed: return "🔄 BTV đã sửa"
    if not ldp_ok and len(ldp_cmts.strip()) > 2 and not ldp_is_pure_neutral: return "🔴 Cần sửa"
    if not tcsx_ok and len(tcsx_cmts.strip()) > 2 and not tcsx_is_pure_neutral: return "🔴 Cần sửa"
    if "sửa" in status: return "🔴 Cần sửa"
    if tcsx_ok or "lđp" in status: return "⏳ Chờ LĐP duyệt"
    if has_link or "tcsx" in status: return "👀 Chờ TCSX duyệt"
    return "📝 BTV đang hoàn thiện"

def format_title_name(text):
    text = text.upper().replace("VIBES OF VN", "VIBES OF VIETNAM")
    text = text.title()
    replacements = { " Of ": " of ", " At ": " at ", " A ": " a ", " An ": " an ", " The ": " the ", " In ": " in ", " On ": " on ", " To ": " to ", " And ": " and " }
    for old, new in replacements.items(): text = text.replace(old, new)
    return text

def parse_khung_cell(cell_val):
    if pd.isna(cell_val) or str(cell_val).strip() == "": return "", ""
    lines = [line.strip() for line in str(cell_val).split('\n') if line.strip()]
    if not lines: return "", ""
    title = lines[0]
    title = re.sub(r'\(.*?\)', '', title) 
    title = re.sub(r'\s*\d+\'?m?\s*$', '', title) 
    title = re.sub(r'\s*\d+\s*$', '', title) 
    title = title.split('/')[0].strip() 
    title = format_title_name(title)
    desc = ""
    if len(lines) > 1:
        for line in lines[1:]:
            if not line.startswith('(') and "PL" not in line and "PM" not in line:
                desc = line.split('/')[0].strip(); break
    return title, desc

def format_time_col(t):
    if pd.isna(t): return ""
    try:
        if isinstance(t, str):
            t = t.strip()
            if len(t) == 5 and ":" in t: return f"{t}:00"
            return t
        return t.strftime("%H:%M:%S")
    except: return str(t)

def dinh_dang_dep(wks):
    wks.merge_cells('A1:N1')
    format_cell_range(wks, 'A1:N1', CellFormat(backgroundColor=Color(0, 1, 1), textFormat=TextFormat(bold=True, fontSize=14), horizontalAlignment='CENTER', verticalAlignment='MIDDLE'))
    format_cell_range(wks, 'A2:N3', CellFormat(textFormat=TextFormat(bold=True), horizontalAlignment='CENTER', verticalAlignment='MIDDLE', wrapStrategy='WRAP', borders=Borders(top=Border("SOLID"), bottom=Border("SOLID"), left=Border("SOLID"), right=Border("SOLID"))))
    format_cell_range(wks, 'A2:N2', CellFormat(backgroundColor=Color(0.8, 1, 1)))
    format_cell_range(wks, 'A4:N4', CellFormat(backgroundColor=Color(1, 1, 0), textFormat=TextFormat(bold=True), horizontalAlignment='CENTER', verticalAlignment='MIDDLE', wrapStrategy='WRAP', borders=Borders(top=Border("SOLID"), bottom=Border("SOLID"), left=Border("SOLID"), right=Border("SOLID"))))
    set_column_width(wks, 'A', 40); set_column_width(wks, 'B', 300); set_column_width(wks, 'C', 100); set_column_width(wks, 'D', 100)
    set_column_width(wks, 'E', 130); set_column_width(wks, 'F', 50); set_column_width(wks, 'G', 80); set_column_width(wks, 'H', 120)
    set_column_width(wks, 'I', 150); set_column_width(wks, 'J', 150); set_column_width(wks, 'K', 80); set_column_width(wks, 'L', 100)
    set_column_width(wks, 'M', 150); set_column_width(wks, 'N', 350)
    format_cell_range(wks, 'B5:B100', CellFormat(wrapStrategy='WRAP', verticalAlignment='TOP'))

def dinh_dang_dong_moi(wks, row_idx):
    rng = f"A{row_idx}:N{row_idx}"
    format_cell_range(wks, rng, CellFormat(wrapStrategy='WRAP', verticalAlignment='TOP', borders=Borders(top=Border("SOLID"), bottom=Border("SOLID"), left=Border("SOLID"), right=Border("SOLID"))))

# ================= 2. AUTH & GIAO DIỆN =================
if 'dang_nhap' not in st.session_state: 
    st.session_state['dang_nhap'] = False; st.session_state['user_info'] = {}

df_users = load_tai_khoan()
list_nv = df_users['HoTen'].tolist() if not df_users.empty else []

if "session_user" in st.query_params and not st.session_state['dang_nhap']:
    saved_username = st.query_params["session_user"]
    u_row = df_users[df_users['TenDangNhap'].astype(str) == saved_username]
    if not u_row.empty:
        st.session_state['dang_nhap'] = True; st.session_state['user_info'] = u_row.iloc[0].to_dict()

if not st.session_state['dang_nhap']:
    st.markdown("## 🔐 CỔNG ĐĂNG NHẬP")
    with st.form("login"):
        user = st.text_input("Tên đăng nhập"); pwd = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("ĐĂNG NHẬP"):
            if not df_users.empty:
                u_row = df_users[(df_users['TenDangNhap'].astype(str)==user) & (df_users['MatKhau'].astype(str)==pwd)]
                if not u_row.empty:
                    st.session_state['dang_nhap'] = True; st.session_state['user_info'] = u_row.iloc[0].to_dict()
                    st.query_params["session_user"] = user
                    sh_main = ket_noi_sheet(SHEET_MAIN)
                    ghi_nhat_ky(sh_main, u_row.iloc[0]['HoTen'], "Đăng nhập", "Success"); clear_cache_and_rerun()
                else: st.error("Sai thông tin!")
            else: st.error("Lỗi dữ liệu Tài khoản.")
else:
    df_duan, df_cv, df_cn, df_log = load_du_lieu_app()
    list_duan = df_duan['TenDuAn'].tolist() if not df_duan.empty else []
    sh_main = ket_noi_sheet(SHEET_MAIN)
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
                            
        if st.button("ĐĂNG XUẤT"): 
            st.session_state['dang_nhap'] = False
            if "session_user" in st.query_params: del st.query_params["session_user"]
            st.rerun()

    sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO) 
    
    list_tabs = ["📝 VỎ TRỰC SỐ", "🔍 TRA CỨU TIN", "📺 TẠO LPS", "✅ CHECKLIST", "📋 CÔNG VIỆC", "🗂️ DỰ ÁN", "📅 LỊCH", "📧 EMAIL"]
    if role == 'LanhDao': list_tabs.extend(["📊 DASHBOARD", "📜 NHẬT KÝ"])
    tabs = st.tabs(list_tabs)

    # ================= TAB 0: VỎ TRỰC SỐ =================
    with tabs[0]:
        c_nav1, c_nav2 = st.columns([1, 4])
        with c_nav1: target_date = st.date_input("📅 CHỌN NGÀY LÀM VIỆC:", value=get_vn_time().date(), format="DD/MM/YYYY")
        
        tab_name_current = target_date.strftime("%d/%m/%Y") 
        date_str_display = target_date.strftime("%d/%m/%Y")
        
        with c_nav2: st.header(f"📝 VỎ TRỰC SỐ NGÀY: {date_str_display}")

        is_shift_admin = (role in ['LanhDao', 'ToChucSanXuat'])
        tab_exists = False
        try: 
            wks_today = sh_trucso.worksheet(tab_name_current)
            tab_exists = True
        except: tab_exists = False

        if not tab_exists:
            st.warning(f"CHƯA CÓ VỎ TRỰC SỐ NGÀY {date_str_display}.")
            if is_shift_admin:
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
                            def_idx = list_nv.index(default_roster[i]) + 1 if default_roster[i] in list_nv else 0
                            val = st.selectbox(f"**{r_t}**", ["--"]+list_nv, index=def_idx, key=f"cr_{i}")
                            roster_vals.append(val if val != "--" else "")
                    
                    if st.form_submit_button("🚀 TẠO VỎ TRỰC SỐ MỚI"):
                        with st.spinner("Đang tạo vỏ trực số..."):
                            try:
                                w = sh_trucso.add_worksheet(title=tab_name_current, rows=100, cols=20)
                                w.update_cell(1, 1, f"VỎ TRỰC SỐ VIETNAM TODAY {date_str_display}")
                                w.update_cell(2, 1, "DANH SÁCH TRỰC:")
                                for i, v in enumerate(ROLES_HEADER): w.update_cell(2, i+2, v)
                                w.update_cell(3, 1, "NHÂN SỰ:")
                                for i, v in enumerate(roster_vals): w.update_cell(3, i+2, v)
                                w.append_row(CONTENT_HEADER); dinh_dang_dep(w); 
                                st.success("ĐÃ TẠO XONG VỎ TRỰC SỐ!"); time.sleep(1); st.rerun()
                            except Exception as e: st.error(str(e))
        elif tab_exists:
            # KIỂM TRA QUYỀN ĐỘNG TRONG CA TRỰC
            is_shift_ldp = False
            is_shift_tcsx = False
            try:
                roster_names_current = wks_today.row_values(3)[1:]
                if len(roster_names_current) > 0 and curr_name == str(roster_names_current[0]).strip(): is_shift_ldp = True
                if len(roster_names_current) > 1 and curr_name == str(roster_names_current[1]).strip(): is_shift_tcsx = True
                if len(roster_names_current) > 4 and curr_name == str(roster_names_current[4]).strip(): is_shift_tcsx = True
            except: pass
            if role == 'LanhDao': is_shift_ldp = True 

            with st.expander("👥 THÔNG TIN EKIP TRỰC SỐ", expanded=False):
                try:
                    r_names = wks_today.row_values(3)[1:]; r_roles = wks_today.row_values(2)[1:]
                    c1, c2, c3, c4 = st.columns(4)
                    cols_1 = [c1, c2, c3, c4]
                    for i in range(4):
                        if i < len(r_names): cols_1[i].markdown(f"<p style='color:gray; font-size:12px; margin-bottom:0px;'>{r_roles[i]}</p><b>{r_names[i]}</b>", unsafe_allow_html=True)
                    st.write("---"); c5, c6, c7, c8 = st.columns(4); cols_2 = [c5, c6, c7, c8]
                    for i in range(4):
                        idx = i + 4
                        if idx < len(r_names): cols_2[i].markdown(f"<p style='color:gray; font-size:12px; margin-bottom:0px;'>{r_roles[idx]}</p><b>{r_names[idx]}</b>", unsafe_allow_html=True)
                except: pass

            # ================= LỒNG KÍNH PHÂN MẢNH (REAL-TIME AUTO UPDATE) =================
            @st.fragment(run_every="15s")
            def real_time_dashboard_and_table(tab_name):
                df_content = fetch_realtime_sheet(tab_name)
                if df_content.empty: return
                
                df_context = df_content.copy()
                
                # BỘ LỌC RÁC THÔNG MINH (Chỉ xóa nếu CẢ 3 cột đều trống)
                def is_valid_row(row):
                    return str(row['STT']).strip() != "" or str(row['NỘI DUNG']).strip() != "" or str(row['NỀN TẢNG']).strip() != ""
                df_context = df_context[df_context.apply(is_valid_row, axis=1)]

                df_context['NỘI DUNG_GROUP'] = df_context['NỘI DUNG'].replace('', pd.NA).ffill()
                df_context['NỘI DUNG_GROUP'] = df_context['NỘI DUNG_GROUP'].fillna("Chưa có tên")
                
                df_context = df_context.dropna(subset=['NỘI DUNG_GROUP'])
                df_context = df_context[df_context['NỘI DUNG_GROUP'].astype(str).str.strip() != "Chưa có tên"]
                
                df_context['NHÂN SỰ'] = df_context['NHÂN SỰ'].replace('', pd.NA).ffill().fillna("Chưa phân công")
                df_context['NHÂN SỰ_NORM'] = df_context['NHÂN SỰ'].apply(normalize_btv_names)
                df_context['NGUỒN'] = df_context['NGUỒN'].replace('', pd.NA).ffill().fillna("")
                
                summary_data = []
                unique_products = df_context['NỘI DUNG_GROUP'].unique()
                valid_products = [p for p in unique_products if str(p).strip() != ""]
                
                for prod in valid_products:
                    group = df_context[df_context['NỘI DUNG_GROUP'] == prod]
                    smart_status = get_smart_status(group)
                    
                    btvs = group['NHÂN SỰ_NORM'].unique()
                    btv_name = ", ".join([b for b in btvs if b and b != "Chưa Phân Công"]) if len(btvs) > 0 else "Chưa phân công"
                    plats = group['NỀN TẢNG'].replace('', pd.NA).dropna().tolist()
                    
                    summary_data.append({
                        "Sản phẩm": prod,
                        "BTV": btv_name,
                        "Tiến độ": smart_status,
                        "Nền tảng": ", ".join(plats)
                    })
                
                df_summary = pd.DataFrame(summary_data)
                
                if not df_summary.empty:
                    st.markdown("##### 📊 BẢNG THEO DÕI & TIẾN ĐỘ CÁ NHÂN (Cập nhật trực tiếp)")
                    btv_list = [b for b in df_summary['BTV'].unique() if b not in ["Chưa Phân Công", "Chưa phân công", ""]]
                    if btv_list:
                        btv_cols = st.columns(len(btv_list))
                        for i, b in enumerate(btv_list):
                            b_df = df_summary[df_summary['BTV'] == b]
                            total_b = len(b_df)
                            done_b = len(b_df[b_df['Tiến độ'] == "✅ Đã duyệt"])
                            btv_cols[i].metric(label=b, value=f"{done_b}/{total_b}", delta="Bài đã duyệt", delta_color="normal" if done_b > 0 else "off")

                        st.write("")
                        fig_btv = px.histogram(df_summary, y="BTV", color="Tiến độ", orientation='h', 
                                               color_discrete_map={
                                                   "✅ Đã duyệt": "#28a745",
                                                   "🔴 Cần sửa": "#dc3545",
                                                   "🔄 BTV đã sửa": "#007bff",
                                                   "👀 Chờ TCSX duyệt": "#ffc107",
                                                   "⏳ Chờ LĐP duyệt": "#fd7e14",
                                                   "📝 BTV đang hoàn thiện": "#6c757d"
                                               })
                        fig_btv.update_layout(barmode='stack', yaxis_title=None, xaxis_title="Số lượng bài", margin=dict(l=0, r=0, t=10, b=0), height=200)
                        st.plotly_chart(fig_btv, use_container_width=True)

                    st.write("")
                    filter_opt = st.pills("Bộ lọc tin bài:", ["Tất cả", "🔴 Cần sửa", "🔄 BTV đã sửa", "👀 Chờ TCSX duyệt", "⏳ Chờ LĐP duyệt", "✅ Đã duyệt"], default="Tất cả")
                    
                    df_show = df_summary.copy()
                    if filter_opt != "Tất cả": df_show = df_show[df_show["Tiến độ"] == filter_opt]
                    st.dataframe(df_show, use_container_width=True, hide_index=True)

            # Gọi Fragment Lồng kính chạy
            real_time_dashboard_and_table(tab_name_current)
            st.divider()

            # ================= 4. KHU VỰC DUYỆT BÀI CHI TIẾT (BÊN NGOÀI FRAGMENT) =================
            st.markdown("##### 🛠️ KHU VỰC XỬ LÝ & DUYỆT BÀI")
            
            # Kéo lại data 1 lần tĩnh để lấy danh sách bài viết cho Form Sửa
            df_content_static = fetch_realtime_sheet(tab_name_current)
            if not df_content_static.empty:
                df_context_st = df_content_static.copy()
                def is_valid_row_st(row): return str(row['STT']).strip() != "" or str(row['NỘI DUNG']).strip() != "" or str(row['NỀN TẢNG']).strip() != ""
                df_context_st = df_context_st[df_context_st.apply(is_valid_row_st, axis=1)]
                df_context_st['NỘI DUNG_GROUP'] = df_context_st['NỘI DUNG'].replace('', pd.NA).ffill()
                df_context_st = df_context_st.dropna(subset=['NỘI DUNG_GROUP'])
                df_context_st = df_context_st[df_context_st['NỘI DUNG_GROUP'].astype(str).str.strip() != "Chưa có tên"]
                
                unique_products = df_context_st['NỘI DUNG_GROUP'].unique()
                valid_products = [p for p in unique_products if str(p).strip() != ""]
                
                sel_product = st.selectbox("📌 CHỌN BÀI VIẾT ĐỂ LÀM VIỆC:", ["-- Chọn bài viết --"] + valid_products)
                
                if sel_product and sel_product != "-- Chọn bài viết --":
                    group_df = df_context_st[df_context_st['NỘI DUNG_GROUP'] == sel_product]
                    first_row_idx = group_df.index[0]
                    first_row_data = group_df.iloc[0]
                    
                    current_text, current_link = split_text_link(first_row_data.get('LINK DUYỆT', ''))
                    
                    with st.form("edit_group_form"):
                        col_left, col_right = st.columns([1.2, 1])
                        
                        with col_left:
                            st.markdown("**:blue[1. NỘI DUNG BÀI VIẾT]**")
                            e_nd = st.text_area("Tên bài / Tiêu đề", value=first_row_data['NỘI DUNG_GROUP'], height=68)
                            
                            c_ns, c_nguon = st.columns(2)
                            e_ns = c_ns.text_input("BTV Thực hiện", value=first_row_data['NHÂN SỰ'])
                            e_ng = c_nguon.text_input("Nguồn", value=first_row_data.get('NGUỒN', ''))
                            
                            st.markdown("---")
                            if current_link: st.link_button("▶️ MỞ LINK GOOGLE DRIVE TRONG TAB MỚI", current_link, type="secondary")
                            e_texttin = st.text_area("Nội dung Text bài đăng (Caption, Hashtag...)", value=current_text, height=150)
                            e_ld = st.text_input("Cập nhật/Sửa Link Drive", value=current_link)
                            
                            st.markdown("---")
                            st.markdown("**:green[2. KHU VỰC NHẬN XÉT & CHỈ ĐẠO]**")
                            
                            all_old_tcsx = "\n".join(group_df['TCSX'].replace('', pd.NA).dropna().astype(str).tolist())
                            all_old_ldp = "\n".join(group_df['LĐP'].replace('', pd.NA).dropna().astype(str).tolist())
                            
                            c_tcsx, c_ldp = st.columns(2)
                            with c_tcsx:
                                st.caption("TỔ CHỨC SẢN XUẤT:")
                                if all_old_tcsx: st.info(all_old_tcsx)
                                else: st.caption("*Chưa có nhận xét*")
                                
                                e_tcsx_new = ""
                                e_tcsx_ok = False
                                if is_shift_tcsx:
                                    e_tcsx_new = st.text_input("TCSX Nhập góp ý (Nếu có):", key="in_tcsx")
                                    e_tcsx_ok = st.checkbox("✅ TCSX CHỐT DUYỆT BÀI", key="chk_tcsx")
                            
                            with c_ldp:
                                st.caption("LÃNH ĐẠO PHÒNG:")
                                if all_old_ldp: st.success(all_old_ldp)
                                else: st.caption("*Chưa có nhận xét*")
                                
                                e_ldp_new = ""
                                e_ldp_ok = False
                                if is_shift_ldp:
                                    e_ldp_new = st.text_input("LĐP Nhập chỉ đạo (Nếu có):", key="in_ldp")
                                    e_ldp_ok = st.checkbox("🚀 LĐP CHỐT FINAL", key="chk_ldp")

                        with col_right:
                            st.markdown("**:orange[3. TRẠNG THÁI TỪNG NỀN TẢNG]**")
                            st.caption("Các nền tảng phát sóng của bài viết này. Chỉ cập nhật khi có thay đổi giờ/link sản phẩm.")
                            
                            platform_updates = {}
                            for i, r in group_df.iterrows():
                                nentang = r['NỀN TẢNG']
                                
                                with st.expander(f"🔹 {nentang} (Status: {r['STATUS']})", expanded=False):
                                    try: idx_st = OPTS_STATUS_TRUCSO.index(r['STATUS'])
                                    except: idx_st = 0
                                    st_val = st.selectbox(f"Trạng thái", OPTS_STATUS_TRUCSO, index=idx_st, key=f"st_{i}")
                                    
                                    c_t, c_d = st.columns(2)
                                    try: 
                                        time_str = str(r.get('GIỜ ĐĂNG', '')).strip()
                                        if time_str.count(":") == 2: val_time = datetime.strptime(time_str, "%H:%M:%S").time()
                                        elif time_str.count(":") == 1: val_time = datetime.strptime(time_str, "%H:%M").time()
                                        else: val_time = None
                                    except: val_time = None
                                    time_val = c_t.time_input("Giờ xuất bản", value=val_time, key=f"ti_{i}")
                                    
                                    try: curr_d_val = datetime.strptime(str(r.get('NGÀY ĐĂNG', '')), "%d/%m/%Y").date()
                                    except: curr_d_val = datetime.now().date()
                                    date_val = c_d.date_input("Ngày", value=curr_d_val, format="DD/MM/YYYY", key=f"da_{i}")
                                    
                                    lsp_val = st.text_input("Link Sản phẩm đã lên", value=r.get('LINK SẢN PHẨM', ''), key=f"lsp_{i}")
                                    
                                    platform_updates[i] = {
                                        'STATUS': st_val, 'TIME': time_val, 'DATE': date_val, 'LINK_SP': lsp_val
                                    }

                        st.markdown("<br>", unsafe_allow_html=True)
                        submit_col1, submit_col2, submit_col3 = st.columns([1, 2, 1])
                        with submit_col2:
                            if st.form_submit_button("💾 LƯU PHÊ DUYỆT & CẬP NHẬT TRÊN SHEET", use_container_width=True, type="primary"):
                                with st.spinner("Đang đồng bộ dữ liệu..."):
                                    merged_link_duyet_update = merge_text_link(e_texttin, e_ld)
                                    final_tcsx = build_appended_comment(all_old_tcsx, e_tcsx_new, e_tcsx_ok) if is_shift_tcsx else all_old_tcsx
                                    final_ldp = build_appended_comment(all_old_ldp, e_ldp_new, e_ldp_ok) if is_shift_ldp else all_old_ldp
                                    
                                    first_sheet_row = first_row_idx + 5
                                    wks_today.update_cell(first_sheet_row, 2, e_nd)     
                                    wks_today.update_cell(first_sheet_row, 7, e_ng)     
                                    wks_today.update_cell(first_sheet_row, 8, e_ns)     
                                    wks_today.update_cell(first_sheet_row, 9, final_tcsx) 
                                    wks_today.update_cell(first_sheet_row, 10, final_ldp) 
                                    wks_today.update_cell(first_sheet_row, 14, merged_link_duyet_update)
                                    
                                    for idx, update_data in platform_updates.items():
                                        sheet_row = idx + 5
                                        wks_today.update_cell(sheet_row, 5, update_data['STATUS']) 
                                        wks_today.update_cell(sheet_row, 11, update_data['TIME'].strftime("%H:%M:%S") if update_data['TIME'] else "") 
                                        wks_today.update_cell(sheet_row, 12, update_data['DATE'].strftime("%d/%m/%Y")) 
                                        wks_today.update_cell(sheet_row, 13, update_data['LINK_SP']) 
                                        if idx != first_row_idx:
                                            wks_today.update_cell(sheet_row, 9, "")
                                            wks_today.update_cell(sheet_row, 10, "") 
                                    st.success("✅ Cập nhật thành công!"); time.sleep(1); st.rerun()

            with st.expander("➕ THÊM BÀI MỚI VÀO VỎ TRỰC SỐ", expanded=False):
                with st.form("add_news_form"):
                    c1, c2 = st.columns([3, 1])
                    ts_noidung = c1.text_area("Tên bài / Nội dung", placeholder="Nhập nội dung...")
                    ts_dinhdang = c2.selectbox("Định dạng", OPTS_DINH_DANG)
                    c3, c4, c5 = st.columns(3)
                    ts_nentang = c3.multiselect("Nền tảng xuất bản", OPTS_NEN_TANG)
                    ts_status = c4.selectbox("Trạng thái", OPTS_STATUS_TRUCSO)
                    ts_nhansu = c5.multiselect("BTV Thực hiện", list_nv, default=[curr_name] if curr_name in list_nv else None)
                    st.markdown("**NỘI DUNG CAPTION/TEXT:**")
                    ts_texttin = st.text_area("TEXT CỦA TIN", height=100)
                    ts_linkduyet = st.text_input("LINK GOOGLE DRIVE")
                    if st.form_submit_button("THÊM VÀO VỎ TRỰC SỐ", type="primary"):
                        with st.spinner("Đang lưu..."):
                            try:
                                all_rows = wks_today.get_all_values(); start_stt = max(0, len(all_rows) - 4) + 1
                                plats = ts_nentang if ts_nentang else [""]
                                merged_link_duyet = merge_text_link(ts_texttin, ts_linkduyet)
                                for p in plats:
                                    row = [start_stt, ts_noidung, ts_dinhdang, p, ts_status, "", "", ", ".join(ts_nhansu), "", "", "", date_str_display, "", merged_link_duyet]
                                    wks_today.append_row(row); last_row_idx = len(wks_today.get_all_values()); dinh_dang_dong_moi(wks_today, last_row_idx); start_stt += 1
                                st.success("ĐÃ THÊM MỚI!"); st.rerun()
                            except Exception as e: st.error(f"Lỗi: {e}")

    # ================= TAB 1: TÍNH NĂNG TRA CỨU MỚI =================
    with tabs[1]:
        st.header("🔍 TRA CỨU TIN BÀI TOÀN HỆ THỐNG")
        st.info("💡 Tính năng này giúp bạn lục tìm bài viết, người phụ trách, hoặc trạng thái trong các Vỏ trực số cũ cực kỳ nhanh chóng mà không cần mở File Excel.")
        
        search_kw = st.text_input("Nhập từ khóa cần tìm (Tên bài, Tên BTV, hoặc Nội dung chữ...):", placeholder="VD: Quang Minh, Infographic, Thúc đẩy...")
        search_days = st.slider("Phạm vi tìm kiếm (Số ngày lùi về trước):", 1, 30, 7)
        
        if st.button("🚀 BẮT ĐẦU TÌM KIẾM", type="primary"):
            if not search_kw.strip():
                st.warning("Vui lòng nhập từ khóa để tìm kiếm!")
            else:
                with st.spinner(f"Đang lật tung hồ sơ {search_days} ngày qua... Xin vui lòng đợi..."):
                    try:
                        all_ws = sh_trucso.worksheets()
                        all_ws_titles = [w.title for w in all_ws]
                        
                        all_found = []
                        for d in range(search_days + 1):
                            check_date = (get_vn_time().date() - timedelta(days=d)).strftime("%d/%m/%Y")
                            if check_date in all_ws_titles:
                                wks = sh_trucso.worksheet(check_date)
                                df_tmp = safe_read_values(wks)
                                if not df_tmp.empty:
                                    df_tmp['NỘI DUNG'] = df_tmp['NỘI DUNG'].replace('', pd.NA).ffill()
                                    df_tmp['NHÂN SỰ'] = df_tmp['NHÂN SỰ'].replace('', pd.NA).ffill()
                                    
                                    mask = df_tmp.apply(lambda row: row.astype(str).str.contains(search_kw, case=False, na=False).any(), axis=1)
                                    df_match = df_tmp[mask].copy()
                                    if not df_match.empty:
                                        df_match.insert(0, 'NGÀY TRỰC', check_date)
                                        all_found.append(df_match)
                        
                        if all_found:
                            final_df = pd.concat(all_found, ignore_index=True)
                            st.success(f"🎉 Tìm thấy {len(final_df)} kết quả phù hợp!")
                            
                            cols_to_show = ['NGÀY TRỰC', 'NỘI DUNG', 'NỀN TẢNG', 'STATUS', 'NHÂN SỰ', 'TCSX', 'LĐP']
                            final_df = final_df[[c for c in cols_to_show if c in final_df.columns]]
                            st.dataframe(final_df, use_container_width=True, hide_index=True)
                        else:
                            st.warning("📭 Không tìm thấy kết quả nào khớp với từ khóa!")
                    except Exception as e:
                        st.error(f"Lỗi tra cứu: {e}")

    # ================= CÁC TAB KHÁC =================
    with tabs[2]:
        st.header("📺 CÔNG CỤ XUẤT LỊCH PHÁT SÓNG TỰ ĐỘNG")
        st.info("Upload file Excel 'Khung Vietnam Today' để hệ thống tự động bóc tách chương trình và xuất Lịch Phát Sóng (LPS). Các slot Đệm, Thời tiết, Trailer sẽ tự động được lọc bỏ.")
        uploaded_file = st.file_uploader("📂 Tải lên file Excel Khung", type=["xlsx", "xls"])
        if uploaded_file is not None:
            try:
                xls = pd.ExcelFile(uploaded_file)
                sheet_names = xls.sheet_names
                col_sh, col_day = st.columns(2)
                selected_sheet = col_sh.selectbox("📍 Chọn Sheet tuần cần xuất", sheet_names)
                days_of_week = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
                selected_day = col_day.selectbox("📅 Chọn Ngày xuất LPS", days_of_week)
                if st.button("🚀 BẮT ĐẦU TẠO LPS", type="primary"):
                    with st.spinner(f"Đang phân tích dữ liệu {selected_day}..."):
                        df_khung = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=None)
                        day_keywords = {"Thứ Hai": ["thứ hai", "monday", "mon"], "Thứ Ba": ["thứ ba", "tuesday", "tue"], "Thứ Tư": ["thứ tư", "wednesday", "wed"], "Thứ Năm": ["thứ năm", "thursday", "thu"], "Thứ Sáu": ["thứ sáu", "friday", "fri"], "Thứ Bảy": ["thứ bảy", "saturday", "sat"], "Chủ Nhật": ["chủ nhật", "sunday", "sun"]}
                        target_col_idx = -1; keywords = day_keywords[selected_day]
                        for r_idx in range(4):
                            for c_idx in range(len(df_khung.columns)):
                                cell_val = str(df_khung.iloc[r_idx, c_idx]).lower()
                                if any(kw in cell_val for kw in keywords):
                                    target_col_idx = c_idx; break
                            if target_col_idx != -1: break
                        if target_col_idx == -1:
                            fallback_map = {"Thứ Hai": 8, "Thứ Ba": 9, "Thứ Tư": 10, "Thứ Năm": 11, "Thứ Sáu": 12, "Thứ Bảy": 13, "Chủ Nhật": 14}
                            target_col_idx = fallback_map[selected_day]
                        time_col_idx = 3 
                        lps_data = []
                        for r_idx in range(5, len(df_khung)):
                            time_val = df_khung.iloc[r_idx, time_col_idx]
                            content_val = df_khung.iloc[r_idx, target_col_idx]
                            if not pd.isna(content_val) and str(content_val).strip() != "":
                                title, desc = parse_khung_cell(content_val)
                                formatted_time = format_time_col(time_val)
                                if title:
                                    exclude_keywords = ["weather forecast", "đệm", "filler", "trailer"]
                                    title_lower = title.lower()
                                    if any(kw in title_lower for kw in exclude_keywords): continue 
                                    lps_data.append({"Giờ phát sóng (hh:mm:ss)": formatted_time, "Tiêu đề": title, "Mô tả": desc})
                        if lps_data:
                            df_lps = pd.DataFrame(lps_data)
                            st.success(f"✅ Đã xử lý thành công LPS cho {selected_day}!")
                            edited_lps = st.data_editor(df_lps, use_container_width=True, hide_index=True)
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='xlsxwriter') as writer: edited_lps.to_excel(writer, index=False, sheet_name=selected_day)
                            st.download_button(label="📥 TẢI FILE EXCEL LPS VỀ MÁY", data=output.getvalue(), file_name=f"LPS_VNTD_{selected_day}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
                        else: st.warning("Không tìm thấy dữ liệu phát sóng.")
            except: pass

    with tabs[3]:
        st.header(f"📝 CHECKLIST CỦA: {curr_name.upper()}")
        try: wks_canhan = sh_main.worksheet("ViecCaNhan")
        except: 
            wks_canhan = sh_main.add_worksheet("ViecCaNhan", 1000, 5); wks_canhan.append_row(["User", "TenViec", "Ngay", "TrangThai", "GhiChu"])
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
            df_my_view = pd.DataFrame(filtered_tasks); df_my_view['Xong'] = df_my_view['TrangThai'].apply(lambda x: True if str(x).upper() == "TRUE" else False)
            edited_df = st.data_editor(df_my_view[['TenViec', 'Ngay', 'GhiChu', 'Xong']], column_config={"Xong": st.column_config.CheckboxColumn("Hoàn thành", default=False), "TenViec": st.column_config.TextColumn("Nội dung công việc", width="medium"), "Ngay": st.column_config.TextColumn("Ngày", disabled=True), "GhiChu": st.column_config.TextColumn("Ghi chú")}, hide_index=True, key="editor_checklist")
            if st.button("💾 CẬP NHẬT CHECKLIST"):
                with st.spinner("Đang lưu..."):
                    try:
                        all_values = wks_canhan.get_all_values()
                        for i, row in edited_df.iterrows():
                            for idx, sheet_row in enumerate(all_values):
                                if idx == 0: continue
                                if sheet_row[0] == curr_name and sheet_row[1] == row['TenViec'] and sheet_row[2] == row['Ngay']:
                                    wks_canhan.update_cell(idx + 1, 4, "TRUE" if row['Xong'] else "FALSE")
                                    wks_canhan.update_cell(idx + 1, 5, row['GhiChu']); break
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
                            t_name = sel.split(" (")[0]; row = my_tasks_cv[my_tasks_cv['TenViec'] == t_name].iloc[0]
                            try: dl = row['Deadline'].split(" ")[1]
                            except: dl = today.strftime("%d/%m/%Y")
                            try: wks_canhan = sh_main.worksheet("ViecCaNhan")
                            except: wks_canhan = sh_main.add_worksheet("ViecCaNhan", 1000, 5); wks_canhan.append_row(["User", "TenViec", "Ngay", "TrangThai", "GhiChu"])
                            wks_canhan.append_row([curr_name, t_name, dl, "FALSE", "Từ hệ thống chung"]); st.success("Xong!"); clear_cache_and_rerun()

    with tabs[4]:
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
                        dl_fmt = f"{tv_time.strftime('%H:%M:%S')} {tv_date.strftime('%d/%m/%Y')}"
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
                        with st.form("f_edit_cv"):
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

    with tabs[5]:
        if role == 'LanhDao':
            with st.form("new_da"):
                d_n = st.text_input("TÊN DỰ ÁN"); d_m = st.text_area("MÔ TẢ"); d_l = st.multiselect("PHỤ TRÁCH", list_nv)
                if st.form_submit_button("TẠO DỰ ÁN"): 
                    with st.spinner("Đang tạo..."):
                        sh_main.worksheet("DuAn").append_row([d_n, d_m, "Đang chạy", ",".join(d_l)]); st.success("Xong!"); clear_cache_and_rerun()
        st.dataframe(df_duan.rename(columns=VN_COLS_DUAN), use_container_width=True)

    with tabs[6]:
        st.header("📅 LỊCH LÀM VIỆC & DEADLINE")
        if not df_cv.empty:
            task_list = []
            for i, r in df_cv.iterrows():
                try:
                    dl_str = r['Deadline']; dl_dt = datetime.strptime(dl_str, "%H:%M:%S %d/%m/%Y")
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

    with tabs[7]:
        tk = st.selectbox("TK GỬI:", range(10), format_func=lambda x:f"TK {x}")
        to = st.multiselect("ĐẾN:", df_users['Email'].tolist())
        sub = st.text_input("TIÊU ĐỀ"); bod = st.text_area("Nội dung")
        if st.button("GỬI EMAIL"): st.markdown(f'<script>window.open("https://mail.google.com/mail/u/{tk}/?view=cm&fs=1&to={",".join(to)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(bod)}", "_blank");</script>', unsafe_allow_html=True)

    if role == 'LanhDao':
        with tabs[8]:
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
        with tabs[9]:
            if not df_log.empty: st.dataframe(df_log.iloc[::-1].rename(columns=VN_COLS_LOG), use_container_width=True)
