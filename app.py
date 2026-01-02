# app.py
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. KẾT NỐI GOOGLE SHEETS ---
def ket_noi_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
    client = gspread.authorize(creds)
    # Mở file sheet (nhớ đổi tên cho đúng file của bạn)
    sheet = client.open("HeThongQuanLy") 
    return sheet

# Tìm đoạn try-except cũ và thay bằng đoạn này:
try:
    sh = ket_noi_sheet()
    worksheet_cv = sh.worksheet("CongViec")
    worksheet_ns = sh.worksheet("NhanSu")
    st.toast("Kết nối dữ liệu thành công!", icon="✅")
except Exception as e:
    st.error(f"LỖI KẾT NỐI: {e}")
    st.warning("Hãy kiểm tra: 1. Đã Share file Sheet cho email trong key.json chưa? 2. Tên Tab trong Sheet có đúng là 'CongViec' không?")
    st.stop() # <--- CÂU LỆNH QUAN TRỌNG: Dừng chương trình tại đây nếu lỗi.

# --- 2. GIAO DIỆN CHÍNH ---
st.title("📱 TÒA SOẠN SỐ - QUẢN LÝ TIẾN ĐỘ")

# Menu bên trái
menu = st.sidebar.selectbox("Chọn chức năng", ["Xem Tiến Độ", "Giao Việc Mới", "Gửi Email"])

if menu == "Xem Tiến Độ":
    st.header("Danh sách bài đang chạy")
    # Lấy dữ liệu về
    data = worksheet_cv.get_all_records()
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

elif menu == "Giao Việc Mới":
    st.header("Thêm đầu việc mới")
    with st.form("form_giao_viec"):
        ten_bai = st.text_input("Tên bài/Phóng sự")
        nguoi_lam = st.text_input("Người phụ trách")
        deadline = st.date_input("Hạn chót")
        submit = st.form_submit_button("Lưu lại")
        
        if submit:
            # Code thêm dòng mới vào sheet
            row = [len(pd.DataFrame(worksheet_cv.get_all_records()))+1, ten_bai, nguoi_lam, str(deadline), "Mới", "", ""]
            worksheet_cv.append_row(row)
            st.success("Đã giao việc thành công!")
            st.rerun() # Tải lại trang

elif menu == "Gửi Email":
    st.write("Chức năng gửi email (Code sau khi đã có App Password)")