import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components
import urllib.parse
from datetime import datetime, date, time as dt_time, timedelta
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
import threading
import unicodedata
import html as html_lib
import copy

# --- THƯ VIỆN ĐỊNH DẠNG SHEET ---
from gspread_formatting import *

# ================= CẤU HÌNH HỆ THỐNG =================
st.set_page_config(page_title="PHÒNG NỘI DUNG SỐ & TRUYỀN THÔNG", page_icon="🏢", layout="wide")

# --- MÃ CSS TÀNG HÌNH CHỐNG CHỚP/MỜ MÀN HÌNH & GIAO DIỆN NEWSROOM HIỆN ĐẠI ---
st.markdown("""
    <style>
    /* Ép Streamlit không được làm mờ khối dữ liệu khi Reload */
    [data-stale="true"], div[data-stale="true"] {
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
        pointer-events: auto !important;
    }
    /* Tối ưu giao diện Thẻ Tin Bài Thông Minh (Smart Expander Cards) */
    div[data-testid="stExpander"] {
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        background: #ffffff !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
        margin-bottom: 8px !important;
        transition: all 0.15s ease-in-out !important;
    }
    div[data-testid="stExpander"]:hover {
        border-color: #93c5fd !important;
        box-shadow: 0 3px 10px rgba(24,119,242,0.08) !important;
    }
    div[data-testid="stExpander"] summary {
        padding: 10px 14px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stExpander"] summary:hover {
        background-color: #f8fafc !important;
        border-radius: 10px !important;
    }
    /* CSS cho Bảng cuộn Timeline & Meta Planner */
    .meta-planner-wrap {
        border: 1px solid #dfe3e8;
        border-radius: 12px;
        background: #f8f9fa;
        max-height: 640px;
        overflow: auto;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    }
    .meta-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 13px;
    }
    .meta-table thead th {
        position: sticky;
        top: 0;
        z-index: 20;
        background: #ffffff;
        color: #1c1e21;
        font-weight: 700;
        padding: 12px 10px;
        border-bottom: 2px solid #e4e6eb;
        border-right: 1px solid #eef0f3;
        text-align: center;
        min-width: 195px;
    }
    .meta-table thead th.time-col-hdr {
        position: sticky;
        left: 0;
        z-index: 30;
        min-width: 92px;
        max-width: 92px;
        background: #f0f2f5;
    }
    .meta-table tbody td {
        padding: 6px 8px;
        border-bottom: 1px solid #ebedf0;
        border-right: 1px solid #eef0f3;
        vertical-align: top;
        background: #ffffff;
    }
    .meta-table tbody tr.slot-busy td {
        background: #fbfcfe;
    }
    .meta-table tbody td.time-cell {
        position: sticky;
        left: 0;
        z-index: 10;
        background: #f7f8fa;
        font-weight: 700;
        color: #4b4f56;
        text-align: center;
        vertical-align: middle;
        border-right: 2px solid #dfe3e8;
        font-size: 12.5px;
    }
    .meta-card {
        background: #ffffff;
        border: 1px solid #d8dfea;
        border-left: 4px solid #1877f2;
        border-radius: 8px;
        padding: 8px 10px;
        margin-bottom: 6px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        text-align: left;
    }
    .meta-card.conflict {
        border: 1.5px solid #dc3545 !important;
        border-left: 5px solid #dc3545 !important;
        background: #fff5f5 !important;
    }
    .meta-card.cross-warn {
        border: 1.5px solid #fd7e14 !important;
        border-left: 5px solid #fd7e14 !important;
        background: #fff9f2 !important;
    }
    .meta-card-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
        font-size: 11.5px;
        font-weight: 700;
    }
    .meta-time-badge {
        background: #e7f3ff;
        color: #1877f2;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 700;
    }
    .meta-time-badge.conflict-badge {
        background: #dc3545;
        color: #ffffff;
    }
    .meta-card-title {
        font-weight: 600;
        color: #1c1e21;
        font-size: 12.5px;
        line-height: 1.35;
        margin-bottom: 4px;
        word-break: break-word;
    }
    .meta-card-sub {
        font-size: 11px;
        color: #65676b;
        display: flex;
        justify-content: space-between;
        gap: 4px;
        flex-wrap: wrap;
    }
    .slot-empty-pill {
        color: #b0b3b8;
        font-size: 11px;
        text-align: center;
        padding: 6px 2px;
        border: 1px dashed #e4e6eb;
        border-radius: 6px;
    }
    .slot-cooldown-pill {
        color: #d97706;
        background: #fffbeb;
        font-size: 11px;
        text-align: center;
        padding: 5px 4px;
        border: 1px dashed #fcd34d;
        border-radius: 6px;
    }
    .news-comment-pill {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 12px;
        margin-right: 6px;
        margin-bottom: 4px;
    }
    </style>
""", unsafe_allow_html=True)

SHEET_MAIN = str(st.secrets.get("sheet_main", os.getenv("SHEET_MAIN", "HeThongQuanLy"))).strip()
SHEET_TRUCSO = "VoTrucSo"
LINK_VO_TRUC_SO = "https://docs.google.com/spreadsheets/d/1WYfdY8OIVWPD-N5xZD36B3v7MV_XFjHXj_v9UZXK0ZI/edit?gid=1107365160#gid=1107365160"
LINK_LICH_BTV_TCSX = "https://docs.google.com/spreadsheets/d/1IFbxenXl7PehWc3Q0L35DHkkUVyEBGXaV7JSRKHMSn8/edit?gid=387062810#gid=387062810"
LINK_LICH_LDP = "https://docs.google.com/spreadsheets/d/1IFbxenXl7PehWc3Q0L35DHkkUVyEBGXaV7JSRKHMSn8/edit?gid=570145520#gid=570145520"
LINK_KHUNG_LPS = "https://docs.google.com/spreadsheets/d/1WfZledcegY7E0Vqm0gEX9kjczx0JxnYv/edit?gid=1508530487#gid=1508530487"

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
def get_vn_time(): return datetime.now(VN_TZ)
def get_vn_today(): return get_vn_time().date()

# KHÓA BẢO VỆ CHỐNG GHI ĐÈ KHI NHẬP LIỆU NHANH
SHEET_LOCK = threading.Lock()
LAST_GSHEET_ERROR = ""

# --- LÕI AI GROQ & BỘ NHỚ DỰ PHÒNG CHỐNG SẬP APP ---
logger = logging.getLogger("vietnam_today")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def get_ai_api_key():
    try:
        key = str(st.secrets.get("groq_api_key", os.getenv("GROQ_API_KEY", ""))).strip()
        return key if key else ""
    except Exception:
        return str(os.getenv("GROQ_API_KEY", "")).strip()

@st.cache_resource
def init_ai_engine():
    return {
        "cache": {},
        "queue": set(),
        "executor": concurrent.futures.ThreadPoolExecutor(max_workers=5),
        "backup_users": pd.DataFrame(),
        "backup_trucso": {},
        "backup_app_data": None,
        "optimistic_posts": [],
        "added_order": {},
        "sessions": {}
    }

AI_ENGINE = init_ai_engine()
for _k, _v in [("added_order", {}), ("sessions", {}), ("optimistic_posts", [])]:
    if _k not in AI_ENGINE:
        AI_ENGINE[_k] = _v

def _call_api(text, api_key, model_name, today_str):
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    system_prompt = f"""Bạn là Thư ký tòa soạn kỳ cựu của kênh Vietnam Today (VTV International). 
Hôm nay là ngày {today_str}.

QUY TẮC CỐT LÕI VỀ DANH XƯNG & THỜI SỰ (BẮT BUỘC TUÂN THỦ):
1. Luôn luôn update tin tức, thông tin mới nhất, tránh bị nhầm, lạc hậu, lỗi thời.
2. Về Lãnh đạo quốc tế & Sự kiện ngoại giao mới: 
   - Không được dùng kiến thức lịch sử cũ để phủ nhận các chuyến thăm, hội đàm hay thỏa thuận nâng cấp quan hệ ngoại giao mới trong bản tin.
   - Nếu bản tin nói về một thỏa thuận ngoại giao/hội đàm cụ thể hoặc một sự kiện mới, hãy mặc định BTV đang cập nhật từ nguồn thông tấn chính thức, tuyệt đối không bắt lỗi 'không có bằng chứng'.
3. Phạm vi rà soát trọng tâm:
   - Tập trung bắt lỗi: Chính tả tiếng Anh/tiếng Việt, ngữ pháp, câu cú lủng củng, format ngày tháng chuẩn quốc tế (có thể chỉ có ngày tháng, hoặc ngày tháng năm), danh xưng tên riêng tiếng Việt chuẩn quốc tế (không dấu).
   - Cảnh báo rủi ro nếu có yếu tố xuyên tạc chủ quyền biển đảo, chính trị, tôn giáo, phân biệt đối xử.
   - Thêm cảnh báo nếu nội dung phi logic hoặc cách viết chưa tốt, từ ngữ lặp hoặc sai sót... kèm gợi ý cách sửa."""

    user_prompt = f"""
    Rà soát nội dung tin tức/bài đăng MXH dưới đây của Vietnam Today:
    
    YÊU CẦU:
    - Nếu nội dung chuẩn xác, không có lỗi ngữ pháp/chính tả nghiêm trọng, trả đúng 1 câu duy nhất: "Nội dung ít rủi ro".
    - Nếu cần sửa: Gạch đầu dòng ngắn gọn lỗi chính tả/ngữ pháp, các lỗi hoặc nhận xét khác, và kèm theo cách sửa. Không dài dòng khen ngợi, không bịa đặt hoặc bắt lỗi sai kiến thức thời sự mới.

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
            if response.status_code == 400 and "model_decommissioned" in response.text:
                payload["model"] = "llama-3.3-70b-versatile"
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
    
    model_name = str(st.secrets.get("groq_model", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))).strip()
    today_str = get_vn_time().strftime("%d/%m/%Y")
    
    AI_ENGINE["queue"].add(text_hash)
    AI_ENGINE["executor"].submit(_bg_task, text, api_key, model_name, today_str, text_hash)

# ================= BACKGROUND TASKS ĐỂ TĂNG TỐC GIAO DIỆN =================
def bg_add_news(tab_name, ts_noidung, ts_dinhdang, plats, ts_status, ts_check, ts_nguon, ts_nhansu, post_time_str, post_date_str, merged_link_duyet):
    with SHEET_LOCK:
        try:
            sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
            wks_today = sh_trucso.worksheet(tab_name)
            all_rows = wks_today.get("A1:O300")
            
            start_stt = 1
            start_row_idx = 5
            for i, r in enumerate(all_rows[5:]):
                r_str = "".join([str(x).strip() for x in r])
                if "PHÂN CÔNG TRẢ LỜI" in r_str.upper(): break
                if r_str: 
                    start_row_idx = i + 5 + 1
                    if len(r) > 0 and str(r[0]).strip().isdigit():
                        start_stt = int(str(r[0]).strip()) + 1

            added_map = AI_ENGINE.setdefault("added_order", {})
            order_list = added_map.setdefault(tab_name, [])
            clean_title = str(ts_noidung).strip()
            if clean_title and clean_title not in order_list:
                order_list.append(clean_title)

            combined_tg = format_thoi_gian_dang(post_time_str, post_date_str)
            rows_to_add = []
            for idx_p, p in enumerate(plats):
                if idx_p == 0:
                    row = [start_stt, ts_noidung, ts_dinhdang, p, ts_status, ts_check, ts_nguon, ", ".join(ts_nhansu), "", "", "", combined_tg, "", merged_link_duyet]
                else:
                    row = [start_stt, "", ts_dinhdang, p, ts_status, "", "", "", "", "", "", "", "", ""]
                rows_to_add.append(row)
                start_stt += 1 
            
            wks_today.insert_rows(rows_to_add, row=start_row_idx + 1)
            
            # Mặc định giữ nguyên vị trí vừa thêm ở cuối bảng (sort_mode="keep"), chỉ gộp ô & đánh lại STT + giữ nguyên màu
            sort_vo_truc_so_sheet(wks_today, sort_mode="keep")

            AI_ENGINE["optimistic_posts"] = [
                op for op in AI_ENGINE.get("optimistic_posts", [])
                if not (op.get("tab_name") == tab_name and op.get("title") == ts_noidung)
            ]
            clear_trucso_cache()
        except Exception as e:
            logger.error(f"Lỗi thêm bài ngầm: {e}")

def bg_update_post(tab_name, first_row_idx, e_nd, e_ng, e_ns, final_tcsx, final_ldp, final_td, merged_link_duyet_update, platform_updates):
    with SHEET_LOCK:
        try:
            sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
            wks_today = sh_trucso.worksheet(tab_name)
            
            all_vals = wks_today.get_all_values()
            header_idx = 3
            for idx in range(min(10, len(all_vals))):
                row_upper = [str(x).strip().upper() for x in all_vals[idx]]
                if "STATUS" in row_upper or "NỘI DUNG" in row_upper:
                    header_idx = idx
                    break
            headers = [str(h).strip().upper() for h in all_vals[header_idx]]

            first_sheet_row = first_row_idx + 6

            if first_sheet_row - 1 < len(all_vals) and len(all_vals[first_sheet_row - 1]) > 1:
                old_title = str(all_vals[first_sheet_row - 1][1]).strip()
                new_title = str(e_nd).strip()
                if old_title and new_title and old_title != new_title:
                    order_list = AI_ENGINE.setdefault("added_order", {}).setdefault(tab_name, [])
                    if old_title in order_list:
                        order_list[order_list.index(old_title)] = new_title

            first_plat_data = platform_updates.get(first_row_idx) or next(iter(platform_updates.values()), None)
            combined_tg = ""
            if first_plat_data:
                t_str = first_plat_data['TIME'].strftime("%H:%M") if first_plat_data.get('TIME') else ""
                d_str = first_plat_data['DATE'].strftime("%d/%m/%Y") if first_plat_data.get('DATE') else ""
                combined_tg = format_thoi_gian_dang(t_str, d_str)

            lsp_vals = [str(u.get('LINK_SP', '')).strip() for u in platform_updates.values() if str(u.get('LINK_SP', '')).strip()]
            consolidated_lsp = "\n".join(list(dict.fromkeys(lsp_vals)))

            if "THỜI GIAN ĐĂNG BÀI" not in headers:
                sort_vo_truc_so_sheet(wks_today, sort_mode="keep")

            cells_to_update = [
                gspread.Cell(first_sheet_row, 2, e_nd),
                gspread.Cell(first_sheet_row, 7, e_ng),
                gspread.Cell(first_sheet_row, 8, e_ns),
                gspread.Cell(first_sheet_row, 9, final_tcsx),
                gspread.Cell(first_sheet_row, 10, final_ldp),
                gspread.Cell(first_sheet_row, 11, final_td),
                gspread.Cell(first_sheet_row, 12, combined_tg),
                gspread.Cell(first_sheet_row, 13, consolidated_lsp),
                gspread.Cell(first_sheet_row, 14, merged_link_duyet_update),
            ]
            for idx, update_data in platform_updates.items():
                sheet_row = idx + 6
                cells_to_update.append(gspread.Cell(sheet_row, 5, update_data['STATUS']))
                if idx != first_row_idx:
                    for c_clear in (9, 10, 11, 12, 13, 14):
                        cells_to_update.append(gspread.Cell(sheet_row, c_clear, ""))
            wks_today.update_cells(cells_to_update)
            clear_trucso_cache()
        except Exception as e:
            logger.error(f"Lỗi cập nhật bài: {e}")

def bg_batch_update_grid(tab_name, updates_list):
    """Lưu hàng loạt chỉnh sửa trực tiếp từ chế độ Bảng Excel Nâng Cao"""
    with SHEET_LOCK:
        try:
            sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
            wks_today = sh_trucso.worksheet(tab_name)
            all_vals = wks_today.get_all_values()
            header_idx = 3
            for idx in range(min(10, len(all_vals))):
                row_upper = [str(x).strip().upper() for x in all_vals[idx]]
                if "STATUS" in row_upper or "NỘI DUNG" in row_upper:
                    header_idx = idx
                    break
            headers = [str(h).strip().upper() for h in all_vals[header_idx]]
            if "THỜI GIAN ĐĂNG BÀI" not in headers:
                sort_vo_truc_so_sheet(wks_today, sort_mode="keep")

            cells = []
            for item in updates_list:
                sheet_r = int(item["first_row_idx"]) + 6
                cells.extend([
                    gspread.Cell(sheet_r, 2, item["NỘI DUNG"]),
                    gspread.Cell(sheet_r, 7, item["NGUỒN"]),
                    gspread.Cell(sheet_r, 8, item["NHÂN SỰ"]),
                    gspread.Cell(sheet_r, 9, item["TCSX"]),
                    gspread.Cell(sheet_r, 10, item["LĐP"]),
                    gspread.Cell(sheet_r, 11, item["THẨM ĐỊNH"]),
                    gspread.Cell(sheet_r, 12, item["THỜI GIAN ĐĂNG BÀI"]),
                ])
            if cells:
                wks_today.update_cells(cells)
            clear_trucso_cache()
        except Exception as e:
            logger.error(f"Lỗi lưu bảng nhanh: {e}")

def bg_quick_reschedule(tab_name, row_indices, new_time_str, new_date_str):
    with SHEET_LOCK:
        try:
            sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
            wks_today = sh_trucso.worksheet(tab_name)
            all_vals = wks_today.get_all_values()
            header_idx = 3
            for idx in range(min(10, len(all_vals))):
                row_upper = [str(x).strip().upper() for x in all_vals[idx]]
                if "STATUS" in row_upper or "NỘI DUNG" in row_upper:
                    header_idx = idx
                    break
            headers = [str(h).strip().upper() for h in all_vals[header_idx]]
            combined_tg = format_thoi_gian_dang(new_time_str, new_date_str)

            if "THỜI GIAN ĐĂNG BÀI" in headers:
                col_tg = headers.index("THỜI GIAN ĐĂNG BÀI") + 1
                cells = []
                for i_pos, r_idx in enumerate(row_indices):
                    sheet_row = int(r_idx) + 6
                    cells.append(gspread.Cell(sheet_row, col_tg, combined_tg if i_pos == 0 else ""))
                if cells:
                    wks_today.update_cells(cells)
            else:
                has_td = ("THẨM ĐỊNH" in headers)
                col_time = (headers.index("GIỜ ĐĂNG") + 1) if "GIỜ ĐĂNG" in headers else (12 if has_td else 11)
                col_date = (headers.index("NGÀY ĐĂNG") + 1) if "NGÀY ĐĂNG" in headers else (13 if has_td else 12)
                cells = []
                for r_idx in row_indices:
                    sheet_row = int(r_idx) + 6
                    cells.append(gspread.Cell(sheet_row, col_time, new_time_str))
                    cells.append(gspread.Cell(sheet_row, col_date, new_date_str))
                if cells:
                    wks_today.update_cells(cells)

            sort_vo_truc_so_sheet(wks_today, sort_mode="keep")
            clear_trucso_cache()
        except Exception as e:
            logger.error(f"Lỗi đổi lịch nhanh: {e}")

def bg_add_seeding(tab_name, s_nhiemvu, s_link, s_phutrach, s_kpi, s_nhansu):
    with SHEET_LOCK:
        try:
            sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
            wks_today = sh_trucso.worksheet(tab_name)
            all_rows = wks_today.get("A1:N300")
            
            header_row = -1
            for i, r_val in enumerate(all_rows):
                r_str = " ".join([str(x).upper() for x in r_val])
                if "LINK" in r_str and "PHỤ TRÁCH" in r_str and "KPI" in r_str: header_row = i + 1
            
            fmt_requests = []; rows_to_append = []
            if header_row == -1:
                r1 = [""] * 14; r1[1] = "PHÂN CÔNG TRẢ LỜI BÌNH LUẬN, MỒI BÌNH LUẬN, TƯƠNG TÁC"
                r2 = [""] * 14; r2[1] = "Tương tác khán giả thì sử dụng tài khoản Vietnam Today, còn mồi bình luận thì sử dụng tài khoản cá nhân hoặc các tài khoản bên ngoài.\nKhi tương tác bằng nick Vietnam Today phải tuân thủ nghiêm ngặt mọi quy định về phát ngôn, đại diện phát ngôn của cơ quan."
                r3 = ["STT", "NHIỆM VỤ", "LINK", "PHỤ TRÁCH", "KPI", "NHÂN SỰ", "KẾT QUẢ"] + [""] * 7
                rows_to_append.extend([[""]*14, r1, r2, r3])
                start_stt = 1
            else:
                start_stt = 1
                for r in reversed(all_rows[header_row:]):
                    if len(r) > 0 and str(r[0]).strip().isdigit():
                        start_stt = int(str(r[0]).strip()) + 1
                        break
                        
            new_task = [start_stt, s_nhiemvu, s_link, s_phutrach, s_kpi, s_nhansu, ""] + [""] * 7
            rows_to_append.append(new_task)
            
            start_append_row = len(all_rows) + 1
            wks_today.append_rows(rows_to_append)
            end_append_row = start_append_row + len(rows_to_append) - 1
            
            if header_row == -1:
                fmt_requests.append({"mergeCells": {"range": {"sheetId": wks_today.id, "startRowIndex": start_append_row, "endRowIndex": start_append_row + 1, "startColumnIndex": 1, "endColumnIndex": 14}, "mergeType": "MERGE_ALL"}})
                fmt_requests.append({"mergeCells": {"range": {"sheetId": wks_today.id, "startRowIndex": start_append_row + 1, "endRowIndex": start_append_row + 2, "startColumnIndex": 1, "endColumnIndex": 14}, "mergeType": "MERGE_ALL"}})
                fmt_requests.append({"repeatCell": {"range": {"sheetId": wks_today.id, "startRowIndex": start_append_row, "endRowIndex": start_append_row + 1, "startColumnIndex": 1, "endColumnIndex": 14}, "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontFamily": "Times New Roman"}, "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(textFormat,horizontalAlignment)"}})
                fmt_requests.append({"repeatCell": {"range": {"sheetId": wks_today.id, "startRowIndex": start_append_row + 1, "endRowIndex": start_append_row + 2, "startColumnIndex": 1, "endColumnIndex": 14}, "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontFamily": "Times New Roman"}, "wrapStrategy": "WRAP", "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(textFormat,wrapStrategy,horizontalAlignment)"}})
                fmt_requests.append({"repeatCell": {"range": {"sheetId": wks_today.id, "startRowIndex": start_append_row + 2, "endRowIndex": start_append_row + 3, "startColumnIndex": 0, "endColumnIndex": 7}, "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontFamily": "Times New Roman"}, "horizontalAlignment": "CENTER", "borders": {"top": {"style": "SOLID"}, "bottom": {"style": "SOLID"}, "left": {"style": "SOLID"}, "right": {"style": "SOLID"}}}}, "fields": "userEnteredFormat(textFormat,horizontalAlignment,borders)"}})
            
            task_row_idx = end_append_row
            fmt_requests.append({"repeatCell": {"range": {"sheetId": wks_today.id, "startRowIndex": task_row_idx - 1, "endRowIndex": task_row_idx, "startColumnIndex": 0, "endColumnIndex": 7}, "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE", "horizontalAlignment": "CENTER", "textFormat": {"fontFamily": "Times New Roman"}, "borders": {"top": {"style": "SOLID"}, "bottom": {"style": "SOLID"}, "left": {"style": "SOLID"}, "right": {"style": "SOLID"}}}}, "fields": "userEnteredFormat(wrapStrategy,verticalAlignment,horizontalAlignment,textFormat,borders)"}})
            if fmt_requests: wks_today.spreadsheet.batch_update({"requests": fmt_requests})
            clear_trucso_cache()
        except Exception: pass

def bg_update_seeding(tab_name, cells_data):
    with SHEET_LOCK:
        try:
            sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
            wks = sh_trucso.worksheet(tab_name)
            cells = [gspread.Cell(r, c, v) for r, c, v in cells_data]
            if cells: wks.update_cells(cells)
            clear_trucso_cache()
        except Exception: pass

def background_save_task(tv_ten, tv_duan, dl_fmt, tv_nguoi_str, tv_ghichu, curr_name):
    with SHEET_LOCK:
        try:
            sh_main = ket_noi_sheet(SHEET_MAIN)
            sh_main.worksheet("CongViec").append_row([tv_ten, tv_duan, dl_fmt, tv_nguoi_str, "Đã giao", "", tv_ghichu, curr_name])
            wks = sh_main.worksheet("NhatKy")
            wks.append_row([get_vn_time().strftime("%H:%M %d/%m/%Y"), curr_name, "Tạo việc", str(tv_ten)[:5000]])
            load_du_lieu_app.clear()
        except Exception: pass

def background_update_task(rn, e_ten, e_dl, e_ng, e_st, e_lk, e_nt):
    with SHEET_LOCK:
        try:
            sh_main = ket_noi_sheet(SHEET_MAIN)
            w = sh_main.worksheet("CongViec")
            cells = [gspread.Cell(rn, 1, e_ten), gspread.Cell(rn, 3, e_dl), gspread.Cell(rn, 4, e_ng), gspread.Cell(rn, 5, e_st), gspread.Cell(rn, 6, e_lk), gspread.Cell(rn, 7, e_nt)]
            w.update_cells(cells)
            load_du_lieu_app.clear()
        except Exception: pass

def bg_update_checklist(edited_data):
    with SHEET_LOCK:
        try:
            sh_main = ket_noi_sheet(SHEET_MAIN)
            try: wks_canhan = sh_main.worksheet("ViecCaNhan")
            except: 
                wks_canhan = sh_main.add_worksheet("ViecCaNhan", 1000, 5)
                wks_canhan.append_row(["User", "TenViec", "Ngay", "TrangThai", "GhiChu"])
            cells = [gspread.Cell(r, c, v) for r, c, v in edited_data]
            if cells: wks_canhan.update_cells(cells)
            load_du_lieu_app.clear()
        except Exception: pass

def update_wks_canhan(action, row_data):
    with SHEET_LOCK:
        try:
            sh_main = ket_noi_sheet(SHEET_MAIN)
            try: wks_canhan = sh_main.worksheet("ViecCaNhan")
            except Exception:
                wks_canhan = sh_main.add_worksheet("ViecCaNhan", 1000, 5)
                wks_canhan.append_row(["User", "TenViec", "Ngay", "TrangThai", "GhiChu"])
            if action == "append":
                wks_canhan.append_row(row_data)
            load_du_lieu_app.clear()
        except Exception as e:
            logger.error(f"Lỗi cập nhật việc cá nhân: {e}")

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

def clear_trucso_cache():
    try: _fetch_vo_truc_so_cached.clear()
    except Exception: pass

def clear_app_caches():
    for fn in (_fetch_vo_truc_so_cached, _fetch_du_lieu_app_cached):
        try: fn.clear()
        except Exception: pass

def clear_cache_and_rerun():
    clear_trucso_cache()
    try: st.rerun()
    except Exception: pass

def apply_optimistic_post_update(tab_name, first_row_idx, e_nd, e_ng, e_ns, final_tcsx, final_ldp, final_td, merged_link, platform_updates):
    """Cập nhật ngay vào RAM (0ms) để giao diện phản hồi tức thì không cần đợi Google Sheet"""
    try:
        if tab_name in AI_ENGINE.get("backup_trucso", {}):
            exists, df_bak, r_names, r_roles = AI_ENGINE["backup_trucso"][tab_name]
            df_new = df_bak.copy()
            first_plat_data = platform_updates.get(first_row_idx) or next(iter(platform_updates.values()), None)
            combined_tg = ""
            if first_plat_data:
                t_str = first_plat_data['TIME'].strftime("%H:%M") if first_plat_data.get('TIME') else ""
                d_str = first_plat_data['DATE'].strftime("%d/%m/%Y") if first_plat_data.get('DATE') else ""
                combined_tg = format_thoi_gian_dang(t_str, d_str)
            lsp_vals = [str(u.get('LINK_SP', '')).strip() for u in platform_updates.values() if str(u.get('LINK_SP', '')).strip()]
            consolidated_lsp = "\n".join(list(dict.fromkeys(lsp_vals)))

            if first_row_idx in df_new.index:
                df_new.loc[first_row_idx, 'NỘI DUNG'] = e_nd
                df_new.loc[first_row_idx, 'NGUỒN'] = e_ng
                df_new.loc[first_row_idx, 'NHÂN SỰ'] = e_ns
                df_new.loc[first_row_idx, 'TCSX'] = final_tcsx
                df_new.loc[first_row_idx, 'LĐP'] = final_ldp
                if 'THẨM ĐỊNH' in df_new.columns:
                    df_new.loc[first_row_idx, 'THẨM ĐỊNH'] = final_td
                df_new.loc[first_row_idx, 'THỜI GIAN ĐĂNG BÀI'] = combined_tg
                df_new.loc[first_row_idx, 'LINK SẢN PHẨM'] = consolidated_lsp
                df_new.loc[first_row_idx, 'LINK DUYỆT'] = merged_link
            for idx_p, u_data in platform_updates.items():
                if idx_p in df_new.index:
                    df_new.loc[idx_p, 'STATUS'] = u_data['STATUS']
            AI_ENGINE["backup_trucso"][tab_name] = (exists, df_new, r_names, r_roles)
    except Exception:
        pass

def ghi_nhat_ky(nguoi_dung, hanh_dong, chi_tiet):
    def _log_bg():
        try:
            sh_main = ket_noi_sheet(SHEET_MAIN)
            wks = sh_main.worksheet("NhatKy")
            wks.append_row([get_vn_time().strftime("%H:%M %d/%m/%Y"), nguoi_dung, hanh_dong, str(chi_tiet)[:5000]])
        except Exception: pass
    AI_ENGINE["executor"].submit(_log_bg)

def get_short_name(full_name):
    if not full_name or full_name == "--" or str(full_name).strip() == "": return "..."
    parts = full_name.strip().split()
    return " ".join(parts[-2:]) if len(parts) >= 2 else full_name

def _clean_vn_str(s):
    if not s: return ""
    s = unicodedata.normalize("NFC", str(s).strip().lower())
    replacements = {"òa": "oà", "óa": "oá", "ỏa": "oả", "õa": "oã", "ọa": "oạ", "ùy": "uỳ", "úy": "uý", "ủy": "uỷ", "ũy": "uỹ", "ụy": "uỵ"}
    for k, v in replacements.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s)

def normalize_btv_names_strict(name_str, list_nv):
    if pd.isna(name_str) or str(name_str).strip() == "": return "Chưa phân công"
    raw_str = _clean_vn_str(name_str)
    found_names = []
    sorted_nv = sorted(list_nv, key=len, reverse=True)
    for nv in sorted_nv:
        nv_lower = _clean_vn_str(nv)
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
    n_clean = _clean_vn_str(name)
    for nv in list_nv:
        if n_clean == _clean_vn_str(nv):
            return nv
    for nv in list_nv:
        nv_clean = _clean_vn_str(nv)
        parts = nv_clean.split()
        if len(parts) >= 2 and " ".join(parts[-2:]) == n_clean:
            return nv
    if len(n_clean) >= 3:
        for nv in list_nv:
            nv_clean = _clean_vn_str(nv)
            if n_clean in nv_clean or nv_clean in n_clean:
                return nv
    return str(name).strip().title()

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
OPTS_NEN_TANG = ["Facebook", "Youtube", "TikTok", "Threads", "LinkedIn", "Instagram", "Web", "App"]
MANDATORY_PLATFORMS = ["Facebook", "LinkedIn", "Youtube", "Instagram"]
OPTIONAL_PLATFORMS = [p for p in OPTS_NEN_TANG if p not in MANDATORY_PLATFORMS]

PLATFORM_BADGE_STYLE = {
    "Facebook": ("🌐 Facebook", "#1877f2"),
    "LinkedIn": ("💼 LinkedIn", "#0a66c2"),
    "Youtube": ("▶️ Youtube", "#ff0000"),
    "Instagram": ("📸 Instagram", "#e1306c"),
    "TikTok": ("🎵 TikTok", "#111111"),
    "Threads": ("🧵 Threads", "#333333"),
    "Web": ("📰 Web", "#d97706"),
    "App": ("📱 App", "#ea580c"),
}

OPTS_STATUS_TRUCSO = [
    "Gửi duyệt TCSX", "Gửi duyệt LĐP", "Scheduled", "Đã đăng", "Posted",
    "Chờ xử lý", "Đang biên tập", "Cảnh báo rủi ro", 
    "Yêu cầu sửa (TCSX)", "Yêu cầu sửa (LĐP)", "Đã duyệt/Chờ đăng", "Hủy"
]

OPTS_TRANG_THAI_VIEC = ["Đã giao", "Đang thực hiện", "Chờ duyệt", "Hoàn thành", "Hủy"]
CONTENT_HEADER = ["STT", "NỘI DUNG", "ĐỊNH DẠNG", "NỀN TẢNG", "STATUS", "CHECK", "NGUỒN", "NHÂN SỰ", "TCSX", "LĐP", "THẨM ĐỊNH", "THỜI GIAN ĐĂNG BÀI", "LINK SẢN PHẨM", "LINK DUYỆT"]

VN_COLS_VIEC = {"TenViec": "Tên công việc", "DuAn": "Dự án", "Deadline": "Hạn chót", "NguoiPhuTrach": "Người thực hiện", "TrangThai": "Trạng thái", "LinkBai": "Link SP", "GhiChu": "Ghi chú"}
VN_COLS_DUAN = {"TenDuAn": "Tên Dự án", "MoTa": "Mô tả", "TrangThai": "Trạng thái", "TruongNhom": "Điều phối"}
VN_COLS_LOG = {"ThoiGian": "Thời gian", "NguoiDung": "Người dùng", "HanhDong": "Hành động", "ChiTiet": "Chi tiết"}

# ================= LÕI PHÂN LOẠI & SẮP XẾP GIỮ NGUYÊN MÀU SẮC TRÊN GOOGLE SHEET =================
NON_CM_KEYWORDS = {
    "off", "tin ht", "ht", "pssx", "tin", "ban tin", "bản tin",
    "bai dich", "bài dịch", "breaking news", "tin nhanh", "live", "truc tiep", "trực tiếp"
}

_VN_ABC_MAP = str.maketrans({
    "đ": "d", "Đ": "D",
    "ă": "a", "ắ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
    "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
    "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
    "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
    "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
    "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
})

def _abc_sort_key(text: str):
    if not text:
        return ("", "")
    s = str(text).strip()
    s_clean = re.sub(r"^[^\w]+", "", s, flags=re.UNICODE).strip().lower()
    s_base = s_clean.translate(_VN_ABC_MAP)
    s_ascii = "".join(
        ch for ch in unicodedata.normalize("NFKD", s_base)
        if not unicodedata.combining(ch)
    )
    return (s_ascii, s_clean)

def format_thoi_gian_dang(time_val, date_val=None, fallback_date=None):
    """Gộp Giờ đăng và Ngày đăng thành chuỗi chuẩn: '10:30 - 21/06/2026'"""
    raw_t = "" if pd.isna(time_val) else str(time_val).strip()
    raw_d = "" if (date_val is None or pd.isna(date_val)) else str(date_val).strip()
    if not raw_t and not raw_d:
        return ""

    fb_d = fallback_date or get_vn_today()
    t_obj = time_val if isinstance(time_val, dt_time) else _parse_post_time(raw_t)

    if isinstance(date_val, date) and not isinstance(date_val, datetime):
        d_obj = date_val
    elif raw_d:
        d_obj = _parse_post_date(raw_d, fb_d)
    else:
        d_obj = _parse_post_date(raw_t, fb_d)

    d_str = d_obj.strftime("%d/%m/%Y") if d_obj else ""
    if t_obj is not None:
        t_str = t_obj.strftime("%H:%M")
        return f"{t_str} - {d_str}" if d_str else t_str
    return d_str

def _is_chuyen_muc_post(title: str, source: str, dinh_dang: str = "") -> bool:
    src_clean = _clean_vn_str(source)
    title_raw = str(title or "").strip()
    title_clean = _clean_vn_str(title_raw)

    if any(re.search(r"\b" + re.escape(k) + r"\b", src_clean) for k in NON_CM_KEYWORDS):
        return False
    if re.match(r"^\s*(\[?\s*(off|tin\s*ht|tin\s*sx|ht|pssx)\s*\]?([:\-\s]|$))", title_clean):
        return False

    if "chuyên mục" in src_clean or "chuyen muc" in src_clean:
        return True

    lines = [ln.strip() for ln in title_raw.splitlines() if ln.strip()]
    if len(lines) >= 2:
        first_line = lines[0]
        fl_clean = _clean_vn_str(first_line).rstrip(":-").strip()
        if fl_clean in NON_CM_KEYWORDS:
            return False
        letters_only = "".join(ch for ch in first_line if ch.isalpha())
        if len(letters_only) >= 2 and first_line == first_line.upper():
            return True

    return False

def _build_cell_data(val_str: str, base_fmt: dict = None, center: bool = False, is_num: bool = False):
    """Tạo cấu trúc CellData chuẩn cho Google Sheets API, giữ nguyên màu nền (backgroundColor) & định dạng chữ do sếp/TCSX bôi tay"""
    fmt = copy.deepcopy(base_fmt) if isinstance(base_fmt, dict) else {}
    fmt["wrapStrategy"] = "WRAP"
    fmt["verticalAlignment"] = "MIDDLE"
    if center:
        fmt["horizontalAlignment"] = "CENTER"
    tf = fmt.get("textFormat", {})
    if not isinstance(tf, dict):
        tf = {}
    else:
        tf = copy.deepcopy(tf)
    tf["fontFamily"] = "Times New Roman"
    fmt["textFormat"] = tf
    fmt["borders"] = {
        "top": {"style": "SOLID"},
        "bottom": {"style": "SOLID"},
        "left": {"style": "SOLID"},
        "right": {"style": "SOLID"}
    }
    s_val = str(val_str or "").strip()
    if s_val == "":
        user_val = {"stringValue": ""}
    elif is_num and s_val.isdigit():
        user_val = {"numberValue": int(s_val)}
    elif s_val.startswith("="):
        user_val = {"formulaValue": s_val}
    else:
        user_val = {"stringValue": s_val}
    return {"userEnteredValue": user_val, "userEnteredFormat": fmt}

def sort_vo_truc_so_sheet(wks, sort_mode="time"):
    """
    Sắp xếp & Chuẩn hóa bảng Vỏ Trực Số:
    - Bảo tồn 100% màu sắc (Vàng, Đỏ, Xanh lá...) và định dạng in đậm/màu chữ do TCSX/LĐP bôi trên Google Sheet.
    - Tự động gộp ô các cột chung của đầu tin (bao gồm THỜI GIAN ĐĂNG BÀI, LINK SẢN PHẨM, LINK DUYỆT).
    - Hỗ trợ 5 chế độ: 'keep' (giữ nguyên), 'added' (thứ tự thêm vào vỏ), 'time' (giờ đăng), 'source' (nguồn), 'btv', 'title' (A-Z).
    """
    try:
        fallback_tab_date = datetime.strptime(wks.title.strip(), "%d/%m/%Y").date()
    except Exception:
        fallback_tab_date = get_vn_today()

    try:
        meta = wks.spreadsheet.fetch_sheet_metadata({
            "includeGridData": "true",
            "ranges": [f"'{wks.title}'!A1:O300"]
        })
        sheet_data_list = meta.get("sheets", [])
        all_row_data = []
        for sh_item in sheet_data_list:
            if sh_item.get("properties", {}).get("sheetId") == wks.id:
                data_blocks = sh_item.get("data", [])
                if data_blocks:
                    all_row_data = data_blocks[0].get("rowData", [])
                break
    except Exception as e:
        logger.error(f"Lỗi đọc GridData khi sắp xếp: {e}")
        return

    if len(all_row_data) <= 5:
        return

    all_rows = []
    all_fmts = []
    for rd in all_row_data:
        cells = rd.get("values", [])
        row_vals = []
        row_fmts = []
        for c in range(15):
            if c < len(cells) and isinstance(cells[c], dict):
                cell_d = cells[c]
                v_str = cell_d.get("formattedValue", "")
                if not v_str and "userEnteredValue" in cell_d:
                    uev = cell_d["userEnteredValue"]
                    v_str = str(uev.get("stringValue", uev.get("numberValue", uev.get("formulaValue", ""))))
                row_vals.append(str(v_str or "").strip())
                row_fmts.append(copy.deepcopy(cell_d.get("userEnteredFormat", {})))
            else:
                row_vals.append("")
                row_fmts.append({})
        all_rows.append(row_vals)
        all_fmts.append(row_fmts)

    header_idx = 3
    for idx in range(min(10, len(all_rows))):
        row_upper = [str(x).strip().upper() for x in all_rows[idx]]
        if "STATUS" in row_upper or "NỘI DUNG" in row_upper:
            header_idx = idx
            break

    headers_upper = [str(x).strip().upper() for x in all_rows[header_idx]]
    has_tham_dinh = ("THẨM ĐỊNH" in headers_upper)
    has_combined_tg = ("THỜI GIAN ĐĂNG BÀI" in headers_upper or "THỜI GIAN ĐĂNG" in headers_upper)

    # Nâng cấp Header lên chuẩn 14 cột nếu bảng cũ chưa chuẩn
    if not (has_tham_dinh and has_combined_tg):
        try:
            hdr_cells = []
            for c_i, h_text in enumerate(CONTENT_HEADER):
                hdr_cells.append(gspread.Cell(header_idx + 1, c_i + 1, h_text))
                hdr_cells.append(gspread.Cell(header_idx + 2, c_i + 1, ""))
            if len(headers_upper) >= 15:
                hdr_cells.append(gspread.Cell(header_idx + 1, 15, ""))
                hdr_cells.append(gspread.Cell(header_idx + 2, 15, ""))
            wks.update_cells(hdr_cells)

            hdr_reqs = [
                {"unmergeCells": {"range": {"sheetId": wks.id, "startRowIndex": 0, "endRowIndex": header_idx + 2, "startColumnIndex": 0, "endColumnIndex": 15}}},
                {"mergeCells": {"range": {"sheetId": wks.id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 14}, "mergeType": "MERGE_ALL"}},
            ]
            for c_i in range(14):
                hdr_reqs.append({"mergeCells": {"range": {"sheetId": wks.id, "startRowIndex": header_idx, "endRowIndex": header_idx + 2, "startColumnIndex": c_i, "endColumnIndex": c_i + 1}, "mergeType": "MERGE_ALL"}})
            hdr_reqs.append({
                "repeatCell": {
                    "range": {"sheetId": wks.id, "startRowIndex": header_idx, "endRowIndex": header_idx + 2, "startColumnIndex": 0, "endColumnIndex": 14},
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                            "textFormat": {"bold": True, "fontFamily": "Times New Roman"},
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE",
                            "wrapStrategy": "WRAP",
                            "borders": {"top": {"style": "SOLID"}, "bottom": {"style": "SOLID"}, "left": {"style": "SOLID"}, "right": {"style": "SOLID"}}
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy,borders)"
                }
            })
            wks.spreadsheet.batch_update({"requests": hdr_reqs})
        except Exception as e:
            logger.error(f"Lỗi nâng cấp Header: {e}")

    start_data_idx = header_idx + 2
    if start_data_idx >= len(all_rows):
        start_data_idx = 5

    split_row_idx = len(all_rows)
    for idx in range(start_data_idx, len(all_rows)):
        r = all_rows[idx]
        b_val = str(r[1] if len(r) > 1 else "").strip().upper()
        c_val = str(r[2] if len(r) > 2 else "").strip().upper()
        d_val = str(r[3] if len(r) > 3 else "").strip().upper()
        if "PHÂN CÔNG TRẢ LỜI BÌNH LUẬN" in b_val or ("LINK" in c_val and "PHỤ TRÁCH" in d_val):
            split_row_idx = idx
            break

    main_slice_vals = all_rows[start_data_idx:split_row_idx]
    main_slice_fmts = all_fmts[start_data_idx:split_row_idx]
    total_main_slots = len(main_slice_vals)
    if total_main_slots == 0:
        return

    groups = []
    current_grp = None
    for raw_r, raw_f in zip(main_slice_vals, main_slice_fmts):
        if has_tham_dinh and has_combined_tg:
            r_14 = [raw_r[c] for c in range(14)]
            f_14 = [raw_f[c] for c in range(14)]
            if r_14[11]:
                r_14[11] = format_thoi_gian_dang(r_14[11], None, fallback_tab_date)
        elif has_tham_dinh and not has_combined_tg:
            tg_str = format_thoi_gian_dang(raw_r[11], raw_r[12], fallback_tab_date)
            r_14 = raw_r[:11] + [tg_str, raw_r[13], raw_r[14]]
            f_14 = raw_f[:11] + [raw_f[11], raw_f[13], raw_f[14]]
        else:
            tg_str = format_thoi_gian_dang(raw_r[10], raw_r[11], fallback_tab_date)
            r_14 = raw_r[:10] + ["", tg_str, raw_r[12], raw_r[13]]
            f_14 = raw_f[:10] + [{}, raw_f[10], raw_f[12], raw_f[13]]

        if not any(r_14[c] != "" for c in range(1, 14)):
            continue

        if r_14[1] != "" or current_grp is None:
            current_grp = {"vals": [r_14], "fmts": [f_14]}
            groups.append(current_grp)
        else:
            current_grp["vals"].append(r_14)
            current_grp["fmts"].append(f_14)

    if not groups:
        return

    cols_to_merge = [1, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    for grp in groups:
        g_vals = grp["vals"]
        g_fmts = grp["fmts"]
        for c_idx in cols_to_merge:
            vals = [row[c_idx] for row in g_vals if row[c_idx]]
            if c_idx in (8, 9, 10, 12):
                consolidated = "\n".join(list(dict.fromkeys(vals)))
            else:
                consolidated = vals[0] if vals else ""
            g_vals[0][c_idx] = consolidated
            for k in range(1, len(g_vals)):
                g_vals[k][c_idx] = ""

            # Nếu một trong các dòng con có được bôi màu nền ở cột gộp, giữ màu đó lên ô đầu
            colored_fmt = next((f_row[c_idx] for f_row in g_fmts if isinstance(f_row[c_idx], dict) and "backgroundColor" in f_row[c_idx]), None)
            if colored_fmt:
                for k in range(len(g_fmts)):
                    g_fmts[k][c_idx] = copy.deepcopy(colored_fmt)

        fb_dinh_dang = next((row[2] for row in g_vals if row[2]), "")
        fb_status = next((row[4] for row in g_vals if row[4]), "")
        for row in g_vals:
            if not row[2] and fb_dinh_dang: row[2] = fb_dinh_dang
            if not row[4] and fb_status: row[4] = fb_status

    # Lưu vết và đồng bộ thứ tự thêm bài vào vỏ (ô ẩn N2)
    tab_key = wks.title.strip()
    added_map = AI_ENGINE.setdefault("added_order", {})
    order_list = list(added_map.get(tab_key, []))
    if not order_list and len(all_rows) > 1 and len(all_rows[1]) > 13:
        raw_saved = str(all_rows[1][13]).strip()
        if raw_saved.startswith("[") and raw_saved.endswith("]"):
            try:
                order_list = json.loads(raw_saved)
            except Exception:
                order_list = []

    changed_order_list = False
    for grp in groups:
        t_clean = str(grp["vals"][0][1]).strip()
        if t_clean and t_clean not in order_list:
            order_list.append(t_clean)
            changed_order_list = True
    added_map[tab_key] = order_list

    if changed_order_list:
        try:
            wks.update_cell(2, 14, json.dumps(order_list, ensure_ascii=False))
            wks.spreadsheet.batch_update({
                "requests": [{
                    "repeatCell": {
                        "range": {"sheetId": wks.id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 13, "endColumnIndex": 14},
                        "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "fontSize": 1}}},
                        "fields": "userEnteredFormat.textFormat"
                    }
                }]
            })
        except Exception:
            pass

    def _group_sort_key(grp):
        g_vals = grp["vals"]
        title = g_vals[0][1]
        dinh_dang = g_vals[0][2]
        source = g_vals[0][6]
        nhansu = g_vals[0][7]
        tg_str = g_vals[0][11]

        plats = [_canonical_platform(row[3]) for row in g_vals if row[3]]
        is_webapp_only = bool(plats) and all(p in ("Web", "App") for p in plats)
        is_cm = _is_chuyen_muc_post(title, source, dinh_dang)

        if not is_webapp_only:
            tier = 0
        elif not is_cm:
            tier = 1
        else:
            tier = 2

        t_obj = _parse_post_time(tg_str)
        d_obj = _parse_post_date(tg_str, fallback_tab_date)
        if t_obj is not None:
            has_no_time = 0
            sort_date, sort_time = d_obj, t_obj
        else:
            has_no_time = 1
            sort_date = d_obj
            sort_time = dt_time(23, 59, 59)

        title_k = _abc_sort_key(title)
        src_k = _abc_sort_key(source)
        has_no_src = 0 if str(source).strip() else 1
        btv_k = _abc_sort_key(nhansu)
        has_no_btv = 0 if str(nhansu).strip() else 1

        if sort_mode == "source":
            return (tier, has_no_src, src_k, has_no_time, sort_date, sort_time, title_k)
        elif sort_mode == "btv":
            return (tier, has_no_btv, btv_k, has_no_time, sort_date, sort_time, title_k)
        elif sort_mode == "title":
            return (tier, title_k, has_no_time, sort_date, sort_time)
        else:
            return (tier, has_no_time, sort_date, sort_time, title_k)

    if sort_mode == "keep":
        sorted_groups = groups
    elif sort_mode == "added":
        sorted_groups = sorted(
            groups,
            key=lambda g: order_list.index(str(g["vals"][0][1]).strip()) if str(g["vals"][0][1]).strip() in order_list else 99999
        )
    else:
        sorted_groups = sorted(groups, key=_group_sort_key)

    sorted_row_objects = []
    merge_spans = []
    curr_row_0 = start_data_idx
    curr_stt = 1
    cols_write_cnt = 15 if (has_tham_dinh and not has_combined_tg) else 14

    for grp in sorted_groups:
        g_vals = grp["vals"]
        g_fmts = grp["fmts"]
        grp_len = len(g_vals)
        for r_v, r_f in zip(g_vals, g_fmts):
            r_v[0] = str(curr_stt)
            curr_stt += 1
            cell_objs = []
            for c_i in range(14):
                cell_objs.append(_build_cell_data(
                    r_v[c_i],
                    base_fmt=r_f[c_i],
                    center=(c_i in (0, 11)),
                    is_num=(c_i == 0)
                ))
            if cols_write_cnt == 15:
                cell_objs.append({"userEnteredValue": {"stringValue": ""}, "userEnteredFormat": {}})
            sorted_row_objects.append({"values": cell_objs})
        if grp_len > 1:
            merge_spans.append((curr_row_0, curr_row_0 + grp_len))
        curr_row_0 += grp_len

    while len(sorted_row_objects) < total_main_slots:
        empty_cells = [{"userEnteredValue": {"stringValue": ""}, "userEnteredFormat": {}} for _ in range(cols_write_cnt)]
        sorted_row_objects.append({"values": empty_cells})

    batch_reqs = [
        {
            "unmergeCells": {
                "range": {
                    "sheetId": wks.id,
                    "startRowIndex": start_data_idx,
                    "endRowIndex": start_data_idx + total_main_slots,
                    "startColumnIndex": 0,
                    "endColumnIndex": 15
                }
            }
        },
        {
            "updateCells": {
                "rows": sorted_row_objects,
                "fields": "userEnteredValue,userEnteredFormat",
                "start": {
                    "sheetId": wks.id,
                    "rowIndex": start_data_idx,
                    "columnIndex": 0
                }
            }
        }
    ]

    for r_start, r_end in merge_spans:
        for col_idx in cols_to_merge:
            batch_reqs.append({
                "mergeCells": {
                    "range": {
                        "sheetId": wks.id,
                        "startRowIndex": r_start,
                        "endRowIndex": r_end,
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1
                    },
                    "mergeType": "MERGE_ALL"
                }
            })

    wks.spreadsheet.batch_update({"requests": batch_reqs})

def move_group_in_sheet(wks, src_start, src_end, dest_index):
    move_req = {
        "moveDimension": {
            "source": {
                "sheetId": wks.id,
                "dimension": "ROWS",
                "startIndex": int(src_start),
                "endIndex": int(src_end)
            },
            "destinationIndex": int(dest_index)
        }
    }
    wks.spreadsheet.batch_update({"requests": [move_req]})
    
    all_rows = wks.get_all_values()
    stt_updates = []
    current_stt = 1
    for r_idx, row in enumerate(all_rows[5:]):
        sheet_r = r_idx + 6
        r_str = "".join([str(x).strip().upper() for x in row])
        if "PHÂN CÔNG TRẢ LỜI" in r_str:
            break
        val_A = str(row[0]).strip() if len(row) > 0 else ""
        if val_A.isdigit():
            stt_updates.append(gspread.Cell(sheet_r, 1, str(current_stt)))
            current_stt += 1
            
    if stt_updates:
        wks.update_cells(stt_updates)

# ================= KẾT NỐI GOOGLE SHEETS AN TOÀN & CÓ BỘ NHỚ DỰ PHÒNG =================
def _create_fresh_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    elif os.path.exists("key.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
    else:
        raise FileNotFoundError("Không tìm thấy cấu hình 'gcp_service_account' trong st.secrets hoặc file 'key.json'.")
    return gspread.authorize(creds)

@st.cache_resource(ttl=1800, show_spinner=False)
def _authorize_gspread_client():
    return _create_fresh_gspread_client()

def get_gspread_client_cached():
    global LAST_GSHEET_ERROR
    try:
        return _authorize_gspread_client()
    except Exception as e:
        LAST_GSHEET_ERROR = f"Lỗi xác thực Service Account: {e}"
        try: _authorize_gspread_client.clear()
        except Exception: pass
        return None

def ket_noi_sheet(sheet_name_or_url):
    global LAST_GSHEET_ERROR
    target = str(sheet_name_or_url).strip()
    for attempt in range(3):
        try:
            client = get_gspread_client_cached() if attempt == 0 else _create_fresh_gspread_client()
            if not client:
                continue
            return client.open_by_url(target) if target.startswith("http") else client.open(target)
        except Exception as e:
            LAST_GSHEET_ERROR = f"{type(e).__name__}: {e}"
            try: _authorize_gspread_client.clear()
            except Exception: pass
            time.sleep(0.5 * (attempt + 1))
    return None

def safe_read_records_with_row(wks, retries=3, delay=0.5):
    global LAST_GSHEET_ERROR
    for attempt in range(retries):
        try:
            values = wks.get_all_values()
            if not values: return pd.DataFrame()
            headers = [str(h).strip() for h in values[0]]
            rows = []
            for sheet_row, raw in enumerate(values[1:], start=2):
                if not any(str(cell).strip() for cell in raw):
                    continue
                row = {headers[i] if i < len(headers) and headers[i] else f"Column_{i+1}": raw[i] if i < len(raw) else "" for i in range(len(headers))}
                row["_sheet_row"] = sheet_row
                rows.append(row)
            return pd.DataFrame(rows)
        except Exception as e:
            LAST_GSHEET_ERROR = f"{type(e).__name__}: {e}"
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
    return pd.DataFrame()

@st.cache_data(ttl=20, show_spinner=False)
def _fetch_vo_truc_so_cached(tab_name):
    sh = ket_noi_sheet(LINK_VO_TRUC_SO)
    if not sh:
        raise RuntimeError("Tam thoi nghen ket noi Vo Truc So")
    try:
        wks = sh.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        return False, pd.DataFrame(columns=CONTENT_HEADER), [], []
        
    data = wks.get_all_values()
    r_roles = (data[1] + [""] * 8)[:8] if len(data) > 1 else [""] * 8
    roster_names = (data[2] + [""] * 8)[:8] if len(data) > 2 else [""] * 8
    
    if len(data) > 5: 
        header_idx = 3
        for idx in range(min(10, len(data))):
            row_upper = [str(x).strip().upper() for x in data[idx]]
            if "STATUS" in row_upper or "NỘI DUNG" in row_upper:
                header_idx = idx
                break
        
        headers = [str(h).strip().upper() for h in data[header_idx]]
        clean_data = []
        
        start_data_idx = header_idx + 2
        if start_data_idx >= len(data): start_data_idx = 5
        
        has_td_in_sheet = ("THẨM ĐỊNH" in headers)
        has_combined_tg = ("THỜI GIAN ĐĂNG BÀI" in headers or "THỜI GIAN ĐĂNG" in headers)
        for row in data[start_data_idx:]:
            r_pad = [str(row[c]).strip() if c < len(row) else "" for c in range(16)]
            if has_td_in_sheet and has_combined_tg:
                clean_row = r_pad[:14]
            elif has_td_in_sheet and not has_combined_tg:
                tg_val = format_thoi_gian_dang(r_pad[11], r_pad[12])
                clean_row = r_pad[:11] + [tg_val, r_pad[13], r_pad[14]]
            else:
                tg_val = format_thoi_gian_dang(r_pad[10], r_pad[11])
                clean_row = r_pad[:10] + ["", tg_val, r_pad[12], r_pad[13]]
            clean_data.append(clean_row)
        df = pd.DataFrame(clean_data, columns=CONTENT_HEADER)
    else:
        df = pd.DataFrame(columns=CONTENT_HEADER)
    res = (True, df, roster_names, r_roles)
    AI_ENGINE["backup_trucso"][tab_name] = res
    return res

def fetch_vo_truc_so(tab_name):
    num_cols = len(CONTENT_HEADER)
    try:
        exists, df, roster_names, r_roles = _fetch_vo_truc_so_cached(tab_name)
    except Exception:
        try: _fetch_vo_truc_so_cached.clear()
        except Exception: pass
        if tab_name in AI_ENGINE["backup_trucso"]:
            exists, df, roster_names, r_roles = AI_ENGINE["backup_trucso"][tab_name]
        else:
            return False, pd.DataFrame(columns=CONTENT_HEADER), [], []

    if not df.empty and list(df.columns) != CONTENT_HEADER:
        for col in CONTENT_HEADER:
            if col not in df.columns:
                df[col] = ""
        df = df[CONTENT_HEADER]

    opt_rows = [op for op in AI_ENGINE.get("optimistic_posts", []) if op.get("tab_name") == tab_name]
    if exists and opt_rows:
        existing_titles = set(df["NỘI DUNG"].astype(str).str.strip().tolist()) if not df.empty else set()
        extra_records = []
        for op in opt_rows:
            if op["title"].strip() not in existing_titles:
                for raw_r in op.get("rows", []):
                    r_list = list(raw_r)
                    if len(r_list) == 15 and num_cols == 14:
                        tg_merged = format_thoi_gian_dang(r_list[11], r_list[12])
                        r_norm = r_list[:11] + [tg_merged, r_list[13], r_list[14]]
                    else:
                        r_norm = (r_list + [""] * num_cols)[:num_cols]
                    extra_records.append(r_norm)
        if extra_records:
            df_extra = pd.DataFrame(extra_records, columns=CONTENT_HEADER)
            df = pd.concat([df, df_extra], ignore_index=True)
    return exists, df, roster_names, r_roles

fetch_vo_truc_so.clear = _fetch_vo_truc_so_cached.clear

def prepare_trucso_context(df_content, list_nv):
    """Tách và chuẩn hóa bảng tin bài chính (`df_context`) & bảng Seeding (`df_seeding`) an toàn 100%, không bao giờ lỗi KeyError"""
    if df_content is None or df_content.empty:
        return pd.DataFrame(), pd.DataFrame()

    split_idx = len(df_content)
    for i, row in df_content.iterrows():
        b_val = str(row.get('NỘI DUNG', '')).strip().upper()
        if "PHÂN CÔNG TRẢ LỜI BÌNH LUẬN" in b_val:
            split_idx = i
            break
        c_val = str(row.get('ĐỊNH DẠNG', '')).strip().upper()
        d_val = str(row.get('NỀN TẢNG', '')).strip().upper()
        if 'LINK' in c_val and 'PHỤ TRÁCH' in d_val:
            split_idx = i
            break

    df_main = df_content.iloc[:split_idx].copy()
    df_seeding = df_content.iloc[split_idx:].copy() if split_idx < len(df_content) else pd.DataFrame()

    if df_main.empty:
        return pd.DataFrame(), df_seeding

    def is_valid_row(row):
        stt = str(row.get('STT', '')).strip()
        nd = str(row.get('NỘI DUNG', '')).strip()
        nt = str(row.get('NỀN TẢNG', '')).strip()
        return any(x.lower() not in ('', 'nan', '<na>', 'none') for x in (stt, nd, nt))

    df_context = df_main[df_main.apply(is_valid_row, axis=1)].copy()
    if df_context.empty:
        return pd.DataFrame(), df_seeding

    for col in CONTENT_HEADER:
        if col not in df_context.columns:
            df_context[col] = ""

    df_context['NỘI DUNG_GROUP'] = df_context['NỘI DUNG'].replace('', pd.NA).ffill().fillna("Chưa có tên")
    df_context = df_context[df_context['NỘI DUNG_GROUP'].astype(str).str.strip() != "Chưa có tên"].copy()
    if df_context.empty:
        return pd.DataFrame(), df_seeding

    df_context['NHÂN SỰ'] = df_context['NHÂN SỰ'].replace('', pd.NA).ffill().fillna("Chưa phân công")
    df_context['NHÂN SỰ_NORM'] = df_context['NHÂN SỰ'].apply(lambda x: normalize_btv_names_strict(x, list_nv))
    df_context['NGUỒN'] = df_context['NGUỒN'].replace('', pd.NA).ffill().fillna("")
    return df_context, df_seeding

@st.cache_data(ttl=900, show_spinner=False)
def _fetch_tai_khoan_cached():
    sh = ket_noi_sheet(SHEET_MAIN)
    if not sh:
        raise RuntimeError(LAST_GSHEET_ERROR or f"Không kết nối được '{SHEET_MAIN}'.")
    wks = sh.worksheet("TaiKhoan")
    df = safe_read_records_with_row(wks)
    if df.empty:
        raise ValueError("Bảng 'TaiKhoan' đang trống hoặc bị nghẽn mạng.")
    AI_ENGINE["backup_users"] = df.copy()
    return df

def load_tai_khoan():
    global LAST_GSHEET_ERROR
    try:
        return _fetch_tai_khoan_cached()
    except Exception as e:
        LAST_GSHEET_ERROR = str(e)
        try: _fetch_tai_khoan_cached.clear()
        except Exception: pass
        if isinstance(AI_ENGINE.get("backup_users"), pd.DataFrame) and not AI_ENGINE["backup_users"].empty:
            return AI_ENGINE["backup_users"]
        return pd.DataFrame()

load_tai_khoan.clear = _fetch_tai_khoan_cached.clear

@st.cache_data(ttl=120, show_spinner=False)
def _fetch_du_lieu_app_cached():
    sh = ket_noi_sheet(SHEET_MAIN)
    if not sh:
        raise RuntimeError(LAST_GSHEET_ERROR or f"Không kết nối được '{SHEET_MAIN}'.")
    df_d = safe_read_records_with_row(sh.worksheet("DuAn"))
    df_c = safe_read_records_with_row(sh.worksheet("CongViec"))
    try: df_cn = safe_read_records_with_row(sh.worksheet("ViecCaNhan"))
    except: df_cn = pd.DataFrame()
    try: df_nk = safe_read_records_with_row(sh.worksheet("NhatKy"))
    except: df_nk = pd.DataFrame()
    res = (df_d, df_c, df_cn, df_nk)
    AI_ENGINE["backup_app_data"] = res
    return res

def load_du_lieu_app():
    try:
        return _fetch_du_lieu_app_cached()
    except Exception:
        try: _fetch_du_lieu_app_cached.clear()
        except Exception: pass
        if AI_ENGINE.get("backup_app_data") is not None:
            return AI_ENGINE["backup_app_data"]
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

load_du_lieu_app.clear = _fetch_du_lieu_app_cached.clear

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
    
    def _fetch_csv(url, kw):
        try:
            sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
            if not sheet_id_match: return kw, pd.DataFrame()
            sheet_id = sheet_id_match.group(1)
            
            gid_match = re.search(r'gid=([0-9]+)', url)
            gid = gid_match.group(1) if gid_match else "0"
            
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            res = requests.get(csv_url, timeout=15)
            if res.status_code == 200:
                res.encoding = 'utf-8' 
                df = pd.read_csv(io.StringIO(res.text), header=None)
                return kw, df
        except Exception: pass
        return kw, pd.DataFrame()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_fetch_csv, url_ldp, "LDP"),
            executor.submit(_fetch_csv, url_btv, "BTV")
        ]
        for f in concurrent.futures.as_completed(futures):
            k, df = f.result()
            results[k] = df
    return results

# ================= THUẬT TOÁN ĐỌC LỊCH TRỰC LĐP (CHUẨN DẢI NGANG 6 THÁNG) =================
def get_ldp_from_df(df, target_date_obj, list_nv):
    if df is None or df.empty:
        return ""
    d_int = target_date_obj.day
    d_str1 = str(d_int)
    d_str2 = f"{d_int:02d}"
    m = target_date_obj.month
    y = target_date_obj.year

    month_pattern = re.compile(rf"tháng\s*0?{m}(?!\d)", re.IGNORECASE)
    any_month_pattern = re.compile(r"tháng\s*0?\d{1,2}", re.IGNORECASE)

    candidate_blocks = []
    for r in reversed(range(len(df))):
        row_series = df.iloc[r]
        month_cols_in_row = []
        for c_idx, val in enumerate(row_series):
            if pd.isna(val):
                continue
            s_val = str(val).strip()
            if any_month_pattern.search(s_val):
                month_cols_in_row.append((c_idx, s_val))
        if not month_cols_in_row:
            continue

        for idx_m, (c_start, s_text) in enumerate(month_cols_in_row):
            if month_pattern.search(s_text):
                years_found = re.findall(r"20\d{2}", s_text)
                year_match = (not years_found) or (str(y) in years_found)
                c_end = month_cols_in_row[idx_m + 1][0] if (idx_m + 1) < len(month_cols_in_row) else len(df.columns)
                candidate_blocks.append((1 if year_match else 0, r, c_start, c_end))

    candidate_blocks.sort(key=lambda x: (x[0], x[1]), reverse=True)

    target_col = -1
    header_row = -1

    for _, r_month, c_start, c_end in candidate_blocks:
        for offset in (1, 2, 0):
            r_day = r_month + offset
            if r_day >= len(df):
                continue
            seen_late_day = False
            for c_idx in range(c_start, min(c_end, len(df.columns))):
                d_val = df.iloc[r_day, c_idx]
                if pd.isna(d_val):
                    continue
                s_val = str(d_val).strip()
                if s_val.endswith(".0"):
                    s_val = s_val[:-2]
                if s_val.isdigit():
                    day_num = int(s_val)
                    if day_num >= 27:
                        seen_late_day = True
                    elif day_num == 1 and seen_late_day and c_idx > c_start + 5:
                        break
                if s_val in (d_str1, d_str2, f"0{d_str1}"):
                    target_col = c_idx
                    header_row = r_day
                    break
            if target_col != -1:
                break
        if target_col != -1:
            break

    if target_col != -1 and header_row != -1:
        for r in range(header_row + 1, min(header_row + 45, len(df))):
            row_sample_str = " ".join([str(df.iloc[r, c]).lower() for c in range(min(15, len(df.columns))) if not pd.isna(df.iloc[r, c])])
            if "tháng " in row_sample_str and ("202" in row_sample_str or "/" in row_sample_str):
                break

            raw_cell = df.iloc[r, target_col]
            if pd.isna(raw_cell):
                continue
            val = _clean_vn_str(raw_cell)
            if not val or val == "nan":
                continue
            if any(x in val for x in ["nghỉ", "off", "công tác", "ốm", "italia", "nhật", "séc"]):
                continue

            if re.search(r"\bsố\b", val) or "trực số" in val or val in ("x", "lđp", "ldp"):
                name = ""
                for c in [1, 0, 2, 3, 4]:
                    if c >= len(df.columns):
                        continue
                    n = str(df.iloc[r, c]).strip()
                    if n and n.lower() != "nan" and not n.replace(".", "").isdigit() and len(n) > 2 and "stt" not in n.lower() and "họ và tên" not in n.lower():
                        name = n
                        break
                if name:
                    matched = match_nv(name, list_nv)
                    if matched:
                        return matched
    return ""

def get_btv_tcsx_from_df(df, target_date_obj, list_nv):
    res_tcsx = ""
    res_btv = []
    if df is None or df.empty: return res_tcsx, res_btv
    d = target_date_obj.day
    m = target_date_obj.month
    y = target_date_obj.year
    target_col = -1
    header_row = -1
    for r in range(len(df)):
        for c in range(len(df.columns)):
            val = str(df.iloc[r, c]).strip().lower()
            if f"{d:02d}/{m:02d}/{y}" in val or f"{d}/{m}/{y}" in val or f"{y}-{m:02d}-{d:02d}" in val:
                target_col = c
                header_row = r
                break
        if target_col != -1: break
        
    if target_col == -1:
        for r in reversed(range(len(df))):
            for c in range(len(df.columns)):
                val = str(df.iloc[r, c]).strip().lower()
                if len(val) < 30:
                    tokens = re.split(r'[\s\n]+', val)
                    if f"{d:02d}/{m:02d}" in tokens or f"{d}/{m}" in tokens:
                        target_col = c
                        header_row = r
                        break
            if target_col != -1: break
            
    if target_col != -1:
        for r in range(header_row + 1, min(header_row + 200, len(df))):
            val = str(df.iloc[r, target_col]).lower().strip()
            if not val or val == 'nan': continue
            
            name = ""
            for c in range(min(5, len(df.columns))):
                n = str(df.iloc[r, c]).strip()
                if n and n.lower() != 'nan' and not n.isdigit() and len(n) > 2 and "stt" not in n.lower() and "tên" not in n.lower():
                    name = n
                    break
            
            if name:
                matched = match_nv(name, list_nv)
                if matched:
                    if "tcsx" in val:
                        res_tcsx = matched
                    elif "trực số" in val or "số" in val or "btv" in val or val == "x":
                        if not any(k in val for k in ["hỗ trợ", "ht", "công tác", "nghỉ", "off"]):
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
            format_cell_range(wks_stats, "A1:I1", CellFormat(textFormat=TextFormat(fontFamily="Times New Roman", bold=True), horizontalAlignment='CENTER'))
        
        row_data = [date_str] + roster
        cell_found = wks_stats.find(date_str)
        if cell_found:
            r = cell_found.row
            cells = [gspread.Cell(r, i+1, val) for i, val in enumerate(row_data)]
            wks_stats.update_cells(cells)
            format_cell_range(wks_stats, f"A{r}:I{r}", CellFormat(textFormat=TextFormat(fontFamily="Times New Roman"), backgroundColor=Color(1, 1, 1)))
        else:
            wks_stats.append_row(row_data)
            last_row = len(wks_stats.get_all_values())
            format_cell_range(wks_stats, f"A{last_row}:I{last_row}", CellFormat(textFormat=TextFormat(fontFamily="Times New Roman"), backgroundColor=Color(1, 1, 1)))
    except Exception: pass

def split_text_link(merged_text):
    if pd.isna(merged_text) or not str(merged_text).strip(): return "", ""
    text = str(merged_text)
    urls = re.findall(r'(https?://[^\s]+|(?:drive|docs|youtube)\.google\.com/[^\s]+|youtu\.be/[^\s]+)', text)
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
    
    link_duyet_vals = group_df['LINK DUYỆT'].replace('', pd.NA).dropna().astype(str).tolist()
    raw_link_duyet = "".join(link_duyet_vals)
    has_link = len(raw_link_duyet) > 5
    
    first_row = group_df.iloc[0]
    status = str(first_row.get('STATUS', '')).lower()
    
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
    title = re.sub(r'\s*\b\d{1,2}\'?m?\s*$', '', title) 
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

# ================= HÀM BÓC TÁCH & HIỂN THỊ META PLANNER TIMELINE (30 PHÚT) =================
def _parse_post_time(val_str):
    if pd.isna(val_str): return None
    s = str(val_str).strip().lower()
    if not s or s in ("nan", "<na>", "none"): return None
    s_no_date = re.sub(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", " ", s)
    s_no_date = re.sub(r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b", " ", s_no_date)
    s_no_date = s_no_date.replace("h", ":").replace("g", ":")
    m = re.search(r"\b(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?\b", s_no_date)
    if not m:
        m4 = re.search(r"\b(\d{2})(\d{2})\b", s_no_date)
        if m4:
            hh, mm = int(m4.group(1)), int(m4.group(2))
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                return dt_time(hh, mm, 0)
        return None
    try:
        hh = int(m.group(1))
        mm = int(m.group(2))
        ss = int(m.group(3)) if m.group(3) is not None else 0
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return dt_time(hh, mm, ss)
    except Exception:
        return None
    return None

def _parse_post_date(val_str, fallback_date):
    if pd.isna(val_str): return fallback_date
    s = str(val_str).strip()
    if not s or s.lower() in ("nan", "<na>", "none"): return fallback_date
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", s)
    if m:
        try:
            d_i = int(m.group(1))
            m_i = int(m.group(2))
            y_i = int(m.group(3)) if m.group(3) else fallback_date.year
            if y_i < 100: y_i += 2000
            return date(y_i, m_i, d_i)
        except Exception:
            pass
    return fallback_date

def _canonical_platform(p_str):
    s = str(p_str or "").strip()
    if not s: return ""
    s_low = s.lower()
    for std_p in OPTS_NEN_TANG:
        if std_p.lower() == s_low:
            return std_p
    if "face" in s_low or s_low == "fb": return "Facebook"
    if "you" in s_low or s_low == "yt": return "Youtube"
    if "linked" in s_low: return "LinkedIn"
    if "insta" in s_low or s_low == "ig": return "Instagram"
    if "tik" in s_low: return "TikTok"
    if "thread" in s_low: return "Threads"
    if "web" in s_low: return "Web"
    if "app" in s_low: return "App"
    return s

def extract_posts_from_tab(tab_name, list_nv):
    try:
        fallback_d = datetime.strptime(tab_name, "%d/%m/%Y").date()
    except Exception:
        fallback_d = get_vn_today()
    exists, df_content, _, _ = fetch_vo_truc_so(tab_name)
    if not exists or df_content.empty:
        return []

    df_main, _ = prepare_trucso_context(df_content, list_nv)
    if df_main.empty:
        return []

    df_main['NHÂN SỰ_FILL'] = df_main['NHÂN SỰ'].replace('', pd.NA).ffill().fillna("Chưa phân công")
    df_main['ĐỊNH DẠNG_FILL'] = df_main['ĐỊNH DẠNG'].replace('', pd.NA).ffill().fillna("")

    records = []
    for prod, grp in df_main.groupby('NỘI DUNG_GROUP', sort=False):
        smart_st = get_smart_status(grp)
        first_tg_raw = ""
        for _, r0 in grp.iterrows():
            if not first_tg_raw and str(r0.get('THỜI GIAN ĐĂNG BÀI', '')).strip():
                first_tg_raw = str(r0.get('THỜI GIAN ĐĂNG BÀI', '')).strip()

        row_indices = list(grp.index)
        for idx_r, r in grp.iterrows():
            plat = _canonical_platform(r.get('NỀN TẢNG', ''))
            if not plat:
                continue
            raw_tg = str(r.get('THỜI GIAN ĐĂNG BÀI', '')).strip() or first_tg_raw
            t_obj = _parse_post_time(raw_tg)
            d_obj = _parse_post_date(raw_tg, fallback_d)
            st_row = str(r.get('STATUS', '')).strip() or smart_st
            btv_norm = normalize_btv_names_strict(r.get('NHÂN SỰ_FILL', ''), list_nv)
            records.append({
                "tab_source": tab_name,
                "row_idx": idx_r,
                "group_indices": row_indices,
                "title": str(prod).strip(),
                "format": str(r.get('ĐỊNH DẠNG_FILL', '')).strip(),
                "platform": plat,
                "status": st_row,
                "smart_status": smart_st,
                "btv": btv_norm,
                "post_date": d_obj,
                "post_date_str": d_obj.strftime("%d/%m/%Y"),
                "post_time": t_obj,
                "post_time_str": t_obj.strftime("%H:%M") if t_obj else "",
            })
    return records

def collect_planner_posts(target_dates, list_nv, extra_source_tabs=None):
    tabs_to_scan = []
    for d in target_dates:
        t_str = d.strftime("%d/%m/%Y")
        if t_str not in tabs_to_scan:
            tabs_to_scan.append(t_str)
    if extra_source_tabs:
        for t_str in extra_source_tabs:
            if t_str and t_str not in tabs_to_scan:
                tabs_to_scan.append(t_str)
    for cached_tab in list(AI_ENGINE.get("backup_trucso", {}).keys()):
        if cached_tab not in tabs_to_scan:
            tabs_to_scan.append(cached_tab)

    all_posts = []
    seen_keys = set()
    target_set = set(target_dates)
    for t_name in tabs_to_scan:
        for item in extract_posts_from_tab(t_name, list_nv):
            if item["post_date"] in target_set:
                uniq_k = (item["tab_source"], item["row_idx"], item["platform"], item["title"])
                if uniq_k not in seen_keys:
                    seen_keys.add(uniq_k)
                    all_posts.append(item)
    return all_posts

@st.fragment(run_every="30s")
def render_meta_planner_section(default_date, current_trucso_tab, list_nv, key_prefix="main_planner"):
    c_hdr_plan, c_btn_plan = st.columns([4.2, 0.8])
    with c_hdr_plan:
        st.markdown("#### 🗓️ LỊCH BÀI ĐĂNG")
        st.caption("Giúp TCSX và BTV kiểm soát lịch đăng trên mọi nền tảng, tự động phát hiện các bài đăng trùng hoặc sát giờ nhau (< 30 phút) để điều phối hợp lý. (Tự động làm mới mỗi 30s)")
    with c_btn_plan:
        if st.button("🔄 Làm mới", key=f"{key_prefix}_btn_refresh", use_container_width=True):
            clear_trucso_cache()

    c_ctrl1, c_ctrl2, c_ctrl3 = st.columns([1.1, 1.5, 2.4])
    with c_ctrl1:
        planner_date = st.date_input(
            "📅 Ngày xem lịch đăng:",
            value=default_date,
            format="DD/MM/YYYY",
            key=f"{key_prefix}_date"
        )
        
    with c_ctrl2:
        view_type = st.radio(
            "Chế độ hiển thị:",
            ["📐 Timeline 30 Phút (Đa nền tảng)", "📅 Lịch Tuần (Kiểu Meta Planner)"],
            horizontal=False,
            key=f"{key_prefix}_view"
        )
    with c_ctrl3:
        opt_selected = st.multiselect(
            "➕ Tùy chọn hiện thêm các nền tảng khác:",
            options=OPTIONAL_PLATFORMS,
            default=["TikTok", "Threads", "Web", "App"],
            key=f"{key_prefix}_opt_plats"
        )

    active_platforms = MANDATORY_PLATFORMS + [p for p in OPTIONAL_PLATFORMS if p in opt_selected]

    if "Timeline 30 Phút" in view_type:
        posts_day = collect_planner_posts(
            [planner_date],
            list_nv,
            extra_source_tabs=[current_trucso_tab, get_vn_today().strftime("%d/%m/%Y")]
        )
        scheduled_posts = [p for p in posts_day if p["post_time"] is not None and p["platform"] in active_platforms]
        unscheduled_posts = [p for p in posts_day if p["post_time"] is None and p["platform"] in active_platforms]

        same_plat_conflicts = set()
        cross_plat_warnings = set()
        conflict_messages = []

        for plat in active_platforms:
            p_list = sorted(
                [p for p in scheduled_posts if p["platform"] == plat],
                key=lambda x: (x["post_time"].hour * 60 + x["post_time"].minute)
            )
            for idx_a in range(len(p_list)):
                for idx_b in range(idx_a + 1, len(p_list)):
                    pa, pb = p_list[idx_a], p_list[idx_b]
                    min_a = pa["post_time"].hour * 60 + pa["post_time"].minute
                    min_b = pb["post_time"].hour * 60 + pb["post_time"].minute
                    diff = abs(min_b - min_a)
                    if diff < 30:
                        same_plat_conflicts.add((pa["tab_source"], pa["row_idx"]))
                        same_plat_conflicts.add((pb["tab_source"], pb["row_idx"]))
                        conflict_messages.append(
                            f"🚨 **{plat} ({pa['post_time_str']} & {pb['post_time_str']})**: Bài *\"{pa['title'][:45]}\"* và *\"{pb['title'][:45]}\"* cách nhau **{diff} phút** (< 30 phút)!"
                        )

        all_sorted = sorted(
            scheduled_posts,
            key=lambda x: (x["post_time"].hour * 60 + x["post_time"].minute)
        )
        for idx_a in range(len(all_sorted)):
            for idx_b in range(idx_a + 1, len(all_sorted)):
                pa, pb = all_sorted[idx_a], all_sorted[idx_b]
                if pa["platform"] == pb["platform"]:
                    continue
                if pa["title"] == pb["title"]:
                    continue
                min_a = pa["post_time"].hour * 60 + pa["post_time"].minute
                min_b = pb["post_time"].hour * 60 + pb["post_time"].minute
                diff = abs(min_b - min_a)
                if diff < 30:
                    cross_plat_warnings.add((pa["tab_source"], pa["row_idx"]))
                    cross_plat_warnings.add((pb["tab_source"], pb["row_idx"]))

        k1, k2, k3, k4 = st.columns([1, 1, 1, 1.5])
        k1.metric("📌 Lượt đăng đã xếp giờ", len(scheduled_posts))
        k2.metric("⏳ Chưa xếp giờ đăng", len(unscheduled_posts))
        k3.metric("🚨 Vi phạm giãn cách <30p", len(conflict_messages))
        with k4:
            slot_filter = st.selectbox(
                "🔍 Khung giờ hiển thị trên bảng cuộn:",
                ["Toàn bộ 24 giờ (00:00 - 23:30)", "Khung giờ hoạt động (06:00 - 23:30)", "Chỉ hiện các khung giờ đã có bài"],
                index=0,
                key=f"{key_prefix}_slot_filter"
            )

        if conflict_messages:
            with st.container(border=True):
                st.error("⚠️ **PHÁT HIỆN BÀI ĐĂNG TRÙNG HOẶC QUÁ SÁT GIỜ (< 30 PHÚT):**")
                for msg in conflict_messages[:8]:
                    st.markdown(f"- {msg}")

        all_slots = []
        for h in range(24):
            for m_slot in (0, 30):
                all_slots.append((h, m_slot, h * 60 + m_slot, f"{h:02d}:{m_slot:02d}"))

        slot_map = {s[3]: {p: [] for p in active_platforms} for s in all_slots}
        occupied_minutes_by_plat = {p: [] for p in active_platforms}

        for p_item in scheduled_posts:
            total_m = p_item["post_time"].hour * 60 + p_item["post_time"].minute
            slot_h = p_item["post_time"].hour
            slot_m = 30 if p_item["post_time"].minute >= 30 else 0
            slot_label = f"{slot_h:02d}:{slot_m:02d}"
            if slot_label in slot_map and p_item["platform"] in slot_map[slot_label]:
                slot_map[slot_label][p_item["platform"]].append(p_item)
                occupied_minutes_by_plat[p_item["platform"]].append((total_m, p_item["post_time_str"], p_item["title"]))

        visible_slots = []
        for h, m_slot, total_m, s_label in all_slots:
            has_any_post = any(len(slot_map[s_label][p]) > 0 for p in active_platforms)
            if slot_filter == "Chỉ hiện các khung giờ đã có bài":
                if has_any_post:
                    visible_slots.append((h, m_slot, total_m, s_label, has_any_post))
            elif slot_filter == "Khung giờ hoạt động (06:00 - 23:30)":
                if h >= 6 or has_any_post:
                    visible_slots.append((h, m_slot, total_m, s_label, has_any_post))
            else:
                visible_slots.append((h, m_slot, total_m, s_label, has_any_post))

        if not visible_slots:
            st.info(f"📭 Chưa có bài viết nào được đặt Giờ đăng trong ngày {planner_date.strftime('%d/%m/%Y')}.")
        else:
            html_parts = ['<div class="meta-planner-wrap"><table class="meta-table"><thead><tr>']
            html_parts.append('<th class="time-col-hdr">⏰ KHUNG GIỜ<br><span style="font-size:10.5px;font-weight:500;color:#65676b;">(Block 30p)</span></th>')
            for plat in active_platforms:
                p_label, p_color = PLATFORM_BADGE_STYLE.get(plat, (plat, "#1877f2"))
                plat_count = sum(len(slot_map[s[3]][plat]) for s in all_slots)
                mandatory_tag = ' <span style="font-size:10px;color:#059669;">●</span>' if plat in MANDATORY_PLATFORMS else ''
                html_parts.append(
                    f'<th><span style="color:{p_color};font-size:13.5px;">{p_label}</span>{mandatory_tag}'
                    f'<div style="font-size:11px;font-weight:500;color:#65676b;margin-top:2px;">{plat_count} bài đã xếp giờ</div></th>'
                )
            html_parts.append('</tr></thead><tbody>')

            for h, m_slot, slot_start_min, s_label, has_any_post in visible_slots:
                row_cls = "slot-busy" if has_any_post else ""
                end_m = slot_start_min + 29
                end_label = f"{end_m // 60:02d}:{end_m % 60:02d}"
                html_parts.append(
                    f'<tr class="{row_cls}"><td class="time-cell">{s_label}<div style="font-size:10px;font-weight:400;color:#8d949e;">đến {end_label}</div></td>'
                )
                for plat in active_platforms:
                    cell_posts = slot_map[s_label][plat]
                    html_parts.append('<td>')
                    if cell_posts:
                        for cp in sorted(cell_posts, key=lambda x: x["post_time"]):
                            is_same_conf = (cp["tab_source"], cp["row_idx"]) in same_plat_conflicts
                            is_cross_warn = (cp["tab_source"], cp["row_idx"]) in cross_plat_warnings
                            card_cls = "meta-card conflict" if is_same_conf else ("meta-card cross-warn" if is_cross_warn else "meta-card")
                            badge_cls = "meta-time-badge conflict-badge" if is_same_conf else "meta-time-badge"
                            _, p_color = PLATFORM_BADGE_STYLE.get(plat, (plat, "#1877f2"))
                            style_border = "" if (is_same_conf or is_cross_warn) else f'style="border-left-color:{p_color};"'
                            safe_title = html_lib.escape(cp["title"])
                            safe_btv = html_lib.escape(get_short_name(cp["btv"]))
                            safe_fmt = html_lib.escape(cp["format"] or "Tin bài")
                            safe_st = html_lib.escape(cp["smart_status"])
                            warn_txt = ' <span style="color:#dc3545;font-weight:700;">⚠️ Sát giờ <30p</span>' if is_same_conf else (
                                ' <span style="color:#d97706;font-weight:700;">⚡ Sát giờ nền tảng khác</span>' if is_cross_warn else ''
                            )
                            html_parts.append(
                                f'<div class="{card_cls}" {style_border}>'
                                f'<div class="meta-card-top"><span class="{badge_cls}">🕒 {cp["post_time_str"]}</span><span>{safe_st}</span></div>'
                                f'<div class="meta-card-title">{safe_title}</div>'
                                f'<div class="meta-card-sub"><span>🎬 {safe_fmt}</span><span>👤 {safe_btv}{warn_txt}</span></div>'
                                f'</div>'
                            )
                    else:
                        near_other = None
                        for occ_min, occ_time_str, occ_title in occupied_minutes_by_plat[plat]:
                            if abs(slot_start_min - occ_min) < 30:
                                near_other = occ_time_str
                                break
                        if near_other:
                            html_parts.append(f'<div class="slot-cooldown-pill">⏳ Giãn cách 30p (Có bài lúc {near_other})</div>')
                        else:
                            html_parts.append('<div class="slot-empty-pill">+ Trống (Có thể xếp bài)</div>')
                    html_parts.append('</td>')
                html_parts.append('</tr>')

            html_parts.append('</tbody></table></div>')
            st.markdown("".join(html_parts), unsafe_allow_html=True)

        if unscheduled_posts:
            with st.expander(f"📌 Có {len(unscheduled_posts)} lượt nền tảng trong ngày {planner_date.strftime('%d/%m/%Y')} CHƯA ĐẶT GIỜ ĐĂNG (Bấm để xem)", expanded=False):
                df_un = pd.DataFrame([
                    {
                        "Tiêu đề bài": p["title"],
                        "Nền tảng": p["platform"],
                        "Định dạng": p["format"],
                        "BTV": p["btv"],
                        "Tiến độ": p["smart_status"],
                        "Vỏ trực số gốc": p["tab_source"]
                    }
                    for p in unscheduled_posts
                ])
                st.dataframe(df_un, use_container_width=True, hide_index=True)

        if posts_day:
            with st.expander("⚡ ĐỔI NHANH GIỜ ĐĂNG / NGÀY ĐĂNG TRỰC TIẾP TỪ BẢNG KẾ HOẠCH", expanded=False):
                with st.form(f"{key_prefix}_quick_sched_form"):
                    options_map = {}
                    for p in posts_day:
                        t_disp = p["post_time_str"] if p["post_time_str"] else "Chưa xếp giờ"
                        lbl = f"[{p['platform']} | {t_disp} - {p['post_date_str']}] {p['title']} (Vỏ {p['tab_source']})"
                        options_map[lbl] = p
                    sel_post_lbl = st.selectbox("Chọn bài viết / nền tảng cần xếp hoặc đổi lịch:", list(options_map.keys()))
                    q_c1, q_c2, q_c3 = st.columns([1, 1, 1.2])
                    new_q_time = q_c1.time_input("⏰ Giờ đăng mới:", value=dt_time(9, 0), step=timedelta(minutes=15), key=f"{key_prefix}_qt")
                    new_q_date = q_c2.date_input("📅 Ngày đăng mới:", value=planner_date, format="DD/MM/YYYY", key=f"{key_prefix}_qd")
                    apply_scope = q_c3.radio(
                        "Phạm vi áp dụng:",
                        ["Chỉ nền tảng đang chọn", "Tất cả nền tảng của bài này"],
                        key=f"{key_prefix}_qscope"
                    )
                    if st.form_submit_button("💾 CẬP NHẬT LỊCH ĐĂNG NGAY", type="primary"):
                        chosen_p = options_map[sel_post_lbl]
                        target_rows = [chosen_p["row_idx"]] if apply_scope == "Chỉ nền tảng đang chọn" else chosen_p["group_indices"]
                        t_str_formatted = new_q_time.strftime("%H:%M:%S") if new_q_time else ""
                        d_str_formatted = new_q_date.strftime("%d/%m/%Y")
                        AI_ENGINE["executor"].submit(bg_quick_reschedule, chosen_p["tab_source"], target_rows, t_str_formatted, d_str_formatted)
                        st.success(f"✅ Đã xếp lịch '{chosen_p['title']}' vào lúc {new_q_time.strftime('%H:%M')} ngày {d_str_formatted}!")
                        time.sleep(0.4)
                        clear_cache_and_rerun()

    else:
        monday = planner_date - timedelta(days=planner_date.weekday())
        week_dates = [monday + timedelta(days=i) for i in range(7)]
        day_names_vn = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]

        st.markdown(f"**📅 Tuần từ {week_dates[0].strftime('%d/%m/%Y')} đến {week_dates[-1].strftime('%d/%m/%Y')}**")
        week_posts = collect_planner_posts(
            week_dates,
            list_nv,
            extra_source_tabs=[current_trucso_tab, get_vn_today().strftime("%d/%m/%Y")]
        )
        week_posts = [p for p in week_posts if p["platform"] in active_platforms]

        html_w = ['<div class="meta-planner-wrap"><table class="meta-table"><thead><tr>']
        for i_d, d_obj in enumerate(week_dates):
            is_today_col = (d_obj == planner_date)
            hdr_bg = 'style="background:#e7f3ff;color:#1877f2;"' if is_today_col else ''
            cnt_d = sum(1 for p in week_posts if p["post_date"] == d_obj)
            html_w.append(
                f'<th {hdr_bg}>{day_names_vn[i_d]} {d_obj.strftime("%d/%m")}'
                f'<div style="font-size:11px;font-weight:500;color:#65676b;">{cnt_d} lượt đăng</div></th>'
            )
        html_w.append('</tr></thead><tbody><tr>')

        for d_obj in week_dates:
            day_items = [p for p in week_posts if p["post_date"] == d_obj]
            day_items.sort(key=lambda x: (x["post_time"] is None, x["post_time"] or dt_time(23, 59)))
            html_w.append('<td style="min-width:200px;background:#f7f8fa;">')
            if not day_items:
                html_w.append('<div class="slot-empty-pill">Chưa có lịch bài</div>')
            else:
                for cp in day_items:
                    p_label, p_color = PLATFORM_BADGE_STYLE.get(cp["platform"], (cp["platform"], "#1877f2"))
                    t_disp = cp["post_time_str"] if cp["post_time_str"] else "Chưa chốt giờ"
                    safe_title = html_lib.escape(cp["title"])
                    safe_btv = html_lib.escape(get_short_name(cp["btv"]))
                    html_w.append(
                        f'<div class="meta-card" style="border-left-color:{p_color};">'
                        f'<div class="meta-card-top"><span class="meta-time-badge">🕒 {t_disp}</span>'
                        f'<span style="color:{p_color};">{p_label}</span></div>'
                        f'<div class="meta-card-title">{safe_title}</div>'
                        f'<div class="meta-card-sub"><span>{html_lib.escape(cp["smart_status"])}</span><span>👤 {safe_btv}</span></div>'
                        f'</div>'
                    )
            html_w.append('</td>')
        html_w.append('</tr></tbody></table></div>')
        st.markdown("".join(html_w), unsafe_allow_html=True)

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
        "repeatCell": {
            "range": {"sheetId": wks.id, "startRowIndex": 0, "endRowIndex": 1000, "startColumnIndex": 0, "endColumnIndex": 20},
            "cell": {"userEnteredFormat": {"textFormat": {"fontFamily": "Times New Roman"}}},
            "fields": "userEnteredFormat.textFormat.fontFamily"
        }
    })
    
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
        "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": {"red": 1.0, "green": 0.0, "blue": 0.0}, "fontFamily": "Times New Roman"},
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
        "textFormat": {"bold": True, "fontFamily": "Times New Roman"},
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
        "textFormat": {"bold": True, "fontFamily": "Times New Roman"},
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
    
    col_widths = [60, 250, 115, 90, 90, 75, 75, 120, 140, 140, 140, 115, 110, 380]
    for c_idx, w in enumerate(col_widths):
        requests.append({
            "updateDimensionProperties": {
                "range": {"sheetId": wks.id, "dimension": "COLUMNS", "startIndex": c_idx, "endIndex": c_idx + 1},
                "properties": {"pixelSize": w}, "fields": "pixelSize"
            }
        })

    btv_colors = [
        {"red": 0.85, "green": 0.93, "blue": 0.98},
        {"red": 0.88, "green": 0.95, "blue": 0.88},
        {"red": 1.0, "green": 0.95, "blue": 0.8},
        {"red": 0.95, "green": 0.88, "blue": 0.95}
    ]
    btv_indices = [2, 5, 6, 7] 
    
    for i, col_idx in enumerate(btv_indices):
        requests.append({
            "repeatCell": {
                "range": {"sheetId": wks.id, "startRowIndex": 1, "endRowIndex": 3, "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
                "cell": {"userEnteredFormat": {"backgroundColor": btv_colors[i]}},
                "fields": "userEnteredFormat.backgroundColor"
            }
        })
        
        btv_name = roster_vals[col_idx]
        if btv_name and btv_name != "--":
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{"sheetId": wks.id, "startRowIndex": 5, "endRowIndex": 1000, "startColumnIndex": 1, "endColumnIndex": 2}],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [{"userEnteredValue": f'=SEARCH("{btv_name}", $H6)'}]
                            },
                            "format": {"backgroundColor": btv_colors[i]}
                        }
                    },
                    "index": 0
                }
            })

    chip_colors = {
        "Facebook": (0.09, 0.47, 0.95, 1, 1, 1),
        "Youtube": (1.0, 0.0, 0.0, 1, 1, 1),
        "YouTube": (1.0, 0.0, 0.0, 1, 1, 1),
        "TikTok": (0.88, 0.88, 0.88, 0, 0, 0),
        "Threads": (0.0, 0.0, 0.0, 1, 1, 1),
        "LinkedIn": (0.04, 0.4, 0.76, 1, 1, 1),
        "Instagram": (0.88, 0.19, 0.58, 1, 1, 1),
        "Web": (1.0, 0.82, 0.2, 0, 0, 0),
        "App": (0.96, 0.5, 0.1, 1, 1, 1),
        "Gửi duyệt TCSX": (0.16, 0.43, 0.75, 1, 1, 1),
        "Gửi duyệt LĐP": (0.42, 0.22, 0.6, 1, 1, 1),
        "Scheduled": (0.98, 0.68, 0.0, 0, 0, 0),
        "Đã đăng": (0.06, 0.62, 0.35, 1, 1, 1),
        "Posted": (0.06, 0.62, 0.35, 1, 1, 1),
        "Đã duyệt/Chờ đăng": (0.2, 0.7, 0.4, 1, 1, 1),
        "Chờ xử lý": (0.9, 0.9, 0.9, 0, 0, 0),
        "Đang biên tập": (0.9, 0.9, 0.9, 0, 0, 0),
        "Cảnh báo rủi ro": (0.9, 0.16, 0.16, 1, 1, 1),
        "Yêu cầu sửa (TCSX)": (0.9, 0.4, 0.4, 1, 1, 1),
        "Yêu cầu sửa (LĐP)": (0.9, 0.4, 0.4, 1, 1, 1),
        "Hủy": (0.4, 0.4, 0.4, 1, 1, 1),
    }

    for val, (br, bg, bb, tr, tg, tb) in chip_colors.items():
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [
                        {"sheetId": wks.id, "startRowIndex": 5, "endRowIndex": 1000, "startColumnIndex": 3, "endColumnIndex": 5}
                    ],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_EQ",
                            "values": [{"userEnteredValue": val}]
                        },
                        "format": {
                            "backgroundColor": {"red": br, "green": bg, "blue": bb},
                            "textFormat": {"foregroundColor": {"red": tr, "green": tg, "blue": tb}, "bold": True}
                        }
                    }
                },
                "index": 0
            }
        })
        
    try:
        wks.spreadsheet.batch_update({"requests": requests})
    except Exception: pass
    
    try:
        validation_dinh_dang = DataValidationRule(condition=BooleanCondition('ONE_OF_LIST', OPTS_DINH_DANG), showCustomUi=True)
        validation_nen_tang = DataValidationRule(condition=BooleanCondition('ONE_OF_LIST', OPTS_NEN_TANG), showCustomUi=True)
        validation_status = DataValidationRule(condition=BooleanCondition('ONE_OF_LIST', OPTS_STATUS_TRUCSO), showCustomUi=True)
        
        set_data_validation_for_cell_range(wks, 'C6:C35', validation_dinh_dang)
        set_data_validation_for_cell_range(wks, 'D6:D35', validation_nen_tang)
        set_data_validation_for_cell_range(wks, 'E6:E35', validation_status)
    except Exception: pass

# ================= 2. AUTH BẢO MẬT (COOKIE + PHIÊN 30 PHÚT, KHÔNG LỘ LINK URL) =================
SESSION_TTL_SECONDS = 1800  # 30 phút (1800 giây)
if "sessions" not in AI_ENGINE:
    AI_ENGINE["sessions"] = {}

def _get_client_fingerprint():
    try:
        ua = str(st.context.headers.get("User-Agent", ""))
        return hashlib.sha256(ua.encode("utf-8")).hexdigest()[:24]
    except Exception:
        return "default_ua"

def _sync_browser_cookie(sid_val: str, max_age: int):
    components.html(
        f"""
        <script>
        (function() {{
            var cookieStr = "vntd_sid={sid_val}; path=/; max-age={max_age}; SameSite=Lax";
            try {{ document.cookie = cookieStr; }} catch(e) {{}}
            try {{ window.parent.document.cookie = cookieStr; }} catch(e) {{}}
        }})();
        </script>
        """,
        height=0,
    )

try:
    if "u" in st.query_params or "t" in st.query_params:
        st.query_params.clear()
except Exception:
    pass

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['user_info'] = {}
    st.session_state['username'] = ''
    st.session_state['sid'] = ''

if not st.session_state['authenticated']:
    try:
        cookie_sid = str(st.context.cookies.get("vntd_sid", "")).strip()
        if cookie_sid and cookie_sid in AI_ENGINE["sessions"]:
            sess = AI_ENGINE["sessions"][cookie_sid]
            now_ts = time.time()
            if sess.get("expires_at", 0) > now_ts and sess.get("ua_hash") == _get_client_fingerprint():
                sess["expires_at"] = now_ts + SESSION_TTL_SECONDS
                st.session_state['authenticated'] = True
                st.session_state['user_info'] = sess['user_info']
                st.session_state['username'] = sess['username']
                st.session_state['sid'] = cookie_sid
            else:
                AI_ENGINE["sessions"].pop(cookie_sid, None)
    except Exception:
        pass

if not st.session_state['authenticated']:
    if st.session_state.pop('_clear_cookie', False):
        _sync_browser_cookie("", 0)
    st.markdown("## 🔐 CỔNG ĐĂNG NHẬP")
    with st.form("login"):
        user = st.text_input("Tên đăng nhập")
        pwd = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("ĐĂNG NHẬP"):
            df_users = load_tai_khoan()
            if df_users.empty:
                try: _fetch_tai_khoan_cached.clear()
                except Exception: pass
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
                    clean_u = str(user).strip()
                    safe_user = authenticated_row.to_dict()
                    safe_user.pop('MatKhau', None)
                    safe_user.pop('_sheet_row', None)

                    new_sid = secrets.token_urlsafe(32)
                    AI_ENGINE["sessions"][new_sid] = {
                        "username": clean_u,
                        "user_info": safe_user,
                        "expires_at": time.time() + SESSION_TTL_SECONDS,
                        "ua_hash": _get_client_fingerprint()
                    }
                    st.session_state['authenticated'] = True
                    st.session_state['user_info'] = safe_user
                    st.session_state['username'] = clean_u
                    st.session_state['sid'] = new_sid
                    ghi_nhat_ky(authenticated_row['HoTen'], "Đăng nhập", "Success")
                    st.rerun()
                else:
                    st.error("Sai thông tin đăng nhập!")
            else:
                st.error(f"Lỗi kết nối CSDL Tài khoản ({LAST_GSHEET_ERROR}). Vui lòng đợi 5 giây rồi bấm Đăng nhập lại.")
else:
    curr_sid = st.session_state.get('sid', '')
    if curr_sid and curr_sid in AI_ENGINE["sessions"]:
        AI_ENGINE["sessions"][curr_sid]["expires_at"] = time.time() + SESSION_TTL_SECONDS

    df_users = load_tai_khoan()
    list_nv = df_users['HoTen'].tolist() if not df_users.empty else []
    u_info = st.session_state['user_info']; curr_name = u_info.get('HoTen', ''); curr_username = str(st.session_state.get('username', '')); role = u_info.get('VaiTro', 'NhanVien')
    
    if role == 'LanhDao':
        df_duan, df_cv, df_cn, df_log = load_du_lieu_app()
    else:
        df_duan, df_cv, df_cn, df_log = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    list_duan = df_duan['TenDuAn'].tolist() if not df_duan.empty else []
    
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
            if curr_sid:
                AI_ENGINE["sessions"].pop(curr_sid, None)
            st.session_state['authenticated'] = False
            st.session_state['user_info'] = {}
            st.session_state['username'] = ''
            st.session_state['sid'] = ''
            st.session_state['_clear_cookie'] = True
            try: st.query_params.clear()
            except Exception: pass
            st.rerun()

        if curr_sid:
            _sync_browser_cookie(curr_sid, SESSION_TTL_SECONDS)

    st.title("🏢 PHÒNG NỘI DUNG SỐ & TRUYỀN THÔNG")
    
    list_tabs = ["📝 VỎ TRỰC SỐ", "🗓️ LỊCH BÀI ĐĂNG", "📺 TẠO LPS"]
    if role == 'LanhDao': 
        list_tabs.extend(["✅ CHECKLIST", "📋 CÔNG VIỆC", "🗂️ DỰ ÁN", "📅 LỊCH", "📧 EMAIL", "📊 DASHBOARD", "📜 NHẬT KÝ"])
        
    tabs = st.tabs(list_tabs)
    tab_dict = {name: tab for name, tab in zip(list_tabs, tabs)}

    # ================= TAB 0: VỎ TRỰC SỐ =================
    if "📝 VỎ TRỰC SỐ" in tab_dict:
        with tab_dict["📝 VỎ TRỰC SỐ"]:
            
            # --- KHỐI HƯỚNG DẪN SỬ DỤNG (TUTORIAL WIZARD) ---
            if 'show_tutorial' not in st.session_state:
                st.session_state['show_tutorial'] = False
            if 'tut_step' not in st.session_state:
                st.session_state['tut_step'] = 1

            def next_step(): st.session_state['tut_step'] += 1
            def prev_step(): st.session_state['tut_step'] -= 1
            def close_tut(): st.session_state['show_tutorial'] = False
            def open_tut(): 
                st.session_state['show_tutorial'] = True
                st.session_state['tut_step'] = 1
            
            c_nav1, c_nav2 = st.columns([1, 4])
            with c_nav1: target_date = st.date_input("📅 CHỌN NGÀY LÀM VIỆC:", value=get_vn_time().date(), format="DD/MM/YYYY")
            
            tab_name_current = target_date.strftime("%d/%m/%Y") 
            date_str_display = target_date.strftime("%d/%m/%Y")
            date_key = date_str_display.replace('/', '')
            
            with c_nav2: 
                c_title, c_reload, c_btn = st.columns([2.6, 0.7, 0.9])
                c_title.header(f"📝 VỎ TRỰC SỐ NGÀY: {date_str_display}")
                if c_reload.button("🔄 Làm mới", use_container_width=True):
                    clear_trucso_cache()
                    st.rerun()
                c_btn.button("💡 Hướng dẫn sử dụng", on_click=open_tut, type="primary", use_container_width=True)

            if st.session_state['show_tutorial']:
                st.markdown("---")
                with st.container(border=True):
                    step = st.session_state['tut_step']
                    
                    if step == 1:
                        st.subheader("🎓 BƯỚC 1: KHỞI TẠO VỎ TRỰC SỐ")
                        st.info("**Tại sao phải tạo Vỏ?** Để tránh phải copy/paste thủ công trên Google Sheet mỗi ngày. Thay vì dùng Excel, Web sẽ tự động hóa mọi thứ cho bạn.")
                        st.markdown("""
                        - **Cách làm:** Mỗi sáng, bạn chỉ cần mở web, chọn ngày ở góc trái.
                        - Hệ thống sẽ **tự động đọc Lịch LĐP và Lịch TCSX** để điền sẵn tên các nhân sự trực trong ngày.
                        - Bạn chỉ việc bấm nút **🚀 TẠO VỎ TRỰC SỐ MỚI**. Form trực số chuẩn định dạng sẽ xuất hiện ngay lập tức.
                        """)
                    elif step == 2:
                        st.subheader("🎓 BƯỚC 2: THÊM BÀI ĐĂNG MỚI & ĐẶT GIỜ ĐĂNG")
                        st.info("**Quên chuyện lùi dòng, lệch ô đi!** Hệ thống sẽ tự động thêm, Gộp ô (Merge Cells) và đẩy thẳng vào Bảng Kế Hoạch Meta Planner.")
                        st.markdown("""
                        - Mở mục **➕ THÊM BÀI MỚI VÀO VỎ TRỰC SỐ**.
                        - Nhập *Tên bài, Định dạng, Nền tảng, Giờ đăng dự kiến, Ngày đăng dự kiến* và dán **Link Drive / Nội dung Text**.
                        - Bấm Thêm. Ngay lập tức bài viết được đưa vào cả Vỏ Trực Số lẫn Timeline 30 phút để kiểm soát trùng giờ!
                        """)
                    elif step == 3:
                        st.subheader("🎓 BƯỚC 3: BẤM TRỰC TIẾP VÀO THẺ TIN BÀI ĐỂ DUYỆT NHANH (0 GIÂY)")
                        st.info("Nhanh và thông minh hơn Excel gấp nhiều lần: Bấm trực tiếp vào tiêu đề bài để xổ ra ngay lập tức hoặc mở cửa sổ Pop-up.")
                        st.markdown("""
                        - Tại mục **📋 DANH SÁCH & THỐNG KÊ TIN BÀI**, bạn chỉ cần **bấm trực tiếp vào dòng bài viết** (mở ra ngay lập tức 0 giây!) hoặc bấm nút **🗔 Mở Pop-up**.
                        - Có nút **Duyệt Nhanh 1-Click** (`✅ TCSX Duyệt OK`, `🚀 LĐP Chốt Final`, `🛡️ Thẩm định OK`) và ô sửa Giờ đăng siêu tốc.
                        - Bạn cũng có thể chuyển sang chế độ **📝 Bảng Sửa Trực Tiếp (Kiểu Excel)** để gõ sửa hàng loạt bài cùng lúc trên bảng.
                        """)
                    elif step == 4:
                        st.subheader("🎓 BƯỚC 4: QUẢN LÝ NHIỆM VỤ SEEDING")
                        st.info("Nhẹ nhàng và nhanh chóng quản lý các yêu cầu tương tác, seeding.")
                        st.markdown("""
                        - Cuối trang là khu vực **🌱 QUẢN LÝ SEEDING**.
                        - Mọi người có thể vào để cập nhật *Kết quả seeding* ngay trên ô bảng như thao tác với Excel.
                        - Nhớ bấm nút **💾 LƯU CẬP NHẬT** để lưu lại lên máy chủ nhé. Chúc bạn một ngày làm việc tuyệt vời!
                        """)
                    
                    st.write("")
                    col_btn_p, col_btn_n, col_btn_c = st.columns([1, 1, 8])
                    if step > 1: col_btn_p.button("⬅️ Quay lại", on_click=prev_step)
                    if step < 4: col_btn_n.button("Tiếp theo ➡️", on_click=next_step)
                    else: col_btn_n.button("🚀 Bắt đầu ngay", type="primary", on_click=close_tut)
                    col_btn_c.button("❌ Đóng hướng dẫn", on_click=close_tut)
                st.markdown("---")

            is_shift_admin = (role in ['LanhDao', 'ToChucSanXuat'])
            
            tab_exists, df_content_static, roster_names_current, r_roles_current = fetch_vo_truc_so(tab_name_current)

            if not tab_exists:
                st.warning(f"CHƯA CÓ VỎ TRỰC SỐ NGÀY {date_str_display}. HIỆN HỆ THỐNG ĐANG KHẮC PHỤC LỖI SAI LỊCH TRỰC LĐP, TCSX VUI LÒNG TỰ CHỌN THỦ CÔNG Ạ.")
                if is_shift_admin:
                    with st.spinner("⚡ Đang kết nối siêu tốc đa luồng để phân tích Lịch..."):
                        auto_ldp, auto_tcsx, auto_btv, auto_ht, scan_errors = lay_nhan_su_tu_lich_phuc_tap(target_date, list_nv)
                    
                    if scan_errors:
                        for err in scan_errors: st.warning(err)
                        
                    default_roster = ["--"] * 8
                    default_roster[0] = match_nv(get_lanh_dao_ban(target_date), list_nv) or "--"
                    default_roster[1] = auto_ldp if auto_ldp else "--"
                    default_roster[2] = auto_btv[0] if len(auto_btv) > 0 else "--" 
                    default_roster[3] = auto_tcsx if auto_tcsx else "--"          
                    default_roster[4] = auto_btv[4] if len(auto_btv) > 4 else "--" 
                    default_roster[5] = auto_btv[3] if len(auto_btv) > 3 else "--" 
                    default_roster[6] = auto_btv[1] if len(auto_btv) > 1 else "--" 
                    default_roster[7] = auto_btv[2] if len(auto_btv) > 2 else "--" 

                    with st.form("init_roster"):
                        cols = st.columns(3); roster_vals = []
                        for i, r_t in enumerate(ROLES_HEADER):
                            with cols[i%3]: 
                                def_val = default_roster[i]
                                options = ["--"] + list_nv
                                if def_val and def_val != "--" and def_val not in options:
                                    options.append(def_val)
                                def_idx = options.index(def_val) if def_val in options else 0
                                val = st.selectbox(f"**{r_t}**", options, index=def_idx, key=f"cr_{i}_{date_key}")
                                roster_vals.append(val if val != "--" else "")
                        
                        if st.form_submit_button("🚀 TẠO VỎ TRỰC SỐ MỚI"):
                            with st.spinner("Đang tạo vỏ trực số chuẩn Formatting..."):
                                try:
                                    sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
                                    w = sh_trucso.add_worksheet(title=tab_name_current, rows=30, cols=20, index=0)
                                    dinh_dang_dep(w, roster_vals)
                                    tu_dong_cap_nhat_thong_ke(date_str_display, roster_vals)
                                    clear_trucso_cache()
                                    st.success("ĐÃ TẠO XONG VỎ TRỰC SỐ!"); time.sleep(1); st.rerun()
                                except Exception as e: st.error(str(e))
            elif tab_exists:
                is_shift_ldp = False
                is_shift_tcsx = False
                try:
                    ldp_in_sheet = str(roster_names_current[1]).strip().lower() if len(roster_names_current) > 1 else ""
                    tcsx_in_sheet = str(roster_names_current[3]).strip().lower() if len(roster_names_current) > 3 else ""
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

                # ================= KHỐI HÀM XỬ LÝ DỮ LIỆU CHUNG =================
                def get_realtime_summary(tab_name):
                    _, df_content, _, _ = fetch_vo_truc_so(tab_name)
                    df_context, df_seeding = prepare_trucso_context(df_content, list_nv)
                    if df_context.empty:
                        return pd.DataFrame(), df_seeding, df_context

                    summary_data = []
                    unique_products = [p for p in df_context['NỘI DUNG_GROUP'].unique() if str(p).strip() != ""]

                    for prod in unique_products:
                        group = df_context[df_context['NỘI DUNG_GROUP'] == prod]
                        smart_status = get_smart_status(group)
                        first_r = group.iloc[0]

                        btvs = group['NHÂN SỰ_NORM'].unique()
                        btv_name = ", ".join([b for b in btvs if b and b != "Chưa Phân Công"]) if len(btvs) > 0 else "Chưa phân công"
                        plats = group['NỀN TẢNG'].replace('', pd.NA).dropna().tolist()
                        tg_list = [str(x).strip() for x in group['THỜI GIAN ĐĂNG BÀI'].tolist() if str(x).strip() and str(x).lower() not in ['nan', '<na>', 'none']]

                        tcsx_str = "\n".join(group['TCSX'].replace('', pd.NA).dropna().astype(str).tolist()).strip()
                        ldp_str = "\n".join(group['LĐP'].replace('', pd.NA).dropna().astype(str).tolist()).strip()
                        td_str = "\n".join(group['THẨM ĐỊNH'].replace('', pd.NA).dropna().astype(str).tolist()).strip() if 'THẨM ĐỊNH' in group.columns else ""

                        summary_data.append({
                            "first_row_idx": int(group.index[0]),
                            "STT": str(first_r.get('STT', '')).strip(),
                            "Sản phẩm": prod,
                            "Nguồn": str(first_r.get('NGUỒN', '')).strip(),
                            "BTV": btv_name,
                            "BTV_RAW": str(first_r.get('NHÂN SỰ', '')).strip(),
                            "Tiến độ": smart_status,
                            "Nền tảng": ", ".join(plats),
                            "Thời gian đăng bài": tg_list[0] if tg_list else date_str_display,
                            "TCSX": tcsx_str,
                            "LĐP": ldp_str,
                            "THẨM ĐỊNH": td_str,
                        })

                        link_duyet_vals = [str(x) for x in group['LINK DUYỆT'].tolist() if str(x).strip() and str(x).lower() not in ['nan', '<na>', 'none']]
                        raw_link_duyet = "\n\n".join(link_duyet_vals)
                        curr_txt, _ = split_text_link(raw_link_duyet)
                        queue_bg_scan(curr_txt, smart_status)

                    df_summary = pd.DataFrame(summary_data)
                    return df_summary, df_seeding, df_context

                # ================= FRAGMENT 1: CHỈ TẢI LẠI BIỂU ĐỒ TRÊN CÙNG =================
                @st.fragment(run_every="20s")
                def render_top_dashboard():
                    df_summary, _, _ = get_realtime_summary(tab_name_current)
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

                render_top_dashboard()
                st.divider()

                # ================= CÔNG CỤ SẮP XẾP LẠI BẢNG GOOGLE SHEET CHO TCSX =================
                with st.container(border=True):
                    st.markdown("##### 🔃 SẮP XẾP & CHUẨN HÓA LẠI BẢNG GOOGLE SHEET (GIỮ NGUYÊN MÀU SẮC BÔI TAY)")
                    st.caption(
                        "Mặc định khi thêm tin mới, bài sẽ tự động nối xuống dưới bảng theo đúng thứ tự thêm vào vỏ. "
                        "Khi bấm các nút sắp xếp dưới đây, **mọi màu nền (Vàng, Đỏ, Xanh lá) do TCSX/LĐP bôi trên Sheet sẽ tự động di chuyển theo đúng bài viết đó**."
                    )
                    csort0, csort1, csort2, csort3, csort4 = st.columns(5)

                    if csort0.button("📥 Xếp theo Thứ tự thêm vào vỏ", type="primary", use_container_width=True, key=f"btn_sort_added_{date_key}"):
                        with st.spinner("Đang khôi phục lại thứ tự thêm tin vào vỏ (giữ nguyên màu ô) trên Google Sheet..."):
                            with SHEET_LOCK:
                                sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
                                wks_today = sh_trucso.worksheet(tab_name_current)
                                sort_vo_truc_so_sheet(wks_today, sort_mode="added")
                            clear_trucso_cache()
                            st.success("✅ Đã xếp lại theo đúng thứ tự thêm tin vào vỏ & giữ nguyên màu sắc!")
                            time.sleep(0.6)
                            st.rerun()

                    if csort1.button("⏰ Sắp xếp theo Giờ đăng", use_container_width=True, key=f"btn_sort_time_{date_key}"):
                        with st.spinner("Đang sắp xếp chuẩn theo Giờ đăng & Chuyên mục (giữ nguyên màu ô) trên Google Sheet..."):
                            with SHEET_LOCK:
                                sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
                                wks_today = sh_trucso.worksheet(tab_name_current)
                                sort_vo_truc_so_sheet(wks_today, sort_mode="time")
                            clear_trucso_cache()
                            st.success("✅ Đã sắp xếp lại theo Giờ đăng & giữ nguyên màu sắc thành công!")
                            time.sleep(0.6)
                            st.rerun()

                    if csort2.button("📂 Sắp xếp theo Nguồn", use_container_width=True, key=f"btn_sort_source_{date_key}"):
                        with st.spinner("Đang sắp xếp theo Nguồn & Giờ đăng (giữ nguyên màu ô) trên Google Sheet..."):
                            with SHEET_LOCK:
                                sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
                                wks_today = sh_trucso.worksheet(tab_name_current)
                                sort_vo_truc_so_sheet(wks_today, sort_mode="source")
                            clear_trucso_cache()
                            st.success("✅ Đã sắp xếp lại theo Nguồn & giữ nguyên màu sắc thành công!")
                            time.sleep(0.6)
                            st.rerun()

                    if csort3.button("👤 Sắp xếp theo BTV", use_container_width=True, key=f"btn_sort_btv_{date_key}"):
                        with st.spinner("Đang sắp xếp theo BTV & Giờ đăng (giữ nguyên màu ô) trên Google Sheet..."):
                            with SHEET_LOCK:
                                sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
                                wks_today = sh_trucso.worksheet(tab_name_current)
                                sort_vo_truc_so_sheet(wks_today, sort_mode="btv")
                            clear_trucso_cache()
                            st.success("✅ Đã sắp xếp lại theo BTV & giữ nguyên màu sắc thành công!")
                            time.sleep(0.6)
                            st.rerun()

                    if csort4.button("🔤 Sắp xếp theo Tên bài (A-Z)", use_container_width=True, key=f"btn_sort_title_{date_key}"):
                        with st.spinner("Đang sắp xếp theo Tên bài A-Z (giữ nguyên màu ô) trên Google Sheet..."):
                            with SHEET_LOCK:
                                sh_trucso = ket_noi_sheet(LINK_VO_TRUC_SO)
                                wks_today = sh_trucso.worksheet(tab_name_current)
                                sort_vo_truc_so_sheet(wks_today, sort_mode="title")
                            clear_trucso_cache()
                            st.success("✅ Đã sắp xếp lại theo Tên bài (A-Z) & giữ nguyên màu sắc thành công!")
                            time.sleep(0.6)
                            st.rerun()

                # ================= FORM THÊM BÀI MỚI (ĐẶT NGAY TRÊN DANH SÁCH ĐỂ TIỆN THAO TÁC) =================
                with st.expander("➕ THÊM BÀI MỚI VÀO VỎ TRỰC SỐ", expanded=False):
                    with st.form("add_news_form", clear_on_submit=True):
                        c1, c2 = st.columns([3, 1])
                        ts_noidung = c1.text_area("Tên bài / Nội dung", placeholder="Nhập nội dung...")
                        ts_dinhdang = c2.selectbox("Định dạng", OPTS_DINH_DANG)
                        
                        c3, c4, c5, c6 = st.columns(4)
                        ts_nentang = c3.multiselect("Nền tảng xuất bản", OPTS_NEN_TANG)
                        
                        idx_cho_xu_ly = OPTS_STATUS_TRUCSO.index("Chờ xử lý") if "Chờ xử lý" in OPTS_STATUS_TRUCSO else 0
                        ts_status = c4.selectbox("Trạng thái", OPTS_STATUS_TRUCSO, index=idx_cho_xu_ly)
                        
                        ts_nhansu = c5.multiselect("BTV Thực hiện", list_nv, default=[curr_name] if curr_name in list_nv else None)
                        ts_check = c6.text_input("Ghi chú Check", placeholder="VD: OK, Sửa video...")

                        st.markdown("**⏰ LỊCH XUẤT BẢN DỰ KIẾN (TỰ ĐỘNG GỘP THÀNH 'GIỜ - NGÀY' TRÊN SHEET & META PLANNER):**")
                        c_time_add, c_date_add, c_note_sched = st.columns([1.2, 1.2, 2.6])
                        ts_giodang = c_time_add.time_input(
                            "Giờ đăng dự kiến (Tùy chọn)",
                            value=None,
                            step=timedelta(minutes=15),
                            help="Chọn giờ đăng (hoặc để trống nếu chưa chốt giờ). Giãn cách khuyến nghị tối thiểu 30 phút."
                        )
                        ts_ngaydang = c_date_add.date_input(
                            "Ngày đăng dự kiến",
                            value=target_date,
                            format="DD/MM/YYYY",
                            help="Mặc định là ngày của Vỏ trực số hiện tại, có thể đổi sang ngày khác nếu làm bài để dành."
                        )
                        c_note_sched.info("💡 Khi thêm tin mới, bài sẽ tự động nối xuống cuối bảng theo đúng thứ tự thêm vào
