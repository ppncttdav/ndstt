import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components
import urllib.parse
from datetime import datetime, date

# ================= CẤU HÌNH GIAO DIỆN =================
st.set_page_config(page_title="Phòng Nội dung số & Truyền thông", page_icon="🏢", layout="wide")

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

# --- HÀM GHI NHẬT KÝ (LOGS) ---
def ghi_nhat_ky(sh, nguoi_dung, hanh_dong, chi_tiet):
    try:
        wks = sh.worksheet("NhatKy")
        thoi_gian = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        wks.append_row([thoi_gian, nguoi_dung, hanh_dong, chi_tiet])
    except:
        pass # Nếu lỗi ghi log thì bỏ qua để không ảnh hưởng app

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
        if st.form_submit_button("Truy cập"):
            users = lay_du_lieu(sh, "TaiKhoan")
            if not users.empty:
                user_row = users[(users['TenDangNhap'].astype(str) == user) & (users['MatKhau'].astype(str) == pwd)]
                if not user_row.empty:
                    st.session_state['dang_nhap'] = True
                    st.session_state['user_info'] = user_row.iloc[0].to_dict()
                    
                    # Ghi log đăng nhập
                    ghi_nhat_ky(sh, user_row.iloc[0]['HoTen'], "Đăng nhập", "Truy cập hệ thống thành công")
                    st.rerun()
                else:
                    st.error("Sai thông tin đăng nhập!")
            else:
                st.error("Không kết nối được dữ liệu tài khoản.")
else:
    # --- Sidebar thông tin (ĐÃ ẨN VAI TRÒ) ---
    user_info = st.session_state['user_info']
    role = user_info.get('VaiTro', 'NhanVien')
    current_user_name = user_info['HoTen']
    
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
        st.success(f"Xin chào: **{current_user_name}**")
        # Đã ẩn dòng hiển thị vai trò ở đây theo yêu cầu
        
        if st.button("Đăng xuất"):
            ghi_nhat_ky(sh, current_user_name, "Đăng xuất", "Thoát hệ thống")
            st.session_state['dang_nhap'] = False
            st.rerun()

    # ================= 3. GIAO DIỆN CHÍNH =================
    st.title("🏢 PHÒNG NỘI DUNG SỐ VÀ TRUYỀN THÔNG")
    
    # --- PHÂN QUYỀN TABS ---
    # Lãnh đạo: Full quyền + Logs + Dashboard
    # Trưởng nhóm: Giao việc + Quản lý dự án + Email (Không Dashboard, Không Logs)
    # Nhân viên: Việc của tôi + Xem dự án + Email
    
    tabs_list = []
    if role == 'LanhDao':
        tabs_list = ["📊 Dashboard", "✅ Quản Lý Công Việc", "🗂️ Dự Án", "📧 Email", "📜 Nhật Ký Hệ Thống"]
    elif role == 'TruongNhom':
        tabs_list = ["✅ Quản Lý Công Việc", "🗂️ Dự Án", "📧 Email"]
    else: # NhanVien
        tabs_list = ["✅ Việc Của Tôi", "🗂️ Dự Án", "📧 Email"]
        
    tabs = st.tabs(tabs_list)

    # ---------------------------------------------------------
    # TAB: DASHBOARD (CHỈ LÃNH ĐẠO)
    # ---------------------------------------------------------
    if role == 'LanhDao':
        with tabs[0]:
            st.header("Tổng quan Phòng")
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

    # ---------------------------------------------------------
    # TAB: QUẢN LÝ CÔNG VIỆC (QUAN TRỌNG NHẤT)
    # ---------------------------------------------------------
    # Xác định đúng Tab index dựa trên vai trò
    idx_viec = 1 if role == 'LanhDao' else 0
    
    with tabs[idx_viec]:
        df_da = lay_du_lieu(sh, "DuAn")
        list_du_an = df_da['TenDuAn'].tolist() if not df_da.empty else ["Việc chung"]
        
        df_users = lay_du_lieu(sh, "TaiKhoan")
        list_nv = df_users['HoTen'].tolist() if not df_users.empty else []

        # --- TIÊU ĐỀ ---
        if role in ['LanhDao', 'TruongNhom']:
            st.subheader("📝 Điều phối & Giao việc (Admin/Lead)")
        else:
            st.subheader(f"📝 Danh sách việc của: {current_user_name}")
        
        # --- A. FORM TẠO VIỆC (Chỉ Lãnh đạo & Trưởng nhóm được dùng) ---
        if role in ['LanhDao', 'TruongNhom']:
            with st.expander("➕ GIAO VIỆC MỚI (Trưởng nhóm/Lãnh đạo)", expanded=False):
                with st.form("tao_viec_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        tv_ten = st.text_input("Tên đầu việc")
                        tv_duan = st.selectbox("Thuộc Dự án", list_du_an)
                        col_gio, col_ngay = st.columns(2)
                        tv_time = col_gio.time_input("Giờ deadline", value=datetime.now().time())
                        tv_date = col_ngay.date_input("Ngày deadline", value=datetime.now())
                    with c2:
                        tv_nguoi = st.multiselect("Giao cho nhân sự:", list_nv)
                        tv_ghichu = st.text_area("Yêu cầu chi tiết")
                    
                    # Chọn tài khoản gửi mail
                    st.markdown("---")
                    col_tk1, col_tk2 = st.columns([2,1])
                    with col_tk1:
                        tk_gui = st.selectbox("Gửi email từ TK số:", list(range(10)), format_func=lambda x: f"TK Gmail {x}")
                    
                    btn_luu = st.form_submit_button("💾 Giao Việc & Tạo Email", type="primary")
                    
                if btn_luu and tv_ten:
                    deadline_str = f"{tv_time.strftime('%H:%M')} {tv_date.strftime('%d/%m/%Y')}"
                    nguoi_str = ", ".join(tv_nguoi)
                    try:
                        wks_cv = sh.worksheet("CongViec")
                        wks_cv.append_row([tv_ten, tv_duan, deadline_str, nguoi_str, "Mới", "", tv_ghichu])
                        
                        # Ghi log
                        ghi_nhat_ky(sh, current_user_name, "Giao việc", f"Việc: {tv_ten} | Cho: {nguoi_str}")
                        st.success("✅ Đã giao việc thành công!")
                        
                        # Tạo link email (Logic cũ)
                        if tv_nguoi:
                            ds_email = df_users[df_users['HoTen'].isin(tv_nguoi)]['Email'].dropna().tolist()
                            ds_email = [e for e in ds_email if str(e).strip() != ""]
                            if ds_email:
                                sub = f"[GIAO VIỆC] {tv_ten} - Deadline: {deadline_str}"
                                body = f"Chào các bạn,\n\nPhòng giao cho bạn việc mới:\n- Việc: {tv_ten}\n- Dự án: {tv_duan}\n- Deadline: {deadline_str}\n\nChi tiết: {tv_ghichu}\n\nNgười giao: {current_user_name}"
                                link = f"https://mail.google.com/mail/u/{tk_gui}/?view=cm&fs=1&to={','.join(ds_email)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(body)}"
                                st.markdown(f'<a href="{link}" target="_blank" style="background:#00C853;color:white;padding:10px;border-radius:5px;text-decoration:none;font-weight:bold">📧 Gửi Email Thông Báo Ngay</a>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

        # --- B. CHỨC NĂNG XÓA (MỚI - Chỉ Lãnh đạo & Trưởng nhóm) ---
        if role in ['LanhDao', 'TruongNhom']:
            with st.expander("🗑️ XÓA CÔNG VIỆC", expanded=False):
                st.warning("⚠️ Hành động này sẽ xóa vĩnh viễn dòng dữ liệu trong Sheet.")
                df_delete = lay_du_lieu(sh, "CongViec")
                if not df_delete.empty:
                    # Tạo danh sách chọn để xóa: Kết hợp Tên việc + Dự án để dễ nhìn
                    df_delete['Label'] = df_delete['TenViec'] + " (" + df_delete['DuAn'] + ")"
                    delete_options = df_delete['Label'].tolist()
                    
                    to_delete = st.multiselect("Chọn việc cần xóa:", delete_options)
                    
                    if st.button("Xác nhận xóa việc"):
                        if to_delete:
                            try:
                                wks_cv = sh.worksheet("CongViec")
                                all_values = wks_cv.get_all_values()
                                # Giữ lại header + các dòng KHÔNG nằm trong danh sách xóa
                                # Logic xóa: Tìm dòng có TenViec + DuAn khớp với label
                                new_data = [all_values[0]] # Header
                                for row in all_values[1:]:
                                    label = row[0] + " (" + row[1] + ")"
                                    if label not in to_delete:
                                        new_data.append(row)
                                
                                wks_cv.clear()
                                wks_cv.update(new_data)
                                
                                ghi_nhat_ky(sh, current_user_name, "Xóa việc", f"Đã xóa: {', '.join(to_delete)}")
                                st.success("Đã xóa thành công! Vui lòng tải lại trang.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi xóa: {e}")
                        else:
                            st.info("Chưa chọn việc nào để xóa.")

        # --- C. HIỂN THỊ DANH SÁCH ---
        st.divider()
        filter_duan = st.selectbox("🔍 Lọc theo Dự án", ["Tất cả"] + list_du_an)
        
        df_view = lay_du_lieu(sh, "CongViec")
        if not df_view.empty:
            if filter_duan != "Tất cả":
                df_view = df_view[df_view['DuAn'] == filter_duan]
            
            # LỌC THEO VAI TRÒ
            if role == 'NhanVien':
                # Nhân viên chỉ thấy việc có tên mình
                df_view = df_view[df_view['NguoiPhuTrach'].astype(str).str.contains(current_user_name, na=False)]
            elif role == 'TruongNhom':
                # Trưởng nhóm thấy tất cả (hoặc có thể lọc thêm logic chỉ thấy dự án mình làm Trưởng - nhưng ở đây để mở cho linh hoạt)
                pass 

            if not df_view.empty:
                st.dataframe(
                    df_view, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "LinkBai": st.column_config.LinkColumn("Link Bài"),
                        "TrangThai": st.column_config.SelectboxColumn("Trạng thái", options=["Mới", "Đang làm", "Xong", "Hủy"]),
                        "Deadline": st.column_config.TextColumn("Hạn chót")
                    }
                )
            else:
                st.info("Không tìm thấy công việc phù hợp.")

    # ---------------------------------------------------------
    # TAB: QUẢN LÝ DỰ ÁN
    # ---------------------------------------------------------
    idx_duan = 2 if role == 'LanhDao' else 1
    with tabs[idx_duan]:
        c1, c2 = st.columns([1, 2])
        
        # Chỉ Lãnh đạo/Trưởng nhóm mới được thêm/xóa dự án
        if role in ['LanhDao', 'TruongNhom']:
            with c1:
                st.subheader("➕ Thêm Dự Án")
                with st.form("add_da"):
                    new_da = st.text_input("Tên Dự án")
                    new_desc = st.text_area("Mô tả")
                    if st.form_submit_button("Tạo mới"):
                        try:
                            wks_da = sh.worksheet("DuAn")
                            wks_da.append_row([new_da, new_desc, "Đang chạy"])
                            ghi_nhat_ky(sh, current_user_name, "Tạo dự án", new_da)
                            st.success(f"Đã thêm: {new_da}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi: {e}")
                
                # Nút xóa dự án
                with st.expander("🗑️ Xóa Dự Án"):
                    da_xoa = st.selectbox("Chọn dự án xóa", list_du_an)
                    if st.button("Xác nhận xóa DA"):
                        try:
                            wks_da = sh.worksheet("DuAn")
                            rows = wks_da.get_all_values()
                            new_rows = [rows[0]] + [r for r in rows[1:] if r[0] != da_xoa]
                            wks_da.clear()
                            wks_da.update(new_rows)
                            ghi_nhat_ky(sh, current_user_name, "Xóa dự án", da_xoa)
                            st.success("Đã xóa dự án.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi: {e}")

        with c2:
            st.subheader("Danh sách Dự án đang chạy")
            df_da_view = lay_du_lieu(sh, "DuAn")
            if not df_da_view.empty:
                st.dataframe(df_da_view, use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # TAB: TRUNG TÂM EMAIL
    # ---------------------------------------------------------
    idx_email = 3 if role == 'LanhDao' else 2
    with tabs[idx_email]:
        st.header("📧 Soạn Thảo & Gửi Email")
        
        col_tk1, col_tk2 = st.columns([2, 1])
        with col_tk1:
            tai_khoan_chon = st.selectbox("📤 Gửi từ Tài khoản số:", list(range(10)), format_func=lambda x: f"Gmail số {x}")
        with col_tk2:
            st.write("Kiểm tra:")
            link_check = f"https://mail.google.com/mail/u/{tai_khoan_chon}"
            st.markdown(f'<a href="{link_check}" target="_blank" style="padding: 5px 10px; background:#eee; text-decoration:none; border-radius:5px;">👁️ Mở Gmail số {tai_khoan_chon}</a>', unsafe_allow_html=True)

        st.divider()

        # Load dữ liệu Email
        try:
            users_data = lay_du_lieu(sh, "TaiKhoan")
            list_ten = users_data['HoTen'].tolist() if not users_data.empty else []
            danh_ba = {r['HoTen']: r['Email'] for i, r in users_data.iterrows() if str(r['Email']).strip()}
            
            mau_data = lay_du_lieu(sh, "MauEmail")
            thu_vien_mau = {r['TenMau']: {"tieu_de": r['TieuDe'], "noi_dung": r['NoiDung']} for i, r in mau_data.iterrows()} if not mau_data.empty else {}
        except:
            st.error("Lỗi đọc dữ liệu danh bạ/mẫu.")
            st.stop()

        c_main1, c_main2 = st.columns(2)
        with c_main1:
            nguoi_nhan = st.multiselect("Đến:", list_ten)
            email_to = [danh_ba[n] for n in nguoi_nhan if n in danh_ba]
        with c_main2:
            chon_mau = st.selectbox("Mẫu:", ["-- Tự soạn --"] + list(thu_vien_mau.keys()))
        
        # Xử lý nội dung
        tieu_de, noi_dung = "", ""
        if chon_mau != "-- Tự soạn --":
            tieu_de = thu_vien_mau[chon_mau]["tieu_de"]
            noi_dung = thu_vien_mau[chon_mau]["noi_dung"]
        
        # Thêm Dear...
        if nguoi_nhan:
            short_names = [n.split()[-1] for n in nguoi_nhan]
            greeting = f"Dear {', '.join(short_names)},\n\n"
            if not noi_dung.startswith("Dear") and not noi_dung.startswith("Kính gửi"):
                noi_dung = greeting + noi_dung

        # Thêm chữ ký
        if current_user_name not in noi_dung:
            noi_dung += f"\n\nTrân trọng,\n{current_user_name}"

        final_td = st.text_input("Tiêu đề:", value=tieu_de)
        final_nd = st.text_area("Nội dung:", value=noi_dung, height=250)
        
        if st.button(f"🚀 Mở Gmail (TK {tai_khoan_chon}) để gửi", type="primary"):
            if email_to:
                # Ghi log hành động gửi (Không ghi nội dung chi tiết vì bảo mật)
                ghi_nhat_ky(sh, current_user_name, "Soạn Email", f"Gửi tới: {', '.join(nguoi_nhan)} | Tiêu đề: {final_td}")
                
                link = f"https://mail.google.com/mail/u/{tai_khoan_chon}/?view=cm&fs=1&to={','.join(email_to)}&su={urllib.parse.quote(final_td)}&body={urllib.parse.quote(final_nd)}"
                js = f"""<script>window.open("{link}", "_blank");</script>"""
                components.html(js, height=0)
                st.success("Đang mở Gmail...")
            else:
                st.warning("Chưa chọn người nhận.")

    # ---------------------------------------------------------
    # TAB: NHẬT KÝ HỆ THỐNG (CHỈ LÃNH ĐẠO MỚI CÓ TAB NÀY)
    # ---------------------------------------------------------
    if role == 'LanhDao':
        with tabs[4]:
            st.header("📜 Nhật ký hoạt động (Logs)")
            st.info("Ghi lại lịch sử đăng nhập, giao việc, xóa việc và soạn email của toàn bộ nhân sự.")
            
            df_logs = lay_du_lieu(sh, "NhatKy")
            if not df_logs.empty:
                # Sắp xếp mới nhất lên đầu
                if 'ThoiGian' in df_logs.columns:
                    df_logs = df_logs.sort_values(by='ThoiGian', ascending=False)
                
                st.dataframe(df_logs, use_container_width=True, hide_index=True)
            else:
                st.caption("Chưa có dữ liệu nhật ký.")