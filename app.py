import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse 

# --- 1. HÀM KẾT NỐI GOOGLE SHEET (Dùng chung cho cả App) ---
def ket_noi_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Ưu tiên lấy Secrets trên mạng
        if "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # Fallback lấy file key.json máy tính
            creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("HeThongQuanLy") 
        return sheet
    except Exception as e:
        st.error(f"Lỗi kết nối Sheet: {e}")
        st.stop()

# --- 2. HÀM KIỂM TRA ĐĂNG NHẬP (Phiên bản đọc từ Sheet) ---
def kiem_tra_dang_nhap(sh):
    # Khởi tạo trạng thái đăng nhập nếu chưa có
    if 'dang_nhap' not in st.session_state:
        st.session_state['dang_nhap'] = False
        st.session_state['user_info'] = {} # Lưu thông tin người dùng (Tên, Họ tên...)

    # Nếu chưa đăng nhập thì hiện Form
    if not st.session_state['dang_nhap']:
        st.markdown("### 🔒 ĐĂNG NHẬP HỆ THỐNG")
        
        with st.form("login_form"):
            col1, col2 = st.columns(2)
            with col1:
                user_input = st.text_input("Tên đăng nhập")
            with col2:
                pwd_input = st.text_input("Mật khẩu", type="password")
            
            btn_login = st.form_submit_button("Đăng nhập", type="primary")

            if btn_login:
                try:
                    # Lấy dữ liệu từ Tab "TaiKhoan"
                    wks_users = sh.worksheet("TaiKhoan")
                    danh_sach_users = wks_users.get_all_records()
                    
                    # Tìm xem có ai khớp User và Pass không
                    tim_thay = False
                    for u in danh_sach_users:
                        # Lưu ý: Convert sang string để so sánh cho chắc chắn (vì Sheet hay hiểu nhầm số)
                        if str(u['TenDangNhap']) == user_input and str(u['MatKhau']) == pwd_input:
                            st.session_state['dang_nhap'] = True
                            st.session_state['user_info'] = u # Lưu toàn bộ thông tin người đó
                            tim_thay = True
                            st.rerun() # Tải lại trang để vào trong
                            break
                    
                    if not tim_thay:
                        st.error("Sai tên đăng nhập hoặc mật khẩu!")
                        
                except Exception as e:
                    st.error(f"Lỗi đọc dữ liệu tài khoản: {e}. Hãy kiểm tra xem đã tạo Tab 'TaiKhoan' chưa?")
        return False
    
    # Nếu đã đăng nhập
    else:
        ho_ten = st.session_state['user_info'].get('HoTen', 'Admin')
        st.sidebar.success(f"Xin chào: **{ho_ten}** 👋")
        
        if st.sidebar.button("Đăng xuất"):
            st.session_state['dang_nhap'] = False
            st.session_state['user_info'] = {}
            st.rerun()
        return True

# ================= CHƯƠNG TRÌNH CHÍNH =================
# 1. Kết nối Sheet trước
sh = ket_noi_sheet()

# 2. Kiểm tra đăng nhập (Truyền biến sh vào để nó đọc dữ liệu)
if kiem_tra_dang_nhap(sh):
    
    # --- NỘI DUNG CHÍNH CỦA APP ---
    st.title("📱 TÒA SOẠN SỐ - QUẢN LÝ TIẾN ĐỘ")

    menu = st.sidebar.selectbox("Chọn chức năng", ["Xem Tiến Độ", "Báo Cáo Mới", "Gửi Email Nhắc Nhở"])
    
    # --- CHỨC NĂNG 1: XEM TIẾN ĐỘ ---
    if menu == "Xem Tiến Độ":
        st.header("Danh sách bài đang chạy")
        try:
            worksheet = sh.worksheet("CongViec")
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            
            # Nếu bảng có dữ liệu thì mới hiển thị
            if not df.empty:
                st.dataframe(
                    df, 
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "LinkBai": st.column_config.LinkColumn("Link Bài", display_text="🔗 Mở Link"),
                        "TrangThai": st.column_config.SelectboxColumn("Trạng Thái", options=["Mới", "Đang làm", "Hoàn thành"], width="small")
                    }
                )
            else:
                st.info("Chưa có dữ liệu công việc.")
        except:
             st.warning("Không tìm thấy Tab 'CongViec'. Hãy kiểm tra lại file Sheet.")

    # --- CHỨC NĂNG 2: BÁO CÁO MỚI ---
    elif menu == "Báo Cáo Mới":
        st.header("📝 Thêm đầu việc mới")
        with st.form("form_them_moi"):
            ten_bai = st.text_input("Tên bài/Phóng sự")
            deadline = st.date_input("Hạn chót")
            # Tự động điền tên người đang đăng nhập vào ô Người làm
            nguoi_lam_mac_dinh = st.session_state['user_info'].get('HoTen', '')
            nguoi_lam = st.text_input("Người thực hiện", value=nguoi_lam_mac_dinh)
            
            submitted = st.form_submit_button("Lưu dữ liệu")
            
            if submitted:
                worksheet = sh.worksheet("CongViec")
                # Thêm dòng mới vào Sheet
                worksheet.append_row([ten_bai, str(deadline), nguoi_lam, "Mới", "", ""])
                st.success("Đã thêm thành công!")

# --- CHỨC NĂNG 3: GỬI EMAIL (TỐI ƯU CHO NHIỀU NGƯỜI DÙNG) ---
    elif menu == "Gửi Email Nhắc Nhở":
        st.header("📧 Trung tâm Soạn Thảo Email")
        import streamlit.components.v1 as components 

        # --- 1. CHỌN TÀI KHOẢN GỬI (QUAN TRỌNG: PHẢI CHỌN TÙY THEO MÁY) ---
        st.info("💡 Lưu ý: Vì mỗi máy tính đăng nhập các tài khoản Gmail theo thứ tự khác nhau, hãy kiểm tra kỹ trước khi gửi.")
        
        col_tk1, col_tk2 = st.columns([2, 1])
        with col_tk1:
            # Cho chọn tài khoản 0, 1, 2, 3
            tai_khoan_chon = st.selectbox(
                "📤 Bạn muốn gửi từ Tài khoản số mấy trên máy này?",
                options=[0, 1, 2, 3],
                format_func=lambda x: f"Tài khoản Gmail số {x} (Mặc định)" if x == 0 else f"Tài khoản Gmail số {x}"
            )
        with col_tk2:
            # Nút kiểm tra thần thánh: Bấm vào là biết ngay số đó là mail nào
            st.write("Kiểm tra xem là Mail nào:")
            link_check = f"https://mail.google.com/mail/u/{tai_khoan_chon}"
            st.markdown(f'''
                <a href="{link_check}" target="_blank" style="
                    display: inline-block;
                    padding: 8px 15px;
                    background-color: #f0f2f6;
                    color: #31333F;
                    text-decoration: none;
                    border-radius: 5px;
                    border: 1px solid #d6d6d8;
                    font-weight: bold;">
                    👁️ Mở Hộp thư số {tai_khoan_chon}
                </a>
            ''', unsafe_allow_html=True)

        st.divider()

        # --- 2. LẤY DỮ LIỆU TỪ SHEET (Giữ nguyên) ---
        try:
            users_data = sh.worksheet("TaiKhoan").get_all_records()
            danh_ba = {u['HoTen']: u['Email'] for u in users_data if str(u['Email']).strip() != ""}
            list_ten = list(danh_ba.keys())

            mau_data = sh.worksheet("MauEmail").get_all_records()
            thu_vien_mau = {}
            for m in mau_data:
                thu_vien_mau[m['TenMau']] = {"tieu_de": m['TieuDe'], "noi_dung": m['NoiDung']}
        except:
            st.error("Lỗi đọc dữ liệu Sheet.")
            st.stop()

        # --- 3. GIAO DIỆN SOẠN THẢO ---
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

        # Xử lý nội dung & Chữ ký (Giữ nguyên)
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

        # --- 4. NÚT GỬI (Tự động cập nhật theo số đã chọn ở trên) ---
        btn_label = f"🚀 Mở Gmail (Tài khoản số {tai_khoan_chon}) để gửi"
        
        if st.button(btn_label, type="primary"):
            if not email_to:
                st.warning("Vui lòng chọn người nhận!")
            else:
                str_to, str_cc, str_bcc = ",".join(email_to), ",".join(email_cc), ",".join(email_bcc)
                su_enc = urllib.parse.quote(final_tieu_de)
                body_enc = urllib.parse.quote(final_noi_dung)
                
                # Link động theo tai_khoan_chon
                gmail_link = f"https://mail.google.com/mail/u/{tai_khoan_chon}/?view=cm&fs=1&to={str_to}&cc={str_cc}&bcc={str_bcc}&su={su_enc}&body={body_enc}"
                
                js_script = f"""<script>window.open("{gmail_link}", "_blank");</script>"""
                components.html(js_script, height=0)
                st.success(f"Đang chuyển hướng sang Gmail số {tai_khoan_chon}...")