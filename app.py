import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components
import urllib.parse
from datetime import datetime, date, timedelta
import pytz
import requests
import random
import plotly.express as px # Thư viện vẽ biểu đồ & lịch

# --- THƯ VIỆN ĐỊNH DẠNG SHEET ---
from gspread_formatting import *

# ================= CẤU HÌNH HỆ THỐNG =================
st.set_page_config(page_title="Phòng Nội dung số và Truyền thông", page_icon="🏢", layout="wide")

# --- TÊN FILE GOOGLE SHEET ---
SHEET_MAIN = "HeThongQuanLy" 
SHEET_TRUCSO = "VoTrucSo"

# --- CẤU HÌNH THỜI GIAN VN ---
def get_vn_time():
    return datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))

# --- HÀM LẤY THỜI TIẾT & LỜI KHUYÊN ---
def get_weather_and_advice():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=21.0285&longitude=105.8542&current_weather=true&timezone=Asia%2FBangkok"
        res = requests.get(url, timeout=3).json()
        temp = res['current_weather']['temperature']
        wcode = res['current_weather']['weathercode']
        
        condition = "Có mây"
        advice = "Chúc bạn một ngày làm việc năng suất!"
        
        if wcode in [0, 1]: 
            condition = "Nắng đẹp ☀️"; advice = "Trời đẹp! Năng lượng tích cực để sáng tạo nhé."
        elif wcode in [2, 3]: 
            condition = "Nhiều mây ☁️"; advice = "Thời tiết dịu mát, tập trung cao độ nào!"
        elif wcode in [51, 53, 55, 61, 63, 65]: 
            condition = "Có mưa 🌧️"; advice = "Trời mưa, đường trơn. Các BTV đi lại cẩn thận nhé!"
        elif wcode >= 95: 
            condition = "Giông bão ⛈️"; advice = "Thời tiết xấu. Hạn chế ra ngoài."
        
        if temp > 35: advice = "Trời nóng, nhớ uống đủ nước nhé các BTV!"
        if temp < 15: advice = "Trời lạnh, nhớ mặc ấm để giữ giọng đọc tốt nhé!"

        return f"{temp}°C - {condition}", advice
    except:
        return "--°C", "Luôn giữ vững đam mê nghề báo nhé!"

# --- 1. DANH SÁCH CHỨC DANH (ROLES) CHUẨN ---
ROLES_HEADER = [
    "Lãnh đạo Ban", "Trực thư ký tòa soạn", "Trực quản trị MXH + Video biên tập",
    "Trực lịch phát sóng", "Trực thư ký tòa soạn", "Trực sản xuất video clip, LPS",
    "Trực quản trị cổng TTĐT", "Trực quản trị app"
]

# --- 2. CÁC TÙY CHỌN CHUẨN ---
OPTS_DINH_DANG = ["Bài dịch", "Video biên tập", "Sản phẩm sản xuất"]
OPTS_NEN_TANG = ["Facebook", "Youtube", "TikTok", "Web + App", "Instagram"]

OPTS_STATUS_TRUCSO = [
    "Chờ xử lý", "Đang biên tập", "Gửi duyệt TCSX", "Yêu cầu sửa (TCSX)", 
    "Gửi duyệt LĐP", "Yêu cầu sửa (LĐP)", "Đã duyệt/Chờ đăng", "Đã đăng", "Hủy"
]

OPTS_TRANG_THAI_VIEC = ["Đã giao", "Đang thực hiện", "Chờ duyệt", "Hoàn thành", "Hủy"]

# --- 3. TIÊU ĐỀ CỘT ---
CONTENT_HEADER = [
    "STT", "NỘI DUNG", "ĐỊNH DẠNG", "NỀN TẢNG", "STATUS", "CHECK", 
    "NGUỒN", "NHÂN SỰ", "Ý KIẾN ĐIỀU CHỈNH", "LINK DUYỆT", 
    "GIỜ ĐĂNG", "NGÀY ĐĂNG", "LINK SẢN PHẨM"
]

# --- TỪ ĐIỂN HIỂN THỊ ---
VN_COLS_VIEC = {"TenViec": "Tên công việc", "DuAn": "Dự án", "Deadline": "Hạn chót", "NguoiPhuTrach": "Người thực hiện", "TrangThai": "Trạng thái", "LinkBai": "Link SP", "GhiChu": "Ghi chú"}
VN_COLS_TRUCSO = {
    "STT": "STT", "NỘI DUNG": "Nội dung", "ĐỊNH DẠNG": "Định dạng", "NỀN TẢNG": "Nền tảng", 
    "STATUS": "Trạng thái", "NGUỒN": "Nguồn", "NHÂN SỰ": "Nhân sự", "Ý KIẾN ĐIỀU CHỈNH": "Ý kiến", 
    "LINK DUYỆT": "Link Duyệt", "GIỜ ĐĂNG": "Giờ đăng", "NGÀY ĐĂNG": "Ngày đăng", "LINK SẢN PHẨM": "Link SP"
}
VN_COLS_DUAN = {"TenDuAn": "Tên Dự án", "MoTa": "Mô tả", "TrangThai": "Trạng thái", "TruongNhom": "Điều phối"}
VN_COLS_LOG = {"ThoiGian": "Thời gian", "NguoiDung": "Người dùng", "HanhDong": "Hành động", "ChiTiet": "Chi tiết"}

# ================= 1. BACKEND =================
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"🔴 Lỗi chứng thực: {e}")
        st.stop()

def ket_noi_main():
    client = get_gspread_client()
    try: return client.open(SHEET_MAIN)
    except: st.error(f"Lỗi kết nối '{SHEET_MAIN}'"); st.stop()

def ket_noi_trucso():
    client = get_gspread_client()
    try: return client.open(SHEET_TRUCSO)
    except: st.error(f"Lỗi kết nối '{SHEET_TRUCSO}'"); st.stop()

def lay_du_lieu_trucso(wks):
    try:
        data = wks.get_all_values()
        if len(data) > 4:
            headers = data[3] 
            rows = data[4:]   
            return pd.DataFrame(rows, columns=headers)
        return pd.DataFrame(columns=CONTENT_HEADER)
    except: return pd.DataFrame()

def lay_du_lieu_main(wks):
    try: return pd.DataFrame(wks.get_all_records())
    except: return pd.DataFrame()

def ghi_nhat_ky(sh_main, nguoi_dung, hanh_dong, chi_tiet):
    try:
        wks = sh_main.worksheet("NhatKy")
        thoi_gian = get_vn_time().strftime("%H:%M %d/%m/%Y")
        wks.append_row([thoi_gian, nguoi_dung, hanh_dong, chi_tiet])
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
    set_column_width(wks, 'A', 40); set_column_width(wks, 'B', 300); set_column_width(wks, 'C', 100)
    set_column_width(wks, 'D', 100); set_column_width(wks, 'E', 130); set_column_width(wks, 'F', 50)
    set_column_width(wks, 'G', 80); set_column_width(wks, 'H', 120); set_column_width(wks, 'I', 120)
    set_column_width(wks, 'J', 100); set_column_width(wks, 'K', 70); set_column_width(wks, 'L', 80); set_column_width(wks, 'M', 100)
    format_cell_range(wks, 'B5:B100', CellFormat(wrapStrategy='WRAP', verticalAlignment='TOP'))

# ================= 2. AUTH =================
if 'dang_nhap' not in st.session_state:
    st.session_state['dang_nhap'] = False
    st.session_state['user_info'] = {}

sh_main = ket_noi_main()

if not st.session_state['dang_nhap']:
    st.markdown("## 🔐 CỔNG ĐĂNG NHẬP")
    with st.form("login"):
        user = st.text_input("Tên đăng nhập")
        pwd = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Đăng nhập"):
            users = lay_du_lieu_main(sh_main.worksheet("TaiKhoan"))
            if not users.empty:
                u_row = users[(users['TenDangNhap'].astype(str)==user) & (users['MatKhau'].astype(str)==pwd)]
                if not u_row.empty:
                    st.session_state['dang_nhap'] = True
                    st.session_state['user_info'] = u_row.iloc[0].to_dict()
                    ghi_nhat_ky(sh_main, u_row.iloc[0]['HoTen'], "Đăng nhập", "Success")
                    st.rerun()
                else: st.error("Sai thông tin!")
            else: st.error("Lỗi dữ liệu Tài khoản.")
else:
    u_info = st.session_state['user_info']
    curr_name = u_info['HoTen']
    role = u_info.get('VaiTro', 'NhanVien')
    
    with st.sidebar:
        st.success(f"Xin chào: **{curr_name}**\n\nChúc bạn một ngày làm việc vui vẻ và hiệu quả nhé! ❤️")
        
        weather_info, advice_msg = get_weather_and_advice()
        st.markdown("---")
        st.markdown(f"**🌤️ Hà Nội:** {weather_info}")
        st.info(f"💡 **Lời khuyên:** {advice_msg}")
        st.markdown("---")

        if st.button("Đăng xuất"):
            st.session_state['dang_nhap'] = False; st.rerun()

    st.title("🏢 PHÒNG NỘI DUNG SỐ & TRUYỀN THÔNG")
    
    sh_trucso = ket_noi_trucso()
    
    # --- CẤU HÌNH MENU TAB ---
    # Lãnh đạo: Thấy Dashboard, Nhật ký
    # Nhân viên: Không thấy
    if role == 'LanhDao':
        tabs = st.tabs(["✅ Quản lý Công việc", "🗂️ Quản lý Dự án", "📝 Vỏ Trực Số", "📅 Lịch làm việc", "📊 Dashboard", "📧 Email", "📜 Nhật ký"])
    else:
        tabs = st.tabs(["✅ Quản lý Công việc", "🗂️ Quản lý Dự án", "📝 Vỏ Trực Số", "📅 Lịch làm việc", "📧 Email"])

    df_duan = lay_du_lieu_main(sh_main.worksheet("DuAn"))
    list_duan = df_duan['TenDuAn'].tolist() if not df_duan.empty else []
    df_users = lay_du_lieu_main(sh_main.worksheet("TaiKhoan"))
    list_nv = df_users['HoTen'].tolist() if not df_users.empty else []

    # ================= TAB 1: CÔNG VIỆC =================
    with tabs[0]:
        st.caption("Quản lý đầu việc dài hạn.")
        with st.expander("➕ TẠO VIỆC DỰ ÁN", expanded=False):
            c1, c2 = st.columns(2)
            tv_ten = c1.text_input("Tên việc"); tv_duan = c1.selectbox("Dự án", list_duan)
            now_vn = get_vn_time()
            tv_time = c1.time_input("Giờ DL", value=now_vn.time()); tv_date = c1.date_input("Ngày DL", value=now_vn.date(), format="DD/MM/YYYY")
            tv_nguoi = c2.multiselect("Biên tập viên thực hiện", list_nv); tv_ghichu = c2.text_area("Yêu cầu", height=100)
            
            ct1, ct2 = st.columns([2,1])
            tk_gui = ct1.selectbox("Gửi Gmail:", range(10), format_func=lambda x: f"TK {x}")
            ct2.markdown(f'<br><a href="https://mail.google.com/mail/u/{tk_gui}" target="_blank">Check Mail</a>', unsafe_allow_html=True)
            opt_nv = st.checkbox("Gửi BTV", True)
            
            if st.button("💾 Lưu & Gửi"):
                try:
                    dl_fmt = f"{tv_time.strftime('%H:%M')} {tv_date.strftime('%d/%m/%Y')}"
                    sh_main.worksheet("CongViec").append_row([tv_ten, tv_duan, dl_fmt, ", ".join(tv_nguoi), "Đã giao", "", tv_ghichu, curr_name])
                    ghi_nhat_ky(sh_main, curr_name, "Tạo việc", tv_ten)
                    st.success("Xong!")
                    if opt_nv and tv_nguoi:
                        mails = df_users[df_users['HoTen'].isin(tv_nguoi)]['Email'].tolist()
                        mails = [m for m in mails if str(m).strip()]
                        if mails: st.markdown(f'<a href="https://mail.google.com/mail/u/{tk_gui}/?view=cm&fs=1&to={",".join(mails)}&su={urllib.parse.quote(tv_ten)}&body={urllib.parse.quote(tv_ghichu)}" target="_blank">📧 Gửi BTV</a>', unsafe_allow_html=True)
                except Exception as e: st.error(str(e))

        st.divider()
        da_filter = st.selectbox("Lọc Dự án:", ["All"]+list_duan)
        df_cv = lay_du_lieu_main(sh_main.worksheet("CongViec"))
        if not df_cv.empty:
            if da_filter != "All": df_cv = df_cv[df_cv['DuAn']==da_filter]
            edits = {f"{r['TenViec']} ({i+2})": {"id": i, "lv": check_quyen(curr_name, role, r, df_duan)} for i, r in df_cv.iterrows() if check_quyen(curr_name, role, r, df_duan)>0}
            if edits:
                with st.expander("🛠️ Cập nhật trạng thái", expanded=True):
                    s_task = st.selectbox("Chọn việc:", list(edits.keys()))
                    if s_task:
                        row_idx = edits[s_task]['id']; lv = edits[s_task]['lv']; r_dat = df_cv.iloc[row_idx]
                        dis = (lv == 1)
                        with st.form("f_edit"):
                            ce1, ce2 = st.columns(2)
                            e_ten = ce1.text_input("Tên", r_dat['TenViec'], disabled=dis)
                            e_ng = ce1.text_input("Biên tập viên", r_dat['NguoiPhuTrach'], disabled=dis)
                            e_lk = ce1.text_input("Link", r_dat.get('LinkBai',''))
                            e_dl = ce2.text_input("Deadline", r_dat.get('Deadline',''), disabled=dis)
                            e_st = ce2.selectbox("Trạng thái", OPTS_TRANG_THAI_VIEC, index=OPTS_TRANG_THAI_VIEC.index(r_dat.get('TrangThai','Đã giao')) if r_dat.get('TrangThai') in OPTS_TRANG_THAI_VIEC else 0)
                            e_nt = ce2.text_area("Ghi chú", r_dat.get('GhiChu',''))
                            if st.form_submit_button("Cập nhật"):
                                w = sh_main.worksheet("CongViec"); rn = row_idx + 2
                                w.update_cell(rn,1,e_ten); w.update_cell(rn,3,e_dl); w.update_cell(rn,4,e_ng)
                                w.update_cell(rn,5,e_st); w.update_cell(rn,6,e_lk); w.update_cell(rn,7,e_nt)
                                st.success("Updated!"); st.rerun()
            st.dataframe(df_cv.drop(columns=['NguoiTao'], errors='ignore').rename(columns=VN_COLS_VIEC), use_container_width=True, hide_index=True)
        else: st.info("Chưa có công việc nào.")

    # ================= TAB 2: DỰ ÁN =================
    with tabs[1]:
        if role == 'LanhDao':
            with st.form("new_da"):
                d_n = st.text_input("Tên DA"); d_m = st.text_area("Mô tả"); d_l = st.multiselect("Lead", list_nv)
                if st.form_submit_button("Tạo DA"): sh_main.worksheet("DuAn").append_row([d_n, d_m, "Đang chạy", ",".join(d_l)]); st.rerun()
        st.dataframe(df_duan.rename(columns=VN_COLS_DUAN), use_container_width=True)

    # ================= TAB 3: VỞ TRỰC SỐ =================
    with tabs[2]:
        today_vn = get_vn_time()
        tab_name_today = today_vn.strftime("%d-%m-%Y")
        st.header(f"📝 Vỏ Trực Số Ngày: {tab_name_today}")

        tab_exists = False
        try: wks_today = sh_trucso.worksheet(tab_name_today); tab_exists = True
        except gspread.WorksheetNotFound: tab_exists = False

        is_shift_admin = (role in ['LanhDao', 'ToChucSanXuat'])
        
        if is_shift_admin:
            with st.expander("⚙️ QUẢN LÝ VỎ / EKIP TRỰC (Admin)", expanded=not tab_exists):
                if not tab_exists:
                    st.warning("Chưa có sổ trực hôm nay.")
                    with st.form("init_roster"):
                        cols = st.columns(3)
                        roster_vals = []
                        for i, r_t in enumerate(ROLES_HEADER):
                            with cols[i%3]: 
                                val = st.selectbox(f"**{r_t}**", ["--"]+list_nv, key=f"cr_{i}")
                                roster_vals.append(val if val != "--" else "")
                        if st.form_submit_button("🚀 Tạo Vỏ Trực Mới"):
                            try:
                                w = sh_trucso.add_worksheet(title=tab_name_today, rows=100, cols=20)
                                w.update_cell(1, 1, f"VỎ TRỰC SỐ VIETNAM TODAY {tab_name_today}")
                                w.update_cell(2, 1, "DANH SÁCH TRỰC:")
                                for i, v in enumerate(ROLES_HEADER): w.update_cell(2, i+2, v)
                                w.update_cell(3, 1, "NHÂN SỰ:")
                                for i, v in enumerate(roster_vals): w.update_cell(3, i+2, v)
                                w.append_row(CONTENT_HEADER)
                                st.info("Đang tô màu và kẻ bảng...")
                                dinh_dang_dep(w)
                                st.success("Đã tạo!"); st.rerun()
                            except Exception as e: st.error(str(e))
                else:
                    st.success("Đã có Vỏ trực. Quản lý Ekip bên dưới:")
                    if st.button("📧 Gửi Email thông báo cho Ekip"):
                        try:
                            roster_names = wks_today.row_values(3)[1:]
                            emails_to_send = []
                            for name in roster_names:
                                if name and name != "--":
                                    found = df_users[df_users['HoTen'] == name]['Email'].values
                                    if len(found) > 0 and str(found[0]).strip():
                                        emails_to_send.append(found[0])
                            if emails_to_send:
                                sub = f"[THÔNG BÁO] Lịch trực số ngày {tab_name_today}"
                                body = f"Chào các BTV,\n\nCác bạn có lịch trực số ngày {tab_name_today}.\nVui lòng truy cập hệ thống để nắm thông tin chi tiết.\n\nTrân trọng."
                                link = f"https://mail.google.com/mail/?view=cm&fs=1&to={','.join(emails_to_send)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(body)}"
                                st.markdown(f'<a href="{link}" target="_blank" style="background:#EA4335;color:white;padding:10px 15px;text-decoration:none;border-radius:5px;font-weight:bold;">🚀 Mở Gmail gửi ngay</a>', unsafe_allow_html=True)
                            else:
                                st.warning("Không tìm thấy email của nhân sự nào trong kíp trực.")
                        except Exception as e:
                            st.error(f"Lỗi: {e}")

                    st.divider()
                    tab_edit_vo, tab_del_vo = st.tabs(["Sửa Ekip Trực", "Xóa Sổ Hôm Nay"])
                    with tab_edit_vo:
                        curr_names = wks_today.row_values(3)[1:]
                        while len(curr_names) < len(ROLES_HEADER): curr_names.append("")
                        with st.form("edit_roster_form"):
                            new_roster_vals = []
                            cols = st.columns(3)
                            for i, r_t in enumerate(ROLES_HEADER):
                                with cols[i%3]:
                                    curr_val = curr_names[i] if i < len(curr_names) else ""
                                    idx = list_nv.index(curr_val) if curr_val in list_nv else 0
                                    val = st.selectbox(f"{r_t}", ["--"]+list_nv, index=idx+1 if curr_val in list_nv else 0, key=f"ed_{i}")
                                    new_roster_vals.append(val if val != "--" else "")
                            if st.form_submit_button("Cập nhật Ekip"):
                                for i, v in enumerate(new_roster_vals): wks_today.update_cell(3, i+2, v)
                                st.success("Đã cập nhật!"); st.rerun()
                    with tab_del_vo:
                        st.error("⚠️ Hành động này sẽ xóa dữ liệu hôm nay!")
                        if st.button("Xác nhận XÓA SỔ hôm nay"):
                            sh_trucso.del_worksheet(wks_today)
                            st.success("Đã xóa sổ!"); st.rerun()

        if tab_exists:
            with st.expander("ℹ️ Ekip trực hôm nay (Nhấn để xem)", expanded=True):
                try:
                    r_names = wks_today.row_values(3)[1:]
                    r_roles = wks_today.row_values(2)[1:]
                    if r_names:
                        c1, c2, c3, c4 = st.columns(4); cols_1 = [c1, c2, c3, c4]
                        for i in range(4):
                            if i < len(r_names):
                                with cols_1[i]:
                                    st.markdown(f"<p style='color:gray; font-size:13px; margin-bottom:0px;'>{r_roles[i]}</p>", unsafe_allow_html=True)
                                    st.markdown(f"<p style='color:#31333F; font-size:16px; font-weight:bold;'>{r_names[i]}</p>", unsafe_allow_html=True)
                        st.write("---")
                        c5, c6, c7, c8 = st.columns(4); cols_2 = [c5, c6, c7, c8]
                        for i in range(4):
                            idx = i + 4
                            if idx < len(r_names):
                                with cols_2[i]:
                                    st.markdown(f"<p style='color:gray; font-size:13px; margin-bottom:0px;'>{r_roles[idx]}</p>", unsafe_allow_html=True)
                                    st.markdown(f"<p style='color:#31333F; font-size:16px; font-weight:bold;'>{r_names[idx]}</p>", unsafe_allow_html=True)
                except: st.caption("Lỗi đọc ekip.")

            st.markdown("### ➕ Thêm Tin Bài / Đầu Mục")
            with st.form("add_news_form"):
                c1, c2 = st.columns([3, 1])
                ts_noidung = c1.text_area("Nội dung", placeholder="Nhập nội dung...")
                ts_dinhdang = c2.selectbox("Định dạng", OPTS_DINH_DANG)
                
                c3, c4, c5 = st.columns(3)
                ts_nentang = c3.multiselect("Nền tảng (Tách dòng)", OPTS_NEN_TANG)
                ts_status = c4.selectbox("Trạng thái", OPTS_STATUS_TRUCSO)
                ts_nhansu = c5.multiselect("Biên tập viên", list_nv, default=[curr_name] if curr_name in list_nv else None)
                
                c6, c7, c8 = st.columns(3)
                ts_nguon = c6.text_input("Nguồn")
                ts_giodang = c7.time_input("Giờ đăng (DK)", value=None)
                ts_ngaydang = c8.date_input("Ngày đăng", value=today_vn.date(), format="DD/MM/YYYY")
                
                c9, c10 = st.columns(2)
                ts_linkduyet = c9.text_input("Link Duyệt")
                ts_linksp = c10.text_input("Link Sản phẩm")
                ts_ykien = st.text_input("Ý kiến / Ghi chú")

                if st.form_submit_button("Lưu vào sổ", type="primary"):
                    try:
                        all_rows = wks_today.get_all_values()
                        start_stt = max(0, len(all_rows) - 4) + 1
                        plats = ts_nentang if ts_nentang else [""]
                        for p in plats:
                            row = [
                                start_stt, ts_noidung, ts_dinhdang, p, ts_status, "", ts_nguon, 
                                ", ".join(ts_nhansu), ts_ykien, ts_linkduyet, 
                                ts_giodang.strftime("%H:%M") if ts_giodang else "", 
                                ts_ngaydang.strftime("%d/%m/%Y"), 
                                ts_linksp
                            ]
                            wks_today.append_row(row)
                            start_stt += 1
                        st.success("Đã lưu!"); st.rerun()
                    except Exception as e: st.error(f"Lỗi: {e}")

            st.divider()
            st.markdown("##### 📋 Danh sách tin bài")
            df_content = lay_du_lieu_trucso(wks_today)
            if not df_content.empty:
                with st.expander("🛠️ Cập nhật / Chỉnh sửa dòng tin", expanded=False):
                    st.info("""
                    **ℹ️ QUY TRÌNH KIỂM DUYỆT NỘI DUNG:**
                    1. **Chờ xử lý** → BTV nhận việc.
                    2. **Đang biên tập** → BTV đang làm.
                    3. **Gửi duyệt TCSX** → BTV gửi bài.
                    4. **Yêu cầu sửa (TCSX/LĐP)** → Cần chỉnh sửa lại.
                    5. **Gửi duyệt LĐP** → Chuyển lên Lãnh đạo Phòng.
                    6. **Đã duyệt/Chờ đăng** → Sẵn sàng publish.
                    """)
                    
                    edit_opts = [f"{r['STT']} - {r['NỘI DUNG'][:30]}... ({r['NỀN TẢNG']})" for i, r in df_content.iterrows()]
                    sel_news = st.selectbox("Chọn dòng tin cần sửa:", edit_opts)
                    if sel_news:
                        idx_news = edit_opts.index(sel_news); r_news = df_content.iloc[idx_news]
                        with st.form("edit_news_form"):
                            ec1, ec2 = st.columns([3, 1])
                            e_nd = ec1.text_area("Nội dung", value=r_news['NỘI DUNG'])
                            try: idx_dd = OPTS_DINH_DANG.index(r_news['ĐỊNH DẠNG'])
                            except: idx_dd = 0
                            e_dd = ec2.selectbox("Định dạng", OPTS_DINH_DANG, index=idx_dd)
                            
                            try: idx_st = OPTS_STATUS_TRUCSO.index(r_news['STATUS'])
                            except: idx_st = 0
                            e_st = ec2.selectbox("Trạng thái", OPTS_STATUS_TRUCSO, index=idx_st)
                            
                            ec3, ec4 = st.columns(2)
                            e_nt = ec3.text_input("Nền tảng", value=r_news['NỀN TẢNG'])
                            e_ns = ec4.text_input("Biên tập viên", value=r_news['NHÂN SỰ'])
                            
                            ec5, ec6, ec7 = st.columns(3)
                            e_ld = ec5.text_input("Link Duyệt", value=r_news['LINK DUYỆT'])
                            
                            curr_d_val = datetime.now().date()
                            try: 
                                if r_news['NGÀY ĐĂNG']: curr_d_val = datetime.strptime(r_news['NGÀY ĐĂNG'], "%d/%m/%Y").date()
                            except: pass
                            e_ndang = ec6.date_input("Ngày đăng", value=curr_d_val, format="DD/MM/YYYY")
                            
                            e_lsp = ec7.text_input("Link SP", value=r_news['LINK SẢN PHẨM'])
                            e_yk = st.text_input("Ý kiến (Ghi chú sửa/duyệt)", value=r_news['Ý KIẾN ĐIỀU CHỈNH'])
                            
                            if st.form_submit_button("Cập nhật dòng tin"):
                                r_sh = idx_news + 5 
                                wks_today.update_cell(r_sh, 2, e_nd); wks_today.update_cell(r_sh, 3, e_dd)
                                wks_today.update_cell(r_sh, 4, e_nt); wks_today.update_cell(r_sh, 5, e_st)
                                wks_today.update_cell(r_sh, 8, e_ns); wks_today.update_cell(r_sh, 9, e_yk)
                                wks_today.update_cell(r_sh, 10, e_ld)
                                wks_today.update_cell(r_sh, 12, e_ndang.strftime("%d/%m/%Y"))
                                wks_today.update_cell(r_sh, 13, e_lsp)
                                st.success("Đã cập nhật!"); st.rerun()
                
                st.dataframe(df_content, use_container_width=True, hide_index=True, column_config={"LINK DUYỆT": st.column_config.LinkColumn(display_text="Xem"),"LINK SẢN PHẨM": st.column_config.LinkColumn(display_text="Link"),})
            else: st.info("Chưa có tin bài nào.")

    # ================= TAB 4: LỊCH LÀM VIỆC (MỚI) =================
    with tabs[3]:
        st.header("📅 Lịch làm việc & Deadline")
        st.caption("Theo dõi tiến độ công việc trực quan.")
        
        # 1. Lấy dữ liệu từ Sheet Công Việc
        df_tasks = lay_du_lieu_main(sh_main.worksheet("CongViec"))
        
        if not df_tasks.empty:
            # Xử lý ngày tháng để vẽ biểu đồ
            task_list = []
            for i, r in df_tasks.iterrows():
                try:
                    # Parse Deadline: "HH:MM DD/MM/YYYY"
                    dl_str = r['Deadline']
                    dl_dt = datetime.strptime(dl_str, "%H:%M %d/%m/%Y")
                    # Start date: giả định là ngày tạo hoặc hôm nay nếu không có
                    # Để đơn giản cho Gantt, ta lấy start = deadline - 2 ngày (hoặc ngày tạo nếu có lưu)
                    start_dt = dl_dt - timedelta(days=2) 
                    
                    # Phân quyền xem
                    if role != 'LanhDao' and curr_name not in r['NguoiPhuTrach']:
                        continue
                    
                    task_list.append({
                        "Task": r['TenViec'],
                        "Start": start_dt,
                        "Finish": dl_dt,
                        "Assignee": r['NguoiPhuTrach'],
                        "Status": r['TrangThai'],
                        "Project": r['DuAn']
                    })
                except:
                    continue # Bỏ qua lỗi format date
            
            if task_list:
                df_gantt = pd.DataFrame(task_list)
                
                # Vẽ biểu đồ Gantt
                fig = px.timeline(
                    df_gantt, 
                    x_start="Start", 
                    x_end="Finish", 
                    y="Assignee", 
                    color="Status", 
                    hover_data=["Task", "Project"],
                    title="Timeline Công việc (Dự kiến)",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig.update_yaxes(autorange="reversed") # Đảo ngược để việc mới nhất lên trên
                st.plotly_chart(fig, use_container_width=True)
                
                st.divider()
                st.subheader("Chi tiết Deadline sắp tới")
                st.dataframe(df_gantt[['Task', 'Finish', 'Assignee', 'Status']], use_container_width=True)
            else:
                st.info("Không có dữ liệu công việc hợp lệ để hiển thị.")
        else:
            st.info("Chưa có công việc nào.")

    # ================= TAB 5: DASHBOARD (MỚI - CHỈ LÃNH ĐẠO) =================
    if role == 'LanhDao':
        with tabs[4]:
            st.header("📊 Dashboard Tổng quan")
            
            # 1. Thống kê từ Công việc (CongViec)
            if not df_cv.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Biểu đồ Trạng thái
                    status_counts = df_cv['TrangThai'].value_counts().reset_index()
                    status_counts.columns = ['Trạng thái', 'Số lượng']
                    fig_pie = px.pie(status_counts, values='Số lượng', names='Trạng thái', title='Tỷ lệ Trạng thái Công việc', hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    # Biểu đồ Năng suất (Ai làm nhiều việc nhất)
                    # Cần tách tên người vì 1 việc có thể nhiều người làm
                    all_staff = []
                    for s in df_cv['NguoiPhuTrach']:
                        names = [n.strip() for n in s.split(',')]
                        all_staff.extend(names)
                    
                    staff_counts = pd.Series(all_staff).value_counts().reset_index()
                    staff_counts.columns = ['BTV', 'Số việc']
                    fig_bar = px.bar(staff_counts, x='BTV', y='Số việc', title='Năng suất nhân sự (Số đầu việc)', color='BTV')
                    st.plotly_chart(fig_bar, use_container_width=True)

            # 2. Thống kê từ Vỏ Trực Số Hôm nay (VoTrucSo)
            if tab_exists and not df_content.empty:
                st.divider()
                st.subheader(f"Thống kê Tin bài ngày {tab_name_today}")
                
                c3, c4 = st.columns(2)
                with c3:
                    # Nền tảng
                    plat_counts = df_content['NỀN TẢNG'].value_counts().reset_index()
                    plat_counts.columns = ['Nền tảng', 'Số lượng']
                    fig_plat = px.bar(plat_counts, x='Số lượng', y='Nền tảng', orientation='h', title='Phân bố Nền tảng hôm nay')
                    st.plotly_chart(fig_plat, use_container_width=True)
                
                with c4:
                    # Trạng thái tin bài
                    st_counts = df_content['STATUS'].value_counts().reset_index()
                    st_counts.columns = ['Status', 'Count']
                    fig_st = px.pie(st_counts, values='Count', names='Status', title='Tiến độ Tin bài hôm nay')
                    st.plotly_chart(fig_st, use_container_width=True)

    # ================= TAB 6: EMAIL =================
    # Xác định index tab dựa trên role
    tab_email_idx = 5 if role == 'LanhDao' else 4
    with tabs[tab_email_idx]:
        tk = st.selectbox("TK Gửi:", range(10), format_func=lambda x:f"TK {x}")
        to = st.multiselect("To:", df_users['Email'].tolist())
        sub = st.text_input("Tiêu đề"); bod = st.text_area("Nội dung")
        if st.button("Gửi"): st.markdown(f'<script>window.open("https://mail.google.com/mail/u/{tk}/?view=cm&fs=1&to={",".join(to)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(bod)}", "_blank");</script>', unsafe_allow_html=True)

    # ================= TAB 7: LOGS =================
    if role == 'LanhDao':
        with tabs[6]: 
            df_log = lay_du_lieu_main(sh_main.worksheet("NhatKy"))
            if not df_log.empty: st.dataframe(df_log.iloc[::-1].rename(columns=VN_COLS_LOG), use_container_width=True)