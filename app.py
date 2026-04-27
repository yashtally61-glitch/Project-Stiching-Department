"""
Stitching Costing Interface v4.3 — Yash Gallery Pvt Ltd
FIXES v4.3:
- Fix AttributeError: Karigar_ID / Name cast to str before .str.contains()
- Style Costing tab: challan-wise, actual expense from production_log vs party rate
- Hour-wise entry: compact card-grid layout (4 columns)
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
.hour-card{background:#fff;border:1px solid #dde3ea;border-radius:8px;padding:10px 12px;margin:4px;}
.hour-card-lunch{background:#fafafa;border:1px dashed #e0e0e0;border-radius:8px;padding:10px 12px;margin:4px;text-align:center;}
.eff-ex{background:#e8f5e9;color:#2e7d32;border-radius:4px;padding:3px 7px;font-size:.76rem;font-weight:600;display:inline-block;margin-top:4px;}
.eff-gd{background:#fff3e0;color:#e65100;border-radius:4px;padding:3px 7px;font-size:.76rem;font-weight:600;display:inline-block;margin-top:4px;}
.eff-bl{background:#ffebee;color:#c62828;border-radius:4px;padding:3px 7px;font-size:.76rem;font-weight:600;display:inline-block;margin-top:4px;}
.sum-bar{background:#1a3a5c;color:#fff;padding:10px 16px;border-radius:8px;display:flex;gap:20px;flex-wrap:wrap;margin:7px 0;}
.sb-item{text-align:center;}.sb-v{font-size:1.2rem;font-weight:700;font-family:'IBM Plex Mono',monospace;}
.sb-l{font-size:.7rem;opacity:.7;text-transform:uppercase;letter-spacing:.04em;}
.tpl-box{background:#fffde7;border:1px dashed #f9a825;border-radius:6px;padding:10px 14px;margin:6px 0;font-size:.84rem;}
.ch-cost-box{background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;padding:14px 16px;margin:8px 0;}
.ch-cost-profit{background:#e8f5e9;border-left:4px solid #2e7d32;border-radius:4px;padding:8px 12px;margin:4px 0;font-size:.88rem;color:#1b5e20;}
.ch-cost-loss{background:#ffebee;border-left:4px solid #c62828;border-radius:4px;padding:8px 12px;margin:4px 0;font-size:.88rem;color:#b71c1c;}
.ch-cost-pending{background:#fff8e1;border-left:4px solid #f9a825;border-radius:4px;padding:8px 12px;margin:4px 0;font-size:.88rem;color:#e65100;}
</style>
""", unsafe_allow_html=True)

HOUR_COLS = ["H_09_10","H_10_11","H_11_12","H_12_13","H_13_14",
             "H_14_15","H_15_16","H_16_17","H_17_18","H_18_19","H_19_20","H_20_21"]
HOUR_LBLS = ["9-10","10-11","11-12","12-13","13-14",
             "14-15","15-16","16-17","17-18","18-19","19-20","20-21"]
DATA_KEYS  = ["style_master","karigar_master","challan_master","production_log",
              "employee_master","karigar_attendance","operating_attendance"]
DEFAULT_PW = hashlib.sha256("admin123".encode()).hexdigest()

SHEET_ID = "1_cMCIn5KlvRqXS2yRy7nBidoTmgX8K48gTBaMAqBoFE"

# ═══════════════════════════════════════════
# GOOGLE SHEETS
# ═══════════════════════════════════════════
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
    st.success("✅ All data restored and saved!")

TEMPLATES = {
    "style_master": pd.DataFrame([{"Style":"1894YKDGREEN","Operation":"Cutting","Target":120,"Rate_Rs":2.50}]),
    "karigar_master": pd.DataFrame([{"Karigar_ID":"K001","Name":"Ramesh Kumar","Skill":"Stitching","Daily_Rate_Rs":450}]),
    "challan_master": pd.DataFrame([{"Challan_No":"10220-2526","Style":"1894YKDGREEN","Party":"Aashirwad Garments","Total_Qty":376,"Received_Qty":0,"Deposit_Rs":0.0,"Rate_Per_Pc":35,"Date":"2026-02-25","Delivery_By":"2026-03-07"}]),
    "production_log": pd.DataFrame([{"Date":"2026-02-25","Karigar_ID":"K001","Karigar_Name":"Ramesh Kumar","Challan_No":"10220-2526","Style":"1894YKDGREEN","Operation":"Cutting",**{h:10 for h in HOUR_COLS},"Total_Pieces":85,"Target":120,"Rate_Rs":2.50,"Efficiency_%":70.8,"Piece_Value_Rs":212.5}]),
    "employee_master": pd.DataFrame([{"E_Code":"E001","Name":"Ramesh Kumar","Type":"Karigar","Daily_Rate_Rs":450,"Hourly_Rate_Rs":56.25}]),
    "karigar_attendance": pd.DataFrame([{"Date":"2026-02-25","E_Code":"E001","In_Punch":"09:00","Out_Punch":"18:00"}]),
    "operating_attendance": pd.DataFrame([{"Date":"2026-02-25","E_Code":"E101","In_Punch":"09:00","Out_Punch":"18:00"}]),
}

DEFAULT_DATA = {
    "style_master": pd.DataFrame([
        {"Style":"1894YKDGREEN","Operation":"Cutting","Target":120,"Rate_Rs":2.50},
        {"Style":"1894YKDGREEN","Operation":"Stitching Front","Target":80,"Rate_Rs":4.00},
        {"Style":"1894YKDGREEN","Operation":"Stitching Back","Target":80,"Rate_Rs":4.00},
        {"Style":"1894YKDGREEN","Operation":"Dupatta Attach","Target":60,"Rate_Rs":5.50},
        {"Style":"1894YKDGREEN","Operation":"Side Seam","Target":90,"Rate_Rs":3.50},
        {"Style":"1894YKDGREEN","Operation":"Hemming","Target":100,"Rate_Rs":3.00},
        {"Style":"1894YKDGREEN","Operation":"Button Attach","Target":110,"Rate_Rs":2.00},
        {"Style":"1894YKDGREEN","Operation":"Finishing","Target":70,"Rate_Rs":4.50},
        {"Style":"1065YKBLUE","Operation":"Cutting","Target":120,"Rate_Rs":2.50},
        {"Style":"1065YKBLUE","Operation":"Stitching Front","Target":80,"Rate_Rs":4.00},
        {"Style":"1065YKBLUE","Operation":"Collar Attach","Target":60,"Rate_Rs":5.50},
        {"Style":"1065YKBLUE","Operation":"Side Seam","Target":90,"Rate_Rs":3.50},
        {"Style":"1065YKBLUE","Operation":"Finishing","Target":70,"Rate_Rs":4.50},
    ]),
    "karigar_master": pd.DataFrame([
        {"Karigar_ID":"K001","Name":"Ramesh Kumar","Skill":"Stitching","Daily_Rate_Rs":450},
        {"Karigar_ID":"K002","Name":"Suresh Singh","Skill":"Cutting","Daily_Rate_Rs":420},
        {"Karigar_ID":"K003","Name":"Priya Devi","Skill":"Finishing","Daily_Rate_Rs":400},
        {"Karigar_ID":"K004","Name":"Mohan Lal","Skill":"Stitching","Daily_Rate_Rs":460},
        {"Karigar_ID":"K005","Name":"Sunita Sharma","Skill":"Hemming","Daily_Rate_Rs":410},
    ]),
    "challan_master": pd.DataFrame([
        {"Challan_No":"10220-2526","Style":"1894YKDGREEN","Party":"Aashirwad Garments","Total_Qty":376,"Received_Qty":0,"Deposit_Rs":0.0,"Rate_Per_Pc":35,"Date":"2026-02-25","Delivery_By":"2026-03-07"},
    ]),
    "production_log": pd.DataFrame(columns=["Date","Karigar_ID","Karigar_Name","Challan_No","Style","Operation"]+HOUR_COLS+["Total_Pieces","Target","Rate_Rs","Efficiency_%","Piece_Value_Rs"]),
    "employee_master": pd.DataFrame([
        {"E_Code":"E001","Name":"Ramesh Kumar","Type":"Karigar","Daily_Rate_Rs":450,"Hourly_Rate_Rs":56.25},
        {"E_Code":"E002","Name":"Suresh Singh","Type":"Karigar","Daily_Rate_Rs":420,"Hourly_Rate_Rs":52.50},
        {"E_Code":"E003","Name":"Priya Devi","Type":"Karigar","Daily_Rate_Rs":400,"Hourly_Rate_Rs":50.00},
        {"E_Code":"E004","Name":"Mohan Lal","Type":"Karigar","Daily_Rate_Rs":460,"Hourly_Rate_Rs":57.50},
        {"E_Code":"E005","Name":"Sunita Sharma","Type":"Karigar","Daily_Rate_Rs":410,"Hourly_Rate_Rs":51.25},
        {"E_Code":"E101","Name":"Amit Sharma","Type":"Operating","Daily_Rate_Rs":600,"Hourly_Rate_Rs":75.00},
        {"E_Code":"E102","Name":"Kavita Rao","Type":"Operating","Daily_Rate_Rs":550,"Hourly_Rate_Rs":68.75},
    ]),
    "karigar_attendance": pd.DataFrame(columns=["Date","E_Code","Name","In_Punch","Out_Punch","Total_Presence_Hrs","Lunch_Deduction_Hrs","Payable_Hrs","Hourly_Rate_Rs","Normal_Pay","OT_Hours","OT_Pay","Total_Pay"]),
    "operating_attendance": pd.DataFrame(columns=["Date","E_Code","Name","In_Punch","Out_Punch","Total_Hours","Hourly_Rate_Rs","Total_Pay"]),
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

def import_section(key, session_key, label):
    tmpl = TEMPLATES.get(key, pd.DataFrame())
    with st.expander(f"📥 Import / Upload {label}", expanded=False):
        st.markdown(f'<div class="tpl-box">Required columns: <b>{", ".join(tmpl.columns.tolist())}</b></div>', unsafe_allow_html=True)
        dl1, dl2 = st.columns(2)
        excel_data, excel_ext, excel_mime = to_excel_bytes(tmpl)
        with dl1: st.download_button(f"⬇️ {'Excel' if EXCEL_AVAILABLE else 'CSV'} Template", data=excel_data, file_name=f"{key}_template{excel_ext}", mime=excel_mime, key=f"tpl_x_{key}", use_container_width=True)
        with dl2: st.download_button(f"⬇️ CSV Template", data=to_csv_bytes(tmpl), file_name=f"{key}_template.csv", mime="text/csv", key=f"tpl_c_{key}", use_container_width=True)
        st.markdown("---")
        uf = st.file_uploader(f"📂 Upload {label}", type=["csv","xlsx","xls"], key=f"uf_{key}")
        mode = st.radio("Import mode", ["➕ Append","🔄 Replace all"], key=f"md_{key}", horizontal=True)
        if uf is not None:
            df_new = read_file(uf)
            if df_new is not None:
                miss = [c for c in tmpl.columns.tolist() if c not in df_new.columns]
                if miss: st.error(f"❌ Missing columns: {miss}"); return
                st.success(f"✅ {len(df_new)} rows"); st.dataframe(df_new.head(5), use_container_width=True, hide_index=True)
                if st.button(f"✅ Confirm Import — {label}", key=f"ci_{key}", use_container_width=True):
                    st.session_state[session_key] = df_new.reset_index(drop=True) if "Replace" in mode else pd.concat([st.session_state[session_key], df_new], ignore_index=True)
                    save_sheet(session_key, st.session_state[session_key])
                    st.success("✅ Imported and saved!"); st.rerun()

# ═══════════════════════════════════════════
# SESSION INIT
# ═══════════════════════════════════════════
def init_state():
    init_auth()
    for key in DATA_KEYS:
        if key not in st.session_state:
            loaded = load_sheet(key)
            st.session_state[key] = DEFAULT_DATA[key].copy() if loaded.empty else loaded

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

# ═══════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════
with st.sidebar:
    st.markdown("### 💾 Backup & Restore")
    st.markdown('<div class="info-box">Data auto-saves to Google Sheets.</div>', unsafe_allow_html=True)
    st.download_button("📦 Export All Data (.zip)", data=export_zip(), file_name=f"yashgallery_{today_str}.zip", mime="application/zip", use_container_width=True)
    rf = st.file_uploader("📂 Restore from ZIP", type=["zip"], key="rzf")
    if rf:
        if st.button("🔄 Restore Now", use_container_width=True, key="do_restore"):
            import_zip(rf.read()); st.rerun()
    st.markdown("---")
    if st.button("🔄 Reload from Google Sheets", use_container_width=True):
        for key in DATA_KEYS:
            if key in st.session_state: del st.session_state[key]
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
    st.metric("Today's Entries", len(tdpl))
    st.metric("Total Karigar", len(st.session_state.karigar_master))
    st.metric("Active Challans", len(st.session_state.challan_master))
    if not tdpl.empty: st.metric("Today's Pieces", int(safe_num(tdpl["Total_Pieces"]).sum()))

# ═══════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════
T = st.tabs(["🏠 Dashboard","📋 Production Entry","🧾 Challan Management",
             "💎 Style Costing","📊 Efficiency","💰 Payroll",
             "🕐 Attendance","🏢 Operating Staff","🌟 Performance","⚙️ Master Data"])
(tab_dash,tab_prod,tab_challan,tab_style,tab_eff,tab_pay,tab_att,tab_op,tab_perf,tab_master) = T

# ══════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════
with tab_dash:
    st.markdown('<div class="sec-hdr">📈 Today\'s Overview</div>', unsafe_allow_html=True)
    pl_all = st.session_state.production_log
    tdpl   = pl_all[pl_all["Date"]==today_str] if not pl_all.empty else pd.DataFrame()
    active_k = tdpl["Karigar_ID"].nunique() if not tdpl.empty else 0
    pieces   = int(safe_num(tdpl["Total_Pieces"]).sum()) if not tdpl.empty else 0
    avg_eff  = safe_num(tdpl["Efficiency_%"]).mean() if not tdpl.empty and "Efficiency_%" in tdpl.columns else 0.0
    pv       = safe_num(tdpl["Piece_Value_Rs"]).sum() if not tdpl.empty else 0.0
    cm_all   = st.session_state.challan_master
    pend_c   = 0
    if not cm_all.empty:
        cm2 = cm_all.copy()
        cm2["Pend"] = safe_num(cm2["Total_Qty"]) - safe_num(cm2.get("Received_Qty",0))
        pend_c = len(cm2[cm2["Pend"]>0])

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    def mcard(col, val, lbl, sub, cls=""):
        with col: st.markdown(f'<div class="mc {cls}"><div class="ml">{lbl}</div><div class="mv">{val}</div><div class="ms">{sub}</div></div>', unsafe_allow_html=True)
    mcard(c1, active_k, "Active Karigar", f"of {len(st.session_state.karigar_master)} total")
    mcard(c2, f"{pieces:,}", "Pieces Done", "today")
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
            cm_d = cm_all.copy()
            cm_d["Pending"] = safe_num(cm_d["Total_Qty"]) - safe_num(cm_d.get("Received_Qty",0))
            cm_d["Status"] = cm_d["Pending"].apply(lambda x:"✅ Done" if x<=0 else f"⏳ {int(x)} pending")
            show_c = [c for c in ["Challan_No","Style","Party","Total_Qty","Pending","Status"] if c in cm_d.columns]
            st.dataframe(cm_d[show_c], use_container_width=True, hide_index=True)
    if not tdpl.empty:
        st.markdown("---")
        st.markdown('<div class="sec-hdr">📋 Today\'s Production</div>', unsafe_allow_html=True)
        sc = [c for c in ["Karigar_Name","Challan_No","Style","Operation","Total_Pieces","Target","Efficiency_%","Piece_Value_Rs"] if c in tdpl.columns]
        st.dataframe(tdpl[sc], use_container_width=True, hide_index=True)
# ══════════════════════════════════════════════════════════
# TAB 2 — PRODUCTION ENTRY v4.8 — FINAL FIX
# Direct session state control for widgets
# ══════════════════════════════════════════════════════════
with tab_prod:
    st.markdown('<div class="sec-hdr">📋 Production Entry — Daily Work</div>', unsafe_allow_html=True)

    lock_widget("prod")
    import_section("production_log", "production_log", "Production Log")
    st.markdown("---")

    # ── HELPER: Clean key ──
    def _clean_key(val):
        if val is None:
            return ""
        try:
            f = float(val)
            if pd.isna(f):
                return ""
            return str(int(f)) if f == int(f) else str(f)
        except (ValueError, TypeError):
            return str(val).strip()

    # ══════════════════════════════════════════════════════════
    # SELECTIONS
    # ══════════════════════════════════════════════════════════
    pe_date = st.date_input("📅 DATE", value=date.today(), key="pe_date")

    st.markdown("**👤 KARIGAR**")
    kdf = st.session_state.karigar_master.copy()
    kdf["Karigar_ID"] = kdf["Karigar_ID"].astype(str)
    kdf["Name"] = kdf["Name"].astype(str)

    srch = st.text_input("Search", key="ksrch", placeholder="Name or ID")
    kdf_f = kdf[
        kdf["Name"].str.contains(srch, case=False, na=False) |
        kdf["Karigar_ID"].str.contains(srch, case=False, na=False)
    ] if srch else kdf

    if kdf_f.empty:
        st.warning("No karigar found.")
        st.stop()

    k_map = {f"{r['Karigar_ID']} — {r['Name']}": r for _, r in kdf_f.iterrows()}
    sel_k_key = st.selectbox("Select Karigar", list(k_map.keys()), key="sel_kar")
    k_row = k_map[sel_k_key]

    sm = st.session_state.style_master
    all_styles = sm["Style"].unique().tolist() if not sm.empty else []
    if not all_styles:
        st.warning("No styles. Add in ⚙️ Master Data.")
        st.stop()
    pe_style = st.selectbox("👗 STYLE", all_styles, key="pe_style")

    ch_df = st.session_state.challan_master
    s_chall = ch_df[ch_df["Style"] == pe_style] if not ch_df.empty else pd.DataFrame()
    if s_chall.empty:
        st.warning(f"No challans for '{pe_style}'.")
        st.stop()

    ch_map = {}
    for _, r in s_chall.iterrows():
        qty = int(safe_num(pd.Series([r["Total_Qty"]])).iloc[0])
        rec = int(safe_num(pd.Series([r.get("Received_Qty", 0)])).iloc[0])
        lbl = f"{r['Challan_No']} | {r.get('Party','—')} | Qty:{qty} | Recv:{rec}"
        ch_map[lbl] = r

    sel_ch_key = st.selectbox("🧾 Challan", list(ch_map.keys()), key="sel_ch")
    ch_row = ch_map[sel_ch_key]

    # ══════════════════════════════════════════════════════════
    # COMPOSITE KEY
    # ══════════════════════════════════════════════════════════
    current_date = _clean_key(pe_date)
    current_karigar_id = _clean_key(k_row["Karigar_ID"])
    challan_no = _clean_key(ch_row["Challan_No"])
    current_style = _clean_key(pe_style)

    composite_key = f"{current_date}__{current_karigar_id}__{challan_no}__{current_style}"
    last_key = st.session_state.get("last_composite_key", "")

    # ══════════════════════════════════════════════════════════
    # KEY CHANGE → CLEAR + LOAD
    # ══════════════════════════════════════════════════════════
    if last_key != composite_key:
        st.info(f"🔄 Loading {k_row['Name']}...")
        
        # STEP 1: Clear ALL hour widgets
        for hcol in HOUR_COLS:
            st.session_state[f"hv_{hcol}"] = 0
            st.session_state[f"sel_op_{hcol}"] = ""
        
        # STEP 2: Load saved data
        pl = st.session_state.production_log
        if not pl.empty:
            pl_check = pl.copy()
            pl_check["_date"] = pl_check["Date"].apply(_clean_key)
            pl_check["_kar"] = pl_check["Karigar_ID"].apply(_clean_key)
            pl_check["_challan"] = pl_check["Challan_No"].apply(_clean_key)
            pl_check["_style"] = pl_check["Style"].apply(_clean_key)

            existing = pl_check[
                (pl_check["_date"] == current_date) &
                (pl_check["_kar"] == current_karigar_id) &
                (pl_check["_challan"] == challan_no) &
                (pl_check["_style"] == current_style)
            ]

            if not existing.empty:
                # Populate widgets directly
                for _, row in existing.iterrows():
                    op_name = str(row["Operation"]).strip()
                    for hcol in HOUR_COLS:
                        raw = row.get(hcol, 0)
                        try:
                            val = 0 if pd.isna(raw) else int(float(raw))
                        except (ValueError, TypeError):
                            val = 0
                        if val > 0:
                            st.session_state[f"hv_{hcol}"] = val
                            st.session_state[f"sel_op_{hcol}"] = op_name
                
                st.success(f"✅ Loaded {len(existing)} saved entry(s)")
        
        # STEP 3: Update tracking
        st.session_state["last_composite_key"] = composite_key
        st.rerun()

    # ══════════════════════════════════════════════════════════
    # EMPLOYEE INFO
    # ══════════════════════════════════════════════════════════
    em_master = st.session_state.employee_master.copy()
    em_master["E_Code"] = em_master["E_Code"].astype(str)
    em_match = em_master[em_master["E_Code"] == str(k_row["Karigar_ID"])]
    
    if not em_match.empty:
        em_r = em_match.iloc[0]
        st.markdown(f'<div class="ok-box">✅ {em_r["Name"]} | Daily: ₹{em_r["Daily_Rate_Rs"]} | Hourly: ₹{em_r["Hourly_Rate_Rs"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="ro-field">{k_row["Karigar_ID"]} | {k_row["Skill"]} | ₹{k_row["Daily_Rate_Rs"]}/day</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # CHALLAN INFO
    # ══════════════════════════════════════════════════════════
    ch_qty = int(safe_num(pd.Series([ch_row["Total_Qty"]])).iloc[0])
    ch_rec = int(safe_num(pd.Series([ch_row.get("Received_Qty",0)])).iloc[0])

    st.markdown(f"""
    <div class="challan-info-card">
      <div class="ci-title">📋 Entry Details</div>
      <div class="ci-row">
        <div class="ci-item">👗 Style: <span>{pe_style}</span></div>
        <div class="ci-item">🧾 Challan: <span>{challan_no}</span></div>
        <div class="ci-item">📦 Total: <span>{ch_qty}</span></div>
        <div class="ci-item">✅ Received: <span>{ch_rec}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # OPERATION INFO
    # ══════════════════════════════════════════════════════════
    style_ops = sm[sm["Style"] == pe_style][["Operation", "Target", "Rate_Rs"]]
    if style_ops.empty:
        st.warning(f"No operations for '{pe_style}'.")
        st.stop()

    op_info = {}
    for _, row in style_ops.iterrows():
        op_info[row["Operation"]] = {
            "Target": int(row["Target"]),
            "Rate_Rs": float(row["Rate_Rs"]),
            "Hourly_Target": max(1, int(row["Target"]) // 8),
        }
    op_list = [""] + style_ops["Operation"].tolist()

    # ══════════════════════════════════════════════════════════
    # HOUR TABLE
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown('<div class="sec-hdr">⏱ Hour-wise Entry</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="entry-table-hdr">
      <span>TIME</span>
      <span>WORK</span>
      <span>TARGET</span>
      <span>ACTUAL</span>
      <span>EFF</span>
    </div>
    """, unsafe_allow_html=True)

    from collections import defaultdict
    h_vals = {}
    op_vals = {}
    op_totals = defaultdict(lambda: {"pieces": 0, "hours": 0, "value": 0})
    prev_op = ""

    for hcol, hlbl in zip(HOUR_COLS, HOUR_LBLS):

        if hcol == "H_13_14":
            st.markdown(f'<div class="entry-row-lunch"><div class="time-lbl" style="color:#9e9e9e;">{hlbl}</div><div style="padding:0 12px;font-size:.82rem;color:#bdbdbd;font-style:italic;">🍽️ Lunch</div></div>', unsafe_allow_html=True)
            op_vals[hcol] = None
            h_vals[hcol] = 0
            continue

        row_c = st.columns([1, 3, 1.2, 1.4, 1.2])

        with row_c[0]:
            st.markdown(f'<div style="padding:10px;text-align:center;font-size:.88rem;font-weight:700;color:#2c5aa0;">{hlbl}</div>', unsafe_allow_html=True)

        with row_c[1]:
            # FIXED: Initialize if not exists
            if f"sel_op_{hcol}" not in st.session_state:
                st.session_state[f"sel_op_{hcol}"] = ""
            
            saved_op = st.session_state[f"sel_op_{hcol}"]
            default_i = 0
            if saved_op and saved_op in op_list:
                default_i = op_list.index(saved_op)
            elif prev_op and prev_op in op_list:
                default_i = op_list.index(prev_op)

            sel_op = st.selectbox(
                f"op_{hlbl}", op_list,
                index=default_i,
                key=f"sel_op_{hcol}",
                label_visibility="collapsed")

            op_vals[hcol] = sel_op if sel_op else None
            if sel_op:
                prev_op = sel_op

        with row_c[2]:
            if sel_op and sel_op in op_info:
                ht = op_info[sel_op]["Hourly_Target"]
                st.markdown(f'<div style="padding:10px;text-align:center;font-size:.92rem;font-weight:700;color:#1a3a5c;">{ht}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="padding:10px;text-align:center;color:#bbb;">—</div>', unsafe_allow_html=True)

        with row_c[3]:
            # FIXED: Initialize if not exists
            if f"hv_{hcol}" not in st.session_state:
                st.session_state[f"hv_{hcol}"] = 0
            
            pcs = st.number_input(
                f"pcs_{hlbl}",
                min_value=0, step=1,
                key=f"hv_{hcol}",
                label_visibility="collapsed")
            
            h_vals[hcol] = pcs

        with row_c[4]:
            if sel_op and sel_op in op_info and pcs > 0:
                ht2 = op_info[sel_op]["Hourly_Target"]
                eff = round(pcs / ht2 * 100) if ht2 > 0 else 0
                rate = op_info[sel_op]["Rate_Rs"]
                cls = "eff-ex" if eff >= 100 else ("eff-gd" if eff >= 75 else "eff-bl")
                st.markdown(f'<div class="{cls}">{eff}%</div>', unsafe_allow_html=True)
                op_totals[sel_op]["pieces"] += pcs
                op_totals[sel_op]["hours"] += 1
                op_totals[sel_op]["value"] += pcs * rate
            else:
                st.markdown('<div style="text-align:center;color:#bbb;padding:10px;">—</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # SUMMARY & SAVE
    # ══════════════════════════════════════════════════════════
    total_pcs = sum(h_vals.values())

    if total_pcs > 0:
        st.markdown("---")
        sum_cols = st.columns(3)
        sum_cols[0].metric("Total Pieces", f"{total_pcs:,}")
        total_value = sum(d["value"] for d in op_totals.values())
        sum_cols[1].metric("Piece Value", f"₹{total_value:,.2f}")
        avg_eff = (sum(op_totals[op]["pieces"] / op_info[op]["Target"] * 100
                      for op in op_totals if op_info[op]["Target"] > 0) / len(op_totals)) if op_totals else 0
        sum_cols[2].metric("Avg Efficiency", f"{avg_eff:.1f}%")

    st.markdown("---")
    
    if st.button("💾 Save", key="pe_save", use_container_width=True, type="primary", disabled=(total_pcs==0)):

        log_df = st.session_state.production_log.copy()

        for op_name, data in op_totals.items():
            od = op_info[op_name]
            op_eff = round(data["pieces"] / od["Target"] * 100, 1) if od["Target"] > 0 else 0.0
            hour_row = {hcol: (h_vals.get(hcol, 0) if op_vals.get(hcol) == op_name else 0) for hcol in HOUR_COLS}

            new_row = {
                "Date": current_date,
                "Karigar_ID": current_karigar_id,
                "Karigar_Name": k_row["Name"],
                "Challan_No": challan_no,
                "Style": current_style,
                "Operation": op_name,
                **hour_row,
                "Total_Pieces": data["pieces"],
                "Target": od["Target"],
                "Rate_Rs": od["Rate_Rs"],
                "Efficiency_%": op_eff,
                "Piece_Value_Rs": round(data["value"], 2),
            }

            # Upsert
            if not log_df.empty:
                log_df["_ck_date"] = log_df["Date"].apply(_clean_key)
                log_df["_ck_kar"] = log_df["Karigar_ID"].apply(_clean_key)
                log_df["_ck_challan"] = log_df["Challan_No"].apply(_clean_key)
                log_df["_ck_style"] = log_df["Style"].apply(_clean_key)
                log_df["_ck_op"] = log_df["Operation"].apply(_clean_key)

                keep = ~(
                    (log_df["_ck_date"] == current_date) &
                    (log_df["_ck_kar"] == current_karigar_id) &
                    (log_df["_ck_challan"] == challan_no) &
                    (log_df["_ck_style"] == current_style) &
                    (log_df["_ck_op"] == _clean_key(op_name))
                )
                log_df = log_df[keep].drop(columns=["_ck_date","_ck_kar","_ck_challan","_ck_style","_ck_op"], errors="ignore")

            log_df = pd.concat([log_df, pd.DataFrame([new_row])], ignore_index=True)

        st.session_state.production_log = log_df
        save_sheet("production_log", log_df)

        # Force reset for next entry
        st.session_state["last_composite_key"] = ""

        st.success("✅ Saved!")
        st.balloons()
        st.rerun()

    # ══════════════════════════════════════════════════════════
    # DAY VIEW
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    if not st.session_state.production_log.empty:
        flt_d = st.date_input("View Date", value=date.today(), key="prod_flt")
        day_pl = st.session_state.production_log[
            st.session_state.production_log["Date"].apply(_clean_key) == _clean_key(flt_d)]
        if not day_pl.empty:
            for c in ["Total_Pieces", "Target", "Efficiency_%", "Piece_Value_Rs"]:
                if c in day_pl.columns:
                    day_pl[c] = safe_num(day_pl[c])
            st.dataframe(day_pl[[c for c in ["Karigar_Name","Challan_No","Style","Operation","Total_Pieces","Target","Efficiency_%","Piece_Value_Rs"] if c in day_pl.columns]], use_container_width=True, hide_index=True)
# ══════════════════════════════════════════════════════════
# TAB 3 — CHALLAN MANAGEMENT
# ══════════════════════════════════════════════════════════
with tab_challan:
    st.markdown('<div class="sec-hdr">🧾 Challan Management</div>', unsafe_allow_html=True)
    import_section("challan_master", "challan_master", "Challan Master")
    with st.expander("➕ Add New Challan", expanded=True):
        with st.form("add_ch", clear_on_submit=True):
            ca1, ca2 = st.columns(2)
            with ca1:
                c_no    = st.text_input("Challan No *", placeholder="e.g. 10220-2526")
                c_style = st.selectbox("Style *", sm["Style"].unique().tolist() if not sm.empty else [""])
                c_party = st.text_input("Party Name")
            with ca2:
                c_qty   = st.number_input("Total Qty *", min_value=1, step=1, value=100)
                c_rec   = st.number_input("Received Qty", min_value=0, step=1, value=0)
                c_dep   = st.number_input("Deposit (₹)", min_value=0.0, step=100.0, value=0.0)
                c_rate  = st.number_input("Rate/Pc (₹)", min_value=0.0, step=1.0, value=35.0)
            c_date  = st.date_input("Issue Date", value=date.today())
            c_deliv = st.text_input("Delivery By (optional)", placeholder="e.g. 2026-03-15")
            if st.form_submit_button("✅ Add Challan", use_container_width=True):
                if not c_no: st.error("Challan No required")
                else:
                    st.session_state.challan_master = pd.concat([st.session_state.challan_master,
                        pd.DataFrame([{"Challan_No":c_no,"Style":c_style,"Party":c_party,"Total_Qty":int(c_qty),"Received_Qty":int(c_rec),"Deposit_Rs":float(c_dep),"Rate_Per_Pc":float(c_rate),"Date":str(c_date),"Delivery_By":c_deliv}])],ignore_index=True)
                    save_sheet("challan_master", st.session_state.challan_master)
                    st.success(f"✅ {c_no} added!"); st.rerun()

    cm = st.session_state.challan_master.copy()
    if not cm.empty:
        cm["Pending"] = safe_num(cm["Total_Qty"]) - safe_num(cm.get("Received_Qty",0))
        cm["Status"]  = cm["Pending"].apply(lambda x:"✅ Complete" if x<=0 else f"⏳ {int(x)} pending")
        sx1,sx2,sx3,sx4 = st.columns(4)
        sx1.metric("Total Challans",  len(cm))
        sx2.metric("Completed",       len(cm[cm["Pending"]<=0]))
        sx3.metric("In Progress",     len(cm[cm["Pending"]>0]))
        lv=(safe_num(cm["Total_Qty"])*safe_num(cm.get("Rate_Per_Pc",0))).sum()
        sx4.metric("Total Labour Value",f"₹{lv:,.0f}")
        show_c=[c for c in ["Challan_No","Style","Party","Total_Qty","Received_Qty","Pending","Status","Rate_Per_Pc","Deposit_Rs","Date"] if c in cm.columns]
        st.dataframe(cm[show_c], use_container_width=True, hide_index=True)

        st.markdown('<div class="sec-hdr">✏️ Update Challan</div>', unsafe_allow_html=True)
        upd_ch  = st.selectbox("Select Challan to Update", cm["Challan_No"].tolist(), key="upd_ch")
        sr = cm[cm["Challan_No"]==upd_ch].iloc[0]
        u1,u2,u3,u4 = st.columns(4)
        with u1: new_qty  = st.number_input("Total Qty",   min_value=1, step=1, value=int(safe_num(pd.Series([sr.get("Total_Qty",1)])).iloc[0]), key="u_qty")
        with u2: new_rec  = st.number_input("Received",    min_value=0, step=1, value=int(safe_num(pd.Series([sr.get("Received_Qty",0)])).iloc[0]), key="u_rec")
        with u3: new_dep  = st.number_input("Deposit (₹)", min_value=0.0, step=100.0, value=float(safe_num(pd.Series([sr.get("Deposit_Rs",0)])).iloc[0]), key="u_dep")
        with u4: new_rate = st.number_input("Rate/Pc",     min_value=0.0, step=1.0, value=float(safe_num(pd.Series([sr.get("Rate_Per_Pc",0)])).iloc[0]), key="u_rate")
        if st.button("💾 Update Challan", use_container_width=True):
            idx = st.session_state.challan_master[st.session_state.challan_master["Challan_No"]==upd_ch].index
            if len(idx)>0:
                st.session_state.challan_master.loc[idx[0],"Total_Qty"]    = new_qty
                st.session_state.challan_master.loc[idx[0],"Received_Qty"] = new_rec
                st.session_state.challan_master.loc[idx[0],"Deposit_Rs"]   = new_dep
                st.session_state.challan_master.loc[idx[0],"Rate_Per_Pc"]  = new_rate
                save_sheet("challan_master", st.session_state.challan_master)
                st.success(f"✅ {upd_ch} updated!"); st.rerun()
    excel_data, excel_ext, excel_mime = to_excel_bytes(st.session_state.challan_master)
    st.download_button("📥 Export Challans", excel_data, f"challans{excel_ext}", mime=excel_mime)


# ══════════════════════════════════════════════════════════
# TAB 4 — STYLE COSTING  (rebuilt: challan-wise with actual expense from production_log)
# ══════════════════════════════════════════════════════════
with tab_style:
    st.markdown('<div class="sec-hdr">💎 Style Costing — Challan-wise Actual Cost vs Party Rate</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    <b>How this works:</b> For each challan, actual labour expense = pieces produced × rate per piece from production log.
    Target price per piece = sum of all operation rates in style master.
    Profit/Loss = (Party Rate × Total Qty) − Actual Labour Expense − Deposit.
    Pending challans are flagged separately.
    </div>""", unsafe_allow_html=True)

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
    pl_sc = st.session_state.production_log.copy()

    if cm_sc.empty:
        st.info("No challans yet.")
    else:
        cm_sc["Date_dt"] = pd.to_datetime(cm_sc["Date"],errors="coerce")
        if sel_mo!="All": cm_sc = cm_sc[cm_sc["Date_dt"].dt.strftime("%Y-%m")==sel_mo]
        if sel_st!="All": cm_sc = cm_sc[cm_sc["Style"]==sel_st]
        if sel_pt!="All" and "Party" in cm_sc.columns: cm_sc = cm_sc[cm_sc["Party"]==sel_pt]

        for col in ["Total_Qty","Rate_Per_Pc","Deposit_Rs","Received_Qty"]:
            cm_sc[col] = safe_num(cm_sc.get(col,0))
        cm_sc["Pending"] = cm_sc["Total_Qty"] - cm_sc["Received_Qty"]
        cm_sc["Is_Pending"] = cm_sc["Pending"] > 0

        # Target labour rate per piece from style master (sum of all ops for that style)
        if not sm.empty:
            target_rate = sm.groupby("Style")["Rate_Rs"].sum().reset_index()
            target_rate.columns = ["Style","Target_Labour_Rate_Pc"]
            cm_sc = cm_sc.merge(target_rate, on="Style", how="left").fillna({"Target_Labour_Rate_Pc":0})
        else:
            cm_sc["Target_Labour_Rate_Pc"] = 0

        # Actual labour expense from production_log grouped by Challan_No
        if not pl_sc.empty:
            pl_sc["Piece_Value_Rs"] = safe_num(pl_sc.get("Piece_Value_Rs",0))
            actual_exp = pl_sc.groupby("Challan_No")["Piece_Value_Rs"].sum().reset_index()
            actual_exp.columns = ["Challan_No","Actual_Labour_Rs"]
            actual_exp["Challan_No"] = actual_exp["Challan_No"].astype(str)
            cm_sc["Challan_No"] = cm_sc["Challan_No"].astype(str)
            cm_sc = cm_sc.merge(actual_exp, on="Challan_No", how="left").fillna({"Actual_Labour_Rs":0})
        else:
            cm_sc["Actual_Labour_Rs"] = 0

        cm_sc["Target_Labour_Rs"]   = (cm_sc["Target_Labour_Rate_Pc"] * cm_sc["Total_Qty"]).round(2)
        cm_sc["Party_Value_Rs"]     = (cm_sc["Rate_Per_Pc"] * cm_sc["Total_Qty"]).round(2)
        cm_sc["Total_Expense_Rs"]   = (cm_sc["Actual_Labour_Rs"] + cm_sc["Deposit_Rs"]).round(2)
        cm_sc["PL_Rs"]              = (cm_sc["Party_Value_Rs"] - cm_sc["Total_Expense_Rs"]).round(2)
        cm_sc["PL_Per_Pc"]          = (cm_sc["PL_Rs"] / cm_sc["Total_Qty"].replace(0,1)).round(2)
        cm_sc["Margin_%"]           = (cm_sc["PL_Rs"] / cm_sc["Party_Value_Rs"].replace(0,1)*100).round(1)
        cm_sc["Cost_vs_Target_%"]   = (cm_sc["Actual_Labour_Rs"] / cm_sc["Target_Labour_Rs"].replace(0,1)*100).round(1)

        # Summary metrics
        tot_v  = cm_sc["Party_Value_Rs"].sum()
        tot_e  = cm_sc["Total_Expense_Rs"].sum()
        tot_pl = cm_sc["PL_Rs"].sum()
        tot_pend = len(cm_sc[cm_sc["Is_Pending"]])

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("Challans",       len(cm_sc))
        m2.metric("Pending",        tot_pend)
        m3.metric("Party Value",    f"₹{tot_v:,.0f}")
        m4.metric("Actual Expense", f"₹{tot_e:,.0f}")
        m5.metric("Net P&L",        f"₹{tot_pl:,.0f}", delta=f"₹{tot_pl:+,.0f}")

        st.markdown("---")

        # ── Show pending challans first ────────────────
        pend_df = cm_sc[cm_sc["Is_Pending"]].copy()
        done_df = cm_sc[~cm_sc["Is_Pending"]].copy()

        if not pend_df.empty:
            st.markdown('<div class="sec-hdr">⏳ Pending Challans</div>', unsafe_allow_html=True)
            for _, row in pend_df.iterrows():
                progress = min(int(row["Received_Qty"]) / max(int(row["Total_Qty"]),1) * 100, 100)
                exp_so_far = row["Actual_Labour_Rs"]
                exp_target = row["Target_Labour_Rs"]
                st.markdown(f"""
                <div class="ch-cost-pending">
                  <b>{row["Challan_No"]}</b> &nbsp;|&nbsp; {row["Style"]} &nbsp;|&nbsp; {row.get("Party","—")} &nbsp;|&nbsp;
                  🎯 {int(row["Total_Qty"])} pcs &nbsp;|&nbsp; ✅ {int(row["Received_Qty"])} done &nbsp;|&nbsp; ⏳ {int(row["Pending"])} pending
                  <br>
                  <small>
                    Labour so far: <b>₹{exp_so_far:,.0f}</b> &nbsp;|&nbsp;
                    Target labour budget: <b>₹{exp_target:,.0f}</b> &nbsp;|&nbsp;
                    Party rate: <b>₹{row["Rate_Per_Pc"]}/pc</b> &nbsp;|&nbsp;
                    Progress: <b>{progress:.0f}%</b>
                  </small>
                </div>""", unsafe_allow_html=True)

        if not done_df.empty:
            st.markdown('<div class="sec-hdr">✅ Completed Challans — P&L</div>', unsafe_allow_html=True)
            for _, row in done_df.iterrows():
                is_profit = row["PL_Rs"] >= 0
                css_cls   = "ch-cost-profit" if is_profit else "ch-cost-loss"
                icon      = "✅ Profit" if is_profit else "🔴 Loss"
                st.markdown(f"""
                <div class="{css_cls}">
                  <b>{row["Challan_No"]}</b> &nbsp;|&nbsp; {row["Style"]} &nbsp;|&nbsp; {row.get("Party","—")} &nbsp;|&nbsp; {int(row["Total_Qty"])} pcs
                  <br>
                  Party Value: <b>₹{row["Party_Value_Rs"]:,.0f}</b> &nbsp;|&nbsp;
                  Actual Labour: <b>₹{row["Actual_Labour_Rs"]:,.0f}</b> &nbsp;|&nbsp;
                  Deposit: <b>₹{row["Deposit_Rs"]:,.0f}</b> &nbsp;|&nbsp;
                  Total Expense: <b>₹{row["Total_Expense_Rs"]:,.0f}</b>
                  <br>
                  {icon}: <b>₹{row["PL_Rs"]:,.0f}</b> &nbsp;|&nbsp;
                  Per Pc: <b>₹{row["PL_Per_Pc"]}</b> &nbsp;|&nbsp;
                  Margin: <b>{row["Margin_%"]}%</b> &nbsp;|&nbsp;
                  Cost vs Target: <b>{row["Cost_vs_Target_%"]}%</b>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="sec-hdr">📋 Full Detail Table</div>', unsafe_allow_html=True)
        detail_cols = [c for c in ["Challan_No","Style","Party","Total_Qty","Received_Qty","Pending",
            "Target_Labour_Rate_Pc","Target_Labour_Rs","Actual_Labour_Rs","Deposit_Rs",
            "Rate_Per_Pc","Party_Value_Rs","Total_Expense_Rs","PL_Rs","PL_Per_Pc","Margin_%",
            "Cost_vs_Target_%","Is_Pending"] if c in cm_sc.columns]
        st.dataframe(cm_sc[detail_cols], use_container_width=True, hide_index=True)

        st.markdown('<div class="sec-hdr">Style Roll-up</div>', unsafe_allow_html=True)
        sru = cm_sc.groupby("Style").agg(
            Challans=("Challan_No","nunique"),
            Qty=("Total_Qty","sum"),
            Actual_Labour=("Actual_Labour_Rs","sum"),
            Party_Value=("Party_Value_Rs","sum"),
            Total_Expense=("Total_Expense_Rs","sum"),
            PL=("PL_Rs","sum"),
            Pending_Challans=("Is_Pending","sum")
        ).reset_index()
        sru["Margin_%"]=(sru["PL"]/sru["Party_Value"].replace(0,1)*100).round(1)
        sru["Result"]=sru["PL"].apply(lambda x:"✅ Profit" if x>0 else("🔴 Loss" if x<0 else"↔ Break-even"))
        st.dataframe(sru, use_container_width=True, hide_index=True)

        e1,e2=st.columns(2)
        excel_data, excel_ext, excel_mime = to_excel_bytes(cm_sc[detail_cols])
        with e1: st.download_button("📥 Style Costing" + (" Excel" if EXCEL_AVAILABLE else " CSV"), excel_data, f"style_costing_{sel_mo}{excel_ext}", mime=excel_mime)
        with e2: st.download_button("📥 CSV", to_csv_bytes(cm_sc[detail_cols]), f"style_costing_{sel_mo}.csv")


# ══════════════════════════════════════════════════════════
# TAB 5 — EFFICIENCY
# ══════════════════════════════════════════════════════════
with tab_eff:
    st.markdown('<div class="sec-hdr">📊 Efficiency Analysis</div>', unsafe_allow_html=True)
    pl_e = st.session_state.production_log
    if pl_e.empty:
        st.info("No production data yet.")
    else:
        df=pl_e.copy()
        for c in ["Total_Pieces","Target","Efficiency_%","Piece_Value_Rs"]:
            if c in df.columns: df[c]=safe_num(df[c])
        df["Date_dt"]=pd.to_datetime(df["Date"],errors="coerce")
        ef1,ef2=st.columns(2)
        with ef1: dr=st.date_input("Date Range",value=[date.today()-timedelta(days=7),date.today()],key="eff_dr")
        with ef2: sf=st.multiselect("Filter Style",df["Style"].unique().tolist(),default=df["Style"].unique().tolist(),key="eff_sf")
        if len(dr)==2:
            mask=(df["Date_dt"]>=pd.Timestamp(dr[0]))&(df["Date_dt"]<=pd.Timestamp(dr[1]))&df["Style"].isin(sf)
            df_f=df[mask].copy()
        else: df_f=df[df["Style"].isin(sf)].copy()
        if df_f.empty: st.warning("No data for filters.")
        else:
            ec1,ec2,ec3=st.columns(3)
            ec1.metric("Avg Efficiency",f"{df_f['Efficiency_%'].mean():.1f}%")
            ec2.metric("Total Piece Value",f"₹{df_f['Piece_Value_Rs'].sum():,.0f}")
            ec3.metric("Total Pieces",f"{int(df_f['Total_Pieces'].sum()):,}")
            st.markdown('<div class="sec-hdr">Karigar-wise</div>', unsafe_allow_html=True)
            ke=df_f.groupby("Karigar_Name").agg(Avg_Eff=("Efficiency_%","mean"),Pieces=("Total_Pieces","sum"),Value=("Piece_Value_Rs","sum"),Ops=("Operation","count")).round(2).reset_index()
            ke["Grade"]=ke["Avg_Eff"].apply(lambda x:"A–Excellent" if x>=100 else("B–Good" if x>=85 else("C–Average" if x>=70 else"D–Below")))
            st.dataframe(ke,use_container_width=True,hide_index=True)
            st.markdown('<div class="sec-hdr">Operation-wise</div>', unsafe_allow_html=True)
            oe=df_f.groupby("Operation").agg(Avg_Eff=("Efficiency_%","mean"),Pieces=("Total_Pieces","sum"),Value=("Piece_Value_Rs","sum")).round(2).reset_index().sort_values("Avg_Eff")
            st.dataframe(oe,use_container_width=True,hide_index=True)
            bn=oe[oe["Avg_Eff"]<80]
            if not bn.empty:
                st.markdown(f'<div class="warn-box">⚠️ <b>Bottleneck (below 80%):</b> {", ".join(bn["Operation"].tolist())}</div>',unsafe_allow_html=True)
            e1,e2=st.columns(2)
            excel_data, excel_ext, excel_mime = to_excel_bytes(ke)
            with e1: st.download_button("📥 "+("Excel" if EXCEL_AVAILABLE else "CSV"),excel_data,f"efficiency{excel_ext}",mime=excel_mime)
            with e2: st.download_button("📥 CSV",to_csv_bytes(ke),"efficiency.csv")


# ══════════════════════════════════════════════════════════
# TAB 6 — PAYROLL
# ══════════════════════════════════════════════════════════
with tab_pay:
    st.markdown('<div class="sec-hdr">💰 Payroll Calculator</div>', unsafe_allow_html=True)
    p1,p2=st.columns(2)
    with p1: pay_s=st.date_input("Pay Period Start",value=date.today()-timedelta(days=6),key="pay_s")
    with p2: pay_e=st.date_input("Pay Period End",value=date.today(),key="pay_e")
    if st.button("📊 Calculate Payroll",use_container_width=True):
        att_p=st.session_state.karigar_attendance
        if att_p.empty: st.warning("No attendance data.")
        else:
            ap=att_p.copy(); ap["Date_dt"]=pd.to_datetime(ap["Date"])
            ap=ap[(ap["Date_dt"]>=pd.Timestamp(pay_s))&(ap["Date_dt"]<=pd.Timestamp(pay_e))]
            if ap.empty: st.warning("No records in pay period.")
            else:
                for c in ["Payable_Hrs","Normal_Pay","OT_Hours","OT_Pay","Total_Pay"]:
                    if c in ap.columns: ap[c]=safe_num(ap[c])
                pr=ap.groupby("E_Code").agg(Name=("Name","first"),Days=("Date","nunique"),Hrs=("Payable_Hrs","sum"),Normal=("Normal_Pay","sum"),OT_Hrs=("OT_Hours","sum"),OT_Pay=("OT_Pay","sum"),Total=("Total_Pay","sum")).round(2).reset_index()
                st.dataframe(pr,use_container_width=True,hide_index=True)
                st.metric("Total Payroll",f"₹{pr['Total'].sum():,.2f}")
                px1,px2=st.columns(2)
                excel_data, excel_ext, excel_mime = to_excel_bytes(pr)
                with px1: st.download_button("📥 Payroll"+(" Excel" if EXCEL_AVAILABLE else " CSV"),excel_data,f"payroll_{pay_s}_{pay_e}{excel_ext}",mime=excel_mime,key="py_x")
                with px2: st.download_button("📥 CSV",to_csv_bytes(pr),f"payroll_{pay_s}_{pay_e}.csv",key="py_c")


# ══════════════════════════════════════════════════════════
# TAB 7 — KARIGAR ATTENDANCE
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
                rows4.append({**row.to_dict(),"Name":nm,"Total_Presence_Hrs":ph,"Lunch_Deduction_Hrs":ld,"Payable_Hrs":py,"Hourly_Rate_Rs":hr,"Normal_Pay":np_,"OT_Hours":oh,"OT_Pay":op,"Total_Pay":tp})
            else: rows4.append(row.to_dict())
        st.session_state.karigar_attendance=pd.DataFrame(rows4)
        save_sheet("karigar_attendance", st.session_state.karigar_attendance); st.rerun()

    with st.expander("✏️ Manual Entry",expanded=True):
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
                na={"Date":str(ad),"E_Code":er2["E_Code"],"Name":er2["Name"],"In_Punch":ip,"Out_Punch":op2,"Total_Presence_Hrs":ph,"Lunch_Deduction_Hrs":ld,"Payable_Hrs":py,"Hourly_Rate_Rs":hr,"Normal_Pay":np_,"OT_Hours":oh,"OT_Pay":op3,"Total_Pay":tp}
                st.session_state.karigar_attendance=pd.concat([st.session_state.karigar_attendance,pd.DataFrame([na])],ignore_index=True)
                save_sheet("karigar_attendance", st.session_state.karigar_attendance)
                st.success(f"✅ {er2['Name']} | {py}h | ₹{tp} — Saved!")

    with st.expander("🔄 Auto-Calculate from Production Log",expanded=False):
        if st.button("📊 Generate Attendance from Production",use_container_width=True):
            pl=st.session_state.production_log
            if pl.empty: st.warning("No production entries.")
            else:
                att_records=[]
                for (d,kid),group in pl.groupby(["Date","Karigar_ID"]):
                    kar_name=group["Karigar_Name"].iloc[0] if "Karigar_Name" in group.columns else f"K-{kid}"
                    hour_cols_worked=[h for h in HOUR_COLS if h!="H_13_14" and any(group[h].astype(str).str.strip()!="0")]
                    hours_worked=len(hour_cols_worked)
                    if hours_worked>0:
                        emp_rec=st.session_state.employee_master[st.session_state.employee_master["E_Code"]==kid]
                        if not emp_rec.empty:
                            dr3=float(emp_rec["Daily_Rate_Rs"].values[0]); hr3=dr3/8
                            np3=hours_worked*hr3 if hours_worked<=8 else 8*hr3
                            ot_h=max(hours_worked-8,0); ot_p=ot_h*hr3*ot_m; tp3=np3+ot_p
                            att_records.append({"Date":str(d),"E_Code":kid,"Name":kar_name,"In_Punch":"09:00","Out_Punch":"18:00","Total_Presence_Hrs":float(hours_worked),"Lunch_Deduction_Hrs":1.0 if hours_worked>=9 else 0.0,"Payable_Hrs":float(max(hours_worked-1,0)) if hours_worked>=9 else float(hours_worked),"Hourly_Rate_Rs":hr3,"Normal_Pay":np3,"OT_Hours":ot_h,"OT_Pay":ot_p,"Total_Pay":tp3})
                if att_records:
                    new_att=pd.DataFrame(att_records)
                    st.session_state.karigar_attendance=pd.concat([st.session_state.karigar_attendance,new_att],ignore_index=True).drop_duplicates(subset=["Date","E_Code"],keep="last")
                    save_sheet("karigar_attendance", st.session_state.karigar_attendance)
                    st.success(f"✅ {len(att_records)} records generated!"); st.dataframe(new_att,use_container_width=True,hide_index=True)
                else: st.info("No working hours found.")

    if not st.session_state.karigar_attendance.empty:
        af=st.date_input("Filter Date",value=date.today(),key="att_f")
        av=st.session_state.karigar_attendance[st.session_state.karigar_attendance["Date"]==str(af)]
        if not av.empty:
            st.dataframe(av,use_container_width=True,hide_index=True)
            excel_data, excel_ext, excel_mime = to_excel_bytes(av)
            st.download_button("📥 Download",excel_data,f"att_{af}{excel_ext}",mime=excel_mime)


# ══════════════════════════════════════════════════════════
# TAB 8 — OPERATING STAFF
# ══════════════════════════════════════════════════════════
with tab_op:
    st.markdown('<div class="sec-hdr">🏢 Operating Staff</div>', unsafe_allow_html=True)
    import_section("operating_attendance","operating_attendance","Operating Staff Attendance")
    eo2=st.session_state.employee_master[st.session_state.employee_master["Type"]=="Operating"]
    oo2={f"{r['E_Code']} – {r['Name']}":r for _,r in eo2.iterrows()}
    if len(oo2)==0:
        st.warning("⚠️ No Operating staff. Add in Master Data → Employee Master.")
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
                        fmt3="%H:%M"; hrs3=round(int((datetime.strptime(oout.strip(),fmt3)-datetime.strptime(oin.strip(),fmt3)).total_seconds())/3600,2)
                    except: hrs3=0
                    hr4=float(er3["Hourly_Rate_Rs"]); tp4=round(hrs3*hr4,2)
                    st.session_state.operating_attendance=pd.concat([st.session_state.operating_attendance,pd.DataFrame([{"Date":str(od),"E_Code":er3["E_Code"],"Name":er3["Name"],"In_Punch":oin,"Out_Punch":oout,"Total_Hours":hrs3,"Hourly_Rate_Rs":hr4,"Total_Pay":tp4}])],ignore_index=True)
                    save_sheet("operating_attendance", st.session_state.operating_attendance)
                    st.success(f"✅ {er3['Name']} | {hrs3}h | ₹{tp4} — Saved!")


# ══════════════════════════════════════════════════════════
# TAB 9 — PERFORMANCE
# ══════════════════════════════════════════════════════════
with tab_perf:
    st.markdown('<div class="sec-hdr">🌟 Employee Performance Dashboard</div>', unsafe_allow_html=True)
    pl_p=st.session_state.production_log; att_p2=st.session_state.karigar_attendance
    if pl_p.empty or att_p2.empty:
        st.info("Need both production entries and attendance records.")
    else:
        pp1,pp2=st.columns(2)
        with pp1: ps=st.date_input("From",value=date.today()-timedelta(days=29),key="ps")
        with pp2: pe=st.date_input("To",value=date.today(),key="pe2")
        pl3=pl_p.copy()
        for c in ["Total_Pieces","Piece_Value_Rs","Efficiency_%"]:
            if c in pl3.columns: pl3[c]=safe_num(pl3[c])
        pl3["Date_dt"]=pd.to_datetime(pl3["Date"])
        pl3=pl3[(pl3["Date_dt"]>=pd.Timestamp(ps))&(pl3["Date_dt"]<=pd.Timestamp(pe))]
        psm=pl3.groupby("Karigar_ID").agg(Piece_Value=("Piece_Value_Rs","sum"),Total_Pieces=("Total_Pieces","sum"),Avg_Eff=("Efficiency_%","mean")).reset_index()
        att3=att_p2.copy(); att3["Date_dt"]=pd.to_datetime(att3["Date"])
        att3=att3[(att3["Date_dt"]>=pd.Timestamp(ps))&(att3["Date_dt"]<=pd.Timestamp(pe))]
        if "Total_Pay" in att3.columns:
            for c in ["Total_Pay","Payable_Hrs"]: att3[c]=safe_num(att3[c])
            ss=att3.groupby("E_Code").agg(Name=("Name","first"),Days=("Date","nunique"),Hrs=("Payable_Hrs","sum"),Salary=("Total_Pay","sum")).round(2).reset_index()
            ss["E_Code"]=ss["E_Code"].astype(str)
            psm2=psm.rename(columns={"Karigar_ID":"E_Code"}).copy(); psm2["E_Code"]=psm2["E_Code"].astype(str)
            perf=ss.merge(psm2,on="E_Code",how="outer").fillna(0)
            perf["Piece_Value"]=perf["Piece_Value"].round(2)
            perf["Surplus"]=(perf["Piece_Value"]-perf["Salary"]).round(2)
            perf["ROI_%"]=(perf["Piece_Value"]/perf["Salary"].replace(0,1)*100).round(1)
            perf["Grade"]=perf["Avg_Eff"].apply(lambda x:"A–Excellent" if x>=100 else("B–Good" if x>=85 else("C–Average" if x>=70 else"D–Needs Improvement")))
            px1,px2,px3=st.columns(3)
            px1.metric("Total Piece Value",f"₹{perf['Piece_Value'].sum():,.0f}")
            px2.metric("Total Salary Paid",f"₹{perf['Salary'].sum():,.0f}")
            px3.metric("Net Surplus",f"₹{perf['Surplus'].sum():,.0f}")
            st.dataframe(perf,use_container_width=True,hide_index=True)
        else: st.warning("Attendance lacks salary data. Add punches in Attendance tab.")


# ══════════════════════════════════════════════════════════
# TAB 10 — MASTER DATA
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
                    st.session_state.style_master=pd.concat([st.session_state.style_master,pd.DataFrame([{"Style":ns,"Operation":no,"Target":nt,"Rate_Rs":nr}])],ignore_index=True)
                    save_sheet("style_master", st.session_state.style_master)
                    st.success(f"✅ Added '{no}' to '{ns}'")
        st.dataframe(st.session_state.style_master,use_container_width=True,hide_index=True)
        excel_data, excel_ext, excel_mime = to_excel_bytes(st.session_state.style_master)
        st.download_button("📥 Export Style Master",excel_data,f"style_master{excel_ext}",mime=excel_mime,key="dl_sm")

    with m2t:
        import_section("karigar_master","karigar_master","Karigar Master")
        with st.expander("➕ Add Karigar",expanded=False):
            with st.form("kf",clear_on_submit=True):
                kc1,kc2=st.columns(2)
                with kc1: k_id=st.text_input("Karigar ID (e.g. K006)"); k_nm=st.text_input("Full Name")
                with kc2: k_sk=st.selectbox("Skill",["Stitching","Cutting","Finishing","Hemming","Checking","Dupatta"]); k_rt=st.number_input("Daily Rate (₹)",min_value=100,step=10,value=420)
                if st.form_submit_button("Add Karigar"):
                    st.session_state.karigar_master=pd.concat([st.session_state.karigar_master,pd.DataFrame([{"Karigar_ID":k_id,"Name":k_nm,"Skill":k_sk,"Daily_Rate_Rs":k_rt}])],ignore_index=True)
                    ec5=f"E{len(st.session_state.employee_master)+1:03d}"
                    st.session_state.employee_master=pd.concat([st.session_state.employee_master,pd.DataFrame([{"E_Code":ec5,"Name":k_nm,"Type":"Karigar","Daily_Rate_Rs":k_rt,"Hourly_Rate_Rs":round(k_rt/8,2)}])],ignore_index=True)
                    save_sheet("karigar_master", st.session_state.karigar_master)
                    save_sheet("employee_master", st.session_state.employee_master)
                    st.success(f"✅ Added {k_nm}")
        st.dataframe(st.session_state.karigar_master,use_container_width=True,hide_index=True)
        excel_data, excel_ext, excel_mime = to_excel_bytes(st.session_state.karigar_master)
        st.download_button("📥 Export Karigar Master",excel_data,f"karigar_master{excel_ext}",mime=excel_mime,key="dl_km")

    with m3t:
        import_section("employee_master","employee_master","Employee Master")
        with st.expander("➕ Add Employee",expanded=False):
            with st.form("ef",clear_on_submit=True):
                ec1,ec2=st.columns(2)
                with ec1: em_c=st.text_input("E-Code"); em_n=st.text_input("Full Name"); em_t=st.selectbox("Type",["Karigar","Operating"])
                with ec2: em_d=st.number_input("Daily Rate (₹)",min_value=100,step=10,value=400); em_h=st.number_input("Hourly Rate (₹)",value=50.0,step=0.5,format="%.2f")
                if st.form_submit_button("Add Employee"):
                    st.session_state.employee_master=pd.concat([st.session_state.employee_master,pd.DataFrame([{"E_Code":em_c,"Name":em_n,"Type":em_t,"Daily_Rate_Rs":em_d,"Hourly_Rate_Rs":em_h}])],ignore_index=True)
                    save_sheet("employee_master", st.session_state.employee_master)
                    st.success(f"✅ Added {em_n}")
        st.dataframe(st.session_state.employee_master,use_container_width=True,hide_index=True)
        excel_data, excel_ext, excel_mime = to_excel_bytes(st.session_state.employee_master)
        st.download_button("📥 Export Employee Master",excel_data,f"employee_master{excel_ext}",mime=excel_mime,key="dl_em")

st.markdown("---")
st.markdown("🧵 <b>Stitching Costing Interface v4.3 — Google Sheets Edition</b> — Yash Gallery Pvt Ltd", unsafe_allow_html=True)
