"""
Stitching Costing Interface v3.0 — Yash Gallery Pvt Ltd
UPGRADES:
- Production Entry: Karigar search bar, Style->Challan flow, tab-wise operations, horizontal hour entry
- Karigar Summary: Live summary panel below entry
- Challan Management: PDF-style size-wise tracking (XL/XXL/3XL/4XL/5XL)
- Style-wise Costing: Month filter, challan/style runs, profit/loss
- Enhanced Dashboard with all KPIs
- Universal Data Export & Import (backup/restore full state)
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import io, hashlib, zipfile

st.set_page_config(
    page_title="Stitching Costing — Yash Gallery",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.main-header { background: linear-gradient(135deg, #1a3a5c 0%, #2c5aa0 60%, #1e7ed4 100%); padding: 18px 24px; border-radius: 10px; color: white; margin-bottom: 18px; }
.main-header h2 { margin: 0; font-size: 1.5rem; font-weight: 700; }
.main-header p  { margin: 4px 0 0; opacity: 0.85; font-size: 0.88rem; }
.metric-card { background: #f0f6ff; padding: 14px 18px; border-radius: 8px; border-left: 4px solid #2c5aa0; color: #1a3a52; text-align: center; margin: 4px 0; }
.metric-card .mv { font-size: 1.8rem; font-weight: 700; color: #2c5aa0; font-family: 'IBM Plex Mono', monospace; }
.metric-card .ml { font-size: 0.78rem; opacity: 0.7; font-weight: 500; margin-bottom: 2px; text-transform: uppercase; letter-spacing: .05em; }
.metric-card .ms { font-size: 0.72rem; opacity: 0.55; margin-top: 2px; }
.metric-green  { background:#f0faf2; border-left-color:#2e7d32; } .metric-green  .mv { color:#2e7d32; }
.metric-red    { background:#fff5f5; border-left-color:#c62828; } .metric-red    .mv { color:#c62828; }
.metric-orange { background:#fff8f0; border-left-color:#e65100; } .metric-orange .mv { color:#e65100; }
.sec-hdr { background: #2c5aa0; color: white; padding: 8px 14px; border-radius: 6px; font-weight: 600; margin: 10px 0 6px; font-size: 0.92rem; }
.info-box  { background:#e8f1f8; border-left:4px solid #2c5aa0; padding:10px 14px; border-radius:4px; margin:6px 0; font-size:0.88rem; color:#1a3a52; }
.warn-box  { background:#fff3e0; border-left:4px solid #f57c00; padding:10px 14px; border-radius:4px; margin:6px 0; font-size:0.88rem; color:#e65100; }
.ok-box    { background:#e8f5e9; border-left:4px solid #2e7d32; padding:10px 14px; border-radius:4px; margin:6px 0; font-size:0.88rem; color:#1b5e20; }
.err-box   { background:#fce4ec; border-left:4px solid #c2185b; padding:10px 14px; border-radius:4px; margin:6px 0; font-size:0.88rem; color:#880e4f; }
.ro-field  { background:#f5f5f5; border:1px solid #bdbdbd; padding:9px 12px; border-radius:4px; font-weight:600; color:#424242; font-size:0.9rem; }
.size-pill { display:inline-block; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; margin:2px; }
.sp-xl  { background:#e3f2fd; color:#1565c0; }
.sp-xxl { background:#ede7f6; color:#4527a0; }
.sp-3xl { background:#e8f5e9; color:#1b5e20; }
.sp-4xl { background:#fff3e0; color:#e65100; }
.sp-5xl { background:#fce4ec; color:#880e4f; }
.summary-strip { background:#1a3a5c; color:white; padding:12px 18px; border-radius:8px; display:flex; gap:24px; align-items:center; flex-wrap:wrap; margin:8px 0; }
.ss-item { text-align:center; }
.ss-val  { font-size:1.3rem; font-weight:700; font-family:'IBM Plex Mono',monospace; }
.ss-lbl  { font-size:0.72rem; opacity:0.7; text-transform:uppercase; letter-spacing:.05em; }
</style>
""", unsafe_allow_html=True)

# ─────── Helpers ───────
def safe_numeric(s): return pd.to_numeric(s, errors='coerce').fillna(0)
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()
def read_upload(f):
    n = f.name.lower()
    if n.endswith(".csv"): return pd.read_csv(f)
    if n.endswith((".xlsx",".xls")): return pd.read_excel(f)
    st.error("Use CSV or XLSX"); return None
def to_excel(df):
    buf = io.BytesIO()
    try:
        with pd.ExcelWriter(buf, engine="openpyxl") as w: df.to_excel(w, index=False)
    except: return df.to_csv(index=False).encode()
    return buf.getvalue()
def to_csv(df): return df.to_csv(index=False).encode()

SIZE_COLS = ["XL","XXL","3XL","4XL","5XL"]
HOUR_COLS = ["H_09_10","H_10_11","H_11_12","H_12_13","H_14_15","H_15_16","H_16_17","H_17_18","H_18_19"]
HOUR_LBLS = ["9-10","10-11","11-12","12-13","14-15","15-16","16-17","17-18","18-19"]
DEFAULT_PW_HASH = hash_pw("admin123")

# ─────── Auth ───────
def init_auth():
    if "admin_pw_hash"  not in st.session_state: st.session_state.admin_pw_hash  = DEFAULT_PW_HASH
    if "sheet_unlocked" not in st.session_state: st.session_state.sheet_unlocked = False

def lock_widget(key="default"):
    if st.session_state.sheet_unlocked:
        c1,c2 = st.columns([5,1])
        with c2:
            if st.button("🔒 Lock", key=f"lock_{key}"): st.session_state.sheet_unlocked=False; st.rerun()
        st.markdown('<div class="ok-box">✅ <b>UNLOCKED</b> — Admin mode active</div>', unsafe_allow_html=True)
        return True
    st.markdown('<div class="warn-box">🔐 <b>LOCKED</b> — Target & Rate read-only</div>', unsafe_allow_html=True)
    c1,c2 = st.columns([3,1])
    with c1: pw = st.text_input("Password", type="password", key=f"pw_{key}", label_visibility="collapsed", placeholder="Admin password")
    with c2:
        if st.button("🔓 Unlock", key=f"ul_{key}"):
            if hash_pw(pw)==st.session_state.admin_pw_hash: st.session_state.sheet_unlocked=True; st.rerun()
            else: st.error("❌ Wrong password")
    return False

# ─────── Salary ───────
def calc_salary(in_str, out_str, daily_rate, ot_mult=1.5):
    try:
        fmt="%H:%M"; t_in=datetime.strptime(in_str.strip(),fmt); t_out=datetime.strptime(out_str.strip(),fmt)
        shift_end=datetime.strptime("18:00",fmt); ls=datetime.strptime("13:00",fmt); le=datetime.strptime("14:00",fmt)
        ph=max(int((t_out-t_in).total_seconds()),0)/3600
        ld=1.0 if(t_in<le and t_out>ls) else 0.0
        pay_h=max(ph-ld,0.0); hr=daily_rate/8; np_=round(pay_h*hr,2)
        oth=max(int((t_out-shift_end).total_seconds()),0)/3600 if t_out>shift_end else 0.0
        otp=round(oth*hr*ot_mult,2); tp=round(np_+otp,2)
        return round(ph,2),round(ld,2),round(pay_h,2),round(hr,2),np_,round(oth,2),otp,tp
    except: return 0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0

# ─────── Op Cost ───────
def op_cost_alloc(report_date):
    pl=st.session_state.production_log; att=st.session_state.karigar_attendance; op=st.session_state.operating_attendance
    empty=pd.DataFrame(columns=["Challan_No","Style","Karigar_Cost_Rs","Karigar_Cost_Pct","Allocated_Op_Cost_Rs","Total_Style_Cost_Rs"])
    if pl.empty or att.empty: return empty,0.0,0.0
    pl_d=pl[pl["Date"]==report_date].copy(); att_d=att[att["Date"]==report_date].copy()
    if pl_d.empty or att_d.empty: return empty,0.0,0.0
    if "Payable_Hrs" not in att_d.columns: return empty,0.0,0.0
    att_d["dc"]=safe_numeric(att_d["Payable_Hrs"])*safe_numeric(att_d["Hourly_Rate_Rs"])
    cm=att_d.set_index("E_Code")["dc"].to_dict()
    pl_d["KC"]=safe_numeric(pl_d["Karigar_ID"].map(cm).fillna(0))
    tpk=pl_d.groupby("Karigar_ID")["Total_Pieces"].transform("sum").replace(0,1)
    pl_d["AC"]=pl_d["KC"]*safe_numeric(pl_d["Total_Pieces"])/tpk
    grp=pl_d.groupby(["Challan_No","Style"])["AC"].sum().reset_index(); grp.columns=["Challan_No","Style","Karigar_Cost_Rs"]
    tok=grp["Karigar_Cost_Rs"].sum()
    if tok==0: return empty,0.0,0.0
    op_d=op[op["Date"]==report_date] if not op.empty else pd.DataFrame()
    too=safe_numeric(op_d["Total_Pay"]).sum() if not op_d.empty else 0.0
    grp["Karigar_Cost_Pct"]=(grp["Karigar_Cost_Rs"]/tok*100).round(2)
    grp["Allocated_Op_Cost_Rs"]=(grp["Karigar_Cost_Pct"]/100*too).round(2)
    grp["Total_Style_Cost_Rs"]=(grp["Karigar_Cost_Rs"]+grp["Allocated_Op_Cost_Rs"]).round(2)
    return grp.round(2),round(tok,2),round(too,2)

# ─────── Backup / Restore ───────
DATA_KEYS=["style_master","karigar_master","challan_master","production_log",
           "employee_master","karigar_attendance","operating_attendance","challan_sizes"]

def export_all():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as zf:
        for k in DATA_KEYS:
            df=st.session_state.get(k,pd.DataFrame())
            if not isinstance(df,pd.DataFrame): df=pd.DataFrame()
            zf.writestr(f"{k}.csv",df.to_csv(index=False))
    return buf.getvalue()

def import_all(zb):
    with zipfile.ZipFile(io.BytesIO(zb)) as zf:
        for nm in zf.namelist():
            k=nm.replace(".csv","")
            if k in DATA_KEYS: st.session_state[k]=pd.read_csv(io.StringIO(zf.read(nm).decode()))
    st.success("✅ All data restored!")

# ─────── Session Init ───────
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
            {"Karigar_ID":"K001","Name":"Ramesh Kumar",  "Skill":"Stitching","Daily_Rate_Rs":450},
            {"Karigar_ID":"K002","Name":"Suresh Singh",  "Skill":"Cutting",  "Daily_Rate_Rs":420},
            {"Karigar_ID":"K003","Name":"Priya Devi",    "Skill":"Finishing","Daily_Rate_Rs":400},
            {"Karigar_ID":"K004","Name":"Mohan Lal",     "Skill":"Stitching","Daily_Rate_Rs":460},
            {"Karigar_ID":"K005","Name":"Sunita Sharma", "Skill":"Hemming",  "Daily_Rate_Rs":410},
        ])
    if "challan_master" not in st.session_state:
        st.session_state.challan_master = pd.DataFrame([
            {"Challan_No":"10220-2526","Style":"1894YKDGREEN","Party":"Aashirwad Garments",
             "Total_Qty":376,"Received_Qty":0,"Deposit_Rs":0.0,"Rate_Per_Pc":35,"Date":"2026-02-25","Delivery_By":"2026-03-07"},
        ])
    if "challan_sizes" not in st.session_state:
        st.session_state.challan_sizes = pd.DataFrame([
            {"Challan_No":"10220-2526","Style":"1894YKDGREEN","XL":20,"XXL":50,"3XL":75,"4XL":90,"5XL":141},
        ])
    if "production_log" not in st.session_state:
        st.session_state.production_log = pd.DataFrame(columns=[
            "Date","Karigar_ID","Karigar_Name","Challan_No","Style","Operation",
        ]+HOUR_COLS+["Total_Pieces","Target","Rate_Rs","Efficiency_%","Piece_Value_Rs"])
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

def import_section(key, required_cols, session_key, label):
    with st.expander(f"📥 Import {label} from Excel/CSV", expanded=False):
        up=st.file_uploader("Upload file", type=["csv","xlsx","xls"], key=f"up_{key}")
        mode=st.radio("Mode",["➕ Append","🔄 Replace"], key=f"im_{key}", horizontal=True)
        if up:
            df_new=read_upload(up)
            if df_new is not None:
                miss=[c for c in required_cols if c not in df_new.columns]
                if miss: st.error(f"Missing columns: {miss}"); return
                st.dataframe(df_new.head(3), use_container_width=True, hide_index=True)
                st.info(f"{len(df_new)} rows detected")
                if st.button(f"✅ Confirm Import", key=f"ci_{key}"):
                    if "Replace" in mode: st.session_state[session_key]=df_new.reset_index(drop=True)
                    else: st.session_state[session_key]=pd.concat([st.session_state[session_key],df_new],ignore_index=True)
                    st.success("Imported!"); st.rerun()

# ═══ HEADER ═══
today_str=str(date.today())
st.markdown(f"""
<div class="main-header">
  <h2>🧵 Stitching Costing Interface — Yash Gallery Pvt Ltd</h2>
  <p>Karigar Tracking • Challan Management (Size-wise) • Style Costing P&L • Payroll • {date.today().strftime("%d %b %Y")}</p>
</div>""", unsafe_allow_html=True)

# ═══ SIDEBAR ═══
with st.sidebar:
    st.markdown("### 💾 Daily Backup & Restore")
    st.markdown('<div class="info-box">Export before closing. Import next morning to continue.</div>', unsafe_allow_html=True)
    st.download_button("📦 Export All Data (ZIP)", data=export_all(),
        file_name=f"yashgallery_backup_{today_str}.zip", mime="application/zip", use_container_width=True)
    rf=st.file_uploader("📂 Restore from ZIP backup", type=["zip"], key="restore_zip")
    if rf:
        if st.button("🔄 Restore Now", use_container_width=True, key="do_restore"):
            import_all(rf.read()); st.rerun()
    st.markdown("---")
    st.markdown("### 🔐 Admin")
    with st.expander("Change Password"):
        cur=st.text_input("Current",type="password",key="sb_cur")
        n1=st.text_input("New",type="password",key="sb_n1")
        n2=st.text_input("Confirm",type="password",key="sb_n2")
        if st.button("Change",key="sb_cp"):
            if hash_pw(cur)!=st.session_state.admin_pw_hash: st.error("Wrong current password")
            elif n1!=n2: st.error("Don't match")
            elif len(n1)<4: st.error("Min 4 chars")
            else: st.session_state.admin_pw_hash=hash_pw(n1); st.success("✅ Changed!")
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    pl_all=st.session_state.production_log
    today_pl_sb=pl_all[pl_all["Date"]==today_str] if not pl_all.empty else pd.DataFrame()
    st.metric("Today's Entries",len(today_pl_sb))
    st.metric("Total Karigar",len(st.session_state.karigar_master))
    st.metric("Active Challans",len(st.session_state.challan_master))
    if not today_pl_sb.empty:
        st.metric("Today's Pieces",int(safe_numeric(today_pl_sb["Total_Pieces"]).sum()))

# ═══ TABS ═══
tabs=st.tabs(["🏠 Dashboard","📋 Production Entry","🧾 Challan Management",
              "💎 Style Costing","📊 Efficiency","💰 Payroll",
              "🕐 Attendance","🏢 Operating Staff","🌟 Performance","⚙️ Master Data"])
(tab_dash,tab_prod,tab_challan,tab_style,tab_eff,tab_pay,tab_att,tab_op,tab_perf,tab_master)=tabs

# ══════════════════════════ TAB 1 — DASHBOARD ══════════════════════════
with tab_dash:
    st.markdown('<div class="sec-hdr">📈 Today\'s Overview</div>', unsafe_allow_html=True)
    pl_all=st.session_state.production_log
    today_pl=pl_all[pl_all["Date"]==today_str] if not pl_all.empty else pd.DataFrame()
    active_k=today_pl["Karigar_ID"].nunique() if not today_pl.empty else 0
    pieces=int(safe_numeric(today_pl["Total_Pieces"]).sum()) if not today_pl.empty else 0
    avg_eff=safe_numeric(today_pl["Efficiency_%"]).mean() if not today_pl.empty and "Efficiency_%" in today_pl.columns else 0.0
    pv=safe_numeric(today_pl["Piece_Value_Rs"]).sum() if not today_pl.empty else 0.0
    cm_all=st.session_state.challan_master
    if not cm_all.empty:
        cm2=cm_all.copy(); cm2["Pend"]=safe_numeric(cm2["Total_Qty"])-safe_numeric(cm2.get("Received_Qty",0))
        pending_c=len(cm2[cm2["Pend"]>0])
    else: pending_c=0

    c1,c2,c3,c4,c5,c6=st.columns(6)
    cards=[(c1,active_k,f"of {len(st.session_state.karigar_master)} total","Active Karigar",""),
           (c2,f"{pieces:,}","pieces today","Pieces Done",""),
           (c3,f"{avg_eff:.1f}%","target: 100%","Avg Efficiency","metric-green" if avg_eff>=85 else "metric-orange"),
           (c4,f"₹{pv:,.0f}","piece-rate value","Today's Value",""),
           (c5,len(cm_all),"total orders","Challans",""),
           (c6,pending_c,"in production","Pending Challans","metric-orange" if pending_c>0 else "metric-green")]
    for col,val,sub,lbl,cls in cards:
        with col: st.markdown(f'<div class="metric-card {cls}"><div class="ml">{lbl}</div><div class="mv">{val}</div><div class="ms">{sub}</div></div>',unsafe_allow_html=True)

    st.markdown("---")
    da,db=st.columns(2)
    with da:
        st.markdown('<div class="sec-hdr">👷 Karigar Status</div>', unsafe_allow_html=True)
        km=st.session_state.karigar_master.copy()
        aids=today_pl["Karigar_ID"].unique().tolist() if not today_pl.empty else []
        km["Today"]=km["Karigar_ID"].apply(lambda x:"🟢 Working" if x in aids else "⚪ Idle")
        if not today_pl.empty and "Piece_Value_Rs" in today_pl.columns:
            pvk=today_pl.groupby("Karigar_ID")["Piece_Value_Rs"].sum().reset_index(); pvk.columns=["Karigar_ID","Value ₹"]
            km=km.merge(pvk,on="Karigar_ID",how="left").fillna({"Value ₹":0})
        st.dataframe(km,use_container_width=True,hide_index=True)
    with db:
        st.markdown('<div class="sec-hdr">🧾 Active Challans</div>', unsafe_allow_html=True)
        if not cm_all.empty:
            cm_d=cm_all.copy(); cm_d["Pending"]=safe_numeric(cm_d["Total_Qty"])-safe_numeric(cm_d.get("Received_Qty",0))
            cm_d["Status"]=cm_d["Pending"].apply(lambda x:"✅ Done" if x<=0 else f"⏳ {int(x)} pending")
            st.dataframe(cm_d[[c for c in["Challan_No","Style","Party","Total_Qty","Pending","Status"] if c in cm_d.columns]],use_container_width=True,hide_index=True)

    if not today_pl.empty:
        st.markdown("---")
        st.markdown('<div class="sec-hdr">📋 Today\'s Production Summary</div>', unsafe_allow_html=True)
        sc=[c for c in["Karigar_Name","Challan_No","Style","Operation","Total_Pieces","Target","Efficiency_%","Piece_Value_Rs"] if c in today_pl.columns]
        st.dataframe(today_pl[sc],use_container_width=True,hide_index=True)
        alloc,tok,too=op_cost_alloc(today_str)
        if not alloc.empty:
            st.markdown('<div class="sec-hdr">💼 Style-wise Cost Today</div>', unsafe_allow_html=True)
            mx1,mx2,mx3=st.columns(3)
            mx1.metric("Karigar Cost",f"₹{tok:,.2f}"); mx2.metric("Operating Cost",f"₹{too:,.2f}"); mx3.metric("Total",f"₹{tok+too:,.2f}")
            st.dataframe(alloc,use_container_width=True,hide_index=True)

# ══════════════════════════ TAB 2 — PRODUCTION ENTRY ══════════════════════════
with tab_prod:
    st.markdown('<div class="sec-hdr">📋 Production Entry</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box"><b>Flow:</b> 🔍 Search Karigar → 👗 Select Style → 🧾 Select Challan → ⚙️ Select Operation Tab → ⏱ Enter Hourly Pieces</div>',unsafe_allow_html=True)
    is_unlocked=lock_widget("prod")
    import_section("production_log",["Date","Karigar_ID","Karigar_Name","Challan_No","Style","Operation"]+HOUR_COLS+["Target","Rate_Rs"],"production_log","Production Log")

    st.markdown("---")
    st.markdown('<div class="sec-hdr">✏️ New Entry</div>', unsafe_allow_html=True)
    pe_col1,pe_col2=st.columns([1,2])
    with pe_col1: pe_date=st.date_input("📅 Date", value=date.today(), key="pe_date")
    with pe_col2:
        karigar_df=st.session_state.karigar_master
        srch=st.text_input("🔍 Search Karigar (name or ID)", key="ksearch", placeholder="Type to filter — e.g. Ramesh or K001")
        if srch:
            mask=(karigar_df["Name"].str.contains(srch,case=False,na=False)|karigar_df["Karigar_ID"].str.contains(srch,case=False,na=False))
            filt_k=karigar_df[mask]
        else: filt_k=karigar_df
        if filt_k.empty: st.warning("No karigar found."); st.stop()
        k_opts={f"{r['Karigar_ID']} — {r['Name']}":r for _,r in filt_k.iterrows()}
        pe_kkey=st.selectbox("👤 Select Karigar",list(k_opts.keys()),key="pe_kar")
        pe_krow=k_opts[pe_kkey]

    all_styles=st.session_state.style_master["Style"].unique().tolist() if not st.session_state.style_master.empty else []
    if not all_styles: st.warning("No styles defined. Add in Master Data."); st.stop()
    pe_style=st.selectbox("👗 Select Style", all_styles, key="pe_style")

    ch_df=st.session_state.challan_master
    style_ch=ch_df[ch_df["Style"]==pe_style] if not ch_df.empty else pd.DataFrame()
    if style_ch.empty:
        st.warning(f"No challans for style '{pe_style}'. Add challan in Challan Management first.")
    else:
        ch_opts={f"{r['Challan_No']} | {r.get('Party','—')} | Qty:{int(safe_numeric(pd.Series([r['Total_Qty']])).iloc[0])}":r for _,r in style_ch.iterrows()}
        pe_chkey=st.selectbox("🧾 Select Challan",list(ch_opts.keys()),key="pe_challan")
        pe_chrow=ch_opts[pe_chkey]; pe_chno=pe_chrow["Challan_No"]
        c_qty=int(safe_numeric(pd.Series([pe_chrow["Total_Qty"]])).iloc[0])
        c_rec=int(safe_numeric(pd.Series([pe_chrow.get("Received_Qty",0)])).iloc[0])
        st.markdown(f'<div class="ro-field">📦 Challan <b>{pe_chno}</b> | Style: <b>{pe_style}</b> | Party: <b>{pe_chrow.get("Party","—")}</b> | Total: <b>{c_qty} pcs</b> | Received: <b>{c_rec}</b> | Pending: <b>{c_qty-c_rec}</b></div>',unsafe_allow_html=True)

        sm_ops=st.session_state.style_master[st.session_state.style_master["Style"]==pe_style][["Operation","Target","Rate_Rs"]]
        if sm_ops.empty: st.warning("No operations for this style.")
        else:
            st.markdown('<div class="sec-hdr">⚙️ Select Operation</div>', unsafe_allow_html=True)
            op_mode=st.radio("",["📋 Existing Operations","➕ Add New Operation"],key="op_mode",horizontal=True,label_visibility="collapsed")

            if "Existing" in op_mode:
                ops_list=sm_ops["Operation"].tolist()
                op_tabs=st.tabs(ops_list)
                for i,op_tab in enumerate(op_tabs):
                    with op_tab:
                        cur_op=ops_list[i]
                        op_row=sm_ops[sm_ops["Operation"]==cur_op]
                        tgt=int(op_row["Target"].values[0]); rate=float(op_row["Rate_Rs"].values[0])
                        ct,cr=st.columns(2)
                        with ct:
                            if is_unlocked: tgt=st.number_input("🎯 Target",value=tgt,min_value=0,key=f"tgt_{i}")
                            else: st.markdown(f'<div class="ro-field">🎯 Target: <b>{tgt} pcs</b> 🔒</div>',unsafe_allow_html=True)
                        with cr:
                            if is_unlocked: rate=st.number_input("💰 Rate/pc",value=rate,min_value=0.0,step=0.25,format="%.2f",key=f"rate_{i}")
                            else: st.markdown(f'<div class="ro-field">💰 Rate: <b>₹{rate:.2f}/pc</b> 🔒</div>',unsafe_allow_html=True)

                        st.markdown("**⏱ Hourly Pieces**")
                        hv={}; hc=st.columns(len(HOUR_COLS))
                        for j,(hcol,hl) in enumerate(zip(HOUR_COLS,HOUR_LBLS)):
                            with hc[j]:
                                st.markdown(f"<div style='text-align:center;font-size:0.73rem;color:#666;margin-bottom:2px'><b>{hl}</b></div>",unsafe_allow_html=True)
                                hv[hcol]=st.number_input("",min_value=0,step=1,value=0,key=f"h{i}_{hcol}",label_visibility="collapsed")

                        tp2=sum(hv.values()); eff2=round(tp2/tgt*100,1) if tgt>0 else 0.0; pval=round(tp2*rate,2)
                        st.markdown(f"""<div class="summary-strip">
                            <div class="ss-item"><div class="ss-val">{tp2}</div><div class="ss-lbl">Total Pieces</div></div>
                            <div class="ss-item"><div class="ss-val">{eff2}%</div><div class="ss-lbl">Efficiency</div></div>
                            <div class="ss-item"><div class="ss-val">₹{pval:,.0f}</div><div class="ss-lbl">Piece Value</div></div>
                            <div class="ss-item"><div class="ss-val">{tgt}</div><div class="ss-lbl">Target</div></div>
                        </div>""",unsafe_allow_html=True)

                        if st.button(f"💾 Save — {cur_op}",key=f"sv_{i}",use_container_width=True):
                            nr={"Date":str(pe_date),"Karigar_ID":pe_krow["Karigar_ID"],"Karigar_Name":pe_krow["Name"],
                                "Challan_No":pe_chno,"Style":pe_style,"Operation":cur_op,**hv,
                                "Total_Pieces":tp2,"Target":tgt,"Rate_Rs":rate,"Efficiency_%":eff2,"Piece_Value_Rs":pval}
                            st.session_state.production_log=pd.concat([st.session_state.production_log,pd.DataFrame([nr])],ignore_index=True)
                            st.success(f"✅ {pe_krow['Name']} | {cur_op} | {tp2} pcs | {eff2}% | ₹{pval}"); st.rerun()
            else:
                st.markdown('<div class="info-box">Enter a new operation not yet in the style master.</div>',unsafe_allow_html=True)
                no_name=st.text_input("Operation Name",key="no_name")
                nc,nr2=st.columns(2)
                with nc: no_tgt=st.number_input("Target",min_value=1,step=1,value=80,key="no_tgt")
                with nr2: no_rate=st.number_input("Rate/pc (₹)",min_value=0.0,step=0.25,format="%.2f",value=3.0,key="no_rate")
                hv2={}; hc2=st.columns(len(HOUR_COLS))
                for j,(hcol,hl) in enumerate(zip(HOUR_COLS,HOUR_LBLS)):
                    with hc2[j]:
                        st.markdown(f"<div style='text-align:center;font-size:0.73rem;color:#666'><b>{hl}</b></div>",unsafe_allow_html=True)
                        hv2[hcol]=st.number_input("",min_value=0,step=1,value=0,key=f"nh{j}",label_visibility="collapsed")
                tp3=sum(hv2.values()); eff3=round(tp3/no_tgt*100,1) if no_tgt>0 else 0.0; pval3=round(tp3*no_rate,2)
                st.markdown(f"""<div class="summary-strip">
                    <div class="ss-item"><div class="ss-val">{tp3}</div><div class="ss-lbl">Total Pieces</div></div>
                    <div class="ss-item"><div class="ss-val">{eff3}%</div><div class="ss-lbl">Efficiency</div></div>
                    <div class="ss-item"><div class="ss-val">₹{pval3:,.0f}</div><div class="ss-lbl">Piece Value</div></div>
                </div>""",unsafe_allow_html=True)
                if st.button("💾 Save New Operation",key="sv_new",use_container_width=True):
                    if not no_name: st.error("Enter operation name")
                    else:
                        st.session_state.style_master=pd.concat([st.session_state.style_master,
                            pd.DataFrame([{"Style":pe_style,"Operation":no_name,"Target":no_tgt,"Rate_Rs":no_rate}])],ignore_index=True)
                        nr3={"Date":str(pe_date),"Karigar_ID":pe_krow["Karigar_ID"],"Karigar_Name":pe_krow["Name"],
                             "Challan_No":pe_chno,"Style":pe_style,"Operation":no_name,**hv2,
                             "Total_Pieces":tp3,"Target":no_tgt,"Rate_Rs":no_rate,"Efficiency_%":eff3,"Piece_Value_Rs":pval3}
                        st.session_state.production_log=pd.concat([st.session_state.production_log,pd.DataFrame([nr3])],ignore_index=True)
                        st.success(f"✅ New operation '{no_name}' saved and added to style master!"); st.rerun()

    st.markdown("---")
    st.markdown('<div class="sec-hdr">👷 Karigar Summary — Daily View</div>', unsafe_allow_html=True)
    if not st.session_state.production_log.empty:
        flt_d=st.date_input("Filter Date",value=date.today(),key="prod_flt")
        day_pl=st.session_state.production_log[st.session_state.production_log["Date"]==str(flt_d)].copy()
        if not day_pl.empty:
            for c in["Total_Pieces","Target","Rate_Rs","Efficiency_%","Piece_Value_Rs"]:
                if c in day_pl.columns: day_pl[c]=safe_numeric(day_pl[c])
            sv1,sv2=st.tabs(["📋 All Entries","👷 Karigar Summary"])
            with sv1:
                sc=[c for c in["Karigar_Name","Challan_No","Style","Operation","Total_Pieces","Target","Efficiency_%","Piece_Value_Rs"] if c in day_pl.columns]
                st.dataframe(day_pl[sc],use_container_width=True,hide_index=True)
            with sv2:
                ks=day_pl.groupby(["Karigar_ID","Karigar_Name"]).agg(
                    Ops=("Operation","count"),Total_Pieces=("Total_Pieces","sum"),
                    Total_Target=("Target","sum"),Piece_Value=("Piece_Value_Rs","sum")).reset_index()
                ks["Efficiency_%"]=(ks["Total_Pieces"]/ks["Total_Target"].replace(0,1)*100).round(1)
                ks["Grade"]=ks["Efficiency_%"].apply(lambda x:"A ⭐" if x>=100 else("B ✅" if x>=85 else("C ⚠️" if x>=70 else"D ❌")))
                st.dataframe(ks,use_container_width=True,hide_index=True)
                # Challan-wise
                cs2=day_pl.groupby(["Challan_No","Style"]).agg(Pieces=("Total_Pieces","sum"),Value=("Piece_Value_Rs","sum"),Ops=("Operation","nunique")).reset_index()
                st.markdown("**Challan-wise:**"); st.dataframe(cs2,use_container_width=True,hide_index=True)
            ex1,ex2=st.columns(2)
            with ex1: st.download_button("📥 Excel",to_excel(day_pl),f"prod_{flt_d}.xlsx")
            with ex2: st.download_button("📥 CSV",to_csv(day_pl),f"prod_{flt_d}.csv")
        else: st.info("No entries for selected date.")
    else: st.info("No production entries yet.")

# ══════════════════════════ TAB 3 — CHALLAN MANAGEMENT ══════════════════════════
with tab_challan:
    st.markdown('<div class="sec-hdr">🧾 Challan Management — Size-wise Tracking</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Manage challans with size breakdown (XL/XXL/3XL/4XL/5XL) as per Yash Gallery challan format.</div>',unsafe_allow_html=True)
    import_section("challan_master",["Challan_No","Style","Party","Total_Qty","Received_Qty","Deposit_Rs","Rate_Per_Pc","Date","Delivery_By"],"challan_master","Challan Master")
    import_section("challan_sizes",["Challan_No","Style"]+SIZE_COLS,"challan_sizes","Challan Size Chart")

    with st.expander("➕ Add New Challan",expanded=False):
        with st.form("add_ch_form",clear_on_submit=True):
            ca1,ca2,ca3=st.columns(3)
            with ca1:
                c_no=st.text_input("Challan No"); c_style=st.selectbox("Style",st.session_state.style_master["Style"].unique().tolist() if not st.session_state.style_master.empty else [""])
                c_party=st.text_input("Party Name")
            with ca2:
                c_date=st.date_input("Issue Date",value=date.today()); c_deliv=st.date_input("Delivery Before",value=date.today()+timedelta(days=10))
                c_rate=st.number_input("Rate/Pc (₹)",min_value=0.0,step=1.0,value=35.0)
            with ca3:
                c_dep=st.number_input("Deposit (₹)",min_value=0.0,step=100.0); c_rec=st.number_input("Received Qty",min_value=0,step=1,value=0)
            st.markdown("**Size-wise Quantity**")
            sb1,sb2,sb3,sb4,sb5=st.columns(5)
            with sb1: sz_xl=st.number_input("XL",min_value=0,step=1,value=0,key="c_xl")
            with sb2: sz_xxl=st.number_input("XXL",min_value=0,step=1,value=0,key="c_xxl")
            with sb3: sz_3xl=st.number_input("3XL",min_value=0,step=1,value=0,key="c_3xl")
            with sb4: sz_4xl=st.number_input("4XL",min_value=0,step=1,value=0,key="c_4xl")
            with sb5: sz_5xl=st.number_input("5XL",min_value=0,step=1,value=0,key="c_5xl")
            tszq=sz_xl+sz_xxl+sz_3xl+sz_4xl+sz_5xl
            if st.form_submit_button("✅ Add Challan") and c_no:
                st.session_state.challan_master=pd.concat([st.session_state.challan_master,pd.DataFrame([{
                    "Challan_No":c_no,"Style":c_style,"Party":c_party,"Total_Qty":max(tszq,1),
                    "Received_Qty":int(c_rec),"Deposit_Rs":float(c_dep),"Rate_Per_Pc":float(c_rate),"Date":str(c_date),"Delivery_By":str(c_deliv)
                }])],ignore_index=True)
                st.session_state.challan_sizes=pd.concat([st.session_state.challan_sizes,pd.DataFrame([{
                    "Challan_No":c_no,"Style":c_style,"XL":sz_xl,"XXL":sz_xxl,"3XL":sz_3xl,"4XL":sz_4xl,"5XL":sz_5xl
                }])],ignore_index=True)
                st.success(f"✅ Challan {c_no} added — {tszq} pieces"); st.rerun()

    st.markdown('<div class="sec-hdr">Challan Register</div>', unsafe_allow_html=True)
    cm=st.session_state.challan_master.copy()
    if not cm.empty:
        cm["Pending"]=safe_numeric(cm["Total_Qty"])-safe_numeric(cm.get("Received_Qty",0))
        cm["Status"]=cm.apply(lambda r:"✅ Complete" if r["Pending"]<=0 else(f"⚠️ Overdue!" if str(r.get("Delivery_By",""))<today_str and r["Pending"]>0 else f"⏳ {int(r['Pending'])} pending"),axis=1)
        cm["Labour_Value"]=(safe_numeric(cm["Total_Qty"])*safe_numeric(cm.get("Rate_Per_Pc",0))).round(2)
        dc=[c for c in["Challan_No","Style","Party","Total_Qty","Received_Qty","Pending","Status","Rate_Per_Pc","Labour_Value","Deposit_Rs","Date","Delivery_By"] if c in cm.columns]
        st.dataframe(cm[dc],use_container_width=True,hide_index=True)
        sx1,sx2,sx3,sx4=st.columns(4)
        sx1.metric("Total Challans",len(cm)); sx2.metric("Completed",len(cm[cm["Pending"]<=0]))
        sx3.metric("In Progress",len(cm[cm["Pending"]>0])); sx4.metric("Total Labour Value",f"₹{safe_numeric(cm['Labour_Value']).sum():,.0f}")

    st.markdown('<div class="sec-hdr">📐 Size-wise Breakdown (MI Color/Size Chart)</div>', unsafe_allow_html=True)
    cs3=st.session_state.challan_sizes.copy()
    if not cs3.empty:
        for sc in SIZE_COLS:
            if sc in cs3.columns: cs3[sc]=safe_numeric(cs3[sc]).astype(int)
        cs3["Total"]=sum(safe_numeric(cs3.get(sc,0)) for sc in SIZE_COLS)
        st.dataframe(cs3,use_container_width=True,hide_index=True)
        sz_tots={sc:int(safe_numeric(cs3.get(sc,0)).sum()) for sc in SIZE_COLS}
        pills=" ".join([f'<span class="size-pill sp-{s.lower().replace("xl","xl")}">{s}: {v}</span>' for s,v in sz_tots.items()])
        st.markdown(f"**All-challan totals:** {pills} &nbsp; <b>Grand: {sum(sz_tots.values())}</b>",unsafe_allow_html=True)

    # Update received qty
    st.markdown('<div class="sec-hdr">📥 Update Received Quantity</div>', unsafe_allow_html=True)
    if not cm.empty:
        upd_ch=st.selectbox("Select Challan to update",cm["Challan_No"].tolist(),key="upd_ch")
        curr_rec_val=int(safe_numeric(cm[cm["Challan_No"]==upd_ch]["Received_Qty"]).iloc[0]) if not cm[cm["Challan_No"]==upd_ch].empty else 0
        new_rec=st.number_input("New Received Qty",min_value=0,step=1,value=curr_rec_val,key="new_rec")
        if st.button("Update Received Qty",key="do_upd_rec"):
            idx=st.session_state.challan_master[st.session_state.challan_master["Challan_No"]==upd_ch].index
            if len(idx)>0: st.session_state.challan_master.loc[idx[0],"Received_Qty"]=new_rec; st.success(f"✅ Updated {upd_ch} received qty to {new_rec}"); st.rerun()

    st.markdown('<div class="sec-hdr">🔍 Challan Detail Drill-down</div>', unsafe_allow_html=True)
    if not cm.empty:
        sel_chdrl=st.selectbox("Select Challan",cm["Challan_No"].tolist(),key="ch_drl")
        ch_r=cm[cm["Challan_No"]==sel_chdrl]; sz_r=cs3[cs3["Challan_No"]==sel_chdrl] if not cs3.empty else pd.DataFrame()
        if not ch_r.empty:
            r=ch_r.iloc[0]
            d1,d2,d3,d4=st.columns(4)
            d1.metric("Total Qty",int(safe_numeric(pd.Series([r["Total_Qty"]])).iloc[0]))
            d2.metric("Received",int(safe_numeric(pd.Series([r.get("Received_Qty",0)])).iloc[0]))
            d3.metric("Pending",int(safe_numeric(pd.Series([r.get("Pending",0)])).iloc[0]))
            d4.metric("Rate/Pc",f"₹{safe_numeric(pd.Series([r.get('Rate_Per_Pc',0)])).iloc[0]:.0f}")
            if not sz_r.empty:
                sz_rr=sz_r.iloc[0]
                sz_html2=" ".join([f'<span class="size-pill sp-{s.lower()}">{s}: {int(safe_numeric(pd.Series([sz_rr.get(s,0)])).iloc[0])}</span>' for s in SIZE_COLS])
                st.markdown(f"**Sizes:** {sz_html2}",unsafe_allow_html=True)
            pl2=st.session_state.production_log
            if not pl2.empty:
                ch_pl=pl2[pl2["Challan_No"]==sel_chdrl].copy()
                if not ch_pl.empty:
                    for c in["Total_Pieces","Piece_Value_Rs","Efficiency_%"]: ch_pl[c]=safe_numeric(ch_pl[c])
                    op_s=ch_pl.groupby("Operation").agg(Pieces=("Total_Pieces","sum"),Avg_Eff=("Efficiency_%","mean"),Value=("Piece_Value_Rs","sum")).round(2).reset_index()
                    st.markdown("**Production by Operation:**"); st.dataframe(op_s,use_container_width=True,hide_index=True)

    ex1,ex2=st.columns(2)
    with ex1: st.download_button("📥 Challans Excel",to_excel(st.session_state.challan_master),"challans.xlsx")
    with ex2: st.download_button("📥 Size Chart CSV",to_csv(st.session_state.challan_sizes),"challan_sizes.csv")

# ══════════════════════════ TAB 4 — STYLE COSTING (P&L) ══════════════════════════
with tab_style:
    st.markdown('<div class="sec-hdr">💎 Style-wise Costing — Profit & Loss</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Filter by month to see which challans ran, what cost was incurred, and profit/loss per piece vs party rate.</div>',unsafe_allow_html=True)

    flt1,flt2,flt3=st.columns(3)
    with flt1:
        mo_avail=["All"]
        if not st.session_state.challan_master.empty:
            try:
                m_dates=pd.to_datetime(st.session_state.challan_master["Date"],errors="coerce").dropna()
                mo_avail+=sorted(m_dates.dt.strftime("%Y-%m").unique().tolist(),reverse=True)
            except: pass
        sel_month=st.selectbox("📅 Month",mo_avail,key="sc_month")
    with flt2:
        all_st_sc=st.session_state.style_master["Style"].unique().tolist() if not st.session_state.style_master.empty else []
        sel_st_sc=st.selectbox("👗 Style",["All"]+all_st_sc,key="sc_style")
    with flt3:
        all_p=["All"]
        if not st.session_state.challan_master.empty and "Party" in st.session_state.challan_master.columns:
            all_p+=st.session_state.challan_master["Party"].dropna().unique().tolist()
        sel_party=st.selectbox("🏭 Party",all_p,key="sc_party")

    cm_sc=st.session_state.challan_master.copy()
    if not cm_sc.empty:
        cm_sc["Date_dt"]=pd.to_datetime(cm_sc["Date"],errors="coerce")
        if sel_month!="All": cm_sc=cm_sc[cm_sc["Date_dt"].dt.strftime("%Y-%m")==sel_month]
        if sel_st_sc!="All": cm_sc=cm_sc[cm_sc["Style"]==sel_st_sc]
        if sel_party!="All" and "Party" in cm_sc.columns: cm_sc=cm_sc[cm_sc["Party"]==sel_party]

    if cm_sc.empty:
        st.info("No challans match filters.")
    else:
        sm2=st.session_state.style_master.copy()
        slr=sm2.groupby("Style")["Rate_Rs"].sum().reset_index(); slr.columns=["Style","Labour_Rate_Per_Pc"]
        cm_sc=cm_sc.merge(slr,on="Style",how="left").fillna({"Labour_Rate_Per_Pc":0})
        for col in["Total_Qty","Labour_Rate_Per_Pc","Rate_Per_Pc","Deposit_Rs","Received_Qty"]: cm_sc[col]=safe_numeric(cm_sc.get(col,0))
        cm_sc["Total_Labour_Cost"]=(cm_sc["Total_Qty"]*cm_sc["Labour_Rate_Per_Pc"]).round(2)
        cm_sc["Party_Rate_Value"]=(cm_sc["Total_Qty"]*cm_sc["Rate_Per_Pc"]).round(2)
        cm_sc["Total_Cost"]=(cm_sc["Total_Labour_Cost"]+cm_sc["Deposit_Rs"]).round(2)
        cm_sc["Profit_Loss"]=(cm_sc["Party_Rate_Value"]-cm_sc["Total_Cost"]).round(2)
        cm_sc["Profit_Per_Pc"]=(cm_sc["Profit_Loss"]/cm_sc["Total_Qty"].replace(0,1)).round(2)
        cm_sc["Margin_%"]=(cm_sc["Profit_Loss"]/cm_sc["Party_Rate_Value"].replace(0,1)*100).round(1)
        cm_sc["Result"]=cm_sc["Profit_Loss"].apply(lambda x:"✅ Profit" if x>0 else("🔴 Loss" if x<0 else"↔ Break-even"))

        tv=cm_sc["Party_Rate_Value"].sum(); tc=cm_sc["Total_Cost"].sum(); tpl=cm_sc["Profit_Loss"].sum()
        mx1,mx2,mx3,mx4=st.columns(4)
        mx1.metric("Total Pieces",f"{int(cm_sc['Total_Qty'].sum()):,}")
        mx2.metric("Party Rate Value",f"₹{tv:,.0f}")
        mx3.metric("Total Cost",f"₹{tc:,.0f}")
        mx4.metric("Net P&L",f"₹{tpl:,.0f}",delta=f"+{tpl:.0f}" if tpl>=0 else f"{tpl:.0f}")

        dc2=[c for c in["Challan_No","Style","Party","Total_Qty","Received_Qty","Labour_Rate_Per_Pc","Total_Labour_Cost","Deposit_Rs","Rate_Per_Pc","Party_Rate_Value","Total_Cost","Profit_Loss","Profit_Per_Pc","Margin_%","Result"] if c in cm_sc.columns]
        st.dataframe(cm_sc[dc2],use_container_width=True,hide_index=True)

        st.markdown('<div class="sec-hdr">Style Roll-up</div>', unsafe_allow_html=True)
        sru=cm_sc.groupby("Style").agg(Challans=("Challan_No","nunique"),Total_Qty=("Total_Qty","sum"),
            Party_Value=("Party_Rate_Value","sum"),Total_Cost=("Total_Cost","sum"),PL=("Profit_Loss","sum")).reset_index()
        sru["Margin_%"]=(sru["PL"]/sru["Party_Value"].replace(0,1)*100).round(1)
        sru["Net"]=sru["PL"].apply(lambda x:"✅ Profit" if x>0 else"🔴 Loss")
        st.dataframe(sru,use_container_width=True,hide_index=True)

        if sel_st_sc!="All":
            st.markdown('<div class="sec-hdr">Operations Breakdown</div>', unsafe_allow_html=True)
            od=sm2[sm2["Style"]==sel_st_sc].copy()
            od["Daily_Value"]=safe_numeric(od["Target"])*safe_numeric(od["Rate_Rs"])
            od["Cost_Share_%"]=(safe_numeric(od["Rate_Rs"])/safe_numeric(od["Rate_Rs"]).sum()*100).round(1)
            st.dataframe(od,use_container_width=True,hide_index=True)

        ex1,ex2=st.columns(2)
        with ex1: st.download_button("📥 Style Costing Excel",to_excel(cm_sc[dc2]),f"style_pl_{sel_month}.xlsx")
        with ex2: st.download_button("📥 Style Costing CSV",  to_csv(cm_sc[dc2]),  f"style_pl_{sel_month}.csv")

# ══════════════════════════ TAB 5 — EFFICIENCY ══════════════════════════
with tab_eff:
    st.markdown('<div class="sec-hdr">📊 Efficiency & Deep Analysis</div>', unsafe_allow_html=True)
    pl_eff=st.session_state.production_log
    if pl_eff.empty: st.info("No production data yet.")
    else:
        df=pl_eff.copy()
        for c in["Total_Pieces","Target","Rate_Rs","Efficiency_%","Piece_Value_Rs"]:
            if c in df.columns: df[c]=safe_numeric(df[c])
        df["Date_dt"]=pd.to_datetime(df["Date"],errors="coerce")
        ef1,ef2=st.columns(2)
        with ef1: dr=st.date_input("Date Range",value=[date.today()-timedelta(days=7),date.today()],key="eff_dr")
        with ef2: sf=st.multiselect("Filter Style",df["Style"].unique().tolist(),default=df["Style"].unique().tolist(),key="eff_sf")
        if len(dr)==2: mask=(df["Date_dt"]>=pd.Timestamp(dr[0]))&(df["Date_dt"]<=pd.Timestamp(dr[1]))&df["Style"].isin(sf); df_f=df[mask].copy()
        else: df_f=df[df["Style"].isin(sf)].copy()
        if df_f.empty: st.warning("No data for filters.")
        else:
            ec1,ec2,ec3=st.columns(3)
            ec1.metric("Avg Efficiency",f"{df_f['Efficiency_%'].mean():.1f}%")
            ec2.metric("Total Piece Value",f"₹{df_f['Piece_Value_Rs'].sum():,.0f}")
            ec3.metric("Total Pieces",f"{int(df_f['Total_Pieces'].sum()):,}")
            st.markdown('<div class="sec-hdr">Karigar-wise</div>', unsafe_allow_html=True)
            ke=df_f.groupby("Karigar_Name").agg(Avg_Eff=("Efficiency_%","mean"),Pieces=("Total_Pieces","sum"),Value=("Piece_Value_Rs","sum"),Ops=("Operation","count")).round(2).reset_index()
            ke["Grade"]=ke["Avg_Eff"].apply(lambda x:"A – Excellent" if x>=100 else("B – Good" if x>=85 else("C – Average" if x>=70 else"D – Below Target")))
            st.dataframe(ke,use_container_width=True,hide_index=True)
            st.markdown('<div class="sec-hdr">Operation-wise</div>', unsafe_allow_html=True)
            oe=df_f.groupby("Operation").agg(Avg_Eff=("Efficiency_%","mean"),Pieces=("Total_Pieces","sum"),Value=("Piece_Value_Rs","sum")).round(2).reset_index().sort_values("Avg_Eff")
            st.dataframe(oe,use_container_width=True,hide_index=True)
            bn=oe[oe["Avg_Eff"]<80]
            if not bn.empty: st.markdown(f'<div class="warn-box">⚠️ <b>Bottleneck Operations (below 80%):</b> {", ".join(bn["Operation"].tolist())}</div>',unsafe_allow_html=True)
            st.markdown('<div class="sec-hdr">Challan-wise</div>', unsafe_allow_html=True)
            ce=df_f.groupby(["Challan_No","Style"]).agg(Pieces=("Total_Pieces","sum"),Value=("Piece_Value_Rs","sum"),Avg_Eff=("Efficiency_%","mean")).round(2).reset_index()
            st.dataframe(ce,use_container_width=True,hide_index=True)
            ex1,ex2=st.columns(2)
            with ex1: st.download_button("📥 Efficiency Excel",to_excel(ke),"efficiency.xlsx")
            with ex2: st.download_button("📥 Efficiency CSV",  to_csv(ke),  "efficiency.csv")

# ══════════════════════════ TAB 6 — PAYROLL ══════════════════════════
with tab_pay:
    st.markdown('<div class="sec-hdr">💰 Payroll Calculator</div>', unsafe_allow_html=True)
    p1,p2=st.columns(2)
    with p1: pay_s=st.date_input("Pay Period Start",value=date.today()-timedelta(days=6),key="pay_s")
    with p2: pay_e=st.date_input("Pay Period End",  value=date.today(),key="pay_e")
    if st.button("📊 Calculate Payroll",use_container_width=True):
        att_p=st.session_state.karigar_attendance
        if att_p.empty: st.warning("No attendance data.")
        else:
            ap=att_p.copy(); ap["Date_dt"]=pd.to_datetime(ap["Date"]); ap=ap[(ap["Date_dt"]>=pd.Timestamp(pay_s))&(ap["Date_dt"]<=pd.Timestamp(pay_e))]
            if ap.empty: st.warning("No records in pay period.")
            else:
                for c in["Payable_Hrs","Normal_Pay","OT_Hours","OT_Pay","Total_Pay"]:
                    if c in ap.columns: ap[c]=safe_numeric(ap[c])
                pr=ap.groupby("E_Code").agg(Name=("Name","first"),Days=("Date","nunique"),Hrs=("Payable_Hrs","sum"),
                    Normal=("Normal_Pay","sum"),OT_Hrs=("OT_Hours","sum"),OT_Pay=("OT_Pay","sum"),Total=("Total_Pay","sum")).round(2).reset_index()
                st.dataframe(pr,use_container_width=True,hide_index=True)
                st.metric("Total Payroll",f"₹{pr['Total'].sum():,.2f}")
                px1,px2=st.columns(2)
                with px1: st.download_button("📥 Payroll Excel",to_excel(pr),f"payroll_{pay_s}_{pay_e}.xlsx",key="py_x")
                with px2: st.download_button("📥 Payroll CSV",  to_csv(pr),  f"payroll_{pay_s}_{pay_e}.csv", key="py_c")

# ══════════════════════════ TAB 7 — ATTENDANCE ══════════════════════════
with tab_att:
    st.markdown('<div class="sec-hdr">🕐 Karigar Salary & Attendance</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box"><b>Shift:</b> 9:00–18:00 | <b>Lunch:</b> 13:00–14:00 (unpaid) | <b>OT:</b> after 18:00</div>',unsafe_allow_html=True)
    ot_m=st.selectbox("OT Multiplier",[1.0,1.5,2.0],index=1,key="ot_m")
    import_section("karigar_attendance",["Date","E_Code","In_Punch","Out_Punch"],"karigar_attendance","Karigar Attendance")
    att_df=st.session_state.karigar_attendance
    if not att_df.empty and "Total_Pay" not in att_df.columns:
        emp4=st.session_state.employee_master; rows4=[]
        for _,row in att_df.iterrows():
            er=emp4[emp4["E_Code"]==row["E_Code"]]
            if not er.empty:
                dr=float(er["Daily_Rate_Rs"].values[0]); nm=er["Name"].values[0]
                ph,ld,py,hr,np_,oth,otp,tp=calc_salary(str(row["In_Punch"]),str(row["Out_Punch"]),dr,ot_m)
                rows4.append({**row.to_dict(),"Name":nm,"Total_Presence_Hrs":ph,"Lunch_Deduction_Hrs":ld,"Payable_Hrs":py,"Hourly_Rate_Rs":hr,"Normal_Pay":np_,"OT_Hours":oth,"OT_Pay":otp,"Total_Pay":tp})
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
                ph,ld,py,hr,np_,oth,otp,tp=calc_salary(ip,op2,dr2,ot_m)
                na={"Date":str(ad),"E_Code":er2["E_Code"],"Name":er2["Name"],"In_Punch":ip,"Out_Punch":op2,
                    "Total_Presence_Hrs":ph,"Lunch_Deduction_Hrs":ld,"Payable_Hrs":py,"Hourly_Rate_Rs":hr,
                    "Normal_Pay":np_,"OT_Hours":oth,"OT_Pay":otp,"Total_Pay":tp}
                st.session_state.karigar_attendance=pd.concat([st.session_state.karigar_attendance,pd.DataFrame([na])],ignore_index=True)
                st.success(f"✅ {er2['Name']} | {py}h | ₹{tp}")
    if not st.session_state.karigar_attendance.empty:
        af=st.date_input("Filter Date",value=date.today(),key="att_f")
        av=st.session_state.karigar_attendance[st.session_state.karigar_attendance["Date"]==str(af)]
        if not av.empty: st.dataframe(av,use_container_width=True,hide_index=True); st.download_button("📥 Download",to_excel(av),f"att_{af}.xlsx")

# ══════════════════════════ TAB 8 — OPERATING STAFF ══════════════════════════
with tab_op:
    st.markdown('<div class="sec-hdr">🏢 Operating Staff</div>', unsafe_allow_html=True)
    import_section("operating_attendance",["Date","E_Code","In_Punch","Out_Punch"],"operating_attendance","Operating Staff Attendance")
    eo2=st.session_state.employee_master[st.session_state.employee_master["Type"]=="Operating"]
    oo2={f"{r['E_Code']} – {r['Name']}":r for _,r in eo2.iterrows()}
    with st.expander("✏️ Manual Entry",expanded=True):
        with st.form("op_form",clear_on_submit=True):
            oa1,oa2,oa3=st.columns(3)
            with oa1: od=st.date_input("Date",value=date.today(),key="od2"); oe=st.selectbox("Employee",list(oo2.keys()),key="oe2")
            with oa2: oin=st.text_input("In",value="09:00",key="oin2"); oout=st.text_input("Out",value="18:00",key="oout2")
            with oa3:
                er3=oo2[oe]; st.info(f"Hourly: ₹{er3['Hourly_Rate_Rs']}")
            if st.form_submit_button("Save"):
                try:
                    fmt3="%H:%M"; hrs3=round(int((datetime.strptime(oout.strip(),fmt3)-datetime.strptime(oin.strip(),fmt3)).total_seconds())/3600,2)
                except: hrs3=0
                hr3=float(er3["Hourly_Rate_Rs"]); tp3=round(hrs3*hr3,2)
                st.session_state.operating_attendance=pd.concat([st.session_state.operating_attendance,pd.DataFrame([{
                    "Date":str(od),"E_Code":er3["E_Code"],"Name":er3["Name"],"In_Punch":oin,"Out_Punch":oout,"Total_Hours":hrs3,"Hourly_Rate_Rs":hr3,"Total_Pay":tp3
                }])],ignore_index=True)
                st.success(f"✅ {er3['Name']} | {hrs3}h | ₹{tp3}")

# ══════════════════════════ TAB 9 — PERFORMANCE ══════════════════════════
with tab_perf:
    st.markdown('<div class="sec-hdr">🌟 Employee Performance Dashboard</div>', unsafe_allow_html=True)
    pl_p=st.session_state.production_log; att_p2=st.session_state.karigar_attendance
    if pl_p.empty or att_p2.empty: st.info("Need production + attendance data.")
    else:
        pp1,pp2=st.columns(2)
        with pp1: ps=st.date_input("From",value=date.today()-timedelta(days=29),key="ps")
        with pp2: pe=st.date_input("To",  value=date.today(),key="pe2")
        pl3=pl_p.copy()
        for c in["Total_Pieces","Piece_Value_Rs","Efficiency_%"]:
            if c in pl3.columns: pl3[c]=safe_numeric(pl3[c])
        pl3["Date_dt"]=pd.to_datetime(pl3["Date"]); pl3=pl3[(pl3["Date_dt"]>=pd.Timestamp(ps))&(pl3["Date_dt"]<=pd.Timestamp(pe))]
        psm=pl3.groupby("Karigar_ID").agg(Piece_Value=("Piece_Value_Rs","sum"),Total_Pieces=("Total_Pieces","sum"),Avg_Eff=("Efficiency_%","mean")).reset_index()
        att3=att_p2.copy(); att3["Date_dt"]=pd.to_datetime(att3["Date"]); att3=att3[(att3["Date_dt"]>=pd.Timestamp(ps))&(att3["Date_dt"]<=pd.Timestamp(pe))]
        if "Total_Pay" in att3.columns:
            for c in["Total_Pay","Payable_Hrs"]: att3[c]=safe_numeric(att3[c])
            ss=att3.groupby("E_Code").agg(Name=("Name","first"),Days=("Date","nunique"),Hrs=("Payable_Hrs","sum"),Salary=("Total_Pay","sum")).round(2).reset_index()
            ss["E_Code"]=ss["E_Code"].astype(str); psm2=psm.rename(columns={"Karigar_ID":"E_Code"}).copy(); psm2["E_Code"]=psm2["E_Code"].astype(str)
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
        else: st.warning("Attendance records lack salary data.")

# ══════════════════════════ TAB 10 — MASTER DATA ══════════════════════════
with tab_master:
    st.markdown('<div class="sec-hdr">⚙️ Master Data Management</div>', unsafe_allow_html=True)
    m1t,m2t,m3t=st.tabs(["👗 Style-Operation Master","👷 Karigar Master","🪪 Employee Master"])
    with m1t:
        import_section("style_master",["Style","Operation","Target","Rate_Rs"],"style_master","Style Master")
        with st.expander("➕ Add Operation",expanded=False):
            with st.form("sf",clear_on_submit=True):
                sc1,sc2=st.columns(2)
                with sc1: ns2=st.text_input("Style Code"); no2=st.text_input("Operation Name")
                with sc2: nt2=st.number_input("Target",min_value=1,step=1,value=80); nr3=st.number_input("Rate/pc",min_value=0.0,step=0.25,format="%.2f",value=3.0)
                if st.form_submit_button("Add"):
                    st.session_state.style_master=pd.concat([st.session_state.style_master,pd.DataFrame([{"Style":ns2,"Operation":no2,"Target":nt2,"Rate_Rs":nr3}])],ignore_index=True); st.success("Added!")
        st.dataframe(st.session_state.style_master,use_container_width=True,hide_index=True)
        st.download_button("📥 Export",to_excel(st.session_state.style_master),"style_master.xlsx",key="dl_sm")
    with m2t:
        import_section("karigar_master",["Karigar_ID","Name","Skill","Daily_Rate_Rs"],"karigar_master","Karigar Master")
        with st.expander("➕ Add Karigar",expanded=False):
            with st.form("kf",clear_on_submit=True):
                kc1,kc2=st.columns(2)
                with kc1: k_id=st.text_input("Karigar ID (e.g. K006)"); k_nm=st.text_input("Full Name")
                with kc2: k_sk=st.selectbox("Skill",["Stitching","Cutting","Finishing","Hemming","Checking","Dupatta"]); k_rt=st.number_input("Daily Rate",min_value=100,step=10,value=420)
                if st.form_submit_button("Add"):
                    st.session_state.karigar_master=pd.concat([st.session_state.karigar_master,pd.DataFrame([{"Karigar_ID":k_id,"Name":k_nm,"Skill":k_sk,"Daily_Rate_Rs":k_rt}])],ignore_index=True)
                    ec5=f"E{len(st.session_state.employee_master)+1:03d}"
                    st.session_state.employee_master=pd.concat([st.session_state.employee_master,pd.DataFrame([{"E_Code":ec5,"Name":k_nm,"Type":"Karigar","Daily_Rate_Rs":k_rt,"Hourly_Rate_Rs":round(k_rt/8,2)}])],ignore_index=True)
                    st.success(f"Added {k_nm}! (Employee: {ec5})")
        st.dataframe(st.session_state.karigar_master,use_container_width=True,hide_index=True)
        st.download_button("📥 Export",to_excel(st.session_state.karigar_master),"karigar_master.xlsx",key="dl_km")
    with m3t:
        import_section("employee_master",["E_Code","Name","Type","Daily_Rate_Rs","Hourly_Rate_Rs"],"employee_master","Employee Master")
        with st.expander("➕ Add Employee",expanded=False):
            with st.form("ef",clear_on_submit=True):
                ec1,ec2=st.columns(2)
                with ec1: em_c=st.text_input("E-Code"); em_n=st.text_input("Full Name"); em_t=st.selectbox("Type",["Karigar","Operating"])
                with ec2: em_d=st.number_input("Daily Rate",min_value=100,step=10,value=400); em_h=st.number_input("Hourly Rate",value=50.0,step=0.5,format="%.2f")
                if st.form_submit_button("Add"):
                    st.session_state.employee_master=pd.concat([st.session_state.employee_master,pd.DataFrame([{"E_Code":em_c,"Name":em_n,"Type":em_t,"Daily_Rate_Rs":em_d,"Hourly_Rate_Rs":em_h}])],ignore_index=True); st.success("Added!")
        st.dataframe(st.session_state.employee_master,use_container_width=True,hide_index=True)

st.markdown("---")
st.markdown("🧵 <b>Stitching Costing Interface v3.0</b> — Yash Gallery Pvt Ltd | Enhanced Karigar Management System", unsafe_allow_html=True)
