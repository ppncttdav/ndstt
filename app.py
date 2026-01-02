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

# --- CẤU HÌNH THỜI GIAN VN ---
def get_vn_time():
    return datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))

# --- DANH SÁCH TRẠNG THÁI ---
OPTS_TRANG_THAI = ["Đã giao", "Đang thực hiện", "Chờ duyệt", "Hoàn thành", "Hủy"]

# --- TỪ ĐIỂN HIỂN THỊ ---
VN_COLS_VIEC = {
    "TenViec": "Tên công việc",
    "DuAn": "Dự án",
    "Deadline": "Hạn chót",
    "NguoiPhuTrach": "Người thực hiện",
    "TrangThai": "Trạng thái",
    "LinkBai": "Link sản phẩm",
    "GhiChu": "Ghi chú"
}

VN_COLS_DUAN = {
    "TenDuAn": "Tên Dự án",
    "MoTa": "Mô tả",
    "TrangThai": "Trạng thái",
    "TruongNhom": "Điều phối (Lead)"
}

VN_COLS_LOG = {
    "ThoiGian": "Thời gian",
    "NguoiDung": "Người dùng",
    "HanhDong": "Hành động",
    "ChiTiet": "Chi tiết"
}

# ================= 1. BACKEND =================
def ket_noi_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("HeThongQuanLy") 
        return sheet
    except Exception as e:
        st.error(f"🔴 Lỗi kết nối: {e}")
        st.stop()

def lay_du_lieu(sh, ten_tab):
    try:
        wks = sh.worksheet(ten_tab)
        data = wks.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def ghi_nhat_ky(sh, nguoi_dung, hanh_dong, chi_tiet):
    try:
        wks = sh.worksheet("NhatKy")
        thoi_gian = get_vn_time().strftime("%H:%M %d/%m/%Y")
        wks.append_row([thoi_gian, nguoi_dung, hanh_dong, chi_tiet])
    except:
        pass

# --- CHECK QUYỀN ---
def check_quyen_truy_cap(current_user, role_system, row_data, df_duan):
    if role_system == 'LanhDao': return 2
    
    nguoi_tao = str(row_data.get('NguoiTao', '')).strip()
    if nguoi_tao == current_user: return 2
        
    try:
        ten_du_an = row_data['DuAn']
        if not df_duan.empty:
            duan_row = df_duan[df_duan['TenDuAn'] == ten_du_an]
            if not duan_row.empty:
                leads = str(duan_row.iloc[0]['TruongNhom'])
                if current_user in leads: return 2
    except: pass

    nguoi_phu_trach = str(row_data.get('NguoiPhuTrach', ''))
    if current_user in nguoi_phu_trach: return 1
        
    return 0

# ================= 2. AUTH =================
if 'dang_nhap' not in st.session_state:
    st.session_state['dang_nhap'] = False
    st.session_state['user_info'] = {}

sh = ket_noi_sheet() 

if not st.session_state['dang_nhap']:
    st.markdown("## 🔐 CỔNG ĐĂNG NHẬP")
    st.markdown("### PHÒNG NỘI DUNG SỐ VÀ TRUYỀN THÔNG")
    with st.form("login"):
        user = st.text_input("Tên đăng nhập")
        pwd = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Đăng nhập"):
            users = lay_du_lieu(sh, "TaiKhoan")
            if not users.empty:
                user_row = users[(users['TenDangNhap'].astype(str) == user) & (users['MatKhau'].astype(str) == pwd)]
                if not user_row.empty:
                    st.session_state['dang_nhap'] = True
                    st.session_state['user_info'] = user_row.iloc[0].to_dict()
                    ghi_nhat_ky(sh, user_row.iloc[0]['HoTen'], "Đăng nhập", "Success")
                    st.rerun()
                else:
                    st.error("Sai thông tin!")
            else:
                st.error("Lỗi dữ liệu.")
else:
    user_info = st.session_state['user_info']
    current_name = user_info['HoTen']
    role_system = user_info.get('VaiTro', 'NhanVien')
    
    with st.sidebar:
        st.success(f"Xin chào: **{current_name}**")
        if st.button("Đăng xuất"):
            st.session_state['dang_nhap'] = False
            st.rerun()

    st.title("🏢 PHÒNG NỘI DUNG SỐ VÀ TRUYỀN THÔNG")

    # --- KHỞI TẠO TABS ĐỘNG DỰA TRÊN QUYỀN ---
    if role_system == 'LanhDao':
        # Lãnh đạo: Thấy đủ 4 Tab
        tabs = st.tabs(["✅ Quản lý Công việc", "🗂️ Quản lý Dự án", "📧 Soạn Email", "📜 Nhật ký"])
    else:
        # Nhân viên: Chỉ thấy 3 Tab (Ẩn Nhật ký)
        tabs = st.tabs(["✅ Quản lý Công việc", "🗂️ Quản lý Dự án", "📧 Soạn Email"])
    
    # --- LOAD DỮ LIỆU ---
    df_duan = lay_du_lieu(sh, "DuAn")
    list_duan = df_duan['TenDuAn'].tolist() if not df_duan.empty else []
    df_users = lay_du_lieu(sh, "TaiKhoan")
    list_nv = df_users['HoTen'].tolist() if not df_users.empty else []

    # ================= TAB 1: CÔNG VIỆC =================
    with tabs[0]:
        st.caption("Quản lý tiến độ, phân công và cập nhật trạng thái.")

        # --- A. TẠO VIỆC ---
        with st.expander("➕ KHỞI TẠO ĐẦU VIỆC MỚI", expanded=False):
            st.info("💡 Bạn có toàn quyền sửa/xóa với công việc do chính mình tạo ra.")
            
            st.markdown("#### 1. Thông tin công việc")
            c1, c2 = st.columns(2)
            with c1:
                tv_ten = st.text_input("Tên đầu việc / Nhiệm vụ")
                tv_duan = st.selectbox("Thuộc Dự án", list_duan)
                
                st.write("⏱️ **Hạn chót (Deadline):**")
                col_h, col_d = st.columns(2)
                
                now_vn = get_vn_time()
                tv_time = col_h.time_input("Giờ", value=now_vn.time())
                tv_date = col_d.date_input("Ngày", value=now_vn.date(), format="DD/MM/YYYY")
                
            with c2:
                tv_nguoi = st.multiselect("Nhân sự thực hiện", list_nv)
                tv_ghichu = st.text_area("Mô tả / Yêu cầu", height=135)

            st.divider()
            st.markdown("#### 2. Cấu hình Email thông báo")
            ct1, ct2 = st.columns([2,1])
            with ct1:
                tk_gui = st.selectbox("Gửi từ Tài khoản số:", range(10), format_func=lambda x: f"Tài khoản {x} (trên máy này)")
            with ct2:
                st.write("Kiểm tra:")
                st.markdown(f'<a href="https://mail.google.com/mail/u/{tk_gui}" target="_blank" style="background:#f0f2f6; padding: 6px 12px; border-radius: 5px; text-decoration: none; border: 1px solid #ccc; display: inline-block;">👁️ Hộp thư số {tk_gui}</a>', unsafe_allow_html=True)
            
            co1, co2 = st.columns(2)
            opt_nv = co1.checkbox("Gửi cho Nhân sự", value=True)
            opt_ld = co2.checkbox("Gửi báo cáo Lãnh đạo", value=False)

            st.markdown("---")
            
            if st.button("💾 Lưu công việc & Tạo Email", type="primary"):
                if tv_ten and tv_duan:
                    try:
                        deadline_fmt = f"{tv_time.strftime('%H:%M')} {tv_date.strftime('%d/%m/%Y')}"
                        nguoi_str = ", ".join(tv_nguoi)
                        
                        wks_cv = sh.worksheet("CongViec")
                        wks_cv.append_row([tv_ten, tv_duan, deadline_fmt, nguoi_str, "Đã giao", "", tv_ghichu, current_name])
                        
                        ghi_nhat_ky(sh, current_name, "Tạo việc", f"{tv_ten} ({tv_duan})")
                        st.success("✅ Đã tạo công việc thành công!")

                        msg_links = []
                        if opt_nv and tv_nguoi:
                            mails_nv = df_users[df_users['HoTen'].isin(tv_nguoi)]['Email'].dropna().tolist()
                            mails_nv = [m for m in mails_nv if str(m).strip()]
                            if mails_nv:
                                sub = f"[GIAO VIỆC] {tv_ten} - Hạn: {deadline_fmt}"
                                body = f"Chào các bạn,\n\nBạn có việc mới:\n- Việc: {tv_ten}\n- Dự án: {tv_duan}\n- Deadline: {deadline_fmt}\n- Ghi chú: {tv_ghichu}\n\nNgười tạo: {current_name}"
                                link = f"https://mail.google.com/mail/u/{tk_gui}/?view=cm&fs=1&to={','.join(mails_nv)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(body)}"
                                msg_links.append(f'<a href="{link}" target="_blank" style="background:#28a745;color:white;padding:8px 12px;text-decoration:none;border-radius:5px;margin-right:10px;">📧 Gửi NV (TK {tk_gui})</a>')
                        
                        if opt_ld:
                            mails_ld = df_users[df_users['VaiTro'] == 'LanhDao']['Email'].dropna().tolist()
                            mails_ld = [m for m in mails_ld if str(m).strip()]
                            if mails_ld:
                                sub = f"[BÁO CÁO] Việc mới: {tv_ten}"
                                body = f"Kính gửi Lãnh đạo,\n\nTôi vừa tạo việc mới:\n- Việc: {tv_ten}\n- Dự án: {tv_duan}\n- Phụ trách: {nguoi_str}\n\nTrân trọng."
                                link = f"https://mail.google.com/mail/u/{tk_gui}/?view=cm&fs=1&to={','.join(mails_ld)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(body)}"
                                msg_links.append(f'<a href="{link}" target="_blank" style="background:#007bff;color:white;padding:8px 12px;text-decoration:none;border-radius:5px;">📧 Báo cáo Lãnh đạo (TK {tk_gui})</a>')
                        
                        if msg_links:
                            st.info("👇 Bấm nút dưới để gửi email:")
                            st.markdown(" ".join(msg_links), unsafe_allow_html=True)
                            
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
                else:
                    st.warning("Thiếu tên việc hoặc dự án.")

        # --- B. DANH SÁCH ---
        st.divider()
        st.subheader("📋 Danh sách Công việc")
        
        filter_da = st.selectbox("Lọc Dự án:", ["-- Tất cả --"] + list_duan)
        
        df_cv = lay_du_lieu(sh, "CongViec")
        if not df_cv.empty:
            df_view = df_cv.copy()
            if filter_da != "-- Tất cả --":
                df_view = df_view[df_view['DuAn'] == filter_da]
            
            editable_tasks = {}
            for idx, row in df_view.iterrows():
                level = check_quyen_truy_cap(current_name, role_system, row, df_duan)
                if level > 0:
                    label = f"{row['TenViec']} (ID: {idx+2})"
                    editable_tasks[label] = {"index": idx, "level": level}
            
            if editable_tasks:
                with st.expander("🛠️ CẬP NHẬT / CHỈNH SỬA", expanded=True):
                    tab_sua, tab_xoa = st.tabs(["✏️ Cập nhật", "🗑️ Xóa việc"])
                    
                    with tab_sua:
                        chon_sua = st.selectbox("Chọn việc:", list(editable_tasks.keys()))
                        if chon_sua:
                            task_info = editable_tasks[chon_sua]
                            original_idx = task_info["index"]
                            permission_level = task_info["level"]
                            row_data = df_cv.iloc[original_idx]

                            if permission_level == 2:
                                st.caption("🌟 Admin Mode: Sửa toàn bộ.")
                                disable_core = False
                            else:
                                st.caption("👤 User Mode: Chỉ cập nhật Tiến độ & Ghi chú.")
                                disable_core = True

                            with st.form("form_sua"):
                                ce1, ce2 = st.columns(2)
                                with ce1:
                                    e_ten = st.text_input("Tên việc", value=row_data['TenViec'], disabled=disable_core)
                                    
                                    # Multiselect for edit
                                    curr_people_str = str(row_data['NguoiPhuTrach'])
                                    curr_people_list = [x.strip() for x in curr_people_str.split(',') if x.strip()]
                                    valid_defaults = [x for x in curr_people_list if x in list_nv]
                                    
                                    e_nguoi_list = st.multiselect("Người phụ trách", options=list_nv, default=valid_defaults, disabled=disable_core)
                                    e_link = st.text_input("Link sản phẩm", value=row_data.get('LinkBai', ''))
                                with ce2:
                                    e_dl = st.text_input("Deadline", value=row_data.get('Deadline', ''), disabled=disable_core)
                                    
                                    curr_stt = row_data.get('TrangThai', 'Đã giao')
                                    idx_stt = OPTS_TRANG_THAI.index(curr_stt) if curr_stt in OPTS_TRANG_THAI else 0
                                    e_tt = st.selectbox("Trạng thái", OPTS_TRANG_THAI, index=idx_stt)
                                    
                                    e_note = st.text_area("Ghi chú / Báo cáo", value=row_data.get('GhiChu', ''), height=100)
                                
                                if st.form_submit_button("Cập nhật ngay"):
                                    e_nguoi_str = ", ".join(e_nguoi_list)
                                    wks_cv = sh.worksheet("CongViec")
                                    r_num = original_idx + 2
                                    wks_cv.update_cell(r_num, 1, e_ten)
                                    wks_cv.update_cell(r_num, 3, e_dl)
                                    wks_cv.update_cell(r_num, 4, e_nguoi_str)
                                    wks_cv.update_cell(r_num, 5, e_tt)
                                    wks_cv.update_cell(r_num, 6, e_link)
                                    wks_cv.update_cell(r_num, 7, e_note)
                                    ghi_nhat_ky(sh, current_name, "Cập nhật", f"{e_ten} -> {e_tt}")
                                    st.success("Đã cập nhật!")
                                    st.rerun()

                    with tab_xoa:
                        tasks_can_delete = [k for k, v in editable_tasks.items() if v["level"] == 2]
                        if tasks_can_delete:
                            chon_xoa = st.multiselect("Chọn việc xóa (Chỉ Admin/Người tạo được xóa):", tasks_can_delete)
                            if st.button("Xác nhận Xóa"):
                                if chon_xoa:
                                    wks_cv = sh.worksheet("CongViec")
                                    all_vals = wks_cv.get_all_values()
                                    names_del = [x.split(" (ID:")[0] for x in chon_xoa]
                                    
                                    new_data = [all_vals[0]]
                                    for row in all_vals[1:]:
                                        if row[0] in names_del: continue
                                        new_data.append(row)
                                    
                                    wks_cv.clear()
                                    wks_cv.update(new_data)
                                    ghi_nhat_ky(sh, current_name, "Xóa việc", str(names_del))
                                    st.success("Đã xóa!")
                                    st.rerun()
                        else:
                            st.info("Bạn không có quyền xóa.")

            df_display = df_view.drop(columns=['NguoiTao'], errors='ignore')
            df_display = df_display.rename(columns=VN_COLS_VIEC)
            st.dataframe(
                df_display, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Link sản phẩm": st.column_config.LinkColumn(display_text="🔗 Link"),
                    "Trạng thái": st.column_config.SelectboxColumn(options=OPTS_TRANG_THAI, width="medium")
                }
            )
        else:
            st.info("Chưa có công việc nào.")

    # ================= TAB 2: DỰ ÁN =================
    with tabs[1]:
        st.header("🗂️ Quản lý Dự án")
        if role_system == 'LanhDao':
            with st.expander("➕ TẠO DỰ ÁN MỚI (Admin)", expanded=False):
                with st.form("tao_duan"):
                    n_da = st.text_input("Tên Dự án")
                    n_mt = st.text_area("Mô tả")
                    n_lead = st.multiselect("Điều phối viên (Lead):", list_nv)
                    if st.form_submit_button("Tạo Dự án"):
                        wks_da = sh.worksheet("DuAn")
                        wks_da.append_row([n_da, n_mt, "Đang chạy", ", ".join(n_lead)])
                        st.success("Xong!")
                        st.rerun()
            with st.expander("🗑️ Xóa Dự án"):
                d_del = st.selectbox("Chọn xóa:", list_duan)
                if st.button("Xóa ngay"):
                    wks = sh.worksheet("DuAn")
                    rows = wks.get_all_values()
                    new = [rows[0]] + [r for r in rows[1:] if r[0] != d_del]
                    wks.clear()
                    wks.update(new)
                    st.success("Đã xóa!")
                    st.rerun()
        st.dataframe(df_duan.rename(columns=VN_COLS_DUAN), use_container_width=True)

    # ================= TAB 3: EMAIL =================
    with tabs[2]:
        st.header("📧 Soạn Email")
        c1, c2 = st.columns([2,1])
        with c1: tk = st.selectbox("Gửi từ TK:", range(10), format_func=lambda x: f"Gmail {x}", key="mail_tab")
        with c2: st.markdown(f'<br><a href="https://mail.google.com/mail/u/{tk}" target="_blank">👁️ Check Mail</a>', unsafe_allow_html=True)
        try:
            danh_ba = {r['HoTen']: r['Email'] for i,r in df_users.iterrows() if str(r['Email']).strip()}
            c_to, c_m = st.columns(2)
            with c_to: to = st.multiselect("To:", list(danh_ba.keys()))
            emails = [danh_ba[x] for x in to]
            sub = st.text_input("Tiêu đề")
            body = st.text_area("Nội dung", height=200)
            if st.button("🚀 Gửi ngay"):
                if emails:
                    lnk = f"https://mail.google.com/mail/u/{tk}/?view=cm&fs=1&to={','.join(emails)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(body)}"
                    st.markdown(f'<script>window.open("{lnk}", "_blank");</script>', unsafe_allow_html=True)
                    st.success("Đang mở...")
        except: st.error("Lỗi data.")

    # ================= TAB 4: LOGS (Chỉ Lãnh Đạo mới thấy) =================
    if role_system == 'LanhDao':
        with tabs[3]:
            st.header("📜 Nhật ký")
            df_log = lay_du_lieu(sh, "NhatKy")
            if not df_log.empty:
                st.dataframe(df_log.iloc[::-1].rename(columns=VN_COLS_LOG), use_container_width=True)