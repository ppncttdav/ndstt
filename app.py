import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components
import urllib.parse
from datetime import datetime, date
import pytz

# ================= CẤU HÌNH HỆ THỐNG =================
st.set_page_config(page_title="Phòng Nội dung số và Truyền thông", page_icon="🏢", layout="wide")

# --- TÊN FILE GOOGLE SHEET ---
SHEET_MAIN = "HeThongQuanLy" 
SHEET_TRUCSO = "VoTrucSo"

# --- CẤU HÌNH THỜI GIAN VN ---
def get_vn_time():
    return datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))

# --- DANH SÁCH LỰA CHỌN ---
OPTS_DINH_DANG = ["Bài dịch", "Sản phẩm sản xuất", "Video biên tập", "Ảnh/Infographic", "Khác"]
OPTS_NEN_TANG = ["Facebook", "TikTok", "Instagram", "Web App", "YouTube", "Zalo"]
OPTS_STATUS_TRUCSO = ["Chờ xử lý", "Đang biên tập", "Đã lên lịch", "Đã đăng", "Hủy"]
OPTS_TRANG_THAI_VIEC = ["Đã giao", "Đang thực hiện", "Chờ duyệt", "Hoàn thành", "Hủy"]

# --- CẤU TRÚC VỞ TRỰC (GIỐNG ẢNH) ---
ROLES_HEADER = ["Lãnh đạo Ban", "Trực thư ký tòa soạn", "Trực quản trị MXH + Video", "Trực lịch phát sóng", "Trực thư ký (Phụ)", "Trực sản xuất video/LPS", "Trực quản trị App"]
CONTENT_HEADER = ["STT", "NỘI DUNG", "ĐỊNH DẠNG", "NỀN TẢNG", "STATUS", "CHECK", "NGUỒN", "NHÂN SỰ", "Ý KIẾN ĐIỀU CHỈNH", "LINK DUYỆT", "GIỜ ĐĂNG", "LINK SẢN PHẨM"]

# --- TỪ ĐIỂN HIỂN THỊ ---
VN_COLS_VIEC = {"TenViec": "Tên công việc", "DuAn": "Dự án", "Deadline": "Hạn chót", "NguoiPhuTrach": "Người thực hiện", "TrangThai": "Trạng thái", "LinkBai": "Link SP", "GhiChu": "Ghi chú"}
VN_COLS_TRUCSO = {"STT": "Giờ", "NỘI DUNG": "Nội dung", "ĐỊNH DẠNG": "Định dạng", "NỀN TẢNG": "Nền tảng", "STATUS": "Trạng thái", "NGUỒN": "Nguồn", "NHÂN SỰ": "Nhân sự", "Ý KIẾN ĐIỀU CHỈNH": "Ý kiến", "LINK DUYỆT": "Link Duyệt", "GIỜ ĐĂNG": "Giờ đăng", "LINK SẢN PHẨM": "Link SP"}
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
        st.success(f"Chào: **{curr_name}**")
        if st.button("Đăng xuất"):
            st.session_state['dang_nhap'] = False; st.rerun()

    st.title("🏢 PHÒNG NỘI DUNG SỐ & TRUYỀN THÔNG")
    
    sh_trucso = ket_noi_trucso()
    
    # --- ĐỊNH NGHĨA THỨ TỰ TAB MỚI ---
    # Tab 1: Công việc
    # Tab 2: Dự án
    # Tab 3: Vở Trực Số (THEO YÊU CẦU)
    # Tab 4: Email
    if role == 'LanhDao':
        tabs = st.tabs(["✅ Quản lý Công việc", "🗂️ Quản lý Dự án", "📝 Vở Trực Số", "📧 Email", "📜 Nhật ký"])
    else:
        tabs = st.tabs(["✅ Quản lý Công việc", "🗂️ Quản lý Dự án", "📝 Vở Trực Số", "📧 Email"])

    # Load Data Chung
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
            tv_nguoi = c2.multiselect("Người làm", list_nv); tv_ghichu = c2.text_area("Yêu cầu", height=100)
            
            ct1, ct2 = st.columns([2,1])
            tk_gui = ct1.selectbox("Gửi Gmail:", range(10), format_func=lambda x: f"TK {x}")
            ct2.markdown(f'<br><a href="https://mail.google.com/mail/u/{tk_gui}" target="_blank">Check Mail</a>', unsafe_allow_html=True)
            opt_nv = st.checkbox("Gửi NV", True)
            
            if st.button("💾 Lưu & Gửi"):
                try:
                    dl_fmt = f"{tv_time.strftime('%H:%M')} {tv_date.strftime('%d/%m/%Y')}"
                    sh_main.worksheet("CongViec").append_row([tv_ten, tv_duan, dl_fmt, ", ".join(tv_nguoi), "Đã giao", "", tv_ghichu, curr_name])
                    ghi_nhat_ky(sh_main, curr_name, "Tạo việc", tv_ten)
                    st.success("Xong!")
                    if opt_nv and tv_nguoi:
                        mails = df_users[df_users['HoTen'].isin(tv_nguoi)]['Email'].tolist()
                        mails = [m for m in mails if str(m).strip()]
                        if mails: st.markdown(f'<a href="https://mail.google.com/mail/u/{tk_gui}/?view=cm&fs=1&to={",".join(mails)}&su={urllib.parse.quote(tv_ten)}&body={urllib.parse.quote(tv_ghichu)}" target="_blank">📧 Gửi NV</a>', unsafe_allow_html=True)
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
                            e_ng = ce1.text_input("Người làm", r_dat['NguoiPhuTrach'], disabled=dis)
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

    # ================= TAB 3: VỞ TRỰC SỐ (VỊ TRÍ MỚI) =================
    with tabs[2]:
        today_vn = get_vn_time()
        tab_name_today = today_vn.strftime("%d-%m-%Y")
        st.header(f"📝 Vở Trực Số Ngày: {tab_name_today}")

        # Check Tab
        tab_exists = False
        try: wks_today = sh_trucso.worksheet(tab_name_today); tab_exists = True
        except gspread.WorksheetNotFound: tab_exists = False

        # --- A. CHƯA CÓ TAB -> TẠO KHUNG (VỎ) ---
        if not tab_exists:
            st.warning(f"⚠️ Chưa có sổ trực cho ngày {tab_name_today}. Vui lòng thiết lập ca trực.")
            with st.form("init_roster"):
                st.markdown("### ☀️ KHỞI TẠO CA TRỰC")
                cols = st.columns(3)
                roster_values = []
                for i, role_title in enumerate(ROLES_HEADER):
                    with cols[i % 3]:
                        sel = st.selectbox(f"**{role_title}**", ["-- Trống --"] + list_nv, key=f"r_{i}")
                        roster_values.append(sel if sel != "-- Trống --" else "")
                
                if st.form_submit_button("🚀 Tạo Sổ & Bắt Đầu"):
                    try:
                        wks_new = sh_trucso.add_worksheet(title=tab_name_today, rows=100, cols=20)
                        wks_new.update_cell(1, 1, f"VỞ TIN BÀI VIETNAM TODAY {tab_name_today}")
                        wks_new.update_cell(2, 1, "DANH SÁCH TRỰC:")
                        for idx, val in enumerate(ROLES_HEADER): wks_new.update_cell(2, idx + 2, val)
                        wks_new.update_cell(3, 1, "NHÂN SỰ:")
                        for idx, val in enumerate(roster_values): wks_new.update_cell(3, idx + 2, val)
                        wks_new.append_row(CONTENT_HEADER)
                        st.success("Đã tạo sổ trực!"); st.rerun()
                    except Exception as e: st.error(f"Lỗi: {e}")

        # --- B. ĐÃ CÓ TAB -> NHẬP TIN BÀI ---
        else:
            # 1. Xem kíp trực (Header)
            with st.expander("ℹ️ Ekip trực hôm nay (Nhấn để xem)", expanded=False):
                try:
                    r_names = wks_today.row_values(3)[1:]
                    r_roles = wks_today.row_values(2)[1:]
                    if r_names:
                        cols = st.columns(len(r_names))
                        for i, n in enumerate(r_names): 
                            if i < len(cols): cols[i].metric(r_roles[i] if i<len(r_roles) else "Vị trí", n)
                except: st.caption("Lỗi đọc ekip.")

            # 2. Form Nhập Tin Bài (Nút tạo tin bài)
            st.markdown("### ➕ Thêm Tin Bài / Đầu Mục Mới")
            with st.form("add_news_form"):
                c1, c2 = st.columns([3, 1])
                ts_noidung = c1.text_area("Nội dung / Tên bài", placeholder="Nhập nội dung...")
                ts_dinhdang = c2.selectbox("Định dạng", OPTS_DINH_DANG)
                
                c3, c4, c5 = st.columns(3)
                ts_nentang = c3.multiselect("Nền tảng", OPTS_NEN_TANG)
                ts_status = c4.selectbox("Trạng thái", OPTS_STATUS_TRUCSO)
                ts_nhansu = c5.multiselect("Nhân sự", list_nv, default=[curr_name] if curr_name in list_nv else None)
                
                c6, c7 = st.columns(2)
                ts_nguon = c6.text_input("Nguồn tin")
                ts_giodang = c7.time_input("Giờ đăng (DK)", value=None)
                
                c8, c9 = st.columns(2)
                ts_linkduyet = c8.text_input("Link Duyệt")
                ts_linksp = c9.text_input("Link Sản phẩm")
                ts_ykien = st.text_input("Ý kiến / Ghi chú")

                if st.form_submit_button("Lưu vào bảng trực", type="primary"):
                    try:
                        stt_val = get_vn_time().strftime("%H:%M") 
                        row_data = [
                            stt_val, ts_noidung, ts_dinhdang, ", ".join(ts_nentang), ts_status, 
                            "", ts_nguon, ", ".join(ts_nhansu), ts_ykien, ts_linkduyet, 
                            ts_giodang.strftime("%H:%M") if ts_giodang else "", ts_linksp
                        ]
                        wks_today.append_row(row_data)
                        st.success("Đã thêm tin bài!"); st.rerun()
                    except Exception as e: st.error(f"Lỗi lưu: {e}")

            # 3. Bảng dữ liệu (Cập nhật liên tục)
            st.divider()
            st.markdown("##### 📋 Danh sách tin bài")
            df_content = lay_du_lieu_trucso(wks_today)
            if not df_content.empty:
                st.dataframe(
                    df_content.iloc[::-1], 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "LINK DUYỆT": st.column_config.LinkColumn(display_text="Xem"),
                        "LINK SẢN PHẨM": st.column_config.LinkColumn(display_text="Link"),
                    }
                )
            else: st.info("Chưa có tin bài nào.")

    # ================= TAB 4: EMAIL =================
    with tabs[3]:
        tk = st.selectbox("TK Gửi:", range(10), format_func=lambda x:f"TK {x}")
        to = st.multiselect("To:", df_users['Email'].tolist())
        sub = st.text_input("Tiêu đề"); bod = st.text_area("Nội dung")
        if st.button("Gửi"): st.markdown(f'<script>window.open("https://mail.google.com/mail/u/{tk}/?view=cm&fs=1&to={",".join(to)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(bod)}", "_blank");</script>', unsafe_allow_html=True)

    # ================= TAB 5: LOGS =================
    if role == 'LanhDao':
        with tabs[4]: 
            df_log = lay_du_lieu_main(sh_main.worksheet("NhatKy"))
            if not df_log.empty: st.dataframe(df_log.iloc[::-1].rename(columns=VN_COLS_LOG), use_container_width=True)