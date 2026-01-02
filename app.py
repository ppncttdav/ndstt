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

    # --- CHỨC NĂNG 3: GỬI EMAIL (Link Mailto) ---
    elif menu == "Gửi Email Nhắc Nhở":
        st.header("📧 Soạn Email Nhắc Việc")
        
        col1, col2 = st.columns(2)
        with col1:
            email_nhan = st.text_input("Email người nhận", placeholder="vidu@gmail.com")
        with col2:
            ten_nhan = st.text_input("Tên người nhận", placeholder="Anh/Chị A")
            
        tieu_de = st.text_input("Tiêu đề", value="[Nhắc nhở] Về tiến độ công việc")
        
        # Lấy Họ tên đầy đủ từ Sheet TaiKhoan để ký tên
        nguoi_ky_ten = st.session_state['user_info'].get('HoTen', 'Ban Thư Ký')
        
        noi_dung_mau = f"""Chào {ten_nhan},
        
Tôi thấy tiến độ công việc của bạn đang bị chậm. Vui lòng cập nhật sớm nhé.

Trân trọng,
{nguoi_ky_ten}"""
        
        noi_dung = st.text_area("Nội dung", value=noi_dung_mau, height=200)
        
        if email_nhan and st.button("Tạo Email 🚀"):
            subject_encoded = urllib.parse.quote(tieu_de)
            body_encoded = urllib.parse.quote(noi_dung)
            mailto_link = f"mailto:{email_nhan}?subject={subject_encoded}&body={body_encoded}"
            
            st.markdown(f"""
            <a href="{mailto_link}" target="_blank" style="
                background-color: #ff4b4b; color: white; padding: 12px 24px; 
                text-decoration: none; border-radius: 8px; font-weight: bold;
                display: inline-block;">
                👉 BẤM ĐỂ GỬI MAIL (Mở App Mail của bạn)
            </a>
            """, unsafe_allow_html=True)