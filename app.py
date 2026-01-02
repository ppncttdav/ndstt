import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components
import urllib.parse
from datetime import datetime, date, timedelta
import pytz

# ================= CẤU HÌNH HỆ THỐNG =================
st.set_page_config(page_title="Phòng Nội dung số và Truyền thông", page_icon="🏢", layout="wide")

# --- TÊN FILE GOOGLE SHEET ---
SHEET_MAIN = "HeThongQuanLy"  # File chứa User, Công việc, Dự án
SHEET_TRUCSO = "VoTrucSo"     # File chứa Vở trực (Mỗi ngày 1 tab)

# --- CẤU HÌNH THỜI GIAN VN ---
def get_vn_time():
    return datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))

# --- DANH SÁCH LỰA CHỌN ---
OPTS_DINH_DANG = ["Bài dịch", "Sản phẩm sản xuất", "Video biên tập", "Ảnh/Infographic", "Khác"]
OPTS_NEN_TANG = ["Facebook", "TikTok", "Instagram", "Web App", "YouTube", "Zalo"]
OPTS_STATUS_TRUCSO = ["Pending (Chờ)", "Editing (Đang làm)", "Scheduled (Đã lên lịch)", "Posted (Đã đăng)", "Omitted (Hủy)"]
OPTS_TRANG_THAI_VIEC = ["Đã giao", "Đang thực hiện", "Chờ duyệt", "Hoàn thành", "Hủy"]

# --- HEADER CỘT CHO TRỰC SỐ (Để tạo Tab mới) ---
HEADER_TRUCSO = ["ThoiGianNhap", "NoiDung", "DinhDang", "NenTang", "Status", "Nguon", "NhanSu", "YKien", "LinkDuyet", "GioDang", "LinkSP"]

# --- TỪ ĐIỂN HIỂN THỊ ---
VN_COLS_VIEC = {
    "TenViec": "Tên công việc", "DuAn": "Dự án", "Deadline": "Hạn chót",
    "NguoiPhuTrach": "Người thực hiện", "TrangThai": "Trạng thái", "LinkBai": "Link SP", "GhiChu": "Ghi chú"
}
VN_COLS_TRUCSO = {
    "ThoiGianNhap": "Giờ nhập", "NoiDung": "Nội dung", "DinhDang": "Định dạng",
    "NenTang": "Nền tảng", "Status": "Trạng thái", "Nguon": "Nguồn", "NhanSu": "Nhân sự",
    "YKien": "Ý kiến", "LinkDuyet": "Link Duyệt", "GioDang": "Giờ đăng", "LinkSP": "Link SP"
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

# Kết nối File Quản lý (User, Task)
def ket_noi_main():
    client = get_gspread_client()
    try:
        return client.open(SHEET_MAIN)
    except:
        st.error(f"🔴 Không tìm thấy file '{SHEET_MAIN}'. Hãy kiểm tra tên hoặc quyền chia sẻ.")
        st.stop()

# Kết nối File Trực Số (Riêng biệt)
def ket_noi_trucso():
    client = get_gspread_client()
    try:
        return client.open(SHEET_TRUCSO)
    except:
        st.error(f"🔴 Không tìm thấy file '{SHEET_TRUCSO}'. Hãy tạo file này và share cho Service Account.")
        st.stop()

# Hàm lấy Tab theo ngày (Tự tạo nếu chưa có)
def get_or_create_daily_tab(sh_trucso, date_obj):
    tab_name = date_obj.strftime("%d-%m-%Y") # Tên tab: 02-01-2026
    try:
        wks = sh_trucso.worksheet(tab_name)
        return wks
    except gspread.WorksheetNotFound:
        # Nếu chưa có thì tạo mới
        wks = sh_trucso.add_worksheet(title=tab_name, rows=100, cols=20)
        # Thêm dòng tiêu đề ngay
        wks.append_row(HEADER_TRUCSO)
        return wks

def lay_du_lieu(wks):
    try:
        data = wks.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def ghi_nhat_ky(sh_main, nguoi_dung, hanh_dong, chi_tiet):
    try:
        wks = sh_main.worksheet("NhatKy")
        thoi_gian = get_vn_time().strftime("%H:%M %d/%m/%Y")
        wks.append_row([thoi_gian, nguoi_dung, hanh_dong, chi_tiet])
    except:
        pass

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

sh_main = ket_noi_main() # Kết nối file chính để đăng nhập

if not st.session_state['dang_nhap']:
    st.markdown("## 🔐 ĐĂNG NHẬP HỆ THỐNG")
    with st.form("login"):
        user = st.text_input("Tên đăng nhập")
        pwd = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Đăng nhập"):
            users = lay_du_lieu(sh_main.worksheet("TaiKhoan"))
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
    
    # KẾT NỐI FILE TRỰC SỐ (Chỉ khi đã đăng nhập mới kết nối để tối ưu)
    sh_trucso = ket_noi_trucso()

    titles = ["📝 Vở Trực Số (Daily)", "✅ Quản lý Công việc", "🗂️ Dự án", "📧 Email"]
    if role == 'LanhDao': titles.append("📜 Nhật ký")
    tabs = st.tabs(titles)

    df_duan = lay_du_lieu(sh_main.worksheet("DuAn"))
    list_duan = df_duan['TenDuAn'].tolist() if not df_duan.empty else []
    df_users = lay_du_lieu(sh_main.worksheet("TaiKhoan"))
    list_nv = df_users['HoTen'].tolist() if not df_users.empty else []

    # ================= TAB 1: TRỰC SỐ (MỖI NGÀY 1 TAB) =================
    with tabs[0]:
        st.header(f"📝 Vở Trực Số - File riêng: {SHEET_TRUCSO}")
        
        # --- KHUNG NHẬP LIỆU ---
        with st.expander("➕ NHẬP TIN BÀI MỚI (Tự động vào Tab hôm nay)", expanded=True):
            with st.form("ts_form"):
                st.caption(f"Dữ liệu sẽ được lưu vào Tab ngày: **{get_vn_time().strftime('%d-%m-%Y')}**")
                c1, c2 = st.columns([2, 1])
                ts_noidung = c1.text_area("Nội dung / Tên bài")
                ts_dinhdang = c2.selectbox("Định dạng", OPTS_DINH_DANG)
                ts_status = c2.selectbox("Trạng thái", OPTS_STATUS_TRUCSO)
                
                c3, c4, c5 = st.columns(3)
                ts_nentang = c3.multiselect("Nền tảng", OPTS_NEN_TANG)
                ts_nguon = c4.text_input("Nguồn")
                ts_nhansu = c5.multiselect("Nhân sự", list_nv, default=[curr_name] if curr_name in list_nv else None)
                
                c6, c7, c8 = st.columns(3)
                ts_giodang = c6.time_input("Giờ đăng (Dự kiến)", value=None)
                ts_linkduyet = c7.text_input("Link Duyệt")
                ts_linksp = c8.text_input("Link SP (Đã đăng)")
                
                ts_ykien = st.text_input("Ý kiến / Ghi chú")
                
                if st.form_submit_button("Lưu vào Vở Trực", type="primary"):
                    try:
                        # 1. Xác định Tab hôm nay
                        today_vn = get_vn_time()
                        wks_today = get_or_create_daily_tab(sh_trucso, today_vn)
                        
                        # 2. Chuẩn bị dữ liệu
                        row_data = [
                            today_vn.strftime("%H:%M"), # Giờ nhập
                            ts_noidung, ts_dinhdang, ", ".join(ts_nentang), ts_status,
                            ts_nguon, ", ".join(ts_nhansu), ts_ykien, ts_linkduyet,
                            ts_giodang.strftime("%H:%M") if ts_giodang else "", ts_linksp
                        ]
                        
                        # 3. Ghi vào Sheet VoTrucSo -> Tab Ngay_Hom_Nay
                        wks_today.append_row(row_data)
                        st.success(f"Đã lưu vào Tab '{today_vn.strftime('%d-%m-%Y')}' thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

        # --- KHUNG XEM DỮ LIỆU (CÓ CHỌN NGÀY) ---
        st.divider()
        c_view1, c_view2 = st.columns([1, 3])
        with c_view1:
            st.markdown("##### 📅 Xem sổ trực ngày:")
            # Mặc định là hôm nay
            view_date = st.date_input("Chọn ngày xem:", value=get_vn_time().date(), format="DD/MM/YYYY")
            tab_name_view = view_date.strftime("%d-%m-%Y")
        
        with c_view2:
            st.markdown(f"##### Danh sách tin bài ngày: {tab_name_view}")
            try:
                # Cố gắng mở Tab theo ngày đã chọn
                wks_view = sh_trucso.worksheet(tab_name_view)
                df_ts = lay_du_lieu(wks_view)
                
                if not df_ts.empty:
                    # Đảo ngược để bài mới nhất lên đầu
                    st.dataframe(
                        df_ts.iloc[::-1].rename(columns=VN_COLS_TRUCSO), 
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Link SP": st.column_config.LinkColumn(display_text="Link"),
                            "Link Duyệt": st.column_config.LinkColumn(display_text="Xem")
                        }
                    )
                else:
                    st.info("Ngày này có Tab nhưng chưa có dữ liệu.")
            except gspread.WorksheetNotFound:
                st.warning(f"Chưa có sổ trực (Tab) cho ngày {tab_name_view}. (Chưa ai nhập liệu)")

    # ================= TAB 2: CÔNG VIỆC =================
    with tabs[1]:
        st.caption("Quản lý tiến độ dự án (File chính).")
        with st.expander("➕ TẠO VIỆC MỚI", expanded=False):
            st.markdown("#### 1. Thông tin")
            c1, c2 = st.columns(2)
            tv_ten = c1.text_input("Tên việc"); tv_duan = c1.selectbox("Dự án", list_duan)
            now_vn = get_vn_time()
            tv_time = c1.time_input("Giờ DL", value=now_vn.time()); tv_date = c1.date_input("Ngày DL", value=now_vn.date(), format="DD/MM/YYYY")
            tv_nguoi = c2.multiselect("Người làm", list_nv); tv_ghichu = c2.text_area("Yêu cầu", height=100)
            
            st.markdown("#### 2. Email & Lưu")
            ct1, ct2 = st.columns([2,1])
            tk_gui = ct1.selectbox("Gửi từ Gmail:", range(10), format_func=lambda x: f"TK {x}")
            ct2.markdown(f'<br><a href="https://mail.google.com/mail/u/{tk_gui}" target="_blank">Check Mail</a>', unsafe_allow_html=True)
            co1, co2 = st.columns(2)
            opt_nv = co1.checkbox("Gửi NV", True); opt_ld = co2.checkbox("Gửi Lãnh đạo", False)
            
            if st.button("💾 Lưu Việc & Gửi Email"):
                try:
                    dl_fmt = f"{tv_time.strftime('%H:%M')} {tv_date.strftime('%d/%m/%Y')}"
                    sh_main.worksheet("CongViec").append_row([tv_ten, tv_duan, dl_fmt, ", ".join(tv_nguoi), "Đã giao", "", tv_ghichu, curr_name])
                    ghi_nhat_ky(sh_main, curr_name, "Tạo việc", tv_ten)
                    st.success("Xong!"); 
                    if opt_nv and tv_nguoi:
                        mails = df_users[df_users['HoTen'].isin(tv_nguoi)]['Email'].tolist()
                        mails = [m for m in mails if str(m).strip()]
                        if mails: st.markdown(f'<a href="https://mail.google.com/mail/u/{tk_gui}/?view=cm&fs=1&to={",".join(mails)}&su={urllib.parse.quote(tv_ten)}&body={urllib.parse.quote(tv_ghichu)}" target="_blank">📧 Gửi NV</a>', unsafe_allow_html=True)
                except Exception as e: st.error(str(e))

        st.divider()
        da_filter = st.selectbox("Lọc Dự án:", ["All"]+list_duan)
        df_cv = lay_du_lieu(sh_main.worksheet("CongViec"))
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

    # ================= TAB 3: DỰ ÁN =================
    with tabs[2]:
        if role == 'LanhDao':
            with st.form("new_da"):
                d_n = st.text_input("Tên DA"); d_m = st.text_area("Mô tả"); d_l = st.multiselect("Lead", list_nv)
                if st.form_submit_button("Tạo DA"): sh_main.worksheet("DuAn").append_row([d_n, d_m, "Đang chạy", ",".join(d_l)]); st.rerun()
        st.dataframe(df_duan.rename(columns=VN_COLS_DUAN), use_container_width=True)

    # ================= TAB 4: EMAIL =================
    with tabs[3]:
        tk = st.selectbox("TK Gửi:", range(10), format_func=lambda x:f"TK {x}")
        to = st.multiselect("To:", df_users['Email'].tolist())
        sub = st.text_input("Tiêu đề"); bod = st.text_area("Nội dung")
        if st.button("Gửi"): st.markdown(f'<script>window.open("https://mail.google.com/mail/u/{tk}/?view=cm&fs=1&to={",".join(to)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(bod)}", "_blank");</script>', unsafe_allow_html=True)

    # ================= TAB 5: LOGS =================
    if role == 'LanhDao':
        with tabs[4]: st.dataframe(lay_du_lieu(sh_main.worksheet("NhatKy")).iloc[::-1].rename(columns=VN_COLS_LOG), use_container_width=True)