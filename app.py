"""
Stitching Costing Interface v4.0 — Yash Gallery Pvt Ltd
FIXES v4:
- Excel template downloads for every import section
- Production Entry: Search Karigar → Style → Challan → Operation (from master) → VERTICAL hour entry with 19-20, 20-21 slots
- Challan Management: Simplified — only Style, Challan No, Received Qty, Deposit, Update button
- All imports show required column names and downloadable templates
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import io, hashlib, zipfile

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
/* Vertical hour table */
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
# HELPERS
# ═══════════════════════════════════════════
def safe_num(s): return pd.to_numeric(s, errors='coerce').fillna(0)
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Export as proper Excel format (.xlsx) using xlsxwriter engine"""
    buf = io.BytesIO()
    try:
        # Use xlsxwriter which doesn't require openpyxl
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Data", startrow=0)
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets["Data"]
            
            # Format header
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#2c5aa0',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            # Apply header formatting
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Auto-adjust column widths
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                ) + 2
                worksheet.set_column(idx, idx, min(max_length, 50))
            
            worksheet.set_row(0, 20)  # Header row height
        
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        # If xlsxwriter fails, return CSV as fallback
        st.warning(f"⚠️ Excel export issue: {str(e)[:50]}... Using CSV format instead.")
        return df.to_csv(index=False).encode()

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
                st.session_state[k]=pd.read_csv(io.StringIO(zf.read(nm).decode()))
    st.success("✅ All data restored!")

# ═══════════════════════════════════════════
# TEMPLATES — exact column structure for each import
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
        {"E_Code":"E001","Name":"Ramesh Kumar","Type":"Karigar",   "Daily_Rate_Rs":450,"Hourly_Rate_Rs":56.25},
        {"E_Code":"E101","Name":"Amit Sharma", "Type":"Operating", "Daily_Rate_Rs":600,"Hourly_Rate_Rs":75.00},
    ]),
    "karigar_attendance": pd.DataFrame([
        {"Date":"2026-02-25","E_Code":"E001","In_Punch":"09:00","Out_Punch":"18:00"},
    ]),
    "operating_attendance": pd.DataFrame([
        {"Date":"2026-02-25","E_Code":"E101","In_Punch":"09:00","Out_Punch":"18:00"},
    ]),
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
# IMPORT WIDGET — with template download
# ═══════════════════════════════════════════
def import_section(key: str, session_key: str, label: str):
    """Shows template download + file upload for any data table."""
    tmpl = TEMPLATES.get(key, pd.DataFrame())
    with st.expander(f"📥 Import / Upload {label}", expanded=False):
        st.markdown(f'<div class="tpl-box">📋 <b>Step 1:</b> Download the template below, fill your data keeping the exact column names, then upload it back.<br>Required columns: <b>{", ".join(tmpl.columns.tolist())}</b></div>', unsafe_allow_html=True)

        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                f"⬇️ Download Excel Template",
                data=to_excel_bytes(tmpl),
                file_name=f"{key}_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"tpl_x_{key}", use_container_width=True
            )
        with dl2:
            st.download_button(
                f"⬇️ Download CSV Template",
                data=to_csv_bytes(tmpl),
                file_name=f"{key}_template.csv",
                mime="text/csv",
                key=f"tpl_c_{key}", use_container_width=True
            )

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
                    st.markdown(f'<div class="warn-box">Your file must have these columns exactly: <b>{required}</b></div>', unsafe_allow_html=True)
                    return
                st.success(f"✅ {len(df_new)} rows detected")
                st.dataframe(df_new.head(5), use_container_width=True, hide_index=True)
                if st.button(f"✅ Confirm Import — {label}", key=f"ci_{key}", use_container_width=True):
                    if "Replace" in mode:
                        st.session_state[session_key] = df_new.reset_index(drop=True)
                        st.success(f"✅ Replaced with {len(df_new)} rows.")
                    else:
                        st.session_state[session_key] = pd.concat([st.session_state[session_key], df_new], ignore_index=True)
                        st.success(f"✅ Appended {len(df_new)} rows.")
                    st.rerun()

# ═══════════════════════════════════════════
# SESSION STATE INIT
# ═══════════════════════════════════════════
def init_state():
    init_auth()
    if "style_master" not in st.session_state:
        st.session_state.style_master = pd.DataFrame([
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
        ])
    if "karigar_master" not in st.session_state:
        st.session_state.karigar_master = pd.DataFrame([
            {"Karigar_ID":"K001","Name":"Ramesh Kumar",   "Skill":"Stitching","Daily_Rate_Rs":450},
            {"Karigar_ID":"K002","Name":"Suresh Singh",   "Skill":"Cutting",  "Daily_Rate_Rs":420},
            {"Karigar_ID":"K003","Name":"Priya Devi",     "Skill":"Finishing","Daily_Rate_Rs":400},
            {"Karigar_ID":"K004","Name":"Mohan Lal",      "Skill":"Stitching","Daily_Rate_Rs":460},
            {"Karigar_ID":"K005","Name":"Sunita Sharma",  "Skill":"Hemming",  "Daily_Rate_Rs":410},
        ])
    if "challan_master" not in st.session_state:
        st.session_state.challan_master = pd.DataFrame([
            {"Challan_No":"10220-2526","Style":"1894YKDGREEN","Party":"Aashirwad Garments",
             "Total_Qty":376,"Received_Qty":0,"Deposit_Rs":0.0,
             "Rate_Per_Pc":35,"Date":"2026-02-25","Delivery_By":"2026-03-07"},
        ])
    if "production_log" not in st.session_state:
        st.session_state.production_log = pd.DataFrame(columns=[
            "Date","Karigar_ID","Karigar_Name","Challan_No","Style","Operation",
        ] + HOUR_COLS + ["Total_Pieces","Target","Rate_Rs","Efficiency_%","Piece_Value_Rs"])
    if "employee_master" not in st.session_state:
        st.session_state.employee_master = pd.DataFrame([
            {"E_Code":"E001","Name":"Ramesh Kumar", "Type":"Karigar",  "Daily_Rate_Rs":450,"Hourly_Rate_Rs":56.25},
            {"E_Code":"E002","Name":"Suresh Singh", "Type":"Karigar",  "Daily_Rate_Rs":420,"Hourly_Rate_Rs":52.50},
            {"E_Code":"E003","Name":"Priya Devi",   "Type":"Karigar",  "Daily_Rate_Rs":400,"Hourly_Rate_Rs":50.00},
            {"E_Code":"E004","Name":"Mohan Lal",    "Type":"Karigar",  "Daily_Rate_Rs":460,"Hourly_Rate_Rs":57.50},
            {"E_Code":"E005","Name":"Sunita Sharma","Type":"Karigar",  "Daily_Rate_Rs":410,"Hourly_Rate_Rs":51.25},
            {"E_Code":"E101","Name":"Amit Sharma",  "Type":"Operating","Daily_Rate_Rs":600,"Hourly_Rate_Rs":75.00},
            {"E_Code":"E102","Name":"Kavita Rao",   "Type":"Operating","Daily_Rate_Rs":550,"Hourly_Rate_Rs":68.75},
        ])
    if "karigar_attendance" not in st.session_state:
        st.session_state.karigar_attendance = pd.DataFrame(columns=[
            "Date","E_Code","Name","In_Punch","Out_Punch",
            "Total_Presence_Hrs","Lunch_Deduction_Hrs","Payable_Hrs",
            "Hourly_Rate_Rs","Normal_Pay","OT_Hours","OT_Pay","Total_Pay"])
    if "operating_attendance" not in st.session_state:
        st.session_state.operating_attendance = pd.DataFrame(columns=[
            "Date","E_Code","Name","In_Punch","Out_Punch","Total_Hours","Hourly_Rate_Rs","Total_Pay"])

init_state()
today_str = str(date.today())

# ═══════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════
st.markdown(f"""
<div class="main-hdr">
  <h2>🧵 Stitching Costing Interface — Yash Gallery Pvt Ltd</h2>
  <p>Karigar Tracking · Challan Management · Style Costing · Payroll &nbsp;|&nbsp; {date.today().strftime("%d %b %Y")}</p>
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════
with st.sidebar:
    st.markdown("### 💾 Backup & Restore")
    st.markdown('<div class="info-box">Export every evening. Import next morning to continue.</div>', unsafe_allow_html=True)
    st.download_button("📦 Export All Data (.zip)",
        data=export_zip(), file_name=f"yashgallery_{today_str}.zip",
        mime="application/zip", use_container_width=True)
    rf = st.file_uploader("📂 Restore from ZIP", type=["zip"], key="rzf")
    if rf:
        if st.button("🔄 Restore Now", use_container_width=True, key="do_restore"):
            import_zip(rf.read()); st.rerun()

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
# TAB 2 ─ PRODUCTION ENTRY  (VERTICAL hour input)
# ══════════════════════════════════════════════════════════
with tab_prod:
    st.markdown('<div class="sec-hdr">📋 Production Entry</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    <b>Flow:</b>&nbsp;
    🔍 Search Karigar &rarr;
    👗 Select Style &rarr;
    🧾 Select Challan &rarr;
    ⚙️ Select Operation (from master) &rarr;
    ⏱ Enter pieces hour-by-hour (vertical)
    </div>""", unsafe_allow_html=True)

    is_unlocked = lock_widget("prod")
    import_section("production_log", "production_log", "Production Log")

    st.markdown("---")
    st.markdown('<div class="sec-hdr">✏️ New Production Entry</div>', unsafe_allow_html=True)

    # ── STEP 1: Date + Karigar Search ──────────────────────────────
    col_date, col_kar = st.columns([1,2])
    with col_date:
        pe_date = st.date_input("📅 Date", value=date.today(), key="pe_date")

    with col_kar:
        st.markdown("**🔍 Search Karigar**")
        kdf = st.session_state.karigar_master
        srch = st.text_input("Type name or ID to filter", key="ksrch",
                             placeholder="e.g. Ramesh  or  K001")
        if srch:
            mask = (kdf["Name"].str.contains(srch, case=False, na=False) |
                    kdf["Karigar_ID"].str.contains(srch, case=False, na=False))
            kdf_f = kdf[mask]
        else:
            kdf_f = kdf

        if kdf_f.empty:
            st.warning("No karigar found. Try a different search term.")
            st.stop()

        k_map = {f"{r['Karigar_ID']} — {r['Name']}": r for _,r in kdf_f.iterrows()}
        sel_k_key = st.selectbox("Select Karigar", list(k_map.keys()), key="sel_kar")
        k_row = k_map[sel_k_key]
        st.markdown(f'<div class="ro-field">ID: <b>{k_row["Karigar_ID"]}</b> &nbsp;|&nbsp; Skill: <b>{k_row["Skill"]}</b> &nbsp;|&nbsp; Daily Rate: <b>₹{k_row["Daily_Rate_Rs"]}</b></div>', unsafe_allow_html=True)

    # ── STEP 2: Style ───────────────────────────────────────────────
    sm = st.session_state.style_master
    all_styles = sm["Style"].unique().tolist() if not sm.empty else []
    if not all_styles:
        st.warning("No styles in master. Add styles in ⚙️ Master Data first.")
        st.stop()

    pe_style = st.selectbox("👗 Select Style", all_styles, key="pe_style")

    # ── STEP 3: Challan (filtered by style) ─────────────────────────
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
    ch_qty      = int(safe_num(pd.Series([ch_row["Total_Qty"]])).iloc[0])
    ch_rec      = int(safe_num(pd.Series([ch_row.get("Received_Qty",0)])).iloc[0])
    st.markdown(
        f'<div class="ro-field">Challan: <b>{challan_no}</b> &nbsp;|&nbsp; '
        f'Style: <b>{pe_style}</b> &nbsp;|&nbsp; '
        f'Total: <b>{ch_qty} pcs</b> &nbsp;|&nbsp; '
        f'Received: <b>{ch_rec}</b> &nbsp;|&nbsp; '
        f'Pending: <b>{ch_qty-ch_rec}</b></div>',
        unsafe_allow_html=True)

    # ── STEP 4: Operation (from master only) ────────────────────────
    style_ops = sm[sm["Style"] == pe_style][["Operation","Target","Rate_Rs"]]
    if style_ops.empty:
        st.warning(f"No operations defined for style '{pe_style}'. Add operations in ⚙️ Master Data.")
        st.stop()

    st.markdown("**⚙️ Select Operation**")
    op_list  = style_ops["Operation"].tolist()
    sel_op   = st.selectbox("Operation (from master)", op_list, key="sel_op")
    op_r     = style_ops[style_ops["Operation"]==sel_op].iloc[0]
    tgt_val  = int(op_r["Target"])
    rate_val = float(op_r["Rate_Rs"])

    col_t, col_r = st.columns(2)
    with col_t:
        if is_unlocked:
            tgt_val = st.number_input("🎯 Target (pcs/day)", value=tgt_val, min_value=0, step=1, key="tgt_v")
        else:
            st.markdown(f'<div class="ro-field">🎯 Target: <b>{tgt_val} pcs</b> &nbsp;🔒</div>', unsafe_allow_html=True)
    with col_r:
        if is_unlocked:
            rate_val = st.number_input("💰 Rate/pc (₹)", value=rate_val, min_value=0.0, step=0.25, format="%.2f", key="rate_v")
        else:
            st.markdown(f'<div class="ro-field">💰 Rate: <b>₹{rate_val:.2f}/pc</b> &nbsp;🔒</div>', unsafe_allow_html=True)

    # ── STEP 5: VERTICAL Hour-wise Entry ────────────────────────────
    st.markdown("---")
    st.markdown('<div class="sec-hdr">⏱ Hour-wise Piece Entry (Vertical)</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Enter pieces produced in each time slot. 🍽️ 13:00–14:00 is the lunch break (not counted). Evening slots 19–20 and 20–21 included.</div>', unsafe_allow_html=True)

    # Two columns: left = inputs (vertical), right = live running total
    inp_col, sum_col = st.columns([2, 1])
    h_vals = {}

    op_vals = {}

    with inp_col:
        # Column header row
        hdr1, hdr2, hdr3 = st.columns([3, 3, 2])
        with hdr1: st.markdown("<div style='font-size:.75rem;font-weight:700;color:#2c5aa0;text-transform:uppercase;letter-spacing:.06em;padding:4px 4px 4px;border-bottom:2px solid #2c5aa0;'>Time Slot</div>", unsafe_allow_html=True)
        with hdr2: st.markdown("<div style='font-size:.75rem;font-weight:700;color:#2c5aa0;text-transform:uppercase;letter-spacing:.06em;padding:4px 4px 4px;border-bottom:2px solid #2c5aa0;'>Operation</div>", unsafe_allow_html=True)
        with hdr3: st.markdown("<div style='font-size:.75rem;font-weight:700;color:#2c5aa0;text-transform:uppercase;letter-spacing:.06em;padding:4px 4px 4px;border-bottom:2px solid #2c5aa0;'>Pieces</div>", unsafe_allow_html=True)

        for hcol, hlbl in zip(HOUR_COLS, HOUR_LBLS):
            is_lunch = (hcol == "H_13_14")
            rc1, rc2, rc3 = st.columns([3, 3, 2])

            # Time label
            with rc1:
                if is_lunch:
                    st.markdown(
                        f"<div style='padding:8px 4px;font-size:.84rem;color:#9e9e9e;background:#fafafa;border-bottom:1px solid #eee;border-radius:3px;'>🍽️ {hlbl}<br><span style='font-size:.71rem;'>Lunch break</span></div>",
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"<div style='padding:8px 4px;font-size:.88rem;font-weight:600;color:#1a3a52;border-bottom:1px solid #eee;'>🕐 {hlbl}</div>",
                        unsafe_allow_html=True)

            # Operation dropdown — every active slot gets its own dropdown
            with rc2:
                if is_lunch:
                    st.markdown("<div style='padding:8px 4px;color:#bdbdbd;font-size:.8rem;border-bottom:1px solid #eee;'>—</div>", unsafe_allow_html=True)
                    op_vals[hcol] = None
                else:
                    op_vals[hcol] = st.selectbox(
                        "",
                        op_list,
                        index=op_list.index(sel_op) if sel_op in op_list else 0,
                        key=f"op_{hcol}",
                        label_visibility="collapsed"
                    )

            # Piece input
            with rc3:
                if is_lunch:
                    st.markdown("<div style='padding:8px 4px;color:#9e9e9e;font-size:.84rem;border-bottom:1px solid #eee;'>— break —</div>", unsafe_allow_html=True)
                    h_vals[hcol] = 0
                else:
                    h_vals[hcol] = st.number_input(
                        "pcs", min_value=0, step=1, value=0,
                        key=f"hv_{hcol}",
                        label_visibility="collapsed"
                    )

    # Live running total on the right
    with sum_col:
        st.markdown('<div class="sec-hdr" style="text-align:center">📊 Live Total</div>', unsafe_allow_html=True)
        total_pcs = sum(h_vals.values())
        eff_pct   = round(total_pcs / tgt_val * 100, 1) if tgt_val > 0 else 0.0
        piece_val = round(total_pcs * rate_val, 2)

        # Running per-hour table
        rows_html = ""
        running = 0
        for hcol, hlbl in zip(HOUR_COLS, HOUR_LBLS):
            is_lunch_r = (hcol == "H_13_14")
            v = h_vals.get(hcol, 0)
            running += v
            if is_lunch_r:
                rows_html += f'<tr style="background:#fafafa;color:#9e9e9e;"><td>🍽️ {hlbl}</td><td colspan="2" style="text-align:center;font-size:.78rem;">lunch</td></tr>'
            else:
                bg = "#f9fbe7" if v > 0 else ""
                rows_html += f'<tr style="background:{bg}"><td>{hlbl}</td><td><b>{v}</b></td><td>{running}</td></tr>'

        st.markdown(f"""
        <table class="hour-table">
          <tr><th>Hour</th><th>Pcs</th><th>Total</th></tr>
          {rows_html}
        </table>""", unsafe_allow_html=True)

        eff_color = "#2e7d32" if eff_pct>=100 else ("#f57c00" if eff_pct>=70 else "#c62828")
        st.markdown(f"""
        <div style="margin-top:10px;background:#1a3a5c;color:#fff;border-radius:8px;padding:12px;text-align:center;">
          <div style="font-size:.7rem;opacity:.7;text-transform:uppercase;letter-spacing:.05em;">Total Pieces</div>
          <div style="font-size:2rem;font-weight:700;font-family:'IBM Plex Mono',monospace;">{total_pcs}</div>
          <div style="font-size:.7rem;opacity:.7;margin-top:6px;">Efficiency</div>
          <div style="font-size:1.5rem;font-weight:700;color:{eff_color};">{eff_pct}%</div>
          <div style="font-size:.7rem;opacity:.7;margin-top:6px;">Piece Value</div>
          <div style="font-size:1.3rem;font-weight:700;">₹{piece_val:,.0f}</div>
          <div style="font-size:.7rem;opacity:.7;margin-top:6px;">Target</div>
          <div style="font-size:1rem;">{tgt_val} pcs</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("💾 Save Production Entry", key="pe_save", use_container_width=True,
                 type="primary"):
        # Group slots by operation and save one row per unique operation
        from collections import defaultdict
        op_groups = defaultdict(lambda: {"hours": {}, "pieces": 0})
        for hcol in HOUR_COLS:
            op = op_vals.get(hcol)
            if op is None:
                continue  # lunch slot
            pcs = h_vals.get(hcol, 0)
            op_groups[op]["hours"][hcol] = pcs
            op_groups[op]["pieces"] += pcs

        if not op_groups:
            st.error("No entries to save.")
        else:
            saved_ops = []
            for op_name, data in op_groups.items():
                op_info = style_ops[style_ops["Operation"] == op_name]
                if op_info.empty:
                    continue
                op_tgt  = int(op_info["Target"].values[0])
                op_rate = float(op_info["Rate_Rs"].values[0])
                op_pcs  = data["pieces"]
                op_eff  = round(op_pcs / op_tgt * 100, 1) if op_tgt > 0 else 0.0
                op_val  = round(op_pcs * op_rate, 2)
                # Build full hour columns (0 for hours not assigned to this op)
                hour_row = {hcol: data["hours"].get(hcol, 0) for hcol in HOUR_COLS}
                new_row = {
                    "Date": str(pe_date),
                    "Karigar_ID": k_row["Karigar_ID"],
                    "Karigar_Name": k_row["Name"],
                    "Challan_No": challan_no,
                    "Style": pe_style,
                    "Operation": op_name,
                    **hour_row,
                    "Total_Pieces": op_pcs,
                    "Target": op_tgt,
                    "Rate_Rs": op_rate,
                    "Efficiency_%": op_eff,
                    "Piece_Value_Rs": op_val,
                }
                st.session_state.production_log = pd.concat(
                    [st.session_state.production_log, pd.DataFrame([new_row])], ignore_index=True)
                saved_ops.append(f"{op_name}: {op_pcs} pcs ({op_eff}%) ₹{op_val}")
            st.success(f"✅ Saved {len(saved_ops)} operation(s) for {k_row['Name']}:\n" + "\n".join(saved_ops))
            st.rerun()

    # ── KARIGAR SUMMARY ────────────────────────────────────────────
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
            with e1: st.download_button("📥 Excel",to_excel_bytes(day_pl),f"prod_{flt_d}.xlsx")
            with e2: st.download_button("📥 CSV",  to_csv_bytes(day_pl),  f"prod_{flt_d}.csv")
        else:
            st.info("No entries for selected date.")
    else:
        st.info("No production entries yet.")


# ══════════════════════════════════════════════════════════
# TAB 3 ─ CHALLAN MANAGEMENT
# ══════════════════════════════════════════════════════════
with tab_challan:
    st.markdown('<div class="sec-hdr">🧾 Challan Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Add challans, track received quantity and deposit. Select any challan below to update it.</div>', unsafe_allow_html=True)

    import_section("challan_master", "challan_master", "Challan Master")

    # ── ADD NEW CHALLAN ──────────────────────────────────────────
    with st.expander("➕ Add New Challan", expanded=True):
        with st.form("add_ch", clear_on_submit=True):
            ca1, ca2 = st.columns(2)
            with ca1:
                c_no    = st.text_input("Challan No *", placeholder="e.g. 10220-2526")
                c_style = st.selectbox("Style *", sm["Style"].unique().tolist() if not sm.empty else [""])
                c_party = st.text_input("Party Name",   placeholder="e.g. Aashirwad Garments")
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
                    st.success(f"✅ Challan {c_no} added — {c_qty} pcs")
                    st.rerun()

    # ── REGISTER ────────────────────────────────────────────────
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

        # ── UPDATE ───────────────────────────────────────────────
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
                    st.success(f"✅ {upd_ch} updated — Qty: {new_qty}, Received: {new_rec}, Deposit: ₹{new_dep}, Rate: ₹{new_rate}")
                    st.rerun()

    st.download_button("📥 Export Challans (Excel)", to_excel_bytes(st.session_state.challan_master), "challans.xlsx")


# ══════════════════════════════════════════════════════════
# TAB 4 ─ STYLE COSTING (P&L)
# ══════════════════════════════════════════════════════════
with tab_style:
    st.markdown('<div class="sec-hdr">💎 Style-wise Costing — Profit & Loss</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Filter by month to see which challans ran, cost vs party rate, and profit/loss per piece.</div>', unsafe_allow_html=True)

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
        m1.metric("Total Pieces",    f"{int(cm_sc['Total_Qty'].sum()):,}")
        m2.metric("Party Value",     f"₹{tv:,.0f}")
        m3.metric("Total Cost",      f"₹{tc:,.0f}")
        m4.metric("Net P&L",         f"₹{tpl:,.0f}", delta=f"{tpl:+.0f}")

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
        with e1: st.download_button("📥 Style Costing Excel",to_excel_bytes(cm_sc[dc]),f"style_pl_{sel_mo}.xlsx")
        with e2: st.download_button("📥 Style Costing CSV",  to_csv_bytes(cm_sc[dc]),  f"style_pl_{sel_mo}.csv")


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
            with e1: st.download_button("📥 Excel",to_excel_bytes(ke),"efficiency.xlsx")
            with e2: st.download_button("📥 CSV",  to_csv_bytes(ke),  "efficiency.csv")


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
                with px1: st.download_button("📥 Payroll Excel",to_excel_bytes(pr),f"payroll_{pay_s}_{pay_e}.xlsx",key="py_x")
                with px2: st.download_button("📥 Payroll CSV",  to_csv_bytes(pr),  f"payroll_{pay_s}_{pay_e}.csv", key="py_c")


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
        st.session_state.karigar_attendance=pd.DataFrame(rows4); st.rerun()

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
                st.session_state.karigar_attendance=pd.concat([st.session_state.karigar_attendance,pd.DataFrame([na])],ignore_index=True)
                st.success(f"✅ {er2['Name']} | {py}h payable | ₹{tp}")

    # ── AUTO-CALCULATE ATTENDANCE FROM PRODUCTION ENTRIES ──────────────
    with st.expander("🔄 Auto-Calculate Attendance from Production Entries",expanded=False):
        st.markdown("""
        <div class="info-box">
        This calculates attendance based on the hour-wise entries you fill in the Production tab.
        It tracks which hours each Karigar worked and generates attendance records.
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📊 Calculate Attendance from Production Log",use_container_width=True):
            pl = st.session_state.production_log
            if pl.empty:
                st.warning("No production entries found.")
            else:
                # Group by Date and Karigar_ID, calculate hours worked
                att_records = []
                for (d, kid), group in pl.groupby(["Date", "Karigar_ID"]):
                    kar_name = group["Karigar_Name"].iloc[0] if "Karigar_Name" in group.columns else f"K-{kid}"
                    
                    # Count non-zero hour slots (9-20 hours, excluding 13-14 lunch)
                    hour_cols_worked = [h for h in HOUR_COLS if h != "H_13_14" and any(group[h].astype(str).str.strip() != "0")]
                    hours_worked = len(hour_cols_worked)
                    
                    if hours_worked > 0:
                        # Get daily rate
                        emp_rec = st.session_state.employee_master[st.session_state.employee_master["E_Code"] == kid]
                        if not emp_rec.empty:
                            daily_rate = float(emp_rec["Daily_Rate_Rs"].values[0])
                            hourly_rate = daily_rate / 8
                            normal_pay = hours_worked * hourly_rate if hours_worked <= 8 else 8 * hourly_rate
                            ot_hours = max(hours_worked - 8, 0)
                            ot_pay = ot_hours * hourly_rate * ot_m
                            total_pay = normal_pay + ot_pay
                            
                            att_records.append({
                                "Date": str(d),
                                "E_Code": kid,
                                "Name": kar_name,
                                "In_Punch": "09:00",
                                "Out_Punch": "18:00",
                                "Total_Presence_Hrs": float(hours_worked),
                                "Lunch_Deduction_Hrs": 1.0 if hours_worked >= 9 else 0.0,
                                "Payable_Hrs": float(max(hours_worked - 1, 0)) if hours_worked >= 9 else float(hours_worked),
                                "Hourly_Rate_Rs": hourly_rate,
                                "Normal_Pay": normal_pay,
                                "OT_Hours": ot_hours,
                                "OT_Pay": ot_pay,
                                "Total_Pay": total_pay
                            })
                
                if att_records:
                    new_att = pd.DataFrame(att_records)
                    st.session_state.karigar_attendance = pd.concat(
                        [st.session_state.karigar_attendance, new_att], 
                        ignore_index=True
                    ).drop_duplicates(subset=["Date", "E_Code"], keep="last")
                    st.success(f"✅ Generated {len(att_records)} attendance records from production entries!")
                    st.dataframe(new_att, use_container_width=True, hide_index=True)
                else:
                    st.info("No working hours found in production entries.")

    if not st.session_state.karigar_attendance.empty:
        af=st.date_input("Filter Date",value=date.today(),key="att_f")
        av=st.session_state.karigar_attendance[st.session_state.karigar_attendance["Date"]==str(af)]
        if not av.empty:
            st.dataframe(av,use_container_width=True,hide_index=True)
            st.download_button("📥 Download",to_excel_bytes(av),f"att_{af}.xlsx")


# ══════════════════════════════════════════════════════════
# TAB 8 ─ OPERATING STAFF
# ══════════════════════════════════════════════════════════
with tab_op:
    st.markdown('<div class="sec-hdr">🏢 Operating Staff</div>', unsafe_allow_html=True)
    import_section("operating_attendance","operating_attendance","Operating Staff Attendance")
    eo2=st.session_state.employee_master[st.session_state.employee_master["Type"]=="Operating"]
    oo2={f"{r['E_Code']} – {r['Name']}":r for _,r in eo2.iterrows()}
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
                st.success(f"✅ {er3['Name']} | {hrs3}h | ₹{tp3}")


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
                    st.success(f"Added operation '{no}' to style '{ns}'!")
        st.dataframe(st.session_state.style_master,use_container_width=True,hide_index=True)
        st.download_button("📥 Export Style Master",to_excel_bytes(st.session_state.style_master),"style_master.xlsx",key="dl_sm")

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
                    st.success(f"✅ Added {k_nm} (Karigar: {k_id}, Employee: {ec5})")
        st.dataframe(st.session_state.karigar_master,use_container_width=True,hide_index=True)
        st.download_button("📥 Export Karigar Master",to_excel_bytes(st.session_state.karigar_master),"karigar_master.xlsx",key="dl_km")

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
                    st.success(f"✅ Added employee {em_n} ({em_c})")
        st.dataframe(st.session_state.employee_master,use_container_width=True,hide_index=True)
        st.download_button("📥 Export Employee Master",to_excel_bytes(st.session_state.employee_master),"employee_master.xlsx",key="dl_em")

st.markdown("---")
st.markdown("🧵 <b>Stitching Costing Interface v4.0</b> — Yash Gallery Pvt Ltd", unsafe_allow_html=True)
