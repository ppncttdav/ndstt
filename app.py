import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components
import urllib.parse
from datetime import datetime, date

# ================= CẤU HÌNH HỆ THỐNG =================
st.set_page_config(page_title="Phòng Nội dung số và Truyền thông", page_icon="🏢", layout="wide")

# --- DANH SÁCH TRẠNG THÁI MỚI (QUY TRÌNH CHUẨN) ---
OPTS_TRANG_THAI = ["Đã giao", "Đang thực hiện", "Chờ duyệt", "Hoàn thành", "Hủy"]

# --- TỪ ĐIỂN HIỂN THỊ ---
VN_COLS_VIEC = {
    "TenViec": "Tên công việc / Nhiệm vụ",
    "DuAn": "Thuộc Dự án",
    "Deadline": "Hạn chót",
    "NguoiPhuTrach": "Người phụ trách",
    "TrangThai": "Trạng thái",
    "LinkBai": "Link sản phẩm",
    "GhiChu": "Ghi chú / Yêu cầu"
}

VN_COLS_DUAN = {
    "TenDuAn": "Tên Dự án",
    "MoTa": "Mô tả chi tiết",
    "TrangThai": "Trạng thái",
    "TruongNhom": "Điều phối viên (Lead)"
}

VN_COLS_LOG = {
    "ThoiGian": "Thời gian",
    "NguoiDung": "Người thực hiện",
    "HanhDong": "Hành động",
    "ChiTiet": "Nội dung chi tiết"
}

# ================= 1. CÁC HÀM XỬ LÝ (BACKEND) =================
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
        st.error(f"🔴 Lỗi kết nối máy chủ: {e}")
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
        thoi_gian = datetime.now().strftime("%H:%M %d/%m/%Y")
        wks.append_row([thoi_gian, nguoi_dung, hanh_dong, chi_tiet])
    except:
        pass

def kiem_tra_quyen_du_an(current_user, role_he_thong, ten_du_an, df_projects):
    if role_he_thong == 'LanhDao':
        return True
    try:
        if not df_projects.empty:
            row = df_projects[df_projects['TenDuAn'] == ten_du_an]
            if not row.empty:
                ds_truong_nhom = str(row.iloc[0]['TruongNhom'])
                if current_user in ds_truong_nhom:
                    return True
    except:
        return False
    return False

# ================= 2. QUẢN LÝ ĐĂNG NHẬP =================
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
        if st.form_submit_button("Đăng nhập hệ thống"):
            users = lay_du_lieu(sh, "TaiKhoan")
            if not users.empty:
                user_row = users[(users['TenDangNhap'].astype(str) == user) & (users['MatKhau'].astype(str) == pwd)]
                if not user_row.empty:
                    st.session_state['dang_nhap'] = True
                    st.session_state['user_info'] = user_row.iloc[0].to_dict()
                    ghi_nhat_ky(sh, user_row.iloc[0]['HoTen'], "Đăng nhập", "Truy cập hệ thống")
                    st.rerun()
                else:
                    st.error("Sai tên đăng nhập hoặc mật khẩu!")
            else:
                st.error("Lỗi: Không kết nối được dữ liệu tài khoản.")
else:
    # --- SIDEBAR ---
    user_info = st.session_state['user_info']
    current_name = user_info['HoTen']
    role_system = user_info.get('VaiTro', 'NhanVien')
    
    with st.sidebar:
        st.success(f"Xin chào: **{current_name}**")
        if st.button("Đăng xuất"):
            st.session_state['dang_nhap'] = False
            st.rerun()

    st.title("🏢 PHÒNG NỘI DUNG SỐ VÀ TRUYỀN THÔNG")

    # --- TABS ---
    tabs = st.tabs(["✅ Quản lý Công việc", "🗂️ Quản lý Dự án", "📧 Soạn thảo & Gửi Email", "📜 Nhật ký Hệ thống"])

    # Load dữ liệu nền
    df_duan = lay_du_lieu(sh, "DuAn")
    list_duan = df_duan['TenDuAn'].tolist() if not df_duan.empty else []
    
    df_users = lay_du_lieu(sh, "TaiKhoan")
    list_nv = df_users['HoTen'].tolist() if not df_users.empty else []

    # =========================================================
    # TAB 1: QUẢN LÝ CÔNG VIỆC
    # =========================================================
    with tabs[0]:
        st.caption("Theo dõi tiến độ, phân công và cập nhật trạng thái.")

        # --- A. FORM TẠO VIỆC (ĐÃ BỎ st.form ĐỂ REAL-TIME) ---
        with st.expander("➕ KHỞI TẠO ĐẦU VIỆC MỚI", expanded=False):
            st.info("💡 Điền thông tin công việc, sau đó cấu hình email và bấm Lưu.")
            
            # 1. THÔNG TIN CÔNG VIỆC
            st.markdown("#### 1. Thông tin công việc")
            c1, c2 = st.columns(2)
            with c1:
                tv_ten = st.text_input("Tên đầu việc / Nhiệm vụ")
                tv_duan = st.selectbox("Thuộc Dự án / Nhóm việc", list_duan)
                
                st.write("⏱️ **Thời hạn hoàn thành (Deadline):**")
                col_h, col_d = st.columns(2)
                tv_time = col_h.time_input("Giờ", value=datetime.now().time())
                tv_date = col_d.date_input("Ngày", value=datetime.now())
                
            with c2:
                tv_nguoi = st.multiselect("Nhân sự thực hiện", list_nv)
                tv_ghichu = st.text_area("Mô tả chi tiết / Yêu cầu", height=135)

            st.divider()

            # 2. CẤU HÌNH GỬI EMAIL (REAL-TIME)
            st.markdown("#### 2. Cấu hình gửi Email thông báo")
            
            ct1, ct2 = st.columns([2,1])
            with ct1:
                # Selectbox này giờ sẽ cập nhật link ngay lập tức khi chọn
                tk_gui = st.selectbox("Gửi từ Tài khoản Gmail số:", range(10), format_func=lambda x: f"Tài khoản số {x} (trên máy này)")
            with ct2:
                st.write("Kiểm tra:")
                # Link này sẽ nhảy số ngay khi tk_gui thay đổi
                st.markdown(f'<a href="https://mail.google.com/mail/u/{tk_gui}" target="_blank" style="background:#f0f2f6; padding: 6px 12px; border-radius: 5px; text-decoration: none; border: 1px solid #ccc; display: inline-block;">👁️ Mở Hộp thư số {tk_gui}</a>', unsafe_allow_html=True)
            
            co1, co2 = st.columns(2)
            opt_nv = co1.checkbox("Gửi cho Nhân sự thực hiện", value=True)
            opt_ld = co2.checkbox("Gửi báo cáo cho Lãnh đạo", value=False)

            st.markdown("---")
            
            # 3. NÚT LƯU (DÙNG BUTTON THƯỜNG VÌ ĐÃ BỎ FORM)
            if st.button("💾 Lưu công việc & Tạo Email", type="primary"):
                if tv_ten and tv_duan:
                    try:
                        deadline_fmt = f"{tv_time.strftime('%H:%M')} {tv_date.strftime('%d/%m/%Y')}"
                        nguoi_str = ", ".join(tv_nguoi)
                        
                        # Mặc định trạng thái ban đầu là "Đã giao"
                        trang_thai_bd = "Đã giao"
                        
                        wks_cv = sh.worksheet("CongViec")
                        wks_cv.append_row([tv_ten, tv_duan, deadline_fmt, nguoi_str, trang_thai_bd, "", tv_ghichu])
                        
                        ghi_nhat_ky(sh, current_name, "Tạo việc", f"{tv_ten} ({tv_duan})")
                        st.success("✅ Đã tạo công việc thành công!")

                        # Tạo link Email
                        msg_links = []
                        # Gửi nhân viên
                        if opt_nv and tv_nguoi:
                            mails_nv = df_users[df_users['HoTen'].isin(tv_nguoi)]['Email'].dropna().tolist()
                            mails_nv = [m for m in mails_nv if str(m).strip()]
                            if mails_nv:
                                sub = f"[GIAO VIỆC] {tv_ten} - Hạn: {deadline_fmt}"
                                body = f"Chào các bạn,\n\nBạn được phân công nhiệm vụ mới:\n- Đầu việc: {tv_ten}\n- Dự án: {tv_duan}\n- Deadline: {deadline_fmt}\n- Ghi chú: {tv_ghichu}\n\nNgười tạo: {current_name}"
                                link = f"https://mail.google.com/mail/u/{tk_gui}/?view=cm&fs=1&to={','.join(mails_nv)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(body)}"
                                msg_links.append(f'<a href="{link}" target="_blank" style="background:#28a745;color:white;padding:8px 12px;text-decoration:none;border-radius:5px;margin-right:10px;">📧 Gửi NV Phụ Trách (TK {tk_gui})</a>')
                        
                        # Gửi Lãnh đạo
                        if opt_ld:
                            mails_ld = df_users[df_users['VaiTro'] == 'LanhDao']['Email'].dropna().tolist()
                            mails_ld = [m for m in mails_ld if str(m).strip()]
                            if mails_ld:
                                sub = f"[BÁO CÁO] Công việc mới: {tv_ten}"
                                body = f"Kính gửi Lãnh đạo,\n\nTôi vừa khởi tạo đầu việc mới:\n- Việc: {tv_ten}\n- Dự án: {tv_duan}\n- Phụ trách: {nguoi_str}\n\nTrân trọng."
                                link = f"https://mail.google.com/mail/u/{tk_gui}/?view=cm&fs=1&to={','.join(mails_ld)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(body)}"
                                msg_links.append(f'<a href="{link}" target="_blank" style="background:#007bff;color:white;padding:8px 12px;text-decoration:none;border-radius:5px;">📧 Báo cáo Lãnh đạo (TK {tk_gui})</a>')
                        
                        if msg_links:
                            st.info("👇 Bấm vào nút dưới đây để gửi email:")
                            st.markdown(" ".join(msg_links), unsafe_allow_html=True)
                            
                    except Exception as e:
                        st.error(f"Lỗi hệ thống: {e}")
                else:
                    st.warning("Vui lòng nhập đầy đủ Tên việc và Dự án.")

        # --- B. DANH SÁCH & CÔNG CỤ ĐIỀU PHỐI ---
        st.divider()
        st.subheader("📋 Danh sách Công việc hiện tại")
        
        filter_da = st.selectbox("Lọc theo Dự án:", ["-- Tất cả dự án --"] + list_duan)
        
        df_cv = lay_du_lieu(sh, "CongViec")
        if not df_cv.empty:
            df_view = df_cv.copy()
            
            if filter_da != "-- Tất cả dự án --":
                df_view = df_view[df_view['DuAn'] == filter_da]
                
                is_admin_duan = kiem_tra_quyen_du_an(current_name, role_system, filter_da, df_duan)
                if is_admin_duan:
                    st.success(f"🌟 Bạn có quyền ĐIỀU PHỐI (Sửa/Xóa) trong dự án: {filter_da}")
                    with st.expander("🛠️ CÔNG CỤ ĐIỀU CHỈNH (Sửa/Xóa)", expanded=True):
                        tab_sua, tab_xoa = st.tabs(["✏️ Chỉnh sửa đầu việc", "🗑️ Xóa đầu việc"])
                        
                        with tab_sua:
                            opts_sua = [f"{row['TenViec']} (ID: {i+2})" for i, row in df_view.iterrows()]
                            if opts_sua:
                                chon_sua = st.selectbox("Chọn việc cần sửa:", opts_sua)
                                original_idx = df_cv.index[df_cv['TenViec'] == chon_sua.split(" (ID:")[0]].tolist()[0]
                                row_data = df_cv.iloc[original_idx]

                                with st.form("form_sua"):
                                    ce1, ce2 = st.columns(2)
                                    with ce1:
                                        e_ten = st.text_input("Tên việc", value=row_data['TenViec'])
                                        e_nguoi = st.text_input("Người phụ trách", value=row_data['NguoiPhuTrach'])
                                    with ce2:
                                        curr_deadline = row_data['Deadline'] if 'Deadline' in row_data else ""
                                        e_dl = st.text_input("Deadline", value=curr_deadline)
                                        
                                        # CẬP NHẬT TRẠNG THÁI MỚI
                                        trang_thai_hien_tai = row_data['TrangThai']
                                        index_tt = OPTS_TRANG_THAI.index(trang_thai_hien_tai) if trang_thai_hien_tai in OPTS_TRANG_THAI else 0
                                        e_tt = st.selectbox("Trạng thái", OPTS_TRANG_THAI, index=index_tt)
                                    
                                    if st.form_submit_button("Cập nhật thay đổi"):
                                        wks_cv = sh.worksheet("CongViec")
                                        row_num = original_idx + 2
                                        wks_cv.update_cell(row_num, 1, e_ten)
                                        wks_cv.update_cell(row_num, 3, e_dl)
                                        wks_cv.update_cell(row_num, 4, e_nguoi)
                                        wks_cv.update_cell(row_num, 5, e_tt)
                                        ghi_nhat_ky(sh, current_name, "Sửa việc", f"{e_ten} -> {e_tt}")
                                        st.success("Đã cập nhật dữ liệu!")
                                        st.rerun()

                        with tab_xoa:
                            if opts_sua:
                                chon_xoa = st.multiselect("Chọn các việc muốn xóa:", opts_sua)
                                if st.button("Xác nhận Xóa vĩnh viễn"):
                                    if chon_xoa:
                                        wks_cv = sh.worksheet("CongViec")
                                        all_vals = wks_cv.get_all_values()
                                        names_to_del = [x.split(" (ID:")[0] for x in chon_xoa]
                                        new_data = [all_vals[0]]
                                        for row in all_vals[1:]:
                                            if row[1] == filter_da and row[0] in names_to_del:
                                                continue
                                            new_data.append(row)
                                        wks_cv.clear()
                                        wks_cv.update(new_data)
                                        ghi_nhat_ky(sh, current_name, "Xóa việc", str(names_to_del))
                                        st.success("Đã xóa thành công!")
                                        st.rerun()

            # --- HIỂN THỊ BẢNG ---
            df_display = df_view.rename(columns=VN_COLS_VIEC)
            st.dataframe(
                df_display, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Link sản phẩm": st.column_config.LinkColumn("Link sản phẩm", display_text="🔗 Mở Link"),
                    "Trạng thái": st.column_config.SelectboxColumn("Trạng thái", options=OPTS_TRANG_THAI, width="medium")
                }
            )
        else:
            st.info("Hiện chưa có dữ liệu công việc.")

    # =========================================================
    # TAB 2: QUẢN LÝ DỰ ÁN
    # =========================================================
    with tabs[1]:
        st.header("🗂️ Hồ sơ & Quản lý Dự án")
        
        if role_system == 'LanhDao':
            with st.expander("➕ THIẾT LẬP DỰ ÁN MỚI (Admin)", expanded=False):
                with st.form("tao_duan"):
                    n_da = st.text_input("Tên Dự án / Nhóm việc")
                    n_mt = st.text_area("Mô tả / Ghi chú")
                    n_lead = st.multiselect("Chỉ định Điều phối viên (Trưởng nhóm):", list_nv)
                    
                    if st.form_submit_button("Tạo Dự án"):
                        try:
                            wks_da = sh.worksheet("DuAn")
                            lead_str = ", ".join(n_lead)
                            wks_da.append_row([n_da, n_mt, "Đang chạy", lead_str])
                            ghi_nhat_ky(sh, current_name, "Tạo Dự án", f"{n_da} (Leads: {lead_str})")
                            st.success("Đã khởi tạo dự án thành công!")
                            st.rerun()
                        except:
                            st.error("Lỗi khi lưu vào Google Sheet.")
            
            with st.expander("🗑️ Xóa Dự án (Admin)", expanded=False):
                del_da = st.selectbox("Chọn dự án muốn xóa:", list_duan)
                if st.button("Xác nhận Xóa Dự án"):
                    wks_da = sh.worksheet("DuAn")
                    rows = wks_da.get_all_values()
                    new = [rows[0]] + [r for r in rows[1:] if r[0] != del_da]
                    wks_da.clear()
                    wks_da.update(new)
                    st.success("Đã xóa dự án khỏi hệ thống.")
                    st.rerun()

        if not df_duan.empty:
            df_da_display = df_duan.rename(columns=VN_COLS_DUAN)
            st.dataframe(df_da_display, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có dự án nào đang chạy.")

    # =========================================================
    # TAB 3: SOẠN THẢO EMAIL
    # =========================================================
    with tabs[2]:
        st.header("📧 Soạn thảo & Gửi Email")
        
        c_acc1, c_acc2 = st.columns([2,1])
        with c_acc1:
            tk_mail = st.selectbox("Gửi từ Tài khoản Gmail số:", range(10), format_func=lambda x: f"Tài khoản {x}", key="mail_center")
        with c_acc2:
            st.markdown(f'<br><a href="https://mail.google.com/mail/u/{tk_mail}" target="_blank">👁️ Kiểm tra Hộp thư</a>', unsafe_allow_html=True)
            
        try:
            mau_data = lay_du_lieu(sh, "MauEmail")
            danh_ba = {r['HoTen']: r['Email'] for i,r in df_users.iterrows() if str(r['Email']).strip()}
            mau_dict = {r['TenMau']: r for i,r in mau_data.iterrows()} if not mau_data.empty else {}
        except:
            danh_ba = {}
            mau_dict = {}

        c_to, c_mau = st.columns(2)
        with c_to:
            send_to = st.multiselect("Người nhận (To):", list(danh_ba.keys()))
            emails_to = [danh_ba[x] for x in send_to]
        with c_mau:
            pick_mau = st.selectbox("Chọn Mẫu Email:", ["-- Tự soạn thảo --"] + list(mau_dict.keys()))
        
        val_td, val_nd = "", ""
        if pick_mau != "-- Tự soạn thảo --":
            val_td = mau_dict[pick_mau]['TieuDe']
            val_nd = mau_dict[pick_mau]['NoiDung']
        
        if send_to:
            names = [n.split()[-1] for n in send_to]
            greeting = f"Dear {', '.join(names)},\n\n"
            if "Dear" not in val_nd: val_nd = greeting + val_nd
            
        final_td = st.text_input("Tiêu đề:", value=val_td)
        final_nd = st.text_area("Nội dung:", value=val_nd, height=250)
        
        if st.button("🚀 Gửi Email ngay", type="primary"):
            if emails_to:
                link = f"https://mail.google.com/mail/u/{tk_mail}/?view=cm&fs=1&to={','.join(emails_to)}&su={urllib.parse.quote(final_td)}&body={urllib.parse.quote(final_nd)}"
                ghi_nhat_ky(sh, current_name, "Gửi Email", f"Tiêu đề: {final_td}")
                st.markdown(f'<script>window.open("{link}", "_blank");</script>', unsafe_allow_html=True)
                st.success("Đang mở trình soạn thảo Gmail...")
            else:
                st.error("Vui lòng chọn ít nhất một người nhận.")

    # =========================================================
    # TAB 4: NHẬT KÝ HỆ THỐNG
    # =========================================================
    if role_system == 'LanhDao':
        with tabs[3]:
            st.header("📜 Nhật ký Hệ thống (Logs)")
            df_log = lay_du_lieu(sh, "NhatKy")
            if not df_log.empty:
                df_log = df_log.iloc[::-1]
                df_log_display = df_log.rename(columns=VN_COLS_LOG)
                st.dataframe(df_log_display, use_container_width=True, hide_index=True)
            else:
                st.info("Chưa có dữ liệu nhật ký.")
    else:
        with tabs[3]:
            st.warning("🔒 Khu vực này chỉ dành cho Lãnh đạo hệ thống.")