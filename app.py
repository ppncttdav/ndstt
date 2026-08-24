import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components
import urllib.parse
from datetime import datetime, date, timedelta
import pytz
import requests
import plotly.express as px
import time
import random
import re
import io
import hashlib
import hmac
import secrets
import logging
import os
import concurrent.futures
import json

# --- THƯ VIỆN ĐỊNH DẠNG SHEET ---
from gspread_formatting import *

# ================= CẤU HÌNH HỆ THỐNG =================
st.set_page_config(page_title="PHÒNG NỘI DUNG SỐ & TRUYỀN THÔNG", page_icon="🏢", layout="wide")

# --- MÃ CSS TÀNG HÌNH CHỐNG CHỚP/MỜ MÀN HÌNH & ÉP WRAP TEXT ---
st.markdown("""
    <style>
    /* Ép Streamlit không được làm mờ khối dữ liệu khi Reload */
    [data-stale="true"], div[data-stale="true"] {
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
        pointer-events: auto !important;
    }
    </style>
""", unsafe_allow_html=True)

SHEET_MAIN = "HeThongQuanLy" 
SHEET_TRUCSO = "VoTrucSo"
LINK_VO_TRUC_SO = "https://docs.google.com/spreadsheets/d/1WYfdY8OIVWPD-N5xZD36B3v7MV_XFjHXj_v9UZXK0ZI/edit?gid=1107365160#gid=1107365160"
LINK_LICH_BTV_TCSX = "https://docs.google.com/spreadsheets/d/1IFbxenXl7PehWc3Q0L35DHkkUVyEBGXaV7JSRKHMSn8/edit?gid=387062810#gid=387062810"
LINK_LICH_LDP = "https://docs.google.com/spreadsheets/d/1IFbxenXl7PehWc3Q0L35DHkkUVyEBGXaV7JSRKHMSn8/edit?gid=570145520#gid=570145520"
LINK_KHUNG_LPS = "https://docs.google.com/spreadsheets/d/1WfZledcegY7E0Vqm0gEX9kjczx0JxnYv/edit?gid=1508530487#gid=1508530487"

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
def get_vn_time(): return datetime.now(VN_TZ)
def get_vn_today(): return get_vn_time().date()

# --- LÕI AI GROQ (CHUẨN OPENAI COMPATIBLE) ---
logger = logging.getLogger("vietnam_today")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def get_ai_api_key():
    key = str(st.secrets.get("groq_api_key", os.getenv("GROQ_API_KEY", ""))).strip()
    return key if key else ""

@st.cache_resource
def init_ai_engine():
    return {
        "cache": {},
        "queue": set(),
        "executor": concurrent.futures.ThreadPoolExecutor(max_workers=3)
    }

AI_ENGINE = init_ai_engine()

def _call_api(text, api_key, model_name, today_str):
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    system_prompt = f"Bạn là một Thư ký tòa soạn/Biên tập viên kỳ cựu của kênh truyền hình đối ngoại, quốc tế Vietnam Today. Vietnam Today là kênh truyền hình chính của Ban Truyền hình đối ngoại (VTV International), Đài truyền hình Việt Nam (VTV), vô cùng khắt khe và ưu tiên an toàn xuất bản. LƯU Ý TỐI QUAN TRỌNG: Hôm nay là ngày {today_str}. Bạn BẮT BUỘC phải dùng mốc thời gian này làm hệ quy chiếu hiện tại để tính toán số năm, đối chiếu các ngày lễ kỷ niệm, sự kiện và kiểm chứng mọi mốc thời gian trong văn bản."

    user_prompt = f"""
    Nhiệm vụ: rà soát nội dung tin tức/bài đăng MXH dưới đây...

    Kiểm tra theo thứ tự:
    1. Rủi ro chính trị, ngoại giao, chủ quyền, danh xưng chính thức.
    2. Logic, mâu thuẫn, dữ kiện thiếu căn cứ hoặc diễn đạt có thể gây hiểu sai.
    3. Bản quyền, nhạy cảm văn hóa/tôn giáo, phân biệt đối xử.
    4. Chính tả, ngữ pháp, diễn đạt lủng củng.
    5. Nội dung cập nhật bị muộn, cũ, hoặc thông tin đã có sự thay đổi.
    6. Cách viết đã chuẩn quốc tế, đã thật sự thu hút khán giả chưa?
    7. Chuẩn định dạng ngày theo ví dụ: 10 August, 2026 hoặc bỏ năm đi cũng được.
    8. Đối với tên riêng tiếng Việt, viết như format tiếng Anh.

    Yêu cầu định dạng: Thẳng thắn, gạch đầu dòng rõ ràng, chỉ ra ý cần sửa và đề xuất cách sửa. Viết gọn gàng súc tích, không khen ngợi dài dòng, chỉ nói những mục phải sửa, cái nào đúng rồi thì thôi không cần đề cập cho gọn gàng.
    Nếu không phát hiện rủi ro nào đáng kể, trả đúng 1 câu duy nhất: "Nội dung ít rủi ro".

    NỘI DUNG CẦN RÀ SOÁT:
    {text}
    """
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 4096
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 429:
                if attempt < 2:
                    time.sleep(1.5 ** (attempt + 1))
                    continue
                return "⚠️ Băng thông AI đang bận. Vui lòng đợi chút rồi Quét lại."
            if response.status_code != 200: 
                return f"⚠️ Lỗi từ máy chủ Groq (HTTP {response.status_code}): {response.text}"
            
            result = response.json()
            answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return answer.strip() or "⚠️ AI không trả về nội dung phân tích."
        except requests.exceptions.Timeout:
            if attempt < 2: continue
            return "⚠️ Quá thời gian chờ phản hồi AI (Timeout). Vui lòng bấm Quét Lại."
        except Exception as e:
            if attempt < 2: continue
            return f"⚠️ Không kết nối được hệ thống AI Groq: {e}"
            
    return "⚠️ Quá giới hạn thử lại do nghẽn mạng."

def _bg_task(text, api_key, model_name, today_str, text_hash):
    try:
        ans = _call_api(text, api_key, model_name, today_str)
        AI_ENGINE["cache"][text_hash] = ans
    except Exception: pass
    finally:
        if text_hash in AI_ENGINE["queue"]: AI_ENGINE["queue"].remove(text_hash)

def queue_bg_scan(text, smart_status=""):
    if any(s in smart_status.lower() for s in ["đã duyệt", "đã đăng", "posted", "scheduled"]): return
    if not text or len(text.strip()) < 10: return
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    
    if text_hash in AI_ENGINE["cache"] or text_hash in AI_ENGINE["queue"]: return
    
    api_key = get_ai_api_key()
    if not api_key: return
    
    model_name = str(st.secrets.get("groq_model", os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))).strip()
    today_str = get_vn_time().strftime("%d/%m/%Y")
    
    AI_ENGINE["queue"].add(text_hash)
    AI_ENGINE["executor"].submit(_bg_task, text, api_key, model_name, today_str, text_hash)

# --- BẢO MẬT & MẬT KHẨU ---
def _scrypt_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    n, r, p = 2**14, 8, 1
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=64)
    return f"scrypt${n}${r}${p}${salt.hex()}${derived.hex()}"

def verify_password(password: str, stored: str) -> bool:
    stored = str(stored or "")
    if stored.startswith("scrypt$"):
        try:
            _, n, r, p, salt_hex, hash_hex = stored.split("$", 5)
            derived = hashlib.scrypt(
                password.encode("utf-8"),
                salt=bytes.fromhex(salt_hex),
                n=int(n), r=int(r), p=int(p), dklen=64,
            )
            return hmac.compare_digest(derived.hex(), hash_hex)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(str(password), stored)

def check_password_and_upgrade(password: str, stored: str):
    ok = verify_password(password, stored)
    needs_upgrade = ok and not str(stored or "").startswith("scrypt$")
    return ok, needs_upgrade

def generate_secure_token(username):
    secret_salt = st.secrets.get("url_salt", os.getenv("URL_SALT", "VietnamToday_Secure_2026_!@#"))
    return hmac.new(
        str(secret_salt).encode("utf-8"),
        str(username).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

def clear_app_caches():
    for fn in (load_tai_khoan, load_du_lieu_app, fetch_vo_truc_so, fetch_and_parse_schedules, get_public_gsheet_as_excel):
        try: fn.clear()
        except Exception: pass

def clear_cache_and_rerun():
    clear_app_caches()
    try: st.rerun()
    except Exception: pass

def ghi_nhat_ky(nguoi_dung, hanh_dong, chi_tiet):
    try:
        sh_main = ket_noi_sheet(SHEET_MAIN)
        wks = sh_main.worksheet("NhatKy")
        wks.append_row([get_vn_time().strftime("%H:%M %d/%m/%Y"), nguoi_dung, hanh_dong, str(chi_tiet)[:5000]])
    except Exception: logger.exception("Không ghi được nhật ký")

def get_short_name(full_name):
    if not full_name or full_name == "--" or str(full_name).strip() == "": return "..."
    parts = full_name.strip().split()
    return " ".join(parts[-2:]) if len(parts) >= 2 else full_name

def normalize_btv_names_strict(name_str, list_nv):
    if pd.isna(name_str) or str(name_str).strip() == "": return "Chưa phân công"
    raw_str = str(name_str).lower()
    found_names = []
    sorted_nv = sorted(list_nv, key=len, reverse=True)
    for nv in sorted_nv:
        nv_lower = nv.lower()
        parts = nv_lower.split()
        short_nv = " ".join(parts[-2:]) if len(parts) >= 2 else nv_lower
        if nv_lower in raw_str:
            if nv not in found_names: found_names.append(nv)
            raw_str = raw_str.replace(nv_lower, " ")
        elif short_nv in raw_str:
            if nv not in found_names: found_names.append(nv)
            raw_str = raw_str.replace(short_nv, " ")
    if not found_names: return "Chưa phân công"
    return ", ".join(found_names)

def match_nv(name, list_nv):
    if not name or str(name).strip() == "": return ""
    n_lower = str(name).lower().strip()
    for nv in list_nv:
        if n_lower == str(nv).lower().strip(): return nv
    if len(n_lower) >= 2:
        for nv in list_nv:
            nv_lower = str(nv).lower().strip()
            if n_lower in nv_lower or nv_lower in n_lower: 
                return nv
    return name.title()

def get_lanh_dao_ban(d_obj):
    wd = d_obj.weekday()
    if wd in [0, 1]: return "Lê Hoàng Linh"
    elif wd in [2, 4]: return "Nguyễn Phương Hà"
    elif wd in [3, 5]: return "Nguyễn Phương Liên"
    elif wd == 6: return "Trần Thu Hà"
    return ""

def _parse_assignees(value):
    return {x.strip().casefold() for x in re.split(r"[,;\n]+", str(value or "")) if x.strip()}

def has_name_access(curr_name, assignees_text):
    target = str(curr_name or "").strip().casefold()
    return target and target in _parse_assignees(assignees_text)

def check_quyen(curr_name, role, task_row, df_duan=None):
    if role in {"LanhDao", "Admin"}: return 2
    if has_name_access(curr_name, task_row.get("NguoiPhuTrach", "")): return 1
    return 0

@st.cache_data(ttl=3600)
def get_weather_and_advice():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=21.0285&longitude=105.8542&current_weather=true&timezone=Asia%2FBangkok"
        res = requests.get(url, timeout=1).json()
        temp = res['current_weather']['temperature']
        wcode = res['current_weather']['weathercode']
        condition = "CÓ MÂY"; advice = "CHÚC BẠN MỘT NGÀY LÀM VIỆC NĂNG SUẤT!"
        if wcode in [0, 1]: condition = "NẮNG ĐẸP ☀️"; advice = "TRỜI ĐẸP! GIỮ NĂNG LƯỢNG TÍCH CỰC NHÉ."
        elif wcode in [2, 3]: condition = "NHIỀU MÂY ☁️"; advice = "THỜI TIẾT DỊU MÁT, TẬP TRUNG CAO ĐỘ NÀO!"
        elif wcode in [51, 53, 55, 61, 63, 65]: condition = "CÓ MƯA 🌧️"; advice = "TRỜI MƯA, ĐƯỜNG TRƠN. CÁC BTV ĐI LẠI CẨN THẬN!"
        elif wcode >= 95: condition = "GIÔNG BÃO ⛈️"; advice = "THỜI TIẾT XẤU. HẠN CHẾ RA NGOÀI."
        return f"{temp}°C - {condition}", advice
    except Exception:
        return "--°C", "LUÔN GIỮ VỮNG ĐAM MÊ NGHỀ BÁO NHÉ!"

ROLES_HEADER = [
    "LÃNH ĐẠO BAN", "TRỰC THƯ KÝ TÒA SOẠN", "TRỰC QUẢN TRỊ MXH + VIDEO BIÊN TẬP",
    "TRỰC LỊCH PHÁT SÓNG", "TRỰC THƯ KÝ TÒA SOẠN", "TRỰC SẢN XUẤT VIDEO CLIP, LPS",
    "TRỰC QUẢN TRỊ CỔNG TTĐT", "TRỰC QUẢN TRỊ APP"
]

OPTS_DINH_DANG = ["Bài dịch", "Video biên tập", "Sản phẩm sản xuất"]
OPTS_NEN_TANG = ["Facebook", "Youtube", "TikTok", "Web + App", "Instagram"]
OPTS_STATUS_TRUCSO = ["Chờ xử lý", "Đang biên tập", "Cảnh báo rủi ro", "Gửi duyệt TCSX", "Yêu cầu sửa (TCSX)", "Gửi duyệt LĐP", "Yêu cầu sửa (LĐP)", "Đã duyệt/Chờ đăng", "Đã đăng", "Scheduled", "Posted", "Hủy"]
OPTS_TRANG_THAI_VIEC = ["Đã giao", "Đang thực hiện", "Chờ duyệt", "Hoàn thành", "Hủy"]
CONTENT_HEADER = ["STT", "NỘI DUNG", "ĐỊNH DẠNG", "NỀN TẢNG", "STATUS", "CHECK", "NGUỒN", "NHÂN SỰ", "TCSX", "LĐP", "GIỜ ĐĂNG", "NGÀY ĐĂNG", "LINK SẢN PHẨM", "LINK DUYỆT"]

VN_COLS_VIEC = {"TenViec": "Tên công việc", "DuAn": "Dự án", "Deadline": "Hạn chót", "NguoiPhuTrach": "Người thực hiện", "TrangThai": "Trạng thái", "LinkBai": "Link SP", "GhiChu": "Ghi chú"}
VN_COLS_DUAN = {"TenDuAn": "Tên Dự án", "MoTa": "Mô tả", "TrangThai": "Trạng thái", "TruongNhom": "Điều phối"}
VN_COLS_LOG = {"ThoiGian": "Thời gian", "NguoiDung": "Người dùng", "HanhDong": "Hành động", "ChiTiet": "Chi tiết"}

# ================= 1. BACKEND & XỬ LÝ DỮ LIỆU =================
@st.cache_resource(ttl=3600, show_spinner=False)
def get_gspread_client_cached():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
        return gspread.authorize(creds)
    except Exception:
        logger.exception("Không khởi tạo được Google Sheets client")
        return None

def ket_noi_sheet(sheet_name_or_url):
    client = get_gspread_client_cached()
    if not client: return None
    try:
        return client.open_by_url(sheet_name_or_url) if str(sheet_name_or_url).startswith("http") else client.open(sheet_name_or_url)
    except Exception:
        logger.exception("Không mở được spreadsheet")
        return None

def safe_read_records_with_row(wks, retries=3, delay=0.4):
    for attempt in range(retries):
        try:
            values = wks.get_all_values()
            if not values: return pd.DataFrame()
            headers = values[0]
            rows = []
            for sheet_row, raw in enumerate(values[1:], start=2):
                row = {headers[i] if i < len(headers) else f"Column_{i+1}": raw[i] if i < len(raw) else "" for i in range(len(headers))}
                row["_sheet_row"] = sheet_row
                rows.append(row)
            return pd.DataFrame(rows)
        except Exception:
            if attempt == retries - 1: logger.exception("Không đọc được worksheet")
            else: time.sleep(delay * (attempt + 1))
    return pd.DataFrame()

@st.cache_data(ttl=15, show_spinner=False)
def fetch_vo_truc_so(tab_name):
    sh = ket_noi_sheet(LINK_VO_TRUC_SO)
    if not sh: return False, pd.DataFrame(columns=CONTENT_HEADER), [], []
    try: wks = sh.worksheet(tab_name)
    except: return False, pd.DataFrame(columns=CONTENT_HEADER), [], []
        
    for _ in range(2):
        try:
            data = wks.get_all_values()
            roster_names = data[2][1:] if len(data) > 2 else []
            r_roles = data[1][1:] if len(data) > 1 else []
            
            if len(data) > 5: 
                num_cols = len(CONTENT_HEADER)
                clean_data = []
                for row in data[5:]:
                    padded_row = row[:num_cols] + [''] * max(0, num_cols - len(row))
                    clean_data.append(padded_row)
                df = pd.DataFrame(clean_data, columns=CONTENT_HEADER)
            else:
                df = pd.DataFrame(columns=CONTENT_HEADER)
            return True, df, roster_names, r_roles
        except: time.sleep(0.2)
    return True, pd.DataFrame(columns=CONTENT_HEADER), [], []

@st.cache_data(ttl=300, show_spinner=False)
def load_tai_khoan():
    try:
        sh = ket_noi_sheet(SHEET_MAIN)
        return safe_read_records_with_row(sh.worksheet("TaiKhoan"))
    except: return pd.DataFrame()

@st.cache_data(ttl=45, show_spinner=False)
def load_du_lieu_app():
    try:
        sh = ket_noi_sheet(SHEET_MAIN)
        df_d = safe_read_records_with_row(sh.worksheet("DuAn"))
        df_c = safe_read_records_with_row(sh.worksheet("CongViec"))
        try: df_cn = safe_read_records_with_row(sh.worksheet("ViecCaNhan"))
        except: df_cn = pd.DataFrame()
        try: df_nk = safe_read_records_with_row(sh.worksheet("NhatKy"))
        except: df_nk = pd.DataFrame()
        return df_d, df_c, df_cn, df_nk
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=1800, show_spinner=False)
def get_public_gsheet_as_excel(url):
    try:
        sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if not sheet_id_match: return None
        sheet_id = sheet_id_match.group(1)
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        res = requests.get(export_url, timeout=15)
        if res.status_code == 200: return res.content
    except Exception: pass
    return None

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_and_parse_schedules(url_ldp, url_btv):
    results = {"LDP": pd.DataFrame(), "BTV": pd.DataFrame()}
    def _fetch_and_parse(url, kw):
        try:
            excel_bytes = get_public_gsheet_as_excel(url)
            if excel_bytes:
                xls = pd.ExcelFile(io.BytesIO(excel_bytes))
                target_sheet = xls.sheet_names[0]
                if kw == "LDP":
                    for sn in xls.sheet_names:
                        if "LĐP" in sn.upper(): target_sheet = sn; break
                else:
                    for sn in xls.sheet_names:
                        if ("SỐ" in sn.upper() or "TRỰC" in sn.upper()) and "LĐP" not in sn.upper():
                            target_sheet = sn; break
                df = pd.read_excel(xls, sheet_name=target_sheet, header=None)
                return kw, df
        except: pass
        return kw, pd.DataFrame()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_fetch_and_parse, url_ldp, "LDP"),
            executor.submit(_fetch_and_parse, url_btv, "BTV")
        ]
        for f in concurrent.futures.as_completed(futures):
            k, df = f.result()
            results[k] = df
    return results

def get_ldp_from_df(df, target_date_obj, list_nv):
    if df is None or df.empty: return ""
    d_str = str(target_date_obj.day)
    d_str_02 = f"{target_date_obj.day:02d}"
    m = target_date_obj.month
    
    target_col = -1
    header_row = -1
    
    # 1. Tìm cột chứa ngày bằng cách quyét dòng có các số ngày (1..31)
    for r in range(len(df)):
        row_vals_clean = [str(x).strip()[:-2] if str(x).strip().endswith('.0') else str(x).strip() for x in df.iloc[r].values]
        if (d_str in row_vals_clean or d_str_02 in row_vals_clean) and ("1" in row_vals_clean or "01" in row_vals_clean):
            # Xác nhận xem có bị nhầm tháng không bằng regex (tìm ngược lên các dòng trên)
            is_correct_month = True
            for pr in range(max(0, r-5), r):
                prev_row = "".join([str(x).lower().strip() for x in df.iloc[pr].values if str(x).lower() != 'nan'])
                if "tháng" in prev_row:
                    match = re.search(r'tháng\s*(\d+)', prev_row)
                    if match and int(match.group(1)) != m:
                        is_correct_month = False
            
            if is_correct_month:
                target_col = row_vals_clean.index(d_str) if d_str in row_vals_clean else row_vals_clean.index(d_str_02)
                header_row = r
                break
                
    if target_col != -1 and header_row != -1:
        # 2. Tìm người trực theo marker
        for r in range(header_row + 1, len(df)):
            val = str(df.iloc[r, target_col]).lower().strip()
            if val and val != 'nan':
                # Bỏ qua các marker nghỉ phép, họp chung, công tác
                if "nghỉ" in val or "off" in val or "công tác" in val: continue
                # Các marker xác nhận trực LĐP (Số, Trực, X, TS)
                if "số" in val or "trực" in val or "ts" in val or val == "x" or val == "v":
                    name = ""
                    for c in [1, 2, 0, 3]:
                        if c < len(df.columns):
                            n = str(df.iloc[r, c]).strip()
                            if n and n.lower() != 'nan' and not n.isdigit() and len(n) > 2 and "stt" not in n.lower():
                                name = n
                                break
                    if name:
                        matched = match_nv(name, list_nv)
                        if matched: return matched
    return ""

def get_btv_tcsx_from_df(df, target_date_obj, list_nv):
    res_tcsx = ""
    res_btv = []
    if df is None or df.empty: return res_tcsx, res_btv
    
    d = target_date_obj.day
    m = target_date_obj.month
    y = target_date_obj.year
    date_patterns = [
        f"{d:02d}/{m:02d}/{y}", f"{d}/{m}/{y}", f"{d:02d}/{m:02d}", f"{d}/{m}",
        f"{y}-{m:02d}-{d:02d}", f"{d:02d}.{m:02d}", f"{d}.{m}"
    ]
    
    target_col = -1
    header_row = -1
    
    for r in range(len(df)):
        for c in range(len(df.columns)):
            val = str(df.iloc[r, c]).strip().lower()
            if any(p in val for p in date_patterns) and "tháng" not in val:
                target_col = c
                header_row = r
                break
        if target_col != -1: break
        
    if target_col != -1:
        for r in range(header_row + 1, len(df)):
            val = str(df.iloc[r, target_col]).lower().strip()
            if not val or val == 'nan': continue
            
            name = ""
            for c in [1, 2, 0, 3]:
                if c < len(df.columns):
                    n = str(df.iloc[r, c]).strip()
                    if n and n != 'nan' and not n.isdigit() and len(n) > 2 and "stt" not in n.lower() and "tên" not in n.lower():
                        name = n
                        break
            
            if name:
                matched = match_nv(name, list_nv)
                if matched:
                    if "tcsx" in val:
                        res_tcsx = matched
                    elif "số" in val or "btv" in val or "trực" in val or val == "x":
                        if "hỗ trợ" not in val and "ht" not in val and "công tác" not in val:
                            if matched not in res_btv: res_btv.append(matched)
    return res_tcsx, res_btv

def lay_nhan_su_tu_lich_phuc_tap(target_date_obj, list_nv):
    ldp, tcsx, ht = "", "", ""
    btv_list = []
    errors = []
    
    dfs = fetch_and_parse_schedules(LINK_LICH_LDP, LINK_LICH_BTV_TCSX)
    
    df_ldp = dfs.get("LDP")
    if df_ldp is None or df_ldp.empty:
        errors.append("⚠️ Không tải được Lịch LĐP. Vui lòng kiểm tra quyền Public của link.")
    else:
        ldp = get_ldp_from_df(df_ldp, target_date_obj, list_nv)
        
    df_btv = dfs.get("BTV")
    if df_btv is None or df_btv.empty:
        errors.append("⚠️ Không tải được Lịch BTV/TCSX. Vui lòng kiểm tra quyền Public của link.")
    else:
        tcsx, btv_list = get_btv_tcsx_from_df(df_btv, target_date_obj, list_nv)
        
    return ldp, tcsx, btv_list, ht, errors

def tu_dong_cap_nhat_thong_ke(date_str, roster):
    try:
        sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
        try: wks_stats = sh_trucso.worksheet("ThongKe")
        except: 
            wks_stats = sh_trucso.add_worksheet("ThongKe", 1000, 20)
            header_stats = ["Ngày trực"] + ROLES_HEADER
            wks_stats.append_row(header_stats)
            format_cell_range(wks_stats, "A1:I1", CellFormat(textFormat=TextFormat(bold=True), horizontalAlignment='CENTER'))
        
        row_data = [date_str] + roster
        cell_found = wks_stats.find(date_str)
        if cell_found:
            r = cell_found.row
            cells = [gspread.Cell(r, i+1, val) for i, val in enumerate(row_data)]
            wks_stats.update_cells(cells)
            format_cell_range(wks_stats, f"A{r}:I{r}", CellFormat(backgroundColor=Color(1, 1, 1)))
        else:
            wks_stats.append_row(row_data)
            last_row = len(wks_stats.get_all_values())
            format_cell_range(wks_stats, f"A{last_row}:I{last_row}", CellFormat(backgroundColor=Color(1, 1, 1)))
    except Exception: pass

def split_text_link(merged_text):
    if pd.isna(merged_text) or not str(merged_text).strip(): return "", ""
    text = str(merged_text)
    urls = re.findall(r'(https?://[^\s]+|drive\.google\.com[^\s]+)', text)
    if urls:
        link = urls[-1]
        caption = text.replace(link, "").strip()
        caption = re.sub(r'\n+$', '', caption).strip()
        return caption, link
    return text, ""

def merge_text_link(caption, link):
    caption = str(caption).strip(); link = str(link).strip()
    if caption and link: return f"{caption}\n\n{link}"
    if caption: return caption
    if link: return link
    return ""

def build_appended_comment(history_text, new_text, is_ok_checked):
    parts = []
    if is_ok_checked: parts.append("OK")
    if new_text.strip(): parts.append(new_text.strip())
    added_str = " - ".join(parts)
    if not added_str: return history_text 
    if history_text.strip(): return f"{history_text.strip()}\n{added_str}" 
    return added_str

def get_smart_status(group_df):
    tcsx_cmts = " ".join(group_df['TCSX'].replace('', pd.NA).dropna().astype(str).tolist()).lower()
    ldp_cmts = " ".join(group_df['LĐP'].replace('', pd.NA).dropna().astype(str).tolist()).lower()
    all_cmts = tcsx_cmts + " " + ldp_cmts
    
    first_row = group_df.iloc[0]
    status = str(first_row.get('STATUS', '')).lower()
    link_duyet = str(first_row.get('LINK DUYỆT', ''))
    
    has_link = len(link_duyet) > 5
    
    if any(s in status for s in ["đã duyệt", "đã đăng", "posted", "scheduled"]): return "✅ Đã duyệt"
    if "rủi ro" in status: return "🚨 Cảnh báo rủi ro"
    
    tcsx_ok = re.search(r'\bok\b|\bokie\b|\bokay\b|\boke\b', tcsx_cmts)
    ldp_ok = re.search(r'\bok\b|\bokie\b|\bokay\b|\boke\b', ldp_cmts)
    
    btv_keywords = ["đã sửa", "đã update", "upd", "đã chỉnh", "đã thay", "e đã", "em đã", "đã xong", "đã bổ sung", "đã cắt"]
    btv_fixed = any(kw in all_cmts for kw in btv_keywords)
    
    neutral_phrases = ["đã xem", "xem rồi", "good", "được", "tks", "cảm ơn", "ok", "okie", "oke", "okay"]
    negative_keywords = ["sửa", "lỗi", "thiếu", "chưa", "sai", "thêm", "đừng", "sao lại", "cắt", "nhạy cảm", "giật", "không", "ko", "nếu"]
    
    tcsx_is_pure_neutral = any(p in tcsx_cmts for p in neutral_phrases) and not any(w in tcsx_cmts for w in negative_keywords)
    ldp_is_pure_neutral = any(p in ldp_cmts for p in neutral_phrases) and not any(w in ldp_cmts for w in negative_keywords)
    
    if ldp_ok: return "✅ Đã duyệt"
    if btv_fixed: return "🔄 BTV đã sửa"
    if not ldp_ok and len(ldp_cmts.strip()) > 2 and not ldp_is_pure_neutral: return "🔴 Cần sửa"
    if not tcsx_ok and len(tcsx_cmts.strip()) > 2 and not tcsx_is_pure_neutral: return "🔴 Cần sửa"
    if "sửa" in status: return "🔴 Cần sửa"
    if tcsx_ok or "lđp" in status: return "⏳ Chờ LĐP duyệt"
    if has_link or "tcsx" in status: return "👀 Chờ TCSX duyệt"
    return "📝 BTV đang hoàn thiện"

def get_priority_score(status):
    if "🚨 Cảnh báo" in status: return 0
    if "🔴 Cần sửa" in status: return 1
    if "🔄 BTV đã sửa" in status: return 2
    if "⏳ Chờ LĐP" in status: return 3
    if "👀 Chờ TCSX" in status: return 4
    if "📝 BTV đang" in status: return 5
    if "✅ Đã duyệt" in status: return 6
    return 7

def format_title_name(text):
    text = text.upper().replace("VIBES OF VN", "VIBES OF VIETNAM")
    text = text.title()
    replacements = { " Of ": " of ", " At ": " at ", " A ": " a ", " An ": " an ", " The ": " the ", " In ": " in ", " On ": " on ", " To ": " to ", " And ": " and " }
    for old, new in replacements.items(): text = text.replace(old, new)
    return text

def parse_khung_cell(cell_val):
    if pd.isna(cell_val) or str(cell_val).strip() == "": return "", ""
    lines = [line.strip() for line in str(cell_val).split('\n') if line.strip()]
    if not lines: return "", ""
    title = lines[0]
    title = re.sub(r'\(.*?\)', '', title) 
    title = re.sub(r'\s*\d+\'?m?\s*$', '', title) 
    title = re.sub(r'\s*\d+\s*$', '', title) 
    title = title.split('/')[0].strip() 
    title = format_title_name(title)
    desc = ""
    if len(lines) > 1:
        for line in lines[1:]:
            if not line.startswith('(') and "PL" not in line and "PM" not in line:
                desc = line.split('/')[0].strip(); break
    return title, desc

def format_time_col(t):
    if pd.isna(t): return ""
    try:
        if isinstance(t, str):
            t = t.strip()
            if len(t) == 5 and ":" in t: return f"{t}:00"
            return t
        return t.strftime("%H:%M:%S")
    except: return str(t)

def dinh_dang_dep(wks, roster_vals):
    date_str_display = wks.title
    row1 = [f"VỎ TRỰC SỐ VIETNAM TODAY {date_str_display}"] + [""]*13
    row2 = ROLES_HEADER + [""]*6
    row3 = roster_vals + [""]*6
    row4 = CONTENT_HEADER
    row5 = [""]*14  
    
    wks.update('A1:N5', [row1, row2, row3, row4, row5])
    requests = []
    
    requests.append({
        "mergeCells": {
            "range": {"sheetId": wks.id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 14},
            "mergeType": "MERGE_ALL"
        }
    })
    
    for c in range(14):
        requests.append({
            "mergeCells": {
                "range": {"sheetId": wks.id, "startRowIndex": 3, "endRowIndex": 5, "startColumnIndex": c, "endColumnIndex": c+1},
                "mergeType": "MERGE_ALL"
            }
        })
        
    fmt_title = {
        "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": {"red": 1.0, "green": 0.0, "blue": 0.0}},
        "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
        "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}
    }
    requests.append({
        "repeatCell": {
            "range": {"sheetId": wks.id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 14},
            "cell": {"userEnteredFormat": fmt_title}, 
            "fields": "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment,backgroundColor)"
        }
    })
    
    fmt_roles = {
        "textFormat": {"bold": True},
        "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP",
        "borders": {
            "top": {"style": "SOLID"}, "bottom": {"style": "SOLID"}, 
            "left": {"style": "SOLID"}, "right": {"style": "SOLID"}
        }
    }
    requests.append({
        "repeatCell": {
            "range": {"sheetId": wks.id, "startRowIndex": 1, "endRowIndex": 3, "startColumnIndex": 0, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": fmt_roles}, 
            "fields": "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment,wrapStrategy,borders)"
        }
    })
    
    fmt_header = {
        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
        "textFormat": {"bold": True},
        "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP",
        "borders": {
            "top": {"style": "SOLID"}, "bottom": {"style": "SOLID"}, 
            "left": {"style": "SOLID"}, "right": {"style": "SOLID"}
        }
    }
    requests.append({
        "repeatCell": {
            "range": {"sheetId": wks.id, "startRowIndex": 3, "endRowIndex": 5, "startColumnIndex": 0, "endColumnIndex": 14},
            "cell": {"userEnteredFormat": fmt_header}, 
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy,borders)"
        }
    })
    
    col_widths = [40, 250, 100, 120, 120, 60, 100, 120, 120, 100, 80, 90, 150, 250]
    for c_idx, w in enumerate(col_widths):
        requests.append({
            "updateDimensionProperties": {
                "range": {"sheetId": wks.id, "dimension": "COLUMNS", "startIndex": c_idx, "endIndex": c_idx + 1},
                "properties": {"pixelSize": w}, "fields": "pixelSize"
            }
        })
        
    try:
        wks.spreadsheet.batch_update({"requests": requests})
    except Exception: pass
    
    try:
        validation_dinh_dang = DataValidationRule(condition=BooleanCondition('ONE_OF_LIST', OPTS_DINH_DANG), showCustomUi=True)
        validation_nen_tang = DataValidationRule(condition=BooleanCondition('ONE_OF_LIST', OPTS_NEN_TANG), showCustomUi=True)
        validation_status = DataValidationRule(condition=BooleanCondition('ONE_OF_LIST', OPTS_STATUS_TRUCSO), showCustomUi=True)
        
        set_data_validation_for_cell_range(wks, 'C6:C100', validation_dinh_dang)
        set_data_validation_for_cell_range(wks, 'D6:D100', validation_nen_tang)
        set_data_validation_for_cell_range(wks, 'E6:E100', validation_status)
    except Exception: pass

def dinh_dang_dong_moi(wks, start_row, end_row):
    try:
        req = [{
            "repeatCell": {
                "range": {"sheetId": wks.id, "startRowIndex": start_row - 1, "endRowIndex": end_row, "startColumnIndex": 0, "endColumnIndex": 14},
                "cell": {"userEnteredFormat": {
                    "wrapStrategy": "WRAP", "verticalAlignment": "TOP",
                    "borders": {"top": {"style": "SOLID"}, "bottom": {"style": "SOLID"}, "left": {"style": "SOLID"}, "right": {"style": "SOLID"}}
                }},
                "fields": "userEnteredFormat(wrapStrategy,verticalAlignment,borders)"
            }
        }]
        wks.spreadsheet.batch_update({"requests": req})
    except Exception: pass

def update_wks_canhan(action_type, data):
    sh_main = ket_noi_sheet(SHEET_MAIN)
    try: wks_canhan = sh_main.worksheet("ViecCaNhan")
    except: 
        wks_canhan = sh_main.add_worksheet("ViecCaNhan", 1000, 5)
        wks_canhan.append_row(["User", "TenViec", "Ngay", "TrangThai", "GhiChu"])
        
    if action_type == "update":
        wks_canhan.update_cells(data)
    elif action_type == "append":
        wks_canhan.append_row(data)

# ================= 2. AUTH & GIAO DIỆN =================
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['user_info'] = {}
    st.session_state['username'] = ''

if not st.session_state['authenticated']:
    st.markdown("## 🔐 CỔNG ĐĂNG NHẬP")
    with st.form("login"):
        user = st.text_input("Tên đăng nhập")
        pwd = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("ĐĂNG NHẬP"):
            df_users = load_tai_khoan()
            if not df_users.empty:
                matches = df_users[df_users['TenDangNhap'].astype(str).str.strip().eq(str(user).strip())]
                authenticated_row = None
                migrate_hash = False
                if not matches.empty:
                    candidate = matches.iloc[0]
                    ok, migrate_hash = check_password_and_upgrade(pwd, candidate.get('MatKhau', ''))
                    if ok:
                        authenticated_row = candidate
                if authenticated_row is not None:
                    if migrate_hash and authenticated_row.get('_sheet_row'):
                        try:
                            sh_main = ket_noi_sheet(SHEET_MAIN)
                            sh_main.worksheet('TaiKhoan').update_cell(int(authenticated_row['_sheet_row']), 2, _scrypt_hash(pwd))
                            load_tai_khoan.clear()
                        except Exception:
                            logger.exception('Không nâng cấp được mật khẩu legacy')
                    st.session_state['authenticated'] = True
                    safe_user = authenticated_row.to_dict()
                    safe_user.pop('MatKhau', None)
                    safe_user.pop('_sheet_row', None)
                    st.session_state['user_info'] = safe_user
                    st.session_state['username'] = str(user).strip()
                    ghi_nhat_ky(authenticated_row['HoTen'], "Đăng nhập", "Success")
                    clear_cache_and_rerun()
                else:
                    st.error("Sai thông tin đăng nhập!")
            else: st.error("Lỗi kết nối CSDL Tài khoản.")
else:
    df_users = load_tai_khoan()
    list_nv = df_users['HoTen'].tolist() if not df_users.empty else []
    df_duan, df_cv, df_cn, df_log = load_du_lieu_app()
    list_duan = df_duan['TenDuAn'].tolist() if not df_duan.empty else []
    u_info = st.session_state['user_info']; curr_name = u_info['HoTen']; curr_username = str(st.session_state.get('username', '')); role = u_info.get('VaiTro', 'NhanVien')
    
    with st.sidebar:
        st.success(f"XIN CHÀO: **{curr_name.upper()}**\n\nCHÚC BẠN MỘT NGÀY LÀM VIỆC VUI VẺ! ❤️")
        weather_info, advice_msg = get_weather_and_advice()
        st.markdown(f"---\n**🌤️ HÀ NỘI:** {weather_info}\n\n💡 **LỜI KHUYÊN:** {advice_msg}\n---")
        
        with st.expander("🔐 ĐỔI MẬT KHẨU"):
            with st.form("change_pass_form"):
                old_p = st.text_input("MẬT KHẨU CŨ", type="password"); new_p = st.text_input("MẬT KHẨU MỚI", type="password"); cfm_p = st.text_input("NHẬP LẠI", type="password")
                if st.form_submit_button("LƯU"):
                    account_df = load_tai_khoan()
                    account_matches = account_df[account_df['TenDangNhap'].astype(str).str.strip().eq(curr_username)] if not account_df.empty else pd.DataFrame()
                    stored_hash = account_matches.iloc[0].get('MatKhau', '') if not account_matches.empty else ''
                    if not verify_password(old_p, stored_hash):
                        st.error("Sai mật khẩu cũ!")
                    elif new_p != cfm_p:
                        st.error("Mật khẩu không khớp!")
                    elif len(new_p) < 8:
                        st.error("Mật khẩu mới phải có ít nhất 8 ký tự!")
                    else:
                        try:
                            sh_main = ket_noi_sheet(SHEET_MAIN)
                            row_no = int(account_matches.iloc[0]['_sheet_row']) if not account_matches.empty else None
                            if row_no:
                                sh_main.worksheet("TaiKhoan").update_cell(row_no, 2, _scrypt_hash(new_p))
                                load_tai_khoan.clear()
                                st.success("Đổi mật khẩu thành công!")
                                clear_cache_and_rerun()
                            else:
                                st.error("Không tìm thấy tài khoản để cập nhật.")
                        except Exception as exc:
                            logger.exception("Đổi mật khẩu thất bại")
                            st.error(f"Không thể đổi mật khẩu: {exc}")
                            
        if st.button("ĐĂNG XUẤT"): 
            st.session_state['authenticated'] = False; st.session_state['user_info'] = {}; st.session_state['username'] = ''
            st.rerun()

    st.title("🏢 PHÒNG NỘI DUNG SỐ & TRUYỀN THÔNG")
    
    list_tabs = ["📝 VỎ TRỰC SỐ", "📺 TẠO LPS", "✅ CHECKLIST", "📋 CÔNG VIỆC", "🗂️ DỰ ÁN", "📅 LỊCH", "📧 EMAIL"]
    if role == 'LanhDao': list_tabs.extend(["📊 DASHBOARD", "📜 NHẬT KÝ"])
    tabs = st.tabs(list_tabs)

    # ================= TAB 0: VỎ TRỰC SỐ =================
    with tabs[0]:
        c_nav1, c_nav2 = st.columns([1, 4])
        with c_nav1: target_date = st.date_input("📅 CHỌN NGÀY LÀM VIỆC:", value=get_vn_time().date(), format="DD/MM/YYYY")
        
        tab_name_current = target_date.strftime("%d/%m/%Y") 
        date_str_display = target_date.strftime("%d/%m/%Y")
        
        with c_nav2: st.header(f"📝 VỎ TRỰC SỐ NGÀY: {date_str_display}")

        is_shift_admin = (role in ['LanhDao', 'ToChucSanXuat'])
        
        tab_exists, df_content_static, roster_names_current, r_roles_current = fetch_vo_truc_so(tab_name_current)

        if not tab_exists:
            st.warning(f"CHƯA CÓ VỎ TRỰC SỐ NGÀY {date_str_display}.")
            if is_shift_admin:
                
                with st.spinner("⚡ Đang kết nối siêu tốc đa luồng để phân tích Lịch..."):
                    auto_ldp, auto_tcsx, auto_btv, auto_ht, scan_errors = lay_nhan_su_tu_lich_phuc_tap(target_date, list_nv)
                
                if scan_errors:
                    for err in scan_errors: st.warning(err)
                    
                default_roster = [""] * 8
                default_roster[0] = match_nv(get_lanh_dao_ban(target_date), list_nv)
                default_roster[1] = auto_ldp if auto_ldp else "--"
                default_roster[2] = auto_btv[0] if len(auto_btv) > 0 else "--" 
                default_roster[3] = "--" 
                default_roster[4] = auto_tcsx if auto_tcsx else "--"
                default_roster[5] = "--" 
                default_roster[6] = auto_btv[1] if len(auto_btv) > 1 else "--" 
                default_roster[7] = auto_btv[2] if len(auto_btv) > 2 else "--" 

                with st.form("init_roster"):
                    cols = st.columns(3); roster_vals = []
                    for i, r_t in enumerate(ROLES_HEADER):
                        with cols[i%3]: 
                            def_val = default_roster[i]
                            # Ép Lãnh đạo xuất hiện ngay cả khi chưa tạo tài khoản trong hệ thống
                            options = ["--"] + list_nv
                            if def_val and def_val != "--" and def_val not in options:
                                options.append(def_val)
                            
                            def_idx = options.index(def_val) if def_val in options else 0
                            val = st.selectbox(f"**{r_t}**", options, index=def_idx, key=f"cr_{i}")
                            roster_vals.append(val if val != "--" else "")
                    
                    if st.form_submit_button("🚀 TẠO VỎ TRỰC SỐ MỚI"):
                        with st.spinner("Đang tạo vỏ trực số chuẩn Formatting..."):
                            try:
                                sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
                                w = sh_trucso.add_worksheet(title=tab_name_current, rows=100, cols=20, index=0)
                                dinh_dang_dep(w, roster_vals)
                                tu_dong_cap_nhat_thong_ke(date_str_display, roster_vals)
                                st.cache_data.clear()
                                st.success("ĐÃ TẠO XONG VỎ TRỰC SỐ!"); time.sleep(1); st.rerun()
                            except Exception as e: st.error(str(e))
        elif tab_exists:
            is_shift_ldp = False
            is_shift_tcsx = False
            try:
                ldp_in_sheet = str(roster_names_current[1]).strip().lower() if len(roster_names_current) > 1 else ""
                tcsx_in_sheet = str(roster_names_current[4]).strip().lower() if len(roster_names_current) > 4 else ""
                curr_lower = curr_name.lower()
                
                if ldp_in_sheet and ldp_in_sheet != "--" and (ldp_in_sheet in curr_lower or curr_lower in ldp_in_sheet): is_shift_ldp = True
                if tcsx_in_sheet and tcsx_in_sheet != "--" and (tcsx_in_sheet in curr_lower or curr_lower in tcsx_in_sheet): is_shift_tcsx = True
            except: pass
            
            if role == 'LanhDao': 
                is_shift_ldp = True
                is_shift_tcsx = True
            if role == 'ToChucSanXuat':
                is_shift_tcsx = True

            with st.expander("👥 THÔNG TIN EKIP TRỰC SỐ", expanded=False):
                try:
                    c1, c2, c3, c4 = st.columns(4)
                    cols_1 = [c1, c2, c3, c4]
                    for i in range(4):
                        if i < len(roster_names_current): cols_1[i].markdown(f"<p style='color:gray; font-size:12px; margin-bottom:0px;'>{r_roles_current[i]}</p><b>{roster_names_current[i]}</b>", unsafe_allow_html=True)
                    st.write("---"); c5, c6, c7, c8 = st.columns(4); cols_2 = [c5, c6, c7, c8]
                    for i in range(4):
                        idx = i + 4
                        if idx < len(roster_names_current): cols_2[i].markdown(f"<p style='color:gray; font-size:12px; margin-bottom:0px;'>{r_roles_current[idx]}</p><b>{roster_names_current[idx]}</b>", unsafe_allow_html=True)
                except: pass

            st.write("")

            filter_opt = st.pills("Bộ lọc", ["Tất cả", "🚨 Cảnh báo rủi ro", "🔴 Cần sửa", "🔄 BTV đã sửa", "👀 Chờ TCSX duyệt", "⏳ Chờ LĐP duyệt", "✅ Đã duyệt"], default="Tất cả", label_visibility="collapsed")

            # ================= LỒNG KÍNH PHÂN MẢNH THỜI GIAN THỰC =================
            @st.fragment(run_every="15s")
            def real_time_dashboard_and_table(current_filter):
                _, df_content, _, _ = fetch_vo_truc_so(tab_name_current)
                if df_content.empty: return
                
                split_idx = -1
                for i, row in df_content.iterrows():
                    nd = str(row.get('NỘI DUNG', '')).strip().upper()
                    nt = str(row.get('NỀN TẢNG', '')).strip().upper()
                    dd = str(row.get('ĐỊNH DẠNG', '')).strip().upper()
                    if nd == 'NỘI DUNG' and ('PHỤ TRÁCH' in nt or 'LINK' in dd):
                        split_idx = i
                        break
                
                if split_idx != -1:
                    df_main = df_content.iloc[:split_idx].copy()
                    df_seeding = df_content.iloc[split_idx+1:].copy()
                else:
                    df_main = df_content.copy()
                    df_seeding = pd.DataFrame()
                
                df_context = df_main.copy()
                def is_valid_row(row):
                    stt = str(row.get('STT', ''))
                    nd = str(row.get('NỘI DUNG', ''))
                    nt = str(row.get('NỀN TẢNG', ''))
                    stt = "" if stt.lower() in ['nan', '<na>', 'none'] else stt.strip()
                    nd = "" if nd.lower() in ['nan', '<na>', 'none'] else nd.strip()
                    nt = "" if nt.lower() in ['nan', '<na>', 'none'] else nt.strip()
                    return stt != "" or nd != "" or nt != ""
                    
                df_context = df_context[df_context.apply(is_valid_row, axis=1)]

                df_context['NỘI DUNG_GROUP'] = df_context['NỘI DUNG'].replace('', pd.NA).ffill()
                df_context['NỘI DUNG_GROUP'] = df_context['NỘI DUNG_GROUP'].fillna("Chưa có tên")
                
                df_context = df_context.dropna(subset=['NỘI DUNG_GROUP'])
                df_context = df_context[df_context['NỘI DUNG_GROUP'].astype(str).str.strip() != "Chưa có tên"]
                
                df_context['NHÂN SỰ'] = df_context['NHÂN SỰ'].replace('', pd.NA).ffill().fillna("Chưa phân công")
                df_context['NHÂN SỰ_NORM'] = df_context['NHÂN SỰ'].apply(lambda x: normalize_btv_names_strict(x, list_nv))
                df_context['NGUỒN'] = df_context['NGUỒN'].replace('', pd.NA).ffill().fillna("")
                
                summary_data = []
                unique_products = df_context['NỘI DUNG_GROUP'].unique()
                valid_products = [p for p in unique_products if str(p).strip() != ""]
                
                for prod in valid_products:
                    group = df_context[df_context['NỘI DUNG_GROUP'] == prod]
                    smart_status = get_smart_status(group)
                    
                    btvs = group['NHÂN SỰ_NORM'].unique()
                    btv_name = ", ".join([b for b in btvs if b and b != "Chưa Phân Công"]) if len(btvs) > 0 else "Chưa phân công"
                    plats = group['NỀN TẢNG'].replace('', pd.NA).dropna().tolist()
                    
                    summary_data.append({
                        "Sản phẩm": prod,
                        "BTV": btv_name,
                        "Tiến độ": smart_status,
                        "Nền tảng": ", ".join(plats)
                    })

                    # BÍ MẬT QUÉT NGẦM
                    first_row_bg = group.iloc[0]
                    curr_txt, _ = split_text_link(first_row_bg.get('LINK DUYỆT', ''))
                    queue_bg_scan(curr_txt, smart_status)
                
                df_summary = pd.DataFrame(summary_data)
                
                if not df_summary.empty:
                    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
                    m1.metric("📌 Tổng bài", len(df_summary))
                    m2.metric("📝 Đang làm", len(df_summary[df_summary["Tiến độ"] == "📝 BTV đang hoàn thiện"]))
                    m3.metric("👀 Chờ TCSX", len(df_summary[df_summary["Tiến độ"] == "👀 Chờ TCSX duyệt"]))
                    m4.metric("⏳ Chờ LĐP", len(df_summary[df_summary["Tiến độ"] == "⏳ Chờ LĐP duyệt"]))
                    m5.metric("🔴 Cần sửa", len(df_summary[df_summary["Tiến độ"] == "🔴 Cần sửa"]))
                    m6.metric("🔄 BTV đã sửa", len(df_summary[df_summary["Tiến độ"] == "🔄 BTV đã sửa"]))
                    m7.metric("✅ Đã chốt", len(df_summary[df_summary["Tiến độ"] == "✅ Đã duyệt"]))
                    
                    st.write("")
                    btv_list = [b for b in df_summary['BTV'].unique() if b not in ["Chưa Phân Công", "Chưa phân công", ""]]
                    if btv_list:
                        btv_cols = st.columns(len(btv_list))
                        for i, b in enumerate(btv_list):
                            b_df = df_summary[df_summary['BTV'] == b]
                            total_b = len(b_df)
                            done_b = len(b_df[b_df['Tiến độ'].astype(str).str.contains("Đã duyệt", na=False)])
                            btv_cols[i].metric(label=b, value=f"{done_b}/{total_b}") 

                        st.write("")
                        fig_btv = px.histogram(df_summary, y="BTV", color="Tiến độ", orientation='h', 
                                               color_discrete_map={
                                                   "✅ Đã duyệt": "#28a745",
                                                   "🔴 Cần sửa": "#dc3545",
                                                   "🚨 Cảnh báo rủi ro": "#ff0000",
                                                   "🔄 BTV đã sửa": "#007bff",
                                                   "👀 Chờ TCSX duyệt": "#ffc107",
                                                   "⏳ Chờ LĐP duyệt": "#fd7e14",
                                                   "📝 BTV đang hoàn thiện": "#6c757d"
                                               })
                        fig_btv.update_layout(barmode='stack', yaxis_title=None, xaxis_title="Số lượng bài", margin=dict(l=0, r=0, t=10, b=0), height=200)
                        st.plotly_chart(fig_btv, use_container_width=True)

                    st.write("")
                    df_show = df_summary.copy()
                    if current_filter != "Tất cả": df_show = df_show[df_show["Tiến độ"] == current_filter]
                    
                    st.dataframe(
                        df_show, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "Sản phẩm": st.column_config.TextColumn("Sản phẩm", width="large"),
                            "BTV": st.column_config.TextColumn("BTV", width="medium"),
                            "Tiến độ": st.column_config.TextColumn("Tiến độ", width="medium"),
                            "Nền tảng": st.column_config.TextColumn("Nền tảng", width="medium"),
                        }
                    )

                seeding_clean = []
                if not df_seeding.empty:
                    for _, r in df_seeding.iterrows():
                        task = str(r.get('NỘI DUNG', '')).strip()
                        if task == "" or task.lower() in ['nan', '<na>', 'none']: continue
                        seeding_clean.append({
                            "STT": str(r.get('STT', '')).replace('nan', '').strip(),
                            "Nhiệm vụ": task,
                            "Link": str(r.get('ĐỊNH DẠNG', '')).replace('nan', '').strip(),
                            "Phụ trách": str(r.get('NỀN TẢNG', '')).replace('nan', '').strip(),
                            "KPI": str(r.get('STATUS', '')).replace('nan', '').strip(),
                            "Tiến độ": str(r.get('CHECK', '')).replace('nan', '').strip()
                        })
                if seeding_clean:
                    st.markdown("---")
                    st.markdown("##### 🚀 DANH SÁCH NHIỆM VỤ SEEDING & QUẢNG BÁ")
                    st.dataframe(
                        pd.DataFrame(seeding_clean), 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "Nhiệm vụ": st.column_config.TextColumn("Nhiệm vụ", width="large"),
                        }
                    )

            real_time_dashboard_and_table(filter_opt)
            st.divider()

            # ================= 4. KHU VỰC DUYỆT BÀI CHI TIẾT =================
            st.markdown("##### 🛠️ KHU VỰC XỬ LÝ & DUYỆT BÀI")
            st.caption("📌 CHỌN BÀI VIẾT ĐỂ LÀM VIỆC (Các bài 'Cảnh báo rủi ro', 'Cần sửa' được đẩy lên đầu)")
            
            if not df_content_static.empty:
                split_idx_st = -1
                for i, row in df_content_static.iterrows():
                    nd = str(row.get('NỘI DUNG', '')).strip().upper()
                    nt = str(row.get('NỀN TẢNG', '')).strip().upper()
                    dd = str(row.get('ĐỊNH DẠNG', '')).strip().upper()
                    if nd == 'NỘI DUNG' and ('PHỤ TRÁCH' in nt or 'LINK' in dd):
                        split_idx_st = i
                        break
                        
                if split_idx_st != -1:
                    df_main_st = df_content_static.iloc[:split_idx_st].copy()
                else:
                    df_main_st = df_content_static.copy()
                    
                df_context_st = df_main_st.copy()
                
                def is_valid_row_st(row):
                    stt = str(row.get('STT', ''))
                    nd = str(row.get('NỘI DUNG', ''))
                    nt = str(row.get('NỀN TẢNG', ''))
                    stt = "" if stt.lower() in ['nan', '<na>', 'none'] else stt.strip()
                    nd = "" if nd.lower() in ['nan', '<na>', 'none'] else nd.strip()
                    nt = "" if nt.lower() in ['nan', '<na>', 'none'] else nt.strip()
                    return stt != "" or nd != "" or nt != ""
                    
                df_context_st = df_context_st[df_context_st.apply(is_valid_row_st, axis=1)]
                df_context_st['NỘI DUNG_GROUP'] = df_context_st['NỘI DUNG'].replace('', pd.NA).ffill()
                df_context_st = df_context_st.dropna(subset=['NỘI DUNG_GROUP'])
                df_context_st = df_context_st[df_context_st['NỘI DUNG_GROUP'].astype(str).str.strip() != "Chưa có tên"]
                
                unique_products = df_context_st['NỘI DUNG_GROUP'].unique()
                valid_products = [p for p in unique_products if str(p).strip() != ""]
                
                dropdown_options = []
                prod_mapping = {} 
                
                for prod in valid_products:
                    group = df_context_st[df_context_st['NỘI DUNG_GROUP'] == prod]
                    smart_status = get_smart_status(group)
                    if filter_opt == "Tất cả" or smart_status == filter_opt:
                        label = f"[{smart_status}] {prod}"
                        dropdown_options.append(label)
                        prod_mapping[label] = prod
                
                dropdown_options = sorted(dropdown_options, key=get_priority_score)
                
                if not dropdown_options:
                    st.info("📭 Không có bài viết nào thuộc nhóm lọc này. Hãy chọn Tất cả để xem lại.")
                else:
                    if len(dropdown_options) == 1:
                        sel_label = st.selectbox("CHỌN BÀI:", dropdown_options, label_visibility="collapsed")
                    else:
                        sel_label = st.selectbox("CHỌN BÀI:", ["-- Chọn bài viết --"] + dropdown_options, label_visibility="collapsed")
                    
                    if sel_label and sel_label != "-- Chọn bài viết --":
                        sel_product = prod_mapping[sel_label]
                        group_df = df_context_st[df_context_st['NỘI DUNG_GROUP'] == sel_product]
                        first_row_idx = group_df.index[0]
                        first_row_data = group_df.iloc[0]
                        
                        current_text, current_link = split_text_link(first_row_data.get('LINK DUYỆT', ''))
                        current_status_val = get_smart_status(group_df)
                        is_already_done = any(s in current_status_val.lower() for s in ["đã duyệt", "đã đăng", "posted", "scheduled"])
                        
                        # --- TÍNH NĂNG AI PHẢN BIỆN ---
                        st.markdown("🤖 **AI CẢNH BÁO RỦI RO**")
                        with st.container(border=True):
                            st.info("Hệ thống tự động rà soát lỗi chính tả, ngữ pháp và một số lỗi rủi ro có khả năng xảy ra.")
                            
                            c_ai1, c_ai2 = st.columns([1, 1])
                            auto_scan = c_ai1.checkbox("🔄 Tự động hiển thị kết quả quét", value=True)
                            btn_scan = c_ai2.button("⚡ RÀ SOÁT LẠI BẰNG AI")
                            
                            if not current_text or len(current_text.strip()) < 10:
                                st.warning("Chưa có đủ nội dung văn bản (Text bài đăng) để rà soát.")
                            elif is_already_done and not btn_scan:
                                st.success("✅ Bài viết này đã được phê duyệt hoặc đã đăng. (Bỏ qua rà soát AI để tiết kiệm tài nguyên).")
                            else:
                                text_hash = hashlib.md5(current_text.encode('utf-8')).hexdigest()
                                cache_key = f"ai_res_{text_hash}"
                                
                                if btn_scan or (auto_scan and cache_key not in st.session_state):
                                    with st.spinner("🤖 AI đang phân tích văn bản để đưa ra gợi ý, cảnh báo..."):
                                        ans = _call_api(current_text, get_ai_api_key(), str(st.secrets.get("groq_model", os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))).strip(), get_vn_time().strftime("%d/%m/%Y"))
                                        st.session_state[cache_key] = ans
                                
                                if cache_key in st.session_state:
                                    ans = st.session_state[cache_key]
                                    if "⚠️" in ans or "⚪" in ans:
                                        st.warning(ans)
                                    elif "nội dung an toàn" in ans.lower() or "đủ điều kiện" in ans.lower() or "ít rủi ro" in ans.lower():
                                        st.success("✅ " + ans)
                                    else:
                                        st.error("🚨 HỆ THỐNG PHÁT HIỆN CÓ RỦI RO HOẶC SAI SÓT TRONG BÀI VIẾT NÀY!")
                                        with st.container(height=350):
                                            st.markdown(ans)
                        # ---------------------------------
                        
                        with st.form("edit_group_form"):
                            col_left, col_right = st.columns([1.2, 1])
                            
                            with col_left:
                                st.markdown("**:blue[1. NỘI DUNG BÀI VIẾT]**")
                                e_nd = st.text_area("Tên bài / Tiêu đề", value=first_row_data['NỘI DUNG_GROUP'], height=68)
                                
                                c_ns, c_nguon = st.columns(2)
                                e_ns = c_ns.text_input("BTV Thực hiện", value=first_row_data['NHÂN SỰ'])
                                e_ng = c_nguon.text_input("Nguồn", value=first_row_data.get('NGUỒN', ''))
                                
                                st.markdown("---")
                                if current_link: st.link_button("▶️ MỞ LINK GOOGLE DRIVE TRONG TAB MỚI", current_link, type="secondary")
                                e_texttin = st.text_area("Nội dung Text bài đăng (Caption, Hashtag...)", value=current_text, height=150)
                                e_ld = st.text_input("Cập nhật/Sửa Link Drive", value=current_link)
                                
                                st.markdown("---")
                                st.markdown("**:green[2. KHU VỰC NHẬN XÉT & CHỈ ĐẠO]**")
                                
                                all_old_tcsx = "\n".join(group_df['TCSX'].replace('', pd.NA).dropna().astype(str).tolist())
                                all_old_ldp = "\n".join(group_df['LĐP'].replace('', pd.NA).dropna().astype(str).tolist())
                                
                                c_tcsx, c_ldp = st.columns(2)
                                with c_tcsx:
                                    st.caption("TỔ CHỨC SẢN XUẤT:")
                                    if all_old_tcsx: st.info(all_old_tcsx)
                                    else: st.caption("*Chưa có nhận xét*")
                                    
                                    e_tcsx_new = st.text_input("TCSX Nhập góp ý (Nếu có):", key="in_tcsx") if is_shift_tcsx else ""
                                    e_tcsx_ok = st.checkbox("✅ TCSX CHỐT DUYỆT BÀI", key="chk_tcsx") if is_shift_tcsx else False
                                
                                with c_ldp:
                                    st.caption("LÃNH ĐẠO PHÒNG:")
                                    if all_old_ldp: st.success(all_old_ldp)
                                    else: st.caption("*Chưa có nhận xét*")
                                    
                                    e_ldp_new = st.text_input("LĐP Nhập chỉ đạo (Nếu có):", key="in_ldp") if is_shift_ldp else ""
                                    e_ldp_ok = st.checkbox("🚀 LĐP CHỐT FINAL", key="chk_ldp") if is_shift_ldp else False

                            with col_right:
                                st.markdown("**:orange[3. TRẠNG THÁI TỪNG NỀN TẢNG]**")
                                st.caption("Các nền tảng phát sóng của bài viết này. Chỉ cập nhật khi có thay đổi giờ/link sản phẩm.")
                                
                                platform_updates = {}
                                for i, r in group_df.iterrows():
                                    nentang = r['NỀN TẢNG']
                                    
                                    with st.expander(f"🔹 {nentang} (Status: {r['STATUS']})", expanded=False):
                                        try: idx_st = OPTS_STATUS_TRUCSO.index(r['STATUS'])
                                        except: idx_st = 0
                                        st_val = st.selectbox(f"Trạng thái", OPTS_STATUS_TRUCSO, index=idx_st, key=f"st_{i}")
                                        
                                        c_t, c_d = st.columns(2)
                                        try: 
                                            time_str = str(r.get('GIỜ ĐĂNG', '')).strip()
                                            if time_str.count(":") == 2: val_time = datetime.strptime(time_str, "%H:%M:%S").time()
                                            elif time_str.count(":") == 1: val_time = datetime.strptime(time_str, "%H:%M").time()
                                            else: val_time = None
                                        except: val_time = None
                                        time_val = c_t.time_input("Giờ xuất bản", value=val_time, key=f"ti_{i}")
                                        
                                        try: curr_d_val = datetime.strptime(str(r.get('NGÀY ĐĂNG', '')), "%d/%m/%Y").date()
                                        except (TypeError, ValueError): curr_d_val = get_vn_today()
                                        date_val = c_d.date_input("Ngày", value=curr_d_val, format="DD/MM/YYYY", key=f"da_{i}")
                                        
                                        lsp_val = st.text_input("Link Sản phẩm đã lên", value=r.get('LINK SẢN PHẨM', ''), key=f"lsp_{i}")
                                        
                                        platform_updates[i] = {
                                            'STATUS': st_val, 'TIME': time_val, 'DATE': date_val, 'LINK_SP': lsp_val
                                        }

                            st.markdown("<br>", unsafe_allow_html=True)
                            submit_col1, submit_col2, submit_col3 = st.columns([1, 2, 1])
                            with submit_col2:
                                if st.form_submit_button("💾 LƯU PHÊ DUYỆT & CẬP NHẬT TRÊN SHEET", use_container_width=True, type="primary"):
                                    with st.spinner("Đang đồng bộ dữ liệu siêu tốc..."):
                                        merged_link_duyet_update = merge_text_link(e_texttin, e_ld)
                                        final_tcsx = build_appended_comment(all_old_tcsx, e_tcsx_new, e_tcsx_ok) if is_shift_tcsx else all_old_tcsx
                                        final_ldp = build_appended_comment(all_old_ldp, e_ldp_new, e_ldp_ok) if is_shift_ldp else all_old_ldp
                                        
                                        first_sheet_row = first_row_idx + 6
                                        sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
                                        wks_today = sh_trucso.worksheet(tab_name_current)
                                        
                                        cells_to_update = [
                                            gspread.Cell(first_sheet_row, 2, e_nd),
                                            gspread.Cell(first_sheet_row, 7, e_ng),
                                            gspread.Cell(first_sheet_row, 8, e_ns),
                                            gspread.Cell(first_sheet_row, 9, final_tcsx),
                                            gspread.Cell(first_sheet_row, 10, final_ldp),
                                            gspread.Cell(first_sheet_row, 14, merged_link_duyet_update)
                                        ]
                                        
                                        for idx, update_data in platform_updates.items():
                                            sheet_row = idx + 6
                                            cells_to_update.append(gspread.Cell(sheet_row, 5, update_data['STATUS']))
                                            cells_to_update.append(gspread.Cell(sheet_row, 11, update_data['TIME'].strftime("%H:%M:%S") if update_data['TIME'] else ""))
                                            cells_to_update.append(gspread.Cell(sheet_row, 12, update_data['DATE'].strftime("%d/%m/%Y")))
                                            cells_to_update.append(gspread.Cell(sheet_row, 13, update_data['LINK_SP']))
                                            if idx != first_row_idx:
                                                cells_to_update.append(gspread.Cell(sheet_row, 9, ""))
                                                cells_to_update.append(gspread.Cell(sheet_row, 10, ""))
                                        
                                        wks_today.update_cells(cells_to_update)
                                        
                                        clear_app_caches()
                                        st.success("✅ Cập nhật thành công!"); time.sleep(1); st.rerun()

            with st.expander("➕ THÊM BÀI MỚI VÀO VỎ TRỰC SỐ", expanded=False):
                with st.form("add_news_form"):
                    c1, c2 = st.columns([3, 1])
                    ts_noidung = c1.text_area("Tên bài / Nội dung", placeholder="Nhập nội dung...")
                    ts_dinhdang = c2.selectbox("Định dạng", OPTS_DINH_DANG)
                    c3, c4, c5 = st.columns(3)
                    ts_nentang = c3.multiselect("Nền tảng xuất bản", OPTS_NEN_TANG)
                    ts_status = c4.selectbox("Trạng thái", OPTS_STATUS_TRUCSO)
                    ts_nhansu = c5.multiselect("BTV Thực hiện", list_nv, default=[curr_name] if curr_name in list_nv else None)
                    st.markdown("**NỘI DUNG CAPTION/TEXT:**")
                    ts_texttin = st.text_area("TEXT CỦA TIN", height=100)
                    ts_linkduyet = st.text_input("LINK GOOGLE DRIVE")
                    if st.form_submit_button("THÊM VÀO VỎ TRỰC SỐ", type="primary"):
                        with st.spinner("Đang lưu..."):
                            try:
                                sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
                                wks_today = sh_trucso.worksheet(tab_name_current)
                                all_rows = wks_today.get_all_values()
                                
                                # FIX STT Logic: Lấy số lớn nhất từ các dòng trước đó để không bị lệch do merge cells
                                start_stt = 1
                                if len(all_rows) > 5:
                                    for r in reversed(all_rows[5:]):
                                        if len(r) > 0 and str(r[0]).strip().isdigit():
                                            start_stt = int(str(r[0]).strip()) + 1
                                            break

                                plats = ts_nentang if ts_nentang else [""]
                                merged_link_duyet = merge_text_link(ts_texttin, ts_linkduyet)
                                rows_to_add = []
                                for p in plats:
                                    row = [start_stt, ts_noidung, ts_dinhdang, p, ts_status, "", "", ", ".join(ts_nhansu), "", "", "", date_str_display, "", merged_link_duyet]
                                    rows_to_add.append(row)
                                
                                start_row_to_format = len(all_rows) + 1
                                wks_today.append_rows(rows_to_add)
                                end_row_to_format = len(all_rows) + len(rows_to_add)
                                
                                dinh_dang_dong_moi(wks_today, start_row_to_format, end_row_to_format)
                                
                                # --- FIX GỘP Ô (MERGE CELLS) TRỰC TIẾP TRÊN SHEET ---
                                if len(rows_to_add) > 1:
                                    merge_requests = []
                                    # Các cột cần merge theo format (trừ Nền tảng, Status, Checklist, Thời gian, Link SP)
                                    cols_to_merge = [0, 1, 2, 6, 7, 8, 9, 13]
                                    for col_idx in cols_to_merge:
                                        merge_requests.append({
                                            "mergeCells": {
                                                "range": {
                                                    "sheetId": wks_today.id,
                                                    "startRowIndex": start_row_to_format - 1,
                                                    "endRowIndex": end_row_to_format,
                                                    "startColumnIndex": col_idx,
                                                    "endColumnIndex": col_idx + 1
                                                },
                                                "mergeType": "MERGE_ALL"
                                            }
                                        })
                                    try:
                                        wks_today.spreadsheet.batch_update({"requests": merge_requests})
                                    except Exception as merge_err:
                                        logger.error(f"Lỗi khi thực hiện gộp ô: {merge_err}")
                                
                                clear_app_caches()
                                st.success("ĐÃ THÊM MỚI!"); time.sleep(1); st.rerun()
                            except Exception as e: st.error(f"Lỗi: {e}")

    # ================= TAB 1: TẠO LPS TỰ ĐỘNG =================
    with tabs[1]:
        st.header("📺 CÔNG CỤ XUẤT LỊCH PHÁT SÓNG TỰ ĐỘNG")
        
        tom_date = get_vn_time().date() + timedelta(days=1)
        col_d, col_s = st.columns([1, 2])
        target_date_lps = col_d.date_input("📅 Chọn Ngày phát sóng:", value=tom_date, format="DD/MM/YYYY")
        
        excel_bytes = get_public_gsheet_as_excel(LINK_KHUNG_LPS)
        
        if not excel_bytes:
            st.error("⚠️ Không thể tải dữ liệu tự động từ đường link Khung. Vui lòng tải file lên thủ công.")
            uploaded_file = st.file_uploader("📂 Tải lên file Excel Khung", type=["xlsx", "xls"])
            if uploaded_file: excel_bytes = uploaded_file.getvalue()
            
        if excel_bytes:
            try:
                xls = pd.ExcelFile(io.BytesIO(excel_bytes))
                sheet_names = xls.sheet_names
                
                best_idx = 0
                for idx, title in enumerate(sheet_names):
                    dates = re.findall(r'(\d{1,2})[./](\d{1,2})', title)
                    if len(dates) >= 1:
                        try:
                            d1, m1 = int(dates[0][0]), int(dates[0][1])
                            d2, m2 = int(dates[1][0]), int(dates[1][1]) if len(dates) >= 2 else (d1, m1)
                            y_target = target_date_lps.year
                            start_date = datetime(y_target, m1, d1).date()
                            y_end = y_target + 1 if m2 < m1 else y_target
                            end_date = datetime(y_end, m2, d2).date()
                            
                            if start_date <= target_date_lps <= end_date:
                                best_idx = idx
                                break
                        except: pass
                
                selected_sheet = col_s.selectbox("📍 Đã tự động chọn Tab Khung phù hợp (Có thể đổi):", sheet_names, index=best_idx)
                
                df_khung = pd.read_excel(xls, sheet_name=selected_sheet, header=None)
                
                days_of_week = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
                selected_day = days_of_week[target_date_lps.weekday()]
                
                day_keywords = {"Thứ Hai": ["thứ hai", "monday", "mon"], "Thứ Ba": ["thứ ba", "tuesday", "tue"], "Thứ Tư": ["thứ tư", "wednesday", "wed"], "Thứ Năm": ["thứ năm", "thursday", "thu"], "Thứ Sáu": ["thứ sáu", "friday", "fri"], "Thứ Bảy": ["thứ bảy", "saturday", "sat"], "Chủ Nhật": ["chủ nhật", "sunday", "sun"]}
                target_col_idx = -1; keywords = day_keywords[selected_day]
                
                for r_idx in range(min(5, len(df_khung))):
                    for c_idx in range(len(df_khung.columns)):
                        cell_val = str(df_khung.iloc[r_idx, c_idx]).lower()
                        if any(kw in cell_val for kw in keywords):
                            target_col_idx = c_idx; break
                    if target_col_idx != -1: break
                    
                if target_col_idx == -1:
                    fallback_map = {"Thứ Hai": 8, "Thứ Ba": 9, "Thứ Tư": 10, "Thứ Năm": 11, "Thứ Sáu": 12, "Thứ Bảy": 13, "Chủ Nhật": 14}
                    target_col_idx = fallback_map[selected_day]
                
                time_col_idx = 3 
                lps_data = []
                
                if target_col_idx < len(df_khung.columns):
                    for r_idx in range(5, len(df_khung)):
                        time_val = df_khung.iloc[r_idx, time_col_idx]
                        content_val = df_khung.iloc[r_idx, target_col_idx]
                        if not pd.isna(content_val) and str(content_val).strip() != "":
                            title, desc = parse_khung_cell(content_val)
                            formatted_time = format_time_col(time_val)
                            if title:
                                exclude_keywords = [
                                    "weather forecast", "đệm", "filler", "trailer", 
                                    "amazing", "block", "promo", "tài trợ", "quảng cáo", "ident",
                                    "thời tiết", "weather", "bản tin thời tiết", "thoi tiet"
                                ]
                                title_lower = title.lower()
                                if not any(kw in title_lower for kw in exclude_keywords): 
                                    lps_data.append({"Giờ phát sóng (hh:mm)": formatted_time, "Tiêu đề": title, "Mô tả": desc})
                
                if lps_data:
                    df_lps = pd.DataFrame(lps_data)
                    st.success(f"✅ Đã tự động bóc tách thành công LPS cho {selected_day} ngày {target_date_lps.strftime('%d/%m/%Y')}!")
                    edited_lps = st.data_editor(df_lps, use_container_width=True, hide_index=True)
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer: 
                        edited_lps.to_excel(writer, index=False, sheet_name=selected_day)
                    
                    st.download_button(
                        label="📥 TẢI FILE EXCEL LPS VỀ MÁY", 
                        data=output.getvalue(), 
                        file_name=f"LPS_VNTD_{target_date_lps.strftime('%d_%m')}.xlsx", 
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                        type="primary"
                    )
                else: 
                    st.warning(f"📭 Không tìm thấy dữ liệu phát sóng trong cột {selected_day} của Tab này.")
            except Exception as e:
                st.error(f"Lỗi khi đọc file Khung: {e}")

    # ================= CÁC TAB KHÁC =================
    with tabs[2]:
        st.header(f"📝 CHECKLIST CỦA: {curr_name.upper()}")
        col_view, col_date = st.columns([1, 2])
        view_mode = col_view.radio("Xem theo:", ["Hôm nay", "Tuần này", "Tháng này"], horizontal=True)
        today = get_vn_today()
        my_tasks = [t for t in df_cn.to_dict('records') if str(t.get('User')) == curr_name]
        filtered_tasks = []
        for t in my_tasks:
            try:
                t_date = datetime.strptime(t['Ngay'], "%d/%m/%Y").date()
                if view_mode == "Hôm nay" and t_date == today: filtered_tasks.append(t)
                elif view_mode == "Tuần này" and today - timedelta(days=today.weekday()) <= t_date <= today + timedelta(days=6-today.weekday()): filtered_tasks.append(t)
                elif view_mode == "Tháng này" and t_date.month == today.month and t_date.year == today.year: filtered_tasks.append(t)
            except: pass
        if filtered_tasks:
            df_my_view = pd.DataFrame(filtered_tasks); df_my_view['Xong'] = df_my_view['TrangThai'].apply(lambda x: True if str(x).upper() == "TRUE" else False)
            edited_df = st.data_editor(df_my_view[['TenViec', 'Ngay', 'GhiChu', 'Xong', '_sheet_row']], column_config={"Xong": st.column_config.CheckboxColumn("Hoàn thành", default=False), "_sheet_row": st.column_config.NumberColumn("ID", disabled=True, width="small"), "TenViec": st.column_config.TextColumn("Nội dung công việc", width="medium"), "Ngay": st.column_config.TextColumn("Ngày", disabled=True), "GhiChu": st.column_config.TextColumn("Ghi chú")}, hide_index=True, key="editor_checklist")
            if st.button("💾 CẬP NHẬT CHECKLIST"):
                with st.spinner("Đang lưu..."):
                    try:
                        sh_main = ket_noi_sheet(SHEET_MAIN)
                        try: wks_canhan = sh_main.worksheet("ViecCaNhan")
                        except: 
                            wks_canhan = sh_main.add_worksheet("ViecCaNhan", 1000, 5)
                            wks_canhan.append_row(["User", "TenViec", "Ngay", "TrangThai", "GhiChu"])
                        
                        all_values = wks_canhan.get_all_values()
                        cells = []
                        for i, row in edited_df.iterrows():
                            source_row = None
                            if i in df_my_view.index and '_sheet_row' in df_my_view.columns:
                                try:
                                    source_row = int(df_my_view.loc[i, '_sheet_row'])
                                except (TypeError, ValueError):
                                    source_row = None
                            if source_row:
                                cells.append(gspread.Cell(source_row, 4, "TRUE" if row['Xong'] else "FALSE"))
                                cells.append(gspread.Cell(source_row, 5, row['GhiChu']))
                        if cells:
                            wks_canhan.update_cells(cells)
                        st.success("Đã cập nhật!"); clear_cache_and_rerun()
                    except Exception as e: st.error(f"Lỗi: {e}")
        else: st.info(f"Bạn chưa có việc cá nhân nào trong {view_mode.lower()}.")
        st.divider()
        c_add1, c_add2 = st.columns(2)
        with c_add1:
            st.markdown("#### ➕ TỰ TẠO VIỆC")
            with st.form("new_personal_task"):
                n_ten = st.text_input("Nội dung"); n_ngay = st.date_input("Ngày", value=today, format="DD/MM/YYYY"); n_ghichu = st.text_input("Ghi chú")
                if st.form_submit_button("THÊM"):
                    if n_ten:
                        with st.spinner("Đang thêm..."):
                            update_wks_canhan("append", [curr_name, n_ten, n_ngay.strftime("%d/%m/%Y"), "FALSE", n_ghichu])
                            st.success("Xong!"); clear_cache_and_rerun()
        with c_add2:
            st.markdown("#### 📥 LẤY TỪ VIỆC CHUNG")
            if not df_cv.empty:
                my_tasks_cv = df_cv[df_cv['NguoiPhuTrach'].apply(lambda x: has_name_access(curr_name, x))]
                if not my_tasks_cv.empty:
                    opts = [f"{r['TenViec']} ({r['Deadline']})" for i, r in my_tasks_cv.iterrows()]
                    sel = st.selectbox("Chọn việc:", opts)
                    if st.button("CHUYỂN SANG CHECKLIST"):
                        with st.spinner("Đang chuyển..."):
                            t_name = sel.split(" (")[0]; row = my_tasks_cv[my_tasks_cv['TenViec'] == t_name].iloc[0]
                            try: dl = row['Deadline'].split(" ")[1]
                            except: dl = today.strftime("%d/%m/%Y")
                            update_wks_canhan("append", [curr_name, t_name, dl, "FALSE", "Từ hệ thống chung"])
                            st.success("Xong!"); clear_cache_and_rerun()

    with tabs[3]:
        st.caption("QUẢN LÝ TIẾN ĐỘ DỰ ÁN TOÀN PHÒNG.")
        with st.expander("➕ TẠO ĐẦU VIỆC MỚI", expanded=False):
            c1, c2 = st.columns(2)
            tv_ten = c1.text_input("TÊN ĐẦU VIỆC"); tv_duan = c1.selectbox("DỰ ÁN", list_duan)
            now_vn = get_vn_time()
            tv_time = c1.time_input("GIỜ DEADLINE", value=now_vn.time()); tv_date = c1.date_input("NGÀY DEADLINE", value=now_vn.date(), format="DD/MM/YYYY")
            tv_nguoi = c2.multiselect("BTV THỰC HIỆN", list_nv); tv_ghichu = c2.text_area("YÊU CẦU", height=100)
            ct1, ct2 = st.columns([2,1])
            tk_gui = ct1.selectbox("GỬI TỪ GMAIL:", range(10), format_func=lambda x: f"TK {x}")
            ct2.markdown(f'<br><a href="https://mail.google.com/mail/u/{tk_gui}" target="_blank">Check Mail</a>', unsafe_allow_html=True)
            opt_nv = st.checkbox("Gửi Email cho BTV", True)
            if st.button("💾 LƯU & GỬI EMAIL"):
                with st.spinner("Đang lưu..."):
                    try:
                        dl_fmt = f"{tv_time.strftime('%H:%M:%S')} {tv_date.strftime('%d/%m/%Y')}"
                        sh_main = ket_noi_sheet(SHEET_MAIN)
                        sh_main.worksheet("CongViec").append_row([tv_ten, tv_duan, dl_fmt, ", ".join(tv_nguoi), "Đã giao", "", tv_ghichu, curr_name])
                        ghi_nhat_ky(curr_name, "Tạo việc", tv_ten); st.success("Xong!")
                        if opt_nv and tv_nguoi:
                            mails = df_users[df_users['HoTen'].isin(tv_nguoi)]['Email'].tolist()
                            mails = [m for m in mails if str(m).strip()]
                            if mails: st.markdown(f'<a href="https://mail.google.com/mail/u/{tk_gui}/?view=cm&fs=1&to={",".join(mails)}&su={urllib.parse.quote(tv_ten)}&body={urllib.parse.quote(tv_ghichu)}" target="_blank">📧 Gửi BTV</a>', unsafe_allow_html=True)
                        clear_cache_and_rerun()
                    except Exception as e: st.error(str(e))
        st.divider()
        da_filter = st.selectbox("LỌC DỰ ÁN:", ["-- TẤT CẢ --"]+list_duan)
        if not df_cv.empty:
            df_display = df_cv.copy()
            if da_filter != "-- TẤT CẢ --": df_display = df_display[df_display['DuAn']==da_filter]
            edits = {f"{r['TenViec']} ({i+2})": {"id": i, "lv": check_quyen(curr_name, role, r, df_duan)} for i, r in df_display.iterrows() if check_quyen(curr_name, role, r, df_duan)>0}
            if edits:
                with st.expander("🛠️ CẬP NHẬT TRẠNG THÁI", expanded=True):
                    s_task = st.selectbox("CHỌN ĐẦU VIỆC:", list(edits.keys()))
                    if s_task:
                        row_idx = edits[s_task]['id']; lv = edits[s_task]['lv']; r_dat = df_display.iloc[row_idx]
                        dis = (lv == 1)
                        with st.form("f_edit_cv"):
                            ce1, ce2 = st.columns(2)
                            e_ten = ce1.text_input("TÊN VIỆC", r_dat['TenViec'], disabled=dis)
                            e_ng = ce1.text_input("BTV THỰC HIỆN", r_dat['NguoiPhuTrach'], disabled=dis)
                            e_lk = ce1.text_input("LINK SẢN PHẨM", r_dat.get('LinkBai',''))
                            e_dl = ce2.text_input("DEADLINE", r_dat.get('Deadline',''), disabled=dis)
                            e_st = ce2.selectbox("TRẠNG THÁI", OPTS_TRANG_THAI_VIEC, index=OPTS_TRANG_THAI_VIEC.index(r_dat.get('TrangThai','Đã giao')) if r_dat.get('TrangThai') in OPTS_TRANG_THAI_VIEC else 0)
                            e_nt = ce2.text_area("GHI CHÚ", r_dat.get('GhiChu',''))
                            if st.form_submit_button("CẬP NHẬT"):
                                float_time = time.time()
                                with st.spinner("Đang cập nhật..."):
                                    sh_main = ket_noi_sheet(SHEET_MAIN)
                                    w = sh_main.worksheet("CongViec")
                                    rn = int(r_dat.get('_sheet_row', 0) or 0)
                                    if rn:
                                        cells = [
                                            gspread.Cell(rn, 1, e_ten),
                                            gspread.Cell(rn, 3, e_dl),
                                            gspread.Cell(rn, 4, e_ng),
                                            gspread.Cell(rn, 5, e_st),
                                            gspread.Cell(rn, 6, e_lk),
                                            gspread.Cell(rn, 7, e_nt)
                                        ]
                                        w.update_cells(cells)
                                        st.success("ĐÃ CẬP NHẬT!"); clear_cache_and_rerun()
            st.dataframe(df_display.drop(columns=['NguoiTao'], errors='ignore').rename(columns=VN_COLS_VIEC), use_container_width=True, hide_index=True)

    with tabs[4]:
        if role == 'LanhDao':
            with st.form("new_da"):
                d_n = st.text_input("TÊN DỰ ÁN"); d_m = st.text_area("MÔ TẢ"); d_l = st.multiselect("PHỤ TRÁCH", list_nv)
                if st.form_submit_button("TẠO DỰ ÁN"): 
                    with st.spinner("Đang tạo..."):
                        sh_main = ket_noi_sheet(SHEET_MAIN)
                        sh_main.worksheet("DuAn").append_row([d_n, d_m, "Đang chạy", ",".join(d_l)]); st.success("Xong!"); clear_cache_and_rerun()
        st.dataframe(df_duan.rename(columns=VN_COLS_DUAN), use_container_width=True)

    with tabs[5]:
        st.header("📅 LỊCH LÀM VIỆC & DEADLINE")
        if not df_cv.empty:
            task_list = []
            for i, r in df_cv.iterrows():
                try:
                    dl_str = r['Deadline']; dl_dt = datetime.strptime(dl_str, "%H:%M:%S %d/%m/%Y")
                    start_dt = dl_dt - timedelta(days=2) 
                    if role not in {'LanhDao', 'Admin'} and not has_name_access(curr_name, r['NguoiPhuTrach']): continue
                    task_list.append({"Task": r['TenViec'], "Start": start_dt, "Finish": dl_dt, "Assignee": r['NguoiPhuTrach'], "Status": r['TrangThai'], "Project": r['DuAn']})
                except: continue
            if task_list:
                df_gantt = pd.DataFrame(task_list)
                fig = px.timeline(df_gantt, x_start="Start", x_end="Finish", y="Assignee", color="Status", hover_data=["Task", "Project"], title="TIMELINE CÔNG VIỆC (DỰ KIẾN)", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
                st.divider()
                st.dataframe(df_gantt[['Task', 'Finish', 'Assignee', 'Status']], use_container_width=True)

    with tabs[6]:
        tk = st.selectbox("TK GỬI:", range(10), format_func=lambda x:f"TK {x}")
        to = st.multiselect("ĐẾN:", df_users['Email'].tolist())
        sub = st.text_input("TIÊU ĐỀ"); bod = st.text_area("Nội dung")
        if st.button("GỬI EMAIL"): st.markdown(f'<script>window.open("https://mail.google.com/mail/u/{tk}/?view=cm&fs=1&to={",".join(to)}&su={urllib.parse.quote(sub)}&body={urllib.parse.quote(bod)}", "_blank");</script>', unsafe_allow_html=True)

    if role == 'LanhDao':
        with tabs[7]:
            st.header("📊 DASHBOARD TỔNG QUAN")
            if not df_cv.empty:
                col1, col2 = st.columns(2)
                with col1:
                    status_counts = df_cv['TrangThai'].value_counts().reset_index(); status_counts.columns = ['Trạng thái', 'Số lượng']
                    fig_pie = px.pie(status_counts, values='Số lượng', names='Trạng thái', title='TỶ LỆ TRẠNG THÁI CÔNG VIỆC', hole=0.4); st.plotly_chart(fig_pie, use_container_width=True)
                with col2:
                    all_staff = []; [all_staff.extend([n.strip() for n in s.split(',')]) for s in df_cv['NguoiPhuTrach']]
                    staff_counts = pd.Series(all_staff).value_counts().reset_index(); staff_counts.columns = ['BTV', 'Số việc']
                    fig_bar = px.bar(staff_counts, x='BTV', y='Số việc', title='NĂNG SUẤT NHÂN SỰ', color='BTV'); st.plotly_chart(fig_bar, use_container_width=True)
        with tabs[8]:
            if not df_log.empty: st.dataframe(df_log.iloc[::-1].rename(columns=VN_COLS_LOG), use_container_width=True)
