"""
Stitching Costing Interface v4.5 — Yash Gallery Pvt Ltd
✅ ALL FIXES APPLIED:
- Karigar change → hour fields auto-reset
- Simple TABLE format: TIME | WORK | TARGET QTY | ACTUAL QTY | EFFICIENCY
- Google Sheets save working properly
- AttributeError fixed (str conversion)
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import io, hashlib, zipfile

import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Stitching Costing — Yash Gallery", page_icon="🧵", layout="wide", initial_sidebar_state="expanded")

if "save_error" in st.session_state:
    st.error(f"Google Sheets Error: {st.session_state['save_error']}")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif;}
.main-hdr{background:linear-gradient(135deg,#1a3a5c,#2c5aa0,#1e7ed4);padding:16px 22px;border-radius:10px;color:#fff;margin-bottom:16px;}
.main-hdr h2{margin:0;font-size:1.4rem;font-weight:700;}
.main-hdr p{margin:3px 0 0;opacity:.85;font-size:.85rem;}
.sec-hdr{background:#2c5aa0;color:#fff;padding:7px 13px;border-radius:6px;font-weight:600;margin:10px 0 5px;font-size:.9rem;}
.info-box{background:#e8f1f8;border-left:4px solid #2c5aa0;padding:9px 13px;border-radius:4px;margin:5px 0;font-size:.86rem;color:#1a3a52;}
.warn-box{background:#fff3e0;border-left:4px solid #f57c00;padding:9px 13px;border-radius:4px;margin:5px 0;font-size:.86rem;color:#e65100;}
.ok-box{background:#e8f5e9;border-left:4px solid #2e7d32;padding:9px 13px;border-radius:4px;margin:5px 0;font-size:.86rem;color:#1b5e20;}
.ro-field{background:#f5f5f5;border:1px solid #bdbdbd;padding:8px 11px;border-radius:4px;font-weight:600;color:#424242;font-size:.88rem;margin:4px 0;}
.mc{background:#f0f6ff;padding:12px 16px;border-radius:8px;border-left:4px solid #2c5aa0;text-align:center;margin:3px 0;}
.mc .mv{font-size:1.7rem;font-weight:700;color:#2c5aa0;font-family:'IBM Plex Mono',monospace;}
.mc .ml{font-size:.74rem;opacity:.7;font-weight:500;text-transform:uppercase;letter-spacing:.05em;}
.mc .ms{font-size:.7rem;opacity:.55;margin-top:2px;}
.mc-g{background:#f0faf2;border-left-color:#2e7d32;}.mc-g .mv{color:#2e7d32;}
.mc-o{background:#fff8f0;border-left-color:#e65100;}.mc-o .mv{color:#e65100;}
.entry-table-hdr{display:grid;grid-template-columns:90px 1fr 100px 110px 100px;background:#1a3a5c;color:#fff;padding:9px 8px;border-radius:6px 6px 0 0;font-size:.8rem;font-weight:700;text-align:center;letter-spacing:.04em;text-transform:uppercase;}
.entry-row{display:grid;grid-template-columns:90px 1fr 100px 110px 100px;border:1px solid #dde3ea;background:#fff;align-items:center;min-height:48px;}
.entry-row:hover{background:#f7faff;}
.entry-row-lunch{display:grid;grid-template-columns:90px 1fr;border:1px solid #dde3ea;background:#fafafa;align-items:center;min-height:38px;}
.time-lbl{font-size:.84rem;font-weight:700;color:#2c5aa0;text-align:center;padding:0 4px;border-right:1px solid #dde3ea;height:100%;display:flex;align-items:center;justify-content:center;}
.eff-ex{background:#e8f5e9;color:#2e7d32;border-radius:4px;padding:3px 7px;font-size:.76rem;font-weight:600;}
.eff-gd{background:#fff3e0;color:#e65100;border-radius:4px;padding:3px 7px;font-size:.76rem;font-weight:600;}
.eff-bl{background:#ffebee;color:#c62828;border-radius:4px;padding:3px 7px;font-size:.76rem;font-weight:600;}
.tpl-box{background:#fffde7;border:1px dashed #f9a825;border-radius:6px;padding:10px 14px;margin:6px 0;font-size:.84rem;}
.ch-cost-profit{background:#e8f5e9;border-left:4px solid #2e7d32;border-radius:4px;padding:8px 12px;margin:4px 0;font-size:.88rem;color:#1b5e20;}
.ch-cost-loss{background:#ffebee;border-left:4px solid #c62828;border-radius:4px;padding:8px 12px;margin:4px 0;font-size:.88rem;color:#b71c1c;}
.ch-cost-pending{background:#fff8e1;border-left:4px solid #f9a825;border-radius:4px;padding:8px 12px;margin:4px 0;font-size:.88rem;color:#e65100;}
</style>
""", unsafe_allow_html=True)

HOUR_COLS = ["H_09_10","H_10_11","H_11_12","H_12_13","H_13_14","H_14_15","H_15_16","H_16_17","H_17_18","H_18_19","H_19_20","H_20_21"]
HOUR_LBLS = ["9-10","10-11","11-12","12-13","13-14","14-15","15-16","16-17","17-18","18-19","19-20","20-21"]
DATA_KEYS = ["style_master","karigar_master","challan_master","production_log","employee_master","karigar_attendance","operating_attendance"]
DEFAULT_PW = hashlib.sha256("admin123".encode()).hexdigest()
SHEET_ID = "1_cMCIn5KlvRqXS2yRy7nBidoTmgX8K48gTBaMAqBoFE"

def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    except Exception:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    return gspread.authorize(creds).open_by_key(SHEET_ID)

def load_sheet(tab_name: str) -> pd.DataFrame:
    try:
        sh = get_gsheet()
        try: ws = sh.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            sh.add_worksheet(title=tab_name, rows=1000, cols=50); return pd.DataFrame()
        all_values = ws.get_all_values()
        if not all_values or len(all_values) < 2: return pd.DataFrame()
        return get_as_dataframe(ws, evaluate_formulas=True).dropna(how="all").reset_index(drop=True)
    except Exception: return pd.DataFrame()

def save_sheet(tab_name: str, df: pd.DataFrame):
    try:
        sh = get_gsheet()
        try: ws = sh.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=tab_name, rows=1000, cols=50)
        ws.clear()
        set_with_dataframe(ws, df, include_index=False, include_column_header=True)
    except Exception as e:
        st.session_state["save_error"] = str(e); st.stop()

EXCEL_AVAILABLE = False; EXCEL_ENGINE = None
try:
    import xlsxwriter; EXCEL_AVAILABLE = True; EXCEL_ENGINE = "xlsxwriter"
except ImportError:
    try:
        import openpyxl; EXCEL_AVAILABLE = True; EXCEL_ENGINE = "openpyxl"
    except ImportError: pass

def safe_num(s): return pd.to_numeric(s, errors='coerce').fillna(0)
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def to_excel_bytes(df):
    if not EXCEL_AVAILABLE: return (df.to_csv(index=False).encode(), ".csv", "text/csv")
    buf = io.BytesIO()
    try:
        if EXCEL_ENGINE == "xlsxwriter":
            with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
                df.to_excel(w, index=False, sheet_name="Data")
                wb = w.book; ws2 = w.sheets["Data"]
                hf = wb.add_format({'bold':True,'bg_color':'#2c5aa0','font_color':'white','border':1,'align':'center'})
                for i, v in enumerate(df.columns.values): ws2.write(0, i, v, hf)
                for i, c in enumerate(df.columns):
                    ml = max(df[c].astype(str).apply(len).max(), len(str(c))) + 2
                    ws2.set_column(i, i, min(ml, 50))
        else:
            with pd.ExcelWriter(buf, engine="openpyxl") as w: df.to_excel(w, index=False, sheet_name="Data")
        buf.seek(0)
        return (buf.getvalue(), ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception: return (df.to_csv(index=False).encode(), ".csv", "text/csv")

def to_csv_bytes(df): return df.to_csv(index=False).encode()
def read_file(f):
    if f.name.lower().endswith(".csv"): return pd.read_csv(f)
    if f.name.lower().endswith((".xlsx",".xls")): return pd.read_excel(f)
    st.error("Use .csv or .xlsx"); return None

def calc_salary(in_str, out_str, daily_rate, ot_mult=1.5):
    try:
        fmt="%H:%M"; ti=datetime.strptime(in_str.strip(),fmt); to_=datetime.strptime(out_str.strip(),fmt)
        se=datetime.strptime("18:00",fmt); ls=datetime.strptime("13:00",fmt); le=datetime.strptime("14:00",fmt)
        ph=max(int((to_-ti).total_seconds()),0)/3600
        ld=1.0 if (ti<le and to_>ls) else 0.0
        py=max(ph-ld,0.0); hr=daily_rate/8; np_=round(py*hr,2)
        oh=max(int((to_-se).total_seconds()),0)/3600 if to_>se else 0.0
        op=round(oh*hr*ot_mult,2); tp=round(np_+op,2)
        return round(ph,2),round(ld,2),round(py,2),round(hr,2),np_,round(oh,2),op,tp
    except: return 0.,0.,0.,0.,0.,0.,0.,0.

def export_zip():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as zf:
        for k in DATA_KEYS:
            df=st.session_state.get(k, pd.DataFrame())
            if not isinstance(df, pd.DataFrame): df=pd.DataFrame()
            zf.writestr(f"{k}.csv", df.to_csv(index=False))
    return buf.getvalue()

def import_zip(zb):
    with zipfile.ZipFile(io.BytesIO(zb)) as zf:
        for nm in zf.namelist():
            k=nm.replace(".csv","")
            if k in DATA_KEYS:
                df = pd.read_csv(io.StringIO(zf.read(nm).decode()))
                st.session_state[k] = df; save_sheet(k, df)
    st.success("✅ Restored!")

TEMPLATES = {
    "style_master": pd.DataFrame([{"Style":"1894YKDGREEN","Operation":"Cutting","Target":120,"Rate_Rs":2.50}]),
    "karigar_master": pd.DataFrame([{"Karigar_ID":"K001","Name":"Ramesh","Skill":"Stitching","Daily_Rate_Rs":450}]),
    "challan_master": pd.DataFrame([{"Challan_No":"10220-2526","Style":"1894YKDGREEN","Party":"Aashirwad","Total_Qty":376,"Received_Qty":0,"Deposit_Rs":0.0,"Rate_Per_Pc":35,"Date":"2026-02-25","Delivery_By":"2026-03-07"}]),
    "production_log": pd.DataFrame([{"Date":"2026-02-25","Karigar_ID":"K001","Karigar_Name":"Ramesh","Challan_No":"10220-2526","Style":"1894YKDGREEN","Operation":"Cutting",**{h:10 for h in HOUR_COLS},"Total_Pieces":85,"Target":120,"Rate_Rs":2.50,"Efficiency_%":70.8,"Piece_Value_Rs":212.5}]),
    "employee_master": pd.DataFrame([{"E_Code":"E001","Name":"Ramesh","Type":"Karigar","Daily_Rate_Rs":450,"Hourly_Rate_Rs":56.25}]),
    "karigar_attendance": pd.DataFrame([{"Date":"2026-02-25","E_Code":"E001","In_Punch":"09:00","Out_Punch":"18:00"}]),
    "operating_attendance": pd.DataFrame([{"Date":"2026-02-25","E_Code":"E101","In_Punch":"09:00","Out_Punch":"18:00"}]),
}
