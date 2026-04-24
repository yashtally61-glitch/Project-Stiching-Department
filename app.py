"""
Stitching Costing Interface v4.2 — Yash Gallery Pvt Ltd
UPDATES v4.2:
- Google Sheets integration as persistent database
- Auto-save on every data change
- Auto-load on app start
- All v4.1 features retained
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import io, hashlib, zipfile

# ── GOOGLE SHEETS IMPORTS ─────────────────────────────────
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Stitching Costing — Yash Gallery", page_icon="🧵", layout="wide", initial_sidebar_state="expanded")

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
.hour-table{width:100%;border-collapse:collapse;margin:8px 0;}
.hour-table th{background:#2c5aa0;color:#fff;padding:6px 10px;font-size:.82rem;text-align:center;border:1px solid #1e4d8a;}
.hour-table td{padding:4px 8px;border:1px solid #dde3ea;font-size:.84rem;text-align:center;background:#fafbfc;}
.hour-table tr:nth-child(even) td{background:#f0f4f9;}
.sz-pill{display:inline-block;padding:2px 9px;border-radius:12px;font-size:.76rem;font-weight:600;margin:2px;}
.sz-xl{background:#e3f2fd;color:#1565c0;}.sz-xxl{background:#ede7f6;color:#4527a0;}
.sz-3xl{background:#e8f5e9;color:#1b5e20;}.sz-4xl{background:#fff3e0;color:#e65100;}.sz-5xl{background:#fce4ec;color:#880e4f;}
.sum-bar{background:#1a3a5c;color:#fff;padding:10px 16px;border-radius:8px;display:flex;gap:20px;flex-wrap:wrap;margin:7px 0;}
.sb-item{text-align:center;}.sb-v{font-size:1.2rem;font-weight:700;font-family:'IBM Plex Mono',monospace;}
.sb-l{font-size:.7rem;opacity:.7;text-transform:uppercase;letter-spacing:.04em;}
.tpl-box{background:#fffde7;border:1px dashed #f9a825;border-radius:6px;padding:10px 14px;margin:6px 0;font-size:.84rem;}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════
HOUR_COLS = ["H_09_10","H_10_11","H_11_12","H_12_13","H_13_14",
             "H_14_15","H_15_16","H_16_17","H_17_18","H_18_19","H_19_20","H_20_21"]
HOUR_LBLS = ["9:00-10:00","10:00-11:00","11:00-12:00","12:00-13:00","13:00-14:00",
             "14:00-15:00","15:00-16:00","16:00-17:00","17:00-18:00","18:00-19:00","19:00-20:00","20:00-21:00"]
DATA_KEYS  = ["style_master","karigar_master","challan_master","production_log",
              "employee_master","karigar_attendance","operating_attendance"]
DEFAULT_PW = hashlib.sha256("admin123".encode()).hexdigest()

# ═══════════════════════════════════════════
# !! PASTE YOUR GOOGLE SHEET ID HERE !!
# ═══════════════════════════════════════════
SHEET_ID = "PASTE_YOUR_SHEET_ID_HERE"

# ═══════════════════════════════════════════
# GOOGLE SHEETS FUNCTIONS
# ═══════════════════════════════════════════
@st.cache_resource
def get_gsheet():
    """Connect to Google Sheets — cached so it connects only once per session."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        # On Streamlit Cloud — uses st.secrets
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    except Exception:
        # Local — uses credentials.json file in project folder
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)


def load_sheet(tab_name: str) -> pd.DataFrame:
    """Read a tab from Google Sheet into DataFrame."""
    try:
        sh = get_gsheet()
        ws = sh.worksheet(tab_name)
        df = get_as_dataframe(ws, evaluate_formulas=True).dropna(how="all")
        return df.reset_index(drop=True)
    except Exception as e:
        st.warning(f"⚠️ Could not load '{tab_name}' from Google Sheets: {e}")
        return pd.DataFrame()


def save_sheet(tab_name: str, df: pd.DataFrame):
    """Write DataFrame back to Google Sheet tab."""
    try:
        sh = get_gsheet()
        ws = sh.worksheet(tab_name)
        ws.clear()
        set_with_dataframe(ws, df)
    except Exception as e:
        st.error(f"❌ Could not save '{tab_name}' to Google Sheets: {e}")


# ═══════════════════════════════════════════
# CHECK EXCEL LIBRARIES
# ═══════════════════════════════════════════
EXCEL_AVAILABLE = False
EXCEL_ENGINE = None

try:
    import xlsxwriter
    EXCEL_AVAILABLE = True
    EXCEL_ENGINE = "xlsxwriter"
except ImportError:
    try:
        import openpyxl
        EXCEL_AVAILABLE = True
        EXCEL_ENGINE = "openpyxl"
    except ImportError:
        EXCEL_AVAILABLE = False
        EXCEL_ENGINE = None

# ═══════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════
def safe_num(s): return pd.to_numeric(s, errors='coerce').fillna(0)
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def to_excel_bytes(df: pd.DataFrame) -> tuple:
    if not EXCEL_AVAILABLE:
        return (df.to_csv(index=False).encode(), ".csv", "text/csv")
    buf = io.BytesIO()
    try:
        if EXCEL_ENGINE == "xlsxwriter":
            with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Data", startrow=0)
                workbook = writer.book
                worksheet = writer.sheets["Data"]
                header_format = workbook.add_format({
                    'bold': True, 'bg_color': '#2c5aa0',
                    'font_color': 'white', 'border': 1,
                    'align': 'center', 'valign': 'vcenter'
                })
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                for idx, col in enumerate(df.columns):
                    max_length = max(df[col].astype(str).apply(len).max(), len(str(col))) + 2
                    worksheet.set_column(idx, idx, min(max_length, 50))
                worksheet.set_row(0, 20)
        elif EXCEL_ENGINE == "openpyxl":
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Data")
        buf.seek(0)
        return (buf.getvalue(), ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception:
        return (df.to_csv(index=False).encode(), ".csv", "text/csv")

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode()

def read_file(f):
    if f.name.lower().endswith(".csv"):    return pd.read_csv(f)
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

def export_zip() -> bytes:
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
                st.session_state[k] = df
                save_sheet(k, df)
    st.success("✅ All data restored and saved to Google Sheets!")

# ═══════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════
TEMPLATES = {
    "style_master": pd.DataFrame([
        {"Style":"1894YKDGREEN","Operation":"Cutting",        "Target":120,"Rate_Rs":2.50},
        {"Style":"1894YKDGREEN","Operation":"Stitching Front","Target":80, "Rate_Rs":4.00},
        {"Style":"1894YKDGREEN","Operation":"Side Seam",      "Target":90, "Rate_Rs":3.50},
    ]),
    "karigar_master": pd.DataFrame([
        {"Karigar_ID":"K001","Name":"Ramesh Kumar","Skill":"Stitching","Daily_Rate_Rs":450},
        {"Karigar_ID":"K002","Name":"Suresh Singh","Skill":"Cutting",  "Daily_Rate_Rs":420},
    ]),
    "challan_master": pd.DataFrame([
        {"Challan_No":"10220-2526","Style":"1894YKDGREEN","Party":"Aashirwad Garments",
         "Total_Qty":376,"Received_Qty":0,"Deposit_Rs":0.0,"Rate_Per_Pc":35,
         "Date":"2026-02-25","Delivery_By":"2026-03-07"},
    ]),
    "production_log": pd.DataFrame([{
        "Date":"2026-02-25","Karigar_ID":"K001","Karigar_Name":"Ramesh Kumar",
        "Challan_No":"10220-2526","Style":"1894YKDGREEN","Operation":"Cutting",
        **{h:10 for h in HOUR_COLS},
        "Total_Pieces":85,"Target":120,"Rate_Rs":2.50,"Efficiency_%":70.8,"Piece_Value_Rs":212.5
    }]),
    "employee_master": pd.DataFrame([
        {"E_Code":"E001","Name":"Ramesh Kumar", "Type":"Karigar",   "Daily_Rate_Rs":450,"Hourly_Rate_Rs":56.25},
        {"E_Code":"E101","Name":"Amit Sharma",  "Type":"Operating", "Daily_Rate_Rs":600,"Hourly_Rate_Rs":75.00},
    ]),
    "karigar_attendance": pd.DataFrame([
        {"Date":"2026-02-25","E_Code":"E001","In_Punch":"09:00","Out_Punch":"18:00"},
    ]),
    "operating_attendance": pd.DataFrame([
        {"Date":"2026-02-25","E_Code":"E101","In_Punch":"09:00","Out_Punch":"18:00"},
    ]),
}

# ═══════════════════════════════════════════
# DEFAULT DATA
# ═══════════════════════════════════════════
DEFAULT_DATA = {
    "style_master": pd.DataFrame([
        {"Style":"1894YKDGREEN","Operation":"Cutting",        "Target":120,"Rate_Rs":2.50},
        {"Style":"1894YKDGREEN","Operation":"Stitching Front","Target":80, "Rate_Rs":4.00},
        {"Style":"1894YKDGREEN","Operation":"Stitching Back", "Target":80, "Rate_Rs":4.00},
        {"Style":"1894YKDGREEN","Operation":"Dupatta Attach", "Target":60, "Rate_Rs":5.50},
        {"Style":"1894YKDGREEN","Operation":"Side Seam",      "Target":90, "Rate_Rs":3.50},
        {"Style":"1894YKDGREEN","Operation":"Hemming",        "Target":100,"Rate_Rs":3.00},
        {"Style":"1894YKDGREEN","Operation":"Button Attach",  "Target":110,"Rate_Rs":2.00},
        {"Style":"1894YKDGREEN","Operation":"Finishing",      "Target":70, "Rate_Rs":4.50},
        {"Style":"1065YKBLUE",  "Operation":"Cutting",        "Target":120,"Rate_Rs":2.50},
        {"Style":"1065YKBLUE",  "Operation":"Stitching Front","Target":80, "Rate_Rs":4.00},
        {"Style":"1065YKBLUE",  "Operation":"Collar Attach",  "Target":60, "Rate_Rs":5.50},
        {"Style":"1065YKBLUE",  "Operation":"Side Seam",      "Target":90, "Rate_Rs":3.50},
        {"Style":"1065YKBLUE",  "Operation":"Finishing",      "Target":70, "Rate_Rs":4.50},
    ]),
    "karigar_master": pd.DataFrame([
        {"Karigar_ID":"K001","Name":"Ramesh Kumar",   "Skill":"Stitching","Daily_Rate_Rs":450},
        {"Karigar_ID":"K002","Name":"Suresh Singh",   "Skill":"Cutting",  "Daily_Rate_Rs":420},
        {"Karigar_ID":"K003","Name":"Priya Devi",     "Skill":"Finishing","Daily_Rate_Rs":400},
        {"Karigar_ID":"K004","Name":"Mohan Lal",      "Skill":"Stitching","Daily_Rate_Rs":460},
        {"Karigar_ID":"K005","Name":"Sunita Sharma",  "Skill":"Hemming",  "Daily_Rate_Rs":410},
    ]),
    "challan_master": pd.DataFrame([
        {"Challan_No":"10220-2526","Style":"1894YKDGREEN","Party":"Aashirwad Garments",
         "Total_Qty":376,"Received_Qty":0,"Deposit_Rs":0.0,
         "Rate_Per_Pc":35,"Date":"2026-02-25","Delivery_By":"2026-03-07"},
    ]),
    "production_log": pd.DataFrame(columns=[
        "Date","Karigar_ID","Karigar_Name","Challan_No","Style","Operation",
    ] + HOUR_COLS + ["Total_Pieces","Target","Rate_Rs","Efficiency_%","Piece_Value_Rs"]),
    "employee_master": pd.DataFrame([
        {"E_Code":"E001","Name":"Ramesh Kumar", "Type":"Karigar",   "Daily_Rate_Rs":450,"Hourly_Rate_Rs":56.25},
        {"E_Code":"E002","Name":"Suresh Singh", "Type":"Karigar",   "Daily_Rate_Rs":420,"Hourly_Rate_Rs":52.50},
        {"E_Code":"E003","Name":"Priya Devi",   "Type":"Karigar",   "Daily_Rate_Rs":400,"Hourly_Rate_Rs":50.00},
        {"E_Code":"E004","Name":"Mohan Lal",    "Type":"Karigar",   "Daily_Rate_Rs":460,"Hourly_Rate_Rs":57.50},
        {"E_Code":"E005","Name":"Sunita Sharma","Type":"Karigar",   "Daily_Rate_Rs":410,"Hourly_Rate_Rs":51.25},
        {"E_Code":"E101","Name":"Amit Sharma",  "Type":"Operating", "Daily_Rate_Rs":600,"Hourly_Rate_Rs":75.00},
        {"E_Code":"E102","Name":"Kavita Rao",   "Type":"Operating", "Daily_Rate_Rs":550,"Hourly_Rate_Rs":68.75},
    ]),
    "karigar_attendance": pd.DataFrame(columns=[
        "Date","E_Code","Name","In_Punch","Out_Punch",
        "Total_Presence_Hrs","Lunch_Deduction_Hrs","Payable_Hrs",
        "Hourly_Rate_Rs","Normal_Pay","OT_Hours","OT_Pay","Total_Pay"]),
    "operating_attendance": pd.DataFrame(columns=[
        "Date","E_Code","Name","In_Punch","Out_Punch","Total_Hours","Hourly_Rate_Rs","Total_Pay"]),
}

# ═══════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════
def init_auth():
    if "admin_pw_hash"  not in st.session_state: st.session_state.admin_pw_hash  = DEFAULT_PW
    if "sheet_unlocked" not in st.session_state: st.session_state.sheet_unlocked = False

def lock_widget(key="x"):
    if st.session_state.sheet_unlocked:
        c1,c2=st.columns([5,1])
        with c2:
            if st.button("🔒 Lock",key=f"lk_{key}"):
                st.session_state.sheet_unlocked=False; st.rerun()
        st.markdown('<div class="ok-box">✅ <b>UNLOCKED</b> — Admin mode active</div>',unsafe_allow_html=True)
        return True
    st.markdown('<div class="warn-box">🔐 <b>LOCKED</b> — Target & Rate are read-only. Unlock to edit.</div>',unsafe_allow_html=True)
    c1,c2=st.columns([3,1])
    with c1: pw=st.text_input("",type="password",key=f"pw_{key}",placeholder="Admin password",label_visibility="collapsed")
    with c2:
        if st.button("🔓 Unlock",key=f"ul_{key}"):
            if hash_pw(pw)==st.session_state.admin_pw_hash: st.session_state.sheet_unlocked=True; st.rerun()
            else: st.error("❌ Wrong password")
    return False

# ═══════════════════════════════════════════
# IMPORT WIDGET
# ═══════════════════════════════════════════
def import_section(key: str, session_key: str, label: str):
    tmpl = TEMPLATES.get(key, pd.DataFrame())
    with st.expander(f"📥 Import / Upload {label}", expanded=False):
        st.markdown(f'<div class="tpl-box">📋 <b>Step 1:</b> Download the template below, fill your data keeping the exact column names, then upload it back.<br>Required columns: <b>{", ".join(tmpl.columns.tolist())}</b></div>', unsafe_allow_html=True)
        dl1, dl2 = st.columns(2)
        excel_data, excel_ext, excel_mime = to_excel_bytes(tmpl)
        with dl1:
            st.download_button(
                f"⬇️ Download {'Excel' if EXCEL_AVAILABLE else 'CSV'} Template",
                data=excel_data, file_name=f"{key}_template{excel_ext}",
                mime=excel_mime, key=f"tpl_x_{key}", use_container_width=True)
        with dl2:
            st.download_button(
                f"⬇️ Download CSV Template",
                data=to_csv_bytes(tmpl), file_name=f"{key}_template.csv",
                mime="text/csv", key=f"tpl_c_{key}", use_container_width=True)
        st.markdown("---")
        uf = st.file_uploader(f"📂 Upload your filled file ({label})", type=["csv","xlsx","xls"], key=f"uf_{key}")
        mode = st.radio("Import mode", ["➕ Append to existing","🔄 Replace all"], key=f"md_{key}", horizontal=True)
        if uf is not None:
            df_new = read_file(uf)
            if df_new is not None:
                required = tmpl.columns.tolist()
                miss = [c for c in required if c not in df_new.columns]
                if miss:
                    st.error(f"❌ Missing columns: {miss}")
                    return
                st.success(f"✅ {len(df_new)} rows detected")
                st.dataframe(df_new.head(5), use_container_width=True, hide_index=True)
                if st.button(f"✅ Confirm Import — {label}", key=f"ci_{key}", use_container_width=True):
                    if "Replace" in mode:
                        st.session_state[session_key] = df_new.reset_index(drop=True)
                    else:
                        st.session_state[session_key] = pd.concat([st.session_state[session_key], df_new], ignore_index=True)
                    save_sheet(session_key, st.session_state[session_key])
                    st.success(f"✅ Imported and saved to Google Sheets!")
                    st.rerun()

# ═══════════════════════════════════════════
# SESSION STATE INIT — loads from Google Sheets
# ═══════════════════════════════════════════
def init_state():
    init_auth()
    for key in DATA_KEYS:
        if key not in st.session_state:
            loaded = load_sheet(key)
            if loaded.empty:
                st.session_state[key] = DEFAULT_DATA[key].copy()
            else:
                st.session_state[key] = loaded

init_state()
today_str = str(date.today())

# ═══════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════
st.markdown(f"""
<div class="main-hdr">
  <h2>🧵 Stitching Costing Interface — Yash Gallery Pvt Ltd</h2>
  <p>Karigar Tracking · Challan Management · Style Costing · Payroll &nbsp;|&nbsp; {date.today().strftime("%d %b %Y")} &nbsp;|&nbsp; 🟢 Google Sheets Connected</p>
</div>""", unsafe_allow_html=True)

if not EXCEL_AVAILABLE:
    st.warning("⚠️ **Excel Export Not Available** — Downloads will be CSV. Run: `pip install xlsxwriter openpyxl`")

# ═══════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════
with st.sidebar:
    st.markdown("### 💾 Backup & Restore")
    st.markdown('<div class="info-box">Data auto-saves to Google Sheets. ZIP backup is optional extra safety.</div>', unsafe_allow_html=True)
    st.download_button("📦 Export All Data (.zip)",
        data=export_zip(), file_name=f"yashgallery_{today_str}.zip",
        mime="application/zip", use_container_width=True)
    rf = st.file_uploader("📂 Restore from ZIP", type=["zip"], key="rzf")
    if rf:
        if st.button("🔄 Restore Now", use_container_width=True, key="do_restore"):
            import_zip(rf.read()); st.rerun()

    st.markdown("---")
    st.markdown("### 🔄 Sync")
    if st.button("🔄 Reload from Google Sheets", use_container_width=True):
        for key in DATA_KEYS:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.markdown("---")
    st.markdown("### 🔐 Admin Password")
    with st.expander("Change Password"):
        cur=st.text_input("Current",type="password",key="sb_cur")
        n1 =st.text_input("New",    type="password",key="sb_n1")
        n2 =st.text_input("Confirm",type="password",key="sb_n2")
        if st.button("Change",key="sb_cp"):
            if hash_pw(cur)!=st.session_state.admin_pw_hash: st.error("Wrong current password")
            elif n1!=n2: st.error("Passwords don't match")
            elif len(n1)<4: st.error("Min 4 characters")
            else: st.session_state.admin_pw_hash=hash_pw(n1); st.success("✅ Changed!")

    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    pl_all = st.session_state.production_log
    tdpl = pl_all[pl_all["Date"]==today_str] if not pl_all.empty else pd.DataFrame()
    st.metric("Today's Entries",   len(tdpl))
    st.metric("Total Karigar",     len(st.session_state.karigar_master))
    st.metric("Active Challans",   len(st.session_state.challan_master))
    if not tdpl.empty:
        st.metric("Today's Pieces", int(safe_num(tdpl["Total_Pieces"]).sum()))

# ═══════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════
T = st.tabs(["🏠 Dashboard","📋 Production Entry","🧾 Challan Management",
             "💎 Style Costing","📊 Efficiency","💰 Payroll",
             "🕐 Attendance","🏢 Operating Staff","🌟 Performance","⚙️ Master Data"])
(tab_dash,tab_prod,tab_challan,tab_style,tab_eff,
 tab_pay,tab_att,tab_op,tab_perf,tab_master) = T

# ══════════════════════════════════════════════════════════
# TAB 1 ─ DASHBOARD
# ══════════════════════════════════════════════════════════
with tab_dash:
    st.markdown('<div class="sec-hdr">📈 Today\'s Overview</div>', unsafe_allow_html=True)
    pl_all = st.session_state.production_log
    tdpl   = pl_all[pl_all["Date"]==today_str] if not pl_all.empty else pd.DataFrame()

    active_k = tdpl["Karigar_ID"].nunique()       if not tdpl.empty else 0
    pieces   = int(safe_num(tdpl["Total_Pieces"]).sum()) if not tdpl.empty else 0
    avg_eff  = safe_num(tdpl["Efficiency_%"]).mean()     if not tdpl.empty and "Efficiency_%" in tdpl.columns else 0.0
    pv       = safe_num(tdpl["Piece_Value_Rs"]).sum()    if not tdpl.empty else 0.0

    cm_all = st.session_state.challan_master
    if not cm_all.empty:
        cm2 = cm_all.copy()
        cm2["Pend"] = safe_num(cm2["Total_Qty"]) - safe_num(cm2.get("Received_Qty",0))
        pend_c = len(cm2[cm2["Pend"]>0])
    else: pend_c=0

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    def mcard(col, val, lbl, sub, cls=""):
        with col:
            st.markdown(f'<div class="mc {cls}"><div class="ml">{lbl}</div><div class="mv">{val}</div><div class="ms">{sub}</div></div>', unsafe_allow_html=True)

    mcard(c1, active_k, "Active Karigar",    f"of {len(st.session_state.karigar_master)} total")
    mcard(c2, f"{pieces:,}", "Pieces Done",  "today")
    mcard(c3, f"{avg_eff:.1f}%", "Avg Efficiency", "target 100%", "mc-g" if avg_eff>=85 else "mc-o")
    mcard(c4, f"₹{pv:,.0f}", "Piece-Rate Value", "today")
    mcard(c5, len(cm_all), "Total Challans", "registered")
    mcard(c6, pend_c, "Pending Challans", "in production", "mc-o" if pend_c>0 else "mc-g")

    st.markdown("---")
    da,db = st.columns(2)
    with da:
        st.markdown('<div class="sec-hdr">👷 Karigar Status</div>', unsafe_allow_html=True)
        km = st.session_state.karigar_master.copy()
        aids = tdpl["Karigar_ID"].unique().tolist() if not tdpl.empty else []
        km["Status"] = km["Karigar_ID"].apply(lambda x:"🟢 Working" if x in aids else "⚪ Idle")
        st.dataframe(km, use_container_width=True, hide_index=True)
    with db:
        st.markdown('<div class="sec-hdr">🧾 Challan Register</div>', unsafe_allow_html=True)
        if not cm_all.empty:
            cm_d=cm_all.copy()
            cm_d["Pending"]=safe_num(cm_d["Total_Qty"])-safe_num(cm_d.get("Received_Qty",0))
            cm_d["Status"]=cm_d["Pending"].apply(lambda x:"✅ Done" if x<=0 else f"⏳ {int(x)} pending")
            show_c=[c for c in["Challan_No","Style","Party","Total_Qty","Pending","Status"] if c in cm_d.columns]
            st.dataframe(cm_d[show_c], use_container_width=True, hide_index=True)

    if not tdpl.empty:
        st.markdown("---")
        st.markdown('<div class="sec-hdr">📋 Today\'s Production</div>', unsafe_allow_html=True)
        sc=[c for c in["Karigar_Name","Challan_No","Style","Operation","Total_Pieces","Target","Efficiency_%","Piece_Value_Rs"] if c in tdpl.columns]
        st.dataframe(tdpl[sc], use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════
# TAB 2 ─ PRODUCTION ENTRY
# ══════════════════════════════════════════════════════════
with tab_prod:
    st.markdown('<div class="sec-hdr">📋 Production Entry — Enhanced v4.2</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    <b>Smart Flow:</b>&nbsp;
    🔍 Search Karigar &rarr;
    👗 Select Style (auto-loads operations) &rarr;
    🧾 Select Challan &rarr;
    ⏱ Hour-wise entry with real-time efficiency tracking
    </div>""", unsafe_allow_html=True)

    is_unlocked = lock_widget("prod")
    import_section("production_log", "production_log", "Production Log")

    st.markdown("---")
    st.markdown('<div class="sec-hdr">✏️ New Production Entry</div>', unsafe_allow_html=True)

    col_date, col_kar = st.columns([1,2])
    with col_date:
        pe_date = st.date_input("📅 Date", value=date.today(), key="pe_date")

    with col_kar:
        st.markdown("**🔍 Search Karigar**")
        kdf = st.session_state.karigar_master
        srch = st.text_input("Type name or ID to filter", key="ksrch", placeholder="e.g. Ramesh  or  K001")
        if srch:
            mask = (kdf["Name"].str.contains(srch, case=False, na=False) |
                    kdf["Karigar_ID"].str.contains(srch, case=False, na=False))
            kdf_f = kdf[mask]
        else:
            kdf_f = kdf

        if kdf_f.empty:
            st.warning("No karigar found.")
            st.stop()

        k_map = {f"{r['Karigar_ID']} — {r['Name']}": r for _,r in kdf_f.iterrows()}
        sel_k_key = st.selectbox("Select Karigar", list(k_map.keys()), key="sel_kar")
        k_row = k_map[sel_k_key]

        if "prev_karigar" not in st.session_state:
            st.session_state.prev_karigar = sel_k_key
        if st.session_state.prev_karigar != sel_k_key:
            st.session_state.prev_karigar = sel_k_key
            st.rerun()

        st.markdown(f'<div class="ro-field">ID: <b>{k_row["Karigar_ID"]}</b> &nbsp;|&nbsp; Skill: <b>{k_row["Skill"]}</b> &nbsp;|&nbsp; Daily Rate: <b>₹{k_row["Daily_Rate_Rs"]}</b></div>', unsafe_allow_html=True)

    sm = st.session_state.style_master
    all_styles = sm["Style"].unique().tolist() if not sm.empty else []
    if not all_styles:
        st.warning("No styles in master. Add styles in ⚙️ Master Data first.")
        st.stop()

    pe_style = st.selectbox("👗 Select Style (SKU)", all_styles, key="pe_style")

    if "prev_style" not in st.session_state:
        st.session_state.prev_style = pe_style
    if st.session_state.prev_style != pe_style:
        st.session_state.prev_style = pe_style
        st.rerun()

    ch_df = st.session_state.challan_master
    s_chall = ch_df[ch_df["Style"] == pe_style] if not ch_df.empty else pd.DataFrame()

    if s_chall.empty:
        st.warning(f"No challans for style '{pe_style}'. Add challan in 🧾 Challan Management first.")
        st.stop()

    ch_map = {}
    for _,r in s_chall.iterrows():
        qty  = int(safe_num(pd.Series([r["Total_Qty"]])).iloc[0])
        rec  = int(safe_num(pd.Series([r.get("Received_Qty",0)])).iloc[0])
        lbl  = f"{r['Challan_No']} | {r.get('Party','—')} | Qty:{qty} | Recv:{rec}"
        ch_map[lbl] = r

    sel_ch_key  = st.selectbox("🧾 Select Challan", list(ch_map.keys()), key="sel_ch")
    ch_row      = ch_map[sel_ch_key]
    challan_no  = ch_row["Challan_No"]

    if "prev_challan" not in st.session_state:
        st.session_state.prev_challan = challan_no
    if st.session_state.prev_challan != challan_no:
        st.session_state.prev_challan = challan_no
        st.rerun()

    ch_qty = int(safe_num(pd.Series([ch_row["Total_Qty"]])).iloc[0])
    ch_rec = int(safe_num(pd.Series([ch_row.get("Received_Qty",0)])).iloc[0])
    st.markdown(
        f'<div class="ro-field">Challan: <b>{challan_no}</b> &nbsp;|&nbsp; '
        f'Style: <b>{pe_style}</b> &nbsp;|&nbsp; '
        f'Total: <b>{ch_qty} pcs</b> &nbsp;|&nbsp; '
        f'Received: <b>{ch_rec}</b> &nbsp;|&nbsp; '
        f'Pending: <b>{ch_qty-ch_rec}</b></div>',
        unsafe_allow_html=True)

    style_ops = sm[sm["Style"] == pe_style][["Operation","Target","Rate_Rs"]]
    if style_ops.empty:
        st.warning(f"No operations defined for style '{pe_style}'. Add in ⚙️ Master Data.")
        st.stop()

    op_list = [""] + style_ops["Operation"].tolist()
    op_info = {}
    for _, row in style_ops.iterrows():
        op_name = row["Operation"]
        daily_target = int(row["Target"])
        op_info[op_name] = {
            "Target": daily_target,
            "Rate_Rs": float(row["Rate_Rs"]),
            "Hourly_Target": max(1, daily_target // 8)
        }

    op_pills = " ".join([f'<span class="sz-pill sz-xl">{op}</span>' for op in style_ops["Operation"].tolist()])
    st.markdown(f'<div class="info-box">📋 <b>Available Operations for {pe_style}:</b><br>{op_pills}</div>', unsafe_allow_html=True)

    st.markdown("---")
    col_hdr, col_btn = st.columns([3, 1])
    with col_hdr:
        st.markdown('<div class="sec-hdr">⏱ Hour-wise Piece Entry</div>', unsafe_allow_html=True)
    with col_btn:
        if st.button("🔄 Clear All", key="clear_all_hours", use_container_width=True):
            st.rerun()

    st.markdown('<div class="info-box">📱 Fill hour by hour. Operation auto-fills from previous hour. 🍽️ Lunch 13:00–14:00 is auto-skipped.</div>', unsafe_allow_html=True)

    h_vals = {}
    op_vals = {}
    prev_op = None
    from collections import defaultdict
    op_totals = defaultdict(lambda: {"pieces": 0, "hours": 0, "value": 0})

    for hcol, hlbl in zip(HOUR_COLS, HOUR_LBLS):
        is_lunch = (hcol == "H_13_14")
        if is_lunch:
            st.markdown(f"""
            <div style="background:#fafafa;border:1px solid #e0e0e0;border-radius:8px;padding:12px;margin:10px 0;text-align:center;">
                <div style="font-size:.9rem;color:#9e9e9e;">🍽️ <b>13:00 – 14:00</b></div>
                <div style="font-size:.75rem;color:#bdbdbd;margin-top:4px;">Lunch Break</div>
            </div>""", unsafe_allow_html=True)
            op_vals[hcol] = None
            h_vals[hcol] = 0
        else:
            with st.container():
                st.markdown(f"""
                <div style="background:#e3f2fd;border-left:4px solid #2c5aa0;padding:8px 12px;border-radius:4px;margin:8px 0 4px;">
                    <b style="font-size:1rem;color:#1a3a5c;">🕐 {hlbl}</b>
                </div>""", unsafe_allow_html=True)

                default_idx = 0
                if prev_op and prev_op in op_list:
                    default_idx = op_list.index(prev_op)

                col1, col2 = st.columns([3, 2])
                with col1:
                    selected_op = st.selectbox(
                        "Operation", op_list, index=default_idx,
                        key=f"op_{hcol}", help=f"Select operation for {hlbl}")
                    op_vals[hcol] = selected_op if selected_op != "" else None
                    if selected_op and selected_op != "":
                        op_data = op_info[selected_op]
                        st.markdown(
                            f"<div style='background:#fff3e0;padding:6px 10px;border-radius:4px;margin-top:4px;'>"
                            f"<b style='color:#e65100;font-size:.85rem;'>🎯 Target: {op_data['Hourly_Target']} pcs/hr</b> "
                            f"<span style='color:#666;font-size:.8rem;'>| Rate: ₹{op_data['Rate_Rs']}/pc</span>"
                            f"</div>", unsafe_allow_html=True)
                        prev_op = selected_op

                with col2:
                    disabled = (not op_vals[hcol] or op_vals[hcol] == "")
                    h_vals[hcol] = st.number_input(
                        f"Pieces Done", min_value=0, step=1, value=0,
                        key=f"hv_{hcol}", disabled=disabled)

                if op_vals[hcol] and op_vals[hcol] != "" and h_vals[hcol] > 0:
                    op_data = op_info[op_vals[hcol]]
                    hourly_eff = (h_vals[hcol] / op_data['Hourly_Target'] * 100) if op_data['Hourly_Target'] > 0 else 0
                    if hourly_eff >= 100:
                        bg_color="#e8f5e9"; text_color="#2e7d32"; icon="✅"; msg="Excellent!"
                    elif hourly_eff >= 80:
                        bg_color="#fff3e0"; text_color="#f57c00"; icon="⚡"; msg="Good"
                    else:
                        bg_color="#ffebee"; text_color="#c62828"; icon="⚠️"; msg="Below target"
                    st.markdown(f"""
                    <div style="background:{bg_color};border-radius:6px;padding:8px 12px;margin-top:8px;text-align:center;">
                        <span style="font-size:1.1rem;font-weight:700;color:{text_color};">{icon} {hourly_eff:.0f}%</span>
                        <span style="font-size:.8rem;color:#666;margin-left:8px;">({msg})</span>
                    </div>""", unsafe_allow_html=True)
                    op_totals[op_vals[hcol]]["pieces"] += h_vals[hcol]
                    op_totals[op_vals[hcol]]["hours"] += 1
                    op_totals[op_vals[hcol]]["value"] += h_vals[hcol] * op_data["Rate_Rs"]

                st.markdown("---")

    total_pcs = sum(h_vals.values())
    total_value = sum(data["value"] for data in op_totals.values())

    if total_pcs > 0:
        st.markdown('<div class="sec-hdr">📊 Today\'s Summary</div>', unsafe_allow_html=True)
        if op_totals:
            for op_name, data in op_totals.items():
                op_data = op_info[op_name]
                daily_eff = (data["pieces"] / op_data["Target"] * 100) if op_data["Target"] > 0 else 0
                if daily_eff >= 100:
                    badge_color="#2e7d32"; badge_text="✅ Excellent"
                elif daily_eff >= 80:
                    badge_color="#f57c00"; badge_text="⚡ Good"
                else:
                    badge_color="#c62828"; badge_text="⚠️ Below Target"
                st.markdown(f"""
                <div style="background:#f5f5f5;border-left:4px solid {badge_color};padding:12px 16px;border-radius:6px;margin:8px 0;">
                    <div style="font-size:.9rem;font-weight:600;color:#424242;margin-bottom:6px;">{op_name}</div>
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
                        <div style="margin-right:12px;">
                            <span style="font-size:1.3rem;font-weight:700;color:#1a3a5c;">{data["pieces"]}</span>
                            <span style="font-size:.8rem;color:#666;"> / {op_data['Target']} pcs</span>
                        </div>
                        <div>
                            <span style="font-size:1.1rem;font-weight:700;color:{badge_color};">{daily_eff:.0f}%</span>
                            <span style="font-size:.8rem;color:#666;margin-left:8px;">₹{data['value']:.0f}</span>
                        </div>
                    </div>
                    <div style="margin-top:4px;font-size:.75rem;color:{badge_color};font-weight:600;">{badge_text}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1a3a5c,#2c5aa0);color:#fff;border-radius:10px;padding:20px;text-align:center;margin:16px 0;">
            <div style="font-size:.8rem;opacity:.7;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Total Production</div>
            <div style="font-size:2.5rem;font-weight:700;font-family:'IBM Plex Mono',monospace;">{total_pcs}</div>
            <div style="font-size:.85rem;opacity:.8;margin:4px 0;">pieces completed</div>
            <div style="border-top:1px solid rgba(255,255,255,0.3);margin:12px 0;"></div>
            <div style="font-size:1.8rem;font-weight:700;">₹{total_value:,.0f}</div>
            <div style="font-size:.8rem;opacity:.7;">total value</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    save_disabled = total_pcs == 0
    if save_disabled:
        st.warning("⚠️ Enter at least one piece to save the entry.")

    if st.button("💾 Save Production Entry", key="pe_save", use_container_width=True,
                 type="primary", disabled=save_disabled):
        if not op_totals:
            st.error("No entries to save.")
        else:
            saved_ops = []
            for op_name, data in op_totals.items():
                op_data = op_info[op_name]
                op_pcs = data["pieces"]
                op_eff = round(op_pcs / op_data["Target"] * 100, 1) if op_data["Target"] > 0 else 0.0
                op_val = round(data["value"], 2)
                hour_row = {}
                for hcol in HOUR_COLS:
                    if op_vals.get(hcol) == op_name:
                        hour_row[hcol] = h_vals.get(hcol, 0)
                    else:
                        hour_row[hcol] = 0
                new_row = {
                    "Date": str(pe_date),
                    "Karigar_ID": k_row["Karigar_ID"],
                    "Karigar_Name": k_row["Name"],
                    "Challan_No": challan_no,
                    "Style": pe_style,
                    "Operation": op_name,
                    **hour_row,
                    "Total_Pieces": op_pcs,
                    "Target": op_data["Target"],
                    "Rate_Rs": op_data["Rate_Rs"],
                    "Efficiency_%": op_eff,
                    "Piece_Value_Rs": op_val,
                }
                st.session_state.production_log = pd.concat(
                    [st.session_state.production_log, pd.DataFrame([new_row])], ignore_index=True)
                badge = "🏆 Excellent" if op_eff >= 100 else ("⭐ Good" if op_eff >= 85 else ("✅ Fair" if op_eff >= 70 else "⚠️ Below Target"))
                saved_ops.append(f"• {op_name}: {op_pcs} pcs ({op_eff:.1f}%) — {badge} — ₹{op_val:.0f}")

            # ✅ SAVE TO GOOGLE SHEETS
            save_sheet("production_log", st.session_state.production_log)

            st.success(f"✅ **Saved {len(saved_ops)} operation(s)** for **{k_row['Name']}** — Synced to Google Sheets! 🟢\n\n" + "\n".join(saved_ops))
            st.balloons()
            st.rerun()

    st.markdown("---")
    st.markdown('<div class="sec-hdr">👷 Karigar-wise Summary</div>', unsafe_allow_html=True)
    if not st.session_state.production_log.empty:
        flt_d = st.date_input("View Date", value=date.today(), key="prod_flt")
        day_pl = st.session_state.production_log[st.session_state.production_log["Date"]==str(flt_d)].copy()
        if not day_pl.empty:
            for c in ["Total_Pieces","Target","Efficiency_%","Piece_Value_Rs"]:
                if c in day_pl.columns: day_pl[c]=safe_num(day_pl[c])
            sv1,sv2 = st.tabs(["📋 All Entries","👷 Summary by Karigar"])
            with sv1:
                sc=[c for c in["Karigar_Name","Challan_No","Style","Operation","Total_Pieces","Target","Efficiency_%","Piece_Value_Rs"] if c in day_pl.columns]
                st.dataframe(day_pl[sc], use_container_width=True, hide_index=True)
            with sv2:
                ks = day_pl.groupby(["Karigar_ID","Karigar_Name"]).agg(
                    Ops=("Operation","count"),
                    Total_Pieces=("Total_Pieces","sum"),
                    Total_Target=("Target","sum"),
                    Piece_Value=("Piece_Value_Rs","sum")
                ).reset_index()
                ks["Efficiency_%"]=(ks["Total_Pieces"]/ks["Total_Target"].replace(0,1)*100).round(1)
                ks["Grade"]=ks["Efficiency_%"].apply(lambda x:"⭐ A" if x>=100 else("✅ B" if x>=85 else("⚠️ C" if x>=70 else"❌ D")))
                st.dataframe(ks, use_container_width=True, hide_index=True)
                ch_s = day_pl.groupby(["Challan_No","Style"]).agg(
                    Pieces=("Total_Pieces","sum"), Value=("Piece_Value_Rs","sum"),
                    Ops=("Operation","nunique")).reset_index()
                st.markdown("**Challan-wise:**")
                st.dataframe(ch_s, use_container_width=True, hide_index=True)
            e1,e2=st.columns(2)
            excel_data, excel_ext, excel_mime = to_excel_bytes(day_pl)
            with e1: st.download_button("📥 Excel" if EXCEL_AVAILABLE else "📥 CSV",
                                       excel_data, f"prod_{flt_d}{excel_ext}", mime=excel_mime)
            with e2: st.download_button("📥 CSV", to_csv_bytes(day_pl), f"prod_{flt_d}.csv")
        else:
            st.info("No entries for selected date.")
    else:
        st.info("No production entries yet.")


# ══════════════════════════════════════════════════════════
# TAB 3 ─ CHALLAN MANAGEMENT
# ══════════════════════════════════════════════════════════
with tab_challan:
    st.markdown('<div class="sec-hdr">🧾 Challan Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Add challans, track received quantity and deposit.</div>', unsafe_allow_html=True)

    import_section("challan_master", "challan_master", "Challan Master")

    with st.expander("➕ Add New Challan", expanded=True):
        with st.form("add_ch", clear_on_submit=True):
            ca1, ca2 = st.columns(2)
            with ca1:
                c_no    = st.text_input("Challan No *", placeholder="e.g. 10220-2526")
                c_style = st.selectbox("Style *", sm["Style"].unique().tolist() if not sm.empty else [""])
                c_party = st.text_input("Party Name", placeholder="e.g. Aashirwad Garments")
            with ca2:
                c_qty   = st.number_input("Total Qty *", min_value=1, step=1, value=100)
                c_rec   = st.number_input("Received Qty", min_value=0, step=1, value=0)
                c_dep   = st.number_input("Deposit (₹)", min_value=0.0, step=100.0, value=0.0)
                c_rate  = st.number_input("Rate/Pc (₹)", min_value=0.0, step=1.0, value=35.0)
            c_date  = st.date_input("Issue Date", value=date.today())
            if st.form_submit_button("✅ Add Challan", use_container_width=True):
                if not c_no:
                    st.error("Challan No is required")
                else:
                    st.session_state.challan_master = pd.concat([
                        st.session_state.challan_master,
                        pd.DataFrame([{"Challan_No":c_no,"Style":c_style,"Party":c_party,
                            "Total_Qty":int(c_qty),"Received_Qty":int(c_rec),
                            "Deposit_Rs":float(c_dep),"Rate_Per_Pc":float(c_rate),
                            "Date":str(c_date),"Delivery_By":""}])
                    ], ignore_index=True)
                    # ✅ SAVE TO GOOGLE SHEETS
                    save_sheet("challan_master", st.session_state.challan_master)
                    st.success(f"✅ Challan {c_no} added — {c_qty} pcs — Saved to Google Sheets! 🟢")
                    st.rerun()

    st.markdown('<div class="sec-hdr">📋 Challan Register</div>', unsafe_allow_html=True)
    cm = st.session_state.challan_master.copy()
    if not cm.empty:
        cm["Pending"] = safe_num(cm["Total_Qty"]) - safe_num(cm.get("Received_Qty", 0))
        cm["Status"]  = cm["Pending"].apply(lambda x: "✅ Complete" if x <= 0 else f"⏳ {int(x)} pending")

        sx1, sx2, sx3, sx4 = st.columns(4)
        sx1.metric("Total Challans",     len(cm))
        sx2.metric("Completed",          len(cm[cm["Pending"] <= 0]))
        sx3.metric("In Progress",        len(cm[cm["Pending"] > 0]))
        lv = (safe_num(cm["Total_Qty"]) * safe_num(cm.get("Rate_Per_Pc", 0))).sum()
        sx4.metric("Total Labour Value", f"₹{lv:,.0f}")

        show_c = [c for c in ["Challan_No","Style","Party","Total_Qty","Received_Qty","Pending","Status","Rate_Per_Pc","Deposit_Rs","Date"] if c in cm.columns]
        st.dataframe(cm[show_c], use_container_width=True, hide_index=True)

        st.markdown('<div class="sec-hdr">✏️ Update Challan</div>', unsafe_allow_html=True)
        upd_ch  = st.selectbox("Select Challan", cm["Challan_No"].tolist(), key="upd_ch")
        sel_row = cm[cm["Challan_No"] == upd_ch]
        if not sel_row.empty:
            sr = sel_row.iloc[0]
            u1, u2, u3, u4 = st.columns(4)
            with u1:
                new_qty = st.number_input("Total Qty", min_value=1, step=1,
                    value=int(safe_num(pd.Series([sr.get("Total_Qty", 1)])).iloc[0]), key="u_qty")
            with u2:
                new_rec = st.number_input("Received Qty", min_value=0, step=1,
                    value=int(safe_num(pd.Series([sr.get("Received_Qty", 0)])).iloc[0]), key="u_rec")
            with u3:
                new_dep = st.number_input("Deposit (₹)", min_value=0.0, step=100.0,
                    value=float(safe_num(pd.Series([sr.get("Deposit_Rs", 0)])).iloc[0]), key="u_dep")
            with u4:
                new_rate = st.number_input("Rate/Pc (₹)", min_value=0.0, step=1.0,
                    value=float(safe_num(pd.Series([sr.get("Rate_Per_Pc", 0)])).iloc[0]), key="u_rate")

            if st.button("💾 Update Challan", key="do_upd", use_container_width=True):
                idx = st.session_state.challan_master[st.session_state.challan_master["Challan_No"] == upd_ch].index
                if len(idx) > 0:
                    st.session_state.challan_master.loc[idx[0], "Total_Qty"]    = new_qty
                    st.session_state.challan_master.loc[idx[0], "Received_Qty"] = new_rec
                    st.session_state.challan_master.loc[idx[0], "Deposit_Rs"]   = new_dep
                    st.session_state.challan_master.loc[idx[0], "Rate_Per_Pc"]  = new_rate
                    # ✅ SAVE TO GOOGLE SHEETS
                    save_sheet("challan_master", st.session_state.challan_master)
                    st.success(f"✅ {upd_ch} updated — Saved to Google Sheets! 🟢")
                    st.rerun()

    excel_data, excel_ext, excel_mime = to_excel_bytes(st.session_state.challan_master)
    st.download_button("📥 Export Challans" + (" (Excel)" if EXCEL_AVAILABLE else " (CSV)"),
                      excel_data, f"challans{excel_ext}", mime=excel_mime)


# ══════════════════════════════════════════════════════════
# TAB 4 ─ STYLE COSTING
# ══════════════════════════════════════════════════════════
with tab_style:
    st.markdown('<div class="sec-hdr">💎 Style-wise Costing — Profit & Loss</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Filter by month to see cost vs party rate and profit/loss per piece.</div>', unsafe_allow_html=True)

    f1,f2,f3 = st.columns(3)
    with f1:
        mo_list = ["All"]
        if not st.session_state.challan_master.empty:
            try:
                m_d = pd.to_datetime(st.session_state.challan_master["Date"],errors="coerce").dropna()
                mo_list += sorted(m_d.dt.strftime("%Y-%m").unique().tolist(), reverse=True)
            except: pass
        sel_mo = st.selectbox("📅 Month", mo_list, key="sc_mo")
    with f2:
        st_list = ["All"] + (sm["Style"].unique().tolist() if not sm.empty else [])
        sel_st  = st.selectbox("👗 Style", st_list, key="sc_st")
    with f3:
        pt_list = ["All"]
        if not st.session_state.challan_master.empty and "Party" in st.session_state.challan_master.columns:
            pt_list += st.session_state.challan_master["Party"].dropna().unique().tolist()
        sel_pt = st.selectbox("🏭 Party", pt_list, key="sc_pt")

    cm_sc = st.session_state.challan_master.copy()
    if not cm_sc.empty:
        cm_sc["Date_dt"] = pd.to_datetime(cm_sc["Date"],errors="coerce")
        if sel_mo!="All": cm_sc=cm_sc[cm_sc["Date_dt"].dt.strftime("%Y-%m")==sel_mo]
        if sel_st!="All": cm_sc=cm_sc[cm_sc["Style"]==sel_st]
        if sel_pt!="All" and "Party" in cm_sc.columns: cm_sc=cm_sc[cm_sc["Party"]==sel_pt]

    if cm_sc.empty:
        st.info("No challans match the selected filters.")
    else:
        slr = sm.groupby("Style")["Rate_Rs"].sum().reset_index() if not sm.empty else pd.DataFrame(columns=["Style","Rate_Rs"])
        slr.columns = ["Style","Labour_Rate_Per_Pc"]
        cm_sc = cm_sc.merge(slr, on="Style", how="left").fillna({"Labour_Rate_Per_Pc":0})
        for col in ["Total_Qty","Labour_Rate_Per_Pc","Rate_Per_Pc","Deposit_Rs","Received_Qty"]:
            cm_sc[col] = safe_num(cm_sc.get(col,0))
        cm_sc["Labour_Cost"]  = (cm_sc["Total_Qty"]*cm_sc["Labour_Rate_Per_Pc"]).round(2)
        cm_sc["Party_Value"]  = (cm_sc["Total_Qty"]*cm_sc["Rate_Per_Pc"]).round(2)
        cm_sc["Total_Cost"]   = (cm_sc["Labour_Cost"]+cm_sc["Deposit_Rs"]).round(2)
        cm_sc["PL"]           = (cm_sc["Party_Value"]-cm_sc["Total_Cost"]).round(2)
        cm_sc["PL_Per_Pc"]    = (cm_sc["PL"]/cm_sc["Total_Qty"].replace(0,1)).round(2)
        cm_sc["Margin_%"]     = (cm_sc["PL"]/cm_sc["Party_Value"].replace(0,1)*100).round(1)
        cm_sc["Result"]       = cm_sc["PL"].apply(lambda x:"✅ Profit" if x>0 else("🔴 Loss" if x<0 else"↔ Break-even"))

        tv=cm_sc["Party_Value"].sum(); tc=cm_sc["Total_Cost"].sum(); tpl=cm_sc["PL"].sum()
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total Pieces",  f"{int(cm_sc['Total_Qty'].sum()):,}")
        m2.metric("Party Value",   f"₹{tv:,.0f}")
        m3.metric("Total Cost",    f"₹{tc:,.0f}")
        m4.metric("Net P&L",       f"₹{tpl:,.0f}", delta=f"{tpl:+.0f}")

        dc=[c for c in["Challan_No","Style","Party","Total_Qty","Received_Qty",
            "Labour_Rate_Per_Pc","Labour_Cost","Deposit_Rs","Rate_Per_Pc",
            "Party_Value","Total_Cost","PL","PL_Per_Pc","Margin_%","Result"] if c in cm_sc.columns]
        st.dataframe(cm_sc[dc], use_container_width=True, hide_index=True)

        st.markdown('<div class="sec-hdr">Style Roll-up</div>', unsafe_allow_html=True)
        sru = cm_sc.groupby("Style").agg(
            Challans=("Challan_No","nunique"), Qty=("Total_Qty","sum"),
            Party_Value=("Party_Value","sum"), Cost=("Total_Cost","sum"), PL=("PL","sum")
        ).reset_index()
        sru["Margin_%"]=(sru["PL"]/sru["Party_Value"].replace(0,1)*100).round(1)
        sru["Net"]=sru["PL"].apply(lambda x:"✅ Profit" if x>0 else "🔴 Loss")
        st.dataframe(sru, use_container_width=True, hide_index=True)

        e1,e2=st.columns(2)
        excel_data, excel_ext, excel_mime = to_excel_bytes(cm_sc[dc])
        with e1: st.download_button("📥 Style Costing" + (" Excel" if EXCEL_AVAILABLE else " CSV"),
                                   excel_data, f"style_pl_{sel_mo}{excel_ext}", mime=excel_mime)
        with e2: st.download_button("📥 Style Costing CSV", to_csv_bytes(cm_sc[dc]), f"style_pl_{sel_mo}.csv")


# ══════════════════════════════════════════════════════════
# TAB 5 ─ EFFICIENCY
# ══════════════════════════════════════════════════════════
with tab_eff:
    st.markdown('<div class="sec-hdr">📊 Efficiency Analysis</div>', unsafe_allow_html=True)
    pl_e = st.session_state.production_log
    if pl_e.empty:
        st.info("No production data yet.")
    else:
        df = pl_e.copy()
        for c in ["Total_Pieces","Target","Efficiency_%","Piece_Value_Rs"]:
            if c in df.columns: df[c]=safe_num(df[c])
        df["Date_dt"] = pd.to_datetime(df["Date"],errors="coerce")
        ef1,ef2 = st.columns(2)
        with ef1: dr=st.date_input("Date Range",value=[date.today()-timedelta(days=7),date.today()],key="eff_dr")
        with ef2: sf=st.multiselect("Filter Style",df["Style"].unique().tolist(),default=df["Style"].unique().tolist(),key="eff_sf")
        if len(dr)==2:
            mask=(df["Date_dt"]>=pd.Timestamp(dr[0]))&(df["Date_dt"]<=pd.Timestamp(dr[1]))&df["Style"].isin(sf)
            df_f=df[mask].copy()
        else: df_f=df[df["Style"].isin(sf)].copy()

        if df_f.empty: st.warning("No data for filters.")
        else:
            ec1,ec2,ec3=st.columns(3)
            ec1.metric("Avg Efficiency",   f"{df_f['Efficiency_%'].mean():.1f}%")
            ec2.metric("Total Piece Value",f"₹{df_f['Piece_Value_Rs'].sum():,.0f}")
            ec3.metric("Total Pieces",     f"{int(df_f['Total_Pieces'].sum()):,}")

            st.markdown('<div class="sec-hdr">Karigar-wise</div>', unsafe_allow_html=True)
            ke=df_f.groupby("Karigar_Name").agg(
                Avg_Eff=("Efficiency_%","mean"),Pieces=("Total_Pieces","sum"),
                Value=("Piece_Value_Rs","sum"),Ops=("Operation","count")).round(2).reset_index()
            ke["Grade"]=ke["Avg_Eff"].apply(lambda x:"A – Excellent" if x>=100 else("B – Good" if x>=85 else("C – Average" if x>=70 else"D – Below Target")))
            st.dataframe(ke,use_container_width=True,hide_index=True)

            st.markdown('<div class="sec-hdr">Operation-wise</div>', unsafe_allow_html=True)
            oe=df_f.groupby("Operation").agg(
                Avg_Eff=("Efficiency_%","mean"),Pieces=("Total_Pieces","sum"),
                Value=("Piece_Value_Rs","sum")).round(2).reset_index().sort_values("Avg_Eff")
            st.dataframe(oe,use_container_width=True,hide_index=True)
            bn=oe[oe["Avg_Eff"]<80]
            if not bn.empty:
                st.markdown(f'<div class="warn-box">⚠️ <b>Bottleneck Operations (below 80%):</b> {", ".join(bn["Operation"].tolist())}</div>',unsafe_allow_html=True)

            e1,e2=st.columns(2)
            excel_data, excel_ext, excel_mime = to_excel_bytes(ke)
            with e1: st.download_button("📥 " + ("Excel" if EXCEL_AVAILABLE else "CSV"),
                                       excel_data, f"efficiency{excel_ext}", mime=excel_mime)
            with e2: st.download_button("📥 CSV", to_csv_bytes(ke), "efficiency.csv")


# ══════════════════════════════════════════════════════════
# TAB 6 ─ PAYROLL
# ══════════════════════════════════════════════════════════
with tab_pay:
    st.markdown('<div class="sec-hdr">💰 Payroll Calculator</div>', unsafe_allow_html=True)
    p1,p2=st.columns(2)
    with p1: pay_s=st.date_input("Pay Period Start",value=date.today()-timedelta(days=6),key="pay_s")
    with p2: pay_e=st.date_input("Pay Period End",  value=date.today(),key="pay_e")
    if st.button("📊 Calculate Payroll",use_container_width=True):
        att_p=st.session_state.karigar_attendance
        if att_p.empty: st.warning("No attendance data.")
        else:
            ap=att_p.copy(); ap["Date_dt"]=pd.to_datetime(ap["Date"])
            ap=ap[(ap["Date_dt"]>=pd.Timestamp(pay_s))&(ap["Date_dt"]<=pd.Timestamp(pay_e))]
            if ap.empty: st.warning("No records in pay period.")
            else:
                for c in["Payable_Hrs","Normal_Pay","OT_Hours","OT_Pay","Total_Pay"]:
                    if c in ap.columns: ap[c]=safe_num(ap[c])
                pr=ap.groupby("E_Code").agg(
                    Name=("Name","first"),Days=("Date","nunique"),Hrs=("Payable_Hrs","sum"),
                    Normal=("Normal_Pay","sum"),OT_Hrs=("OT_Hours","sum"),OT_Pay=("OT_Pay","sum"),
                    Total=("Total_Pay","sum")).round(2).reset_index()
                st.dataframe(pr,use_container_width=True,hide_index=True)
                st.metric("Total Payroll",f"₹{pr['Total'].sum():,.2f}")
                px1,px2=st.columns(2)
                excel_data, excel_ext, excel_mime = to_excel_bytes(pr)
                with px1: st.download_button("📥 Payroll" + (" Excel" if EXCEL_AVAILABLE else " CSV"),
                                            excel_data, f"payroll_{pay_s}_{pay_e}{excel_ext}",
                                            mime=excel_mime, key="py_x")
                with px2: st.download_button("📥 Payroll CSV", to_csv_bytes(pr), f"payroll_{pay_s}_{pay_e}.csv", key="py_c")


# ══════════════════════════════════════════════════════════
# TAB 7 ─ KARIGAR ATTENDANCE
# ══════════════════════════════════════════════════════════
with tab_att:
    st.markdown('<div class="sec-hdr">🕐 Karigar Salary & Attendance</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box"><b>Shift:</b> 9:00–18:00 | <b>Lunch:</b> 13:00–14:00 (unpaid) | <b>OT:</b> after 18:00</div>',unsafe_allow_html=True)
    ot_m=st.selectbox("OT Multiplier",[1.0,1.5,2.0],index=1,key="ot_m")
    import_section("karigar_attendance","karigar_attendance","Karigar Attendance")

    att_df=st.session_state.karigar_attendance
    if not att_df.empty and "Total_Pay" not in att_df.columns:
        emp4=st.session_state.employee_master; rows4=[]
        for _,row in att_df.iterrows():
            er=emp4[emp4["E_Code"]==row["E_Code"]]
            if not er.empty:
                dr=float(er["Daily_Rate_Rs"].values[0]); nm=er["Name"].values[0]
                ph,ld,py,hr,np_,oh,op,tp=calc_salary(str(row["In_Punch"]),str(row["Out_Punch"]),dr,ot_m)
                rows4.append({**row.to_dict(),"Name":nm,"Total_Presence_Hrs":ph,"Lunch_Deduction_Hrs":ld,
                    "Payable_Hrs":py,"Hourly_Rate_Rs":hr,"Normal_Pay":np_,"OT_Hours":oh,"OT_Pay":op,"Total_Pay":tp})
            else: rows4.append(row.to_dict())
        st.session_state.karigar_attendance=pd.DataFrame(rows4)
        save_sheet("karigar_attendance", st.session_state.karigar_attendance)
        st.rerun()

    with st.expander("✏️ Manual Attendance Entry",expanded=True):
        ek=st.session_state.employee_master[st.session_state.employee_master["Type"]=="Karigar"]
        eo={f"{r['E_Code']} – {r['Name']}":r for _,r in ek.iterrows()}
        with st.form("att_form",clear_on_submit=True):
            ak1,ak2,ak3=st.columns(3)
            with ak1: ad=st.date_input("Date",value=date.today()); es=st.selectbox("Employee",list(eo.keys()))
            with ak2: ip=st.text_input("In Punch (HH:MM)",value="09:00"); op2=st.text_input("Out Punch (HH:MM)",value="18:00")
            with ak3:
                er2=eo[es]; dr2=float(er2["Daily_Rate_Rs"])
                st.info(f"Daily: ₹{dr2}\nHourly: ₹{dr2/8:.2f}\nOT: {ot_m}×")
            if st.form_submit_button("💾 Calculate & Save"):
                ph,ld,py,hr,np_,oh,op3,tp=calc_salary(ip,op2,dr2,ot_m)
                na={"Date":str(ad),"E_Code":er2["E_Code"],"Name":er2["Name"],
                    "In_Punch":ip,"Out_Punch":op2,"Total_Presence_Hrs":ph,
                    "Lunch_Deduction_Hrs":ld,"Payable_Hrs":py,"Hourly_Rate_Rs":hr,
                    "Normal_Pay":np_,"OT_Hours":oh,"OT_Pay":op3,"Total_Pay":tp}
                st.session_state.karigar_attendance=pd.concat(
                    [st.session_state.karigar_attendance,pd.DataFrame([na])],ignore_index=True)
                # ✅ SAVE TO GOOGLE SHEETS
                save_sheet("karigar_attendance", st.session_state.karigar_attendance)
                st.success(f"✅ {er2['Name']} | {py}h payable | ₹{tp} — Saved to Google Sheets! 🟢")

    with st.expander("🔄 Auto-Calculate Attendance from Production Entries",expanded=False):
        st.markdown('<div class="info-box">Calculates attendance based on hour-wise production entries.</div>', unsafe_allow_html=True)
        if st.button("📊 Calculate Attendance from Production Log",use_container_width=True):
            pl = st.session_state.production_log
            if pl.empty:
                st.warning("No production entries found.")
            else:
                att_records = []
                for (d, kid), group in pl.groupby(["Date", "Karigar_ID"]):
                    kar_name = group["Karigar_Name"].iloc[0] if "Karigar_Name" in group.columns else f"K-{kid}"
                    hour_cols_worked = [h for h in HOUR_COLS if h != "H_13_14" and any(group[h].astype(str).str.strip() != "0")]
                    hours_worked = len(hour_cols_worked)
                    if hours_worked > 0:
                        emp_rec = st.session_state.employee_master[st.session_state.employee_master["E_Code"] == kid]
                        if not emp_rec.empty:
                            daily_rate = float(emp_rec["Daily_Rate_Rs"].values[0])
                            hourly_rate = daily_rate / 8
                            normal_pay = hours_worked * hourly_rate if hours_worked <= 8 else 8 * hourly_rate
                            ot_hours = max(hours_worked - 8, 0)
                            ot_pay = ot_hours * hourly_rate * ot_m
                            total_pay = normal_pay + ot_pay
                            att_records.append({
                                "Date": str(d), "E_Code": kid, "Name": kar_name,
                                "In_Punch": "09:00", "Out_Punch": "18:00",
                                "Total_Presence_Hrs": float(hours_worked),
                                "Lunch_Deduction_Hrs": 1.0 if hours_worked >= 9 else 0.0,
                                "Payable_Hrs": float(max(hours_worked - 1, 0)) if hours_worked >= 9 else float(hours_worked),
                                "Hourly_Rate_Rs": hourly_rate, "Normal_Pay": normal_pay,
                                "OT_Hours": ot_hours, "OT_Pay": ot_pay, "Total_Pay": total_pay
                            })
                if att_records:
                    new_att = pd.DataFrame(att_records)
                    st.session_state.karigar_attendance = pd.concat(
                        [st.session_state.karigar_attendance, new_att], ignore_index=True
                    ).drop_duplicates(subset=["Date", "E_Code"], keep="last")
                    # ✅ SAVE TO GOOGLE SHEETS
                    save_sheet("karigar_attendance", st.session_state.karigar_attendance)
                    st.success(f"✅ Generated {len(att_records)} attendance records — Saved to Google Sheets! 🟢")
                    st.dataframe(new_att, use_container_width=True, hide_index=True)
                else:
                    st.info("No working hours found in production entries.")

    if not st.session_state.karigar_attendance.empty:
        af=st.date_input("Filter Date",value=date.today(),key="att_f")
        av=st.session_state.karigar_attendance[st.session_state.karigar_attendance["Date"]==str(af)]
        if not av.empty:
            st.dataframe(av,use_container_width=True,hide_index=True)
            excel_data, excel_ext, excel_mime = to_excel_bytes(av)
            st.download_button("📥 Download" + (" Excel" if EXCEL_AVAILABLE else " CSV"),
                             excel_data, f"att_{af}{excel_ext}", mime=excel_mime)


# ══════════════════════════════════════════════════════════
# TAB 8 ─ OPERATING STAFF
# ══════════════════════════════════════════════════════════
with tab_op:
    st.markdown('<div class="sec-hdr">🏢 Operating Staff</div>', unsafe_allow_html=True)
    import_section("operating_attendance","operating_attendance","Operating Staff Attendance")
    eo2=st.session_state.employee_master[st.session_state.employee_master["Type"]=="Operating"]
    oo2={f"{r['E_Code']} – {r['Name']}":r for _,r in eo2.iterrows()}

    if len(oo2) == 0:
        st.warning("⚠️ No Operating staff found. Add in Master Data → Employee Master tab first.")
    else:
        with st.expander("✏️ Manual Entry",expanded=True):
            with st.form("op_form",clear_on_submit=True):
                oa1,oa2,oa3=st.columns(3)
                with oa1: od=st.date_input("Date",value=date.today(),key="od2"); oem=st.selectbox("Employee",list(oo2.keys()),key="oe2")
                with oa2: oin=st.text_input("In",value="09:00",key="oin2"); oout=st.text_input("Out",value="18:00",key="oout2")
                with oa3:
                    er3=oo2[oem]; st.info(f"Hourly: ₹{er3['Hourly_Rate_Rs']}")
                if st.form_submit_button("Save"):
                    try:
                        fmt3="%H:%M"
                        hrs3=round(int((datetime.strptime(oout.strip(),fmt3)-datetime.strptime(oin.strip(),fmt3)).total_seconds())/3600,2)
                    except: hrs3=0
                    hr3=float(er3["Hourly_Rate_Rs"]); tp3=round(hrs3*hr3,2)
                    st.session_state.operating_attendance=pd.concat([st.session_state.operating_attendance,pd.DataFrame([{
                        "Date":str(od),"E_Code":er3["E_Code"],"Name":er3["Name"],
                        "In_Punch":oin,"Out_Punch":oout,"Total_Hours":hrs3,"Hourly_Rate_Rs":hr3,"Total_Pay":tp3
                    }])],ignore_index=True)
                    # ✅ SAVE TO GOOGLE SHEETS
                    save_sheet("operating_attendance", st.session_state.operating_attendance)
                    st.success(f"✅ {er3['Name']} | {hrs3}h | ₹{tp3} — Saved to Google Sheets! 🟢")


# ══════════════════════════════════════════════════════════
# TAB 9 ─ PERFORMANCE
# ══════════════════════════════════════════════════════════
with tab_perf:
    st.markdown('<div class="sec-hdr">🌟 Employee Performance Dashboard</div>', unsafe_allow_html=True)
    pl_p=st.session_state.production_log; att_p2=st.session_state.karigar_attendance
    if pl_p.empty or att_p2.empty:
        st.info("Need both production entries and attendance records.")
    else:
        pp1,pp2=st.columns(2)
        with pp1: ps=st.date_input("From",value=date.today()-timedelta(days=29),key="ps")
        with pp2: pe=st.date_input("To",  value=date.today(),key="pe2")
        pl3=pl_p.copy()
        for c in["Total_Pieces","Piece_Value_Rs","Efficiency_%"]:
            if c in pl3.columns: pl3[c]=safe_num(pl3[c])
        pl3["Date_dt"]=pd.to_datetime(pl3["Date"])
        pl3=pl3[(pl3["Date_dt"]>=pd.Timestamp(ps))&(pl3["Date_dt"]<=pd.Timestamp(pe))]
        psm=pl3.groupby("Karigar_ID").agg(
            Piece_Value=("Piece_Value_Rs","sum"),
            Total_Pieces=("Total_Pieces","sum"),
            Avg_Eff=("Efficiency_%","mean")).reset_index()
        att3=att_p2.copy(); att3["Date_dt"]=pd.to_datetime(att3["Date"])
        att3=att3[(att3["Date_dt"]>=pd.Timestamp(ps))&(att3["Date_dt"]<=pd.Timestamp(pe))]
        if "Total_Pay" in att3.columns:
            for c in["Total_Pay","Payable_Hrs"]: att3[c]=safe_num(att3[c])
            ss=att3.groupby("E_Code").agg(
                Name=("Name","first"),Days=("Date","nunique"),
                Hrs=("Payable_Hrs","sum"),Salary=("Total_Pay","sum")).round(2).reset_index()
            ss["E_Code"]=ss["E_Code"].astype(str)
            psm2=psm.rename(columns={"Karigar_ID":"E_Code"}).copy(); psm2["E_Code"]=psm2["E_Code"].astype(str)
            perf=ss.merge(psm2,on="E_Code",how="outer").fillna(0)
            perf["Piece_Value"]=perf["Piece_Value"].round(2)
            perf["Surplus"]=(perf["Piece_Value"]-perf["Salary"]).round(2)
            perf["ROI_%"]=(perf["Piece_Value"]/perf["Salary"].replace(0,1)*100).round(1)
            perf["Grade"]=perf["Avg_Eff"].apply(lambda x:"A – Excellent" if x>=100 else("B – Good" if x>=85 else("C – Average" if x>=70 else"D – Needs Improvement")))
            px1,px2,px3=st.columns(3)
            px1.metric("Total Piece Value",f"₹{perf['Piece_Value'].sum():,.0f}")
            px2.metric("Total Salary Paid",f"₹{perf['Salary'].sum():,.0f}")
            px3.metric("Net Surplus/Deficit",f"₹{perf['Surplus'].sum():,.0f}")
            st.dataframe(perf,use_container_width=True,hide_index=True)
        else: st.warning("Attendance records lack salary data. Add In/Out punches in Attendance tab.")


# ══════════════════════════════════════════════════════════
# TAB 10 ─ MASTER DATA
# ══════════════════════════════════════════════════════════
with tab_master:
    st.markdown('<div class="sec-hdr">⚙️ Master Data Management</div>', unsafe_allow_html=True)
    m1t,m2t,m3t = st.tabs(["👗 Style-Operation Master","👷 Karigar Master","🪪 Employee Master"])

    with m1t:
        import_section("style_master","style_master","Style Master")
        with st.expander("➕ Add Operation to Style",expanded=False):
            with st.form("sf",clear_on_submit=True):
                sc1,sc2=st.columns(2)
                with sc1: ns=st.text_input("Style Code"); no=st.text_input("Operation Name")
                with sc2: nt=st.number_input("Daily Target",min_value=1,step=1,value=80); nr=st.number_input("Rate/pc (₹)",min_value=0.0,step=0.25,format="%.2f",value=3.0)
                if st.form_submit_button("Add"):
                    st.session_state.style_master=pd.concat([st.session_state.style_master,
                        pd.DataFrame([{"Style":ns,"Operation":no,"Target":nt,"Rate_Rs":nr}])],ignore_index=True)
                    # ✅ SAVE TO GOOGLE SHEETS
                    save_sheet("style_master", st.session_state.style_master)
                    st.success(f"✅ Added operation '{no}' to style '{ns}' — Saved to Google Sheets! 🟢")
        st.dataframe(st.session_state.style_master,use_container_width=True,hide_index=True)
        excel_data, excel_ext, excel_mime = to_excel_bytes(st.session_state.style_master)
        st.download_button("📥 Export Style Master" + (" Excel" if EXCEL_AVAILABLE else " CSV"),
                          excel_data, f"style_master{excel_ext}", mime=excel_mime, key="dl_sm")

    with m2t:
        import_section("karigar_master","karigar_master","Karigar Master")
        with st.expander("➕ Add Karigar",expanded=False):
            with st.form("kf",clear_on_submit=True):
                kc1,kc2=st.columns(2)
                with kc1: k_id=st.text_input("Karigar ID (e.g. K006)"); k_nm=st.text_input("Full Name")
                with kc2: k_sk=st.selectbox("Skill",["Stitching","Cutting","Finishing","Hemming","Checking","Dupatta"]); k_rt=st.number_input("Daily Rate (₹)",min_value=100,step=10,value=420)
                if st.form_submit_button("Add Karigar"):
                    st.session_state.karigar_master=pd.concat([st.session_state.karigar_master,
                        pd.DataFrame([{"Karigar_ID":k_id,"Name":k_nm,"Skill":k_sk,"Daily_Rate_Rs":k_rt}])],ignore_index=True)
                    ec5=f"E{len(st.session_state.employee_master)+1:03d}"
                    st.session_state.employee_master=pd.concat([st.session_state.employee_master,
                        pd.DataFrame([{"E_Code":ec5,"Name":k_nm,"Type":"Karigar","Daily_Rate_Rs":k_rt,"Hourly_Rate_Rs":round(k_rt/8,2)}])],ignore_index=True)
                    # ✅ SAVE BOTH TO GOOGLE SHEETS
                    save_sheet("karigar_master", st.session_state.karigar_master)
                    save_sheet("employee_master", st.session_state.employee_master)
                    st.success(f"✅ Added {k_nm} — Saved to Google Sheets! 🟢")
        st.dataframe(st.session_state.karigar_master,use_container_width=True,hide_index=True)
        excel_data, excel_ext, excel_mime = to_excel_bytes(st.session_state.karigar_master)
        st.download_button("📥 Export Karigar Master" + (" Excel" if EXCEL_AVAILABLE else " CSV"),
                          excel_data, f"karigar_master{excel_ext}", mime=excel_mime, key="dl_km")

    with m3t:
        import_section("employee_master","employee_master","Employee Master")
        with st.expander("➕ Add Employee",expanded=False):
            with st.form("ef",clear_on_submit=True):
                ec1,ec2=st.columns(2)
                with ec1: em_c=st.text_input("E-Code"); em_n=st.text_input("Full Name"); em_t=st.selectbox("Type",["Karigar","Operating"])
                with ec2: em_d=st.number_input("Daily Rate (₹)",min_value=100,step=10,value=400); em_h=st.number_input("Hourly Rate (₹)",value=50.0,step=0.5,format="%.2f")
                if st.form_submit_button("Add Employee"):
                    st.session_state.employee_master=pd.concat([st.session_state.employee_master,
                        pd.DataFrame([{"E_Code":em_c,"Name":em_n,"Type":em_t,"Daily_Rate_Rs":em_d,"Hourly_Rate_Rs":em_h}])],ignore_index=True)
                    # ✅ SAVE TO GOOGLE SHEETS
                    save_sheet("employee_master", st.session_state.employee_master)
                    st.success(f"✅ Added employee {em_n} — Saved to Google Sheets! 🟢")
        st.dataframe(st.session_state.employee_master,use_container_width=True,hide_index=True)
        excel_data, excel_ext, excel_mime = to_excel_bytes(st.session_state.employee_master)
        st.download_button("📥 Export Employee Master" + (" Excel" if EXCEL_AVAILABLE else " CSV"),
                          excel_data, f"employee_master{excel_ext}", mime=excel_mime, key="dl_em")

st.markdown("---")
st.markdown("🧵 <b>Stitching Costing Interface v4.2 — Google Sheets Edition</b> — Yash Gallery Pvt Ltd", unsafe_allow_html=True)
