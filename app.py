import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components
import urllib.parse
from datetime import datetime, date

# ================= CẤU HÌNH GIAO DIỆN =================
st.set_page_config(page_title="Hệ thống Tòa Soạn Số", page_icon="📰", layout="wide")

# ================= 1. CÁC HÀM HỖ TRỢ (BACKEND) =================

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
        st.error(f"🔴 Lỗi kết nối Sheet: {e}")
        st.stop()

def lay_du_lieu(sh, ten_tab):
    try:
        wks = sh.worksheet(ten_tab)
        data = wks.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# ================= 2. QUẢN LÝ ĐĂNG NHẬP =================
if 'dang_nhap' not in st.session_state:
    st.session_state['dang_nhap'] = False
    st.session_state['user_info'] = {}

sh = ket_noi_sheet() 

if not st.session_state['dang_nhap']:
    st.markdown("## 🔐 ĐĂNG NHẬP HỆ THỐNG")
    with st.form("login"):
        user = st.text_input("Tên đăng nhập")
        pwd = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Truy cập"):
            users = lay_du_lieu(sh, "TaiKhoan")
            if not users.empty:
                user_row = users[(users['TenDangNhap'].astype(str) == user) & (users['MatKhau'].astype(str) == pwd)]
                if not user_row.empty:
                    st.session_state['dang_nhap'] = True
                    st.session_state['user_info'] = user_row.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Sai tên đăng nhập hoặc mật khẩu!")
            else:
                st.error("Chưa có dữ liệu tài khoản trong Sheet.")
else:
    # --- Sidebar thông tin ---
    user_info = st.session_state['user_info']
    role = user_info.get('VaiTro', 'NhanVien')
    current_user_name = user_info['HoTen'] # Lấy tên người đang đăng nhập
    
    with st.sidebar:
        st.success(f"Xin chào: **{current_user_name}**")
        st.caption(f"Vai trò: {role}")
        if role == 'LanhDao':
            st.info("⭐ Quyền Quản trị viên")
        
        if st.button("Đăng xuất"):
            st.session_state['dang_nhap'] = False
            st.rerun()

    # ================= 3. GIAO DIỆN CHÍNH =================
    st.title("📰 TÒA SOẠN SỐ THÔNG MINH")
    
    if role == 'LanhDao':
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "✅ Quản Lý Công Việc", "🗂️ Quản lý Dự Án", "📧 Trung Tâm Email"])
    else:
        # Đổi tên Tab cho thân thiện với nhân viên
        tab1, tab2, tab3 = st.tabs(["✅ Việc Của Tôi", "🗂️ Quản lý Dự Án", "📧 Trung Tâm Email"])
        tab4 = None 

    # ---------------------------------------------------------
    # TAB 1: DASHBOARD (CHỈ LÃNH ĐẠO)
    # ---------------------------------------------------------
    if role == 'LanhDao':
        with tab1:
            st.header("Tổng quan Tòa soạn")
            df_cv = lay_du_lieu(sh, "CongViec")
            
            if not df_cv.empty:
                total = len(df_cv)
                completed = len(df_cv[df_cv['TrangThai'] == 'Xong'])
                in_progress = len(df_cv[df_cv['TrangThai'] == 'Đang làm'])
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Tổng đầu việc", total)
                c2.metric("Hoàn thành", completed)
                c3.metric("Đang triển khai", in_progress)
                
                st.divider()
                st.write("📊 **Tiến độ theo Dự án:**")
                try:
                    stats = df_cv.groupby(['DuAn', 'TrangThai']).size().unstack(fill_value=0)
                    st.bar_chart(stats)
                except:
                    st.caption("Chưa đủ dữ liệu biểu đồ.")
            else:
                st.info("Chưa có dữ liệu.")

    # ---------------------------------------------------------
    # TAB 2: QUẢN LÝ CÔNG VIỆC (ĐÃ CẬP NHẬT LOGIC RIÊNG TƯ)
    # ---------------------------------------------------------
    target_tab_viec = tab2 if role == 'LanhDao' else tab1
    
    with target_tab_viec:
        df_da = lay_du_lieu(sh, "DuAn")
        list_du_an = df_da['TenDuAn'].tolist() if not df_da.empty else ["Việc chung"]
        
        df_users = lay_du_lieu(sh, "TaiKhoan")
        list_nv = df_users['HoTen'].tolist() if not df_users.empty else []

        # --- TIÊU ĐỀ THAY ĐỔI THEO VAI TRÒ ---
        if role == 'LanhDao':
            st.subheader("📝 Quản lý toàn bộ công việc (Admin)")
        else:
            st.subheader(f"📝 Danh sách việc của: {current_user_name}")
        
        # --- FORM TẠO VIỆC MỚI ---
        with st.expander("➕ TẠO VIỆC MỚI", expanded=False):
            with st.form("tao_viec_form"):
                st.markdown("### 1. Thông tin công việc")
                c1, c2 = st.columns(2)
                with c1:
                    tv_ten = st.text_input("Tên đầu việc", placeholder="Vd: Duyệt maket trang 1")
                    tv_duan = st.selectbox("Thuộc Cụm dự án", list_du_an)
                    
                    st.write("⏱️ **Hạn chót (Deadline):**")
                    col_gio, col_ngay = st.columns(2)
                    tv_time = col_gio.time_input("Giờ", value=datetime.now().time())
                    tv_date = col_ngay.date_input("Ngày", value=datetime.now())
                    
                with c2:
                    # Mặc định chọn chính mình nếu là nhân viên
                    default_nguoi = [current_user_name] if role == 'NhanVien' and current_user_name in list_nv else []
                    tv_nguoi = st.multiselect("Người thực hiện", list_nv, default=default_nguoi, placeholder="Chọn nhân sự...")
                    tv_ghichu = st.text_area("Ghi chú / Yêu cầu chi tiết", height=100)
                
                st.divider()
                st.markdown("### 2. Cấu hình gửi Email thông báo")
                
                col_tk_1, col_tk_2 = st.columns([2, 1])
                with col_tk_1:
                    tk_gui_viec = st.selectbox(
                        "📤 Gửi từ tài khoản Gmail số:",
                        options=list(range(10)),
                        format_func=lambda x: f"Tài khoản số {x}",
                        help="Chọn số tài khoản Gmail bạn đang đăng nhập trên máy này."
                    )
                with col_tk_2:
                    st.write("Kiểm tra:")
                    link_check_viec = f"https://mail.google.com/mail/u/{tk_gui_viec}"
                    st.markdown(f'<a href="{link_check_viec}" target="_blank" style="padding: 5px 10px; background:#eee; text-decoration:none; border-radius:5px; font-size:12px;">👁️ Xem hộp thư số {tk_gui_viec}</a>', unsafe_allow_html=True)

                c_opt1, c_opt2 = st.columns(2)
                opt_gui_nv = c_opt1.checkbox("Gửi cho những người thực hiện", value=True)
                opt_gui_ld = c_opt2.checkbox("Gửi báo cáo cho Lãnh đạo", value=False)
                
                btn_luu = st.form_submit_button("💾 Lưu Công Việc & Tạo Email", type="primary")
                
            if btn_luu and tv_ten:
                deadline_str = f"{tv_time.strftime('%H:%M')} {tv_date.strftime('%d/%m/%Y')}"
                nguoi_str = ", ".join(tv_nguoi)
                
                try:
                    wks_cv = sh.worksheet("CongViec")
                    wks_cv.append_row([tv_ten, tv_duan, deadline_str, nguoi_str, "Mới", "", tv_ghichu])
                    st.success("✅ Đã lưu công việc thành công!")
                    
                    msg_links = []
                    
                    if opt_gui_nv and tv_nguoi:
                        ds_email_nv = df_users[df_users['HoTen'].isin(tv_nguoi)]['Email'].dropna().tolist()
                        ds_email_nv = [e for e in ds_email_nv if str(e).strip() != ""]
                        
                        if ds_email_nv:
                            str_to_nv = ",".join(ds_email_nv)
                            sub_nv = f"[GIAO VIỆC] {tv_ten} - Deadline: {deadline_str}"
                            body_nv = f"Chào các bạn,\n\nBạn được phân công tham gia công việc:\n- Đầu việc: {tv_ten}\n- Dự án: {tv_duan}\n- Hạn chót: {deadline_str}\n- Yêu cầu: {tv_ghichu}\n\nVui lòng kiểm tra và thực hiện đúng hạn.\n\nNgười tạo việc:\n{user_info['HoTen']}"
                            link_nv = f"https://mail.google.com/mail/u/{tk_gui_viec}/?view=cm&fs=1&to={str_to_nv}&su={urllib.parse.quote(sub_nv)}&body={urllib.parse.quote(body_nv)}"
                            msg_links.append(f'<a href="{link_nv}" target="_blank" style="background:#00C853;color:white;padding:10px;border-radius:5px;text-decoration:none;font-weight:bold">📧 Gửi NV Phụ Trách (TK số {tk_gui_viec})</a>')
                    
                    if opt_gui_ld:
                        ds_email_ld = df_users[df_users['VaiTro'] == 'LanhDao']['Email'].dropna().tolist()
                        ds_email_ld = [e for e in ds_email_ld if str(e).strip() != ""]
                        if ds_email_ld:
                            str_to_ld = ",".join(ds_email_ld)
                            sub_ld = f"[BÁO CÁO] Tạo việc mới: {tv_ten}"
                            body_ld = f"Kính gửi Lãnh đạo,\n\nTôi vừa khởi tạo đầu việc mới trên hệ thống:\n- Việc: {tv_ten}\n- Dự án: {tv_duan}\n- Phụ trách: {nguoi_str}\n- Deadline: {deadline_str}\n\nTrân trọng báo cáo."
                            link_ld = f"https://mail.google.com/mail/u/{tk_gui_viec}/?view=cm&fs=1&to={str_to_ld}&su={urllib.parse.quote(sub_ld)}&body={urllib.parse.quote(body_ld)}"
                            msg_links.append(f'<a href="{link_ld}" target="_blank" style="background:#2962FF;color:white;padding:10px;border-radius:5px;text-decoration:none;font-weight:bold;margin-left:10px">📧 Gửi Báo Cáo Lãnh Đạo (TK số {tk_gui_viec})</a>')

                    if msg_links:
                        st.info(f"👇 Bấm vào nút bên dưới để gửi email thông báo (Từ tài khoản số {tk_gui_viec}):")
                        st.markdown(" ".join(msg_links), unsafe_allow_html=True)
                        
                except Exception as e:
                    st.error(f"Lỗi khi lưu: {e}")

        st.divider()
        filter_duan = st.selectbox("🔍 Lọc theo Dự án", ["Tất cả"] + list_du_an)
        
        df_view = lay_du_lieu(sh, "CongViec")
        if not df_view.empty:
            # 1. LỌC THEO DỰ ÁN
            if filter_duan != "Tất cả":
                df_view = df_view[df_view['DuAn'] == filter_duan]
            
            # 2. LỌC THEO NGƯỜI (QUAN TRỌNG)
            # Nếu là Lãnh đạo: Xem hết (Không lọc)
            # Nếu là Nhân viên: Chỉ giữ lại dòng nào CÓ TÊN MÌNH trong cột NguoiPhuTrach
            if role != 'LanhDao':
                # Chuyển cột NguoiPhuTrach sang dạng chuỗi để tìm kiếm
                # Dùng str.contains để tìm tên mình trong chuỗi "Huy, Lan, Tùng"
                df_view = df_view[df_view['NguoiPhuTrach'].astype(str).str.contains(current_user_name, na=False)]

            # Hiển thị
            if not df_view.empty:
                st.dataframe(
                    df_view, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "LinkBai": st.column_config.LinkColumn("Link Bài"),
                        "TrangThai": st.column_config.SelectboxColumn("Trạng thái", options=["Mới", "Đang làm", "Xong", "Hủy"]),
                        "Deadline": st.column_config.TextColumn("Hạn chót (Giờ - Ngày)")
                    }
                )
            else:
                if role != 'LanhDao':
                    st.info(f"Bạn ({current_user_name}) hiện chưa có công việc nào trong dự án này.")
                else:
                    st.info("Chưa có dữ liệu.")
        else:
            st.info("Chưa có công việc nào.")

    # ---------------------------------------------------------
    # TAB 3: QUẢN LÝ DỰ ÁN
    # ---------------------------------------------------------
    target_tab_da = tab3 if role == 'LanhDao' else tab2
    with target_tab_da:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("➕ Thêm Dự Án Mới")
            with st.form("add_da"):
                new_da = st.text_input("Tên Dự án / Chuyên mục")
                new_desc = st.text_area("Mô tả")
                if st.form_submit_button("Tạo Dự Án"):
                    try:
                        wks_da = sh.worksheet("DuAn")
                        wks_da.append_row([new_da, new_desc, "Đang chạy"])
                        st.success(f"Đã thêm: {new_da}")
                        st.rerun()
                    except:
                        st.error("Lỗi lưu dự án.")
        with c2:
            st.subheader("Danh sách Cụm Dự án")
            df_da_view = lay_du_lieu(sh, "DuAn")
            if not df_da_view.empty:
                st.dataframe(df_da_view, use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # TAB 4: TRUNG TÂM EMAIL (10 TÀI KHOẢN)
    # ---------------------------------------------------------
    target_tab_email = tab4 if role == 'LanhDao' else tab3
    with target_tab_email:
        st.header("📧 Trung tâm Soạn Thảo Email")
        
        st.info("💡 Lưu ý: Hãy chọn số tài khoản Gmail tương ứng trên máy tính này.")
        col_tk1, col_tk2 = st.columns([2, 1])
        with col_tk1:
            tai_khoan_chon = st.selectbox(
                "📤 Bạn muốn gửi từ Tài khoản số mấy?",
                options=list(range(10)), 
                format_func=lambda x: f"Tài khoản Gmail số {x} (Mặc định)" if x == 0 else f"Tài khoản Gmail số {x}"
            )
        with col_tk2:
            st.write("Kiểm tra:")
            link_check = f"https://mail.google.com/mail/u/{tai_khoan_chon}"
            st.markdown(f'<a href="{link_check}" target="_blank" style="padding: 5px 10px; background:#eee; text-decoration:none; border-radius:5px;">👁️ Mở Hộp thư số {tai_khoan_chon}</a>', unsafe_allow_html=True)

        st.divider()

        # ... (Logic Email Center giữ nguyên) ...
        try:
            users_data = lay_du_lieu(sh, "TaiKhoan")
            if not users_data.empty:
                danh_ba = {row['HoTen']: row['Email'] for index, row in users_data.iterrows() if str(row['Email']).strip() != ""}
                list_ten = list(danh_ba.keys())
            else:
                list_ten = []
                danh_ba = {}

            mau_data = lay_du_lieu(sh, "MauEmail")
            thu_vien_mau = {}
            if not mau_data.empty:
                for index, row in mau_data.iterrows():
                    thu_vien_mau[row['TenMau']] = {"tieu_de": row['TieuDe'], "noi_dung": row['NoiDung']}
        except:
            st.error("Lỗi đọc dữ liệu.")
            st.stop()

        col_main_1, col_main_2 = st.columns(2)
        with col_main_1:
            nguoi_nhan_ten = st.multiselect("Đến (To):", list_ten, placeholder="Chọn người nhận...")
            email_to = [danh_ba[ten] for ten in nguoi_nhan_ten]
            co_dear = st.checkbox("Tự động thêm 'Dear...'", value=True)
        with col_main_2:
            ds_ten_mau = ["-- Tự soạn thảo --"] + list(thu_vien_mau.keys())
            ten_mau_chon = st.selectbox("Chọn mẫu nội dung:", ds_ten_mau)

        with st.expander("Mở rộng: Thêm CC / BCC"):
            c_cc, c_bcc = st.columns(2)
            with c_cc:
                cc_ten = st.multiselect("CC:", list_ten)
                email_cc = [danh_ba[ten] for ten in cc_ten]
            with c_bcc:
                bcc_ten = st.multiselect("BCC:", list_ten)
                email_bcc = [danh_ba[ten] for ten in bcc_ten]

        val_tieu_de = ""
        val_noi_dung = ""
        if ten_mau_chon != "-- Tự soạn thảo --":
            val_tieu_de = thu_vien_mau[ten_mau_chon]["tieu_de"]
            val_noi_dung = thu_vien_mau[ten_mau_chon]["noi_dung"]

        def lay_ten_ngan(full_name): return full_name.strip().split(" ")[-1] if full_name else ""
        if co_dear and nguoi_nhan_ten:
            ds_ten_ngan = [lay_ten_ngan(ten) for ten in nguoi_nhan_ten]
            loi_chao = f"Dear {', '.join(ds_ten_ngan)},\n\n"
            if not val_noi_dung: val_noi_dung = loi_chao
            elif "Dear" not in val_noi_dung and "Kính gửi" not in val_noi_dung: val_noi_dung = loi_chao + val_noi_dung

        nguoi_ky = st.session_state['user_info'].get('HoTen', 'Ban Thư Ký')
        if val_noi_dung and nguoi_ky not in val_noi_dung:
            val_noi_dung += f"\n\nTrân trọng,\n{nguoi_ky}"

        st.markdown("### ✍️ Soạn thảo chi tiết")
        final_tieu_de = st.text_input("Tiêu đề:", value=val_tieu_de)
        final_noi_dung = st.text_area("Nội dung:", value=val_noi_dung, height=300)

        if st.button(f"🚀 Mở Gmail (TK số {tai_khoan_chon}) để gửi", type="primary"):
            if not email_to:
                st.warning("Vui lòng chọn người nhận!")
            else:
                str_to, str_cc, str_bcc = ",".join(email_to), ",".join(email_cc), ",".join(email_bcc)
                su_enc = urllib.parse.quote(final_tieu_de)
                body_enc = urllib.parse.quote(final_noi_dung)
                
                gmail_link = f"https://mail.google.com/mail/u/{tai_khoan_chon}/?view=cm&fs=1&to={str_to}&cc={str_cc}&bcc={str_bcc}&su={su_enc}&body={body_enc}"
                
                js_script = f"""<script>window.open("{gmail_link}", "_blank");</script>"""
                components.html(js_script, height=0)
                st.success(f"Đang chuyển hướng sang Gmail số {tai_khoan_chon}...")