"""
Enhanced Stitching Costing Interface - Streamlit App
Textile Garments Company - Karigar Time Tracking & Costing System
IMPROVEMENTS:
- Normal color scheme (no pink/gradients)
- New Style Costing tab with full cost breakdown
- Enhanced Challan Management with received quantities and deposits
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import io
import hashlib

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Stitching Costing Interface",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# Custom CSS - NORMAL COLORS (No Pink/Gradient)
# ─────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: #f0f4f8;
    padding: 20px;
    border-radius: 8px;
    color: #1a3a52;
    text-align: center;
    margin: 5px 0;
    border-left: 4px solid #2c5aa0;
}
.metric-card .metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #2c5aa0;
}
.metric-card .metric-label {
    font-size: 0.85rem;
    opacity: 0.8;
    font-weight: 500;
}
.metric-card .metric-sub {
    font-size: 0.75rem;
    opacity: 0.6;
    margin-top: 4px;
}
.section-header {
    background: #2c5aa0;
    color: white;
    padding: 10px 16px;
    border-radius: 6px;
    font-weight: 600;
    margin: 10px 0;
}
.info-box {
    background: #e8f1f8;
    border-left: 4px solid #2c5aa0;
    padding: 12px 15px;
    border-radius: 4px;
    margin: 8px 0;
    font-size: 0.9rem;
    color: #1a3a52;
}
.lock-box {
    background: #fff3e0;
    border-left: 4px solid #f57c00;
    padding: 10px 15px;
    border-radius: 4px;
    margin: 8px 0;
    font-size: 0.9rem;
    color: #e65100;
}
.success-box {
    background: #e8f5e9;
    border-left: 4px solid #2e7d32;
    padding: 10px 15px;
    border-radius: 4px;
    margin: 8px 0;
    font-size: 0.9rem;
    color: #1b5e20;
}
.warning-box {
    background: #fce4ec;
    border-left: 4px solid #c2185b;
    padding: 10px 15px;
    border-radius: 4px;
    margin: 8px 0;
    font-size: 0.9rem;
    color: #880e4f;
}
.readonly-field {
    background: #f5f5f5;
    border: 1px solid #bdbdbd;
    padding: 10px 12px;
    border-radius: 4px;
    font-weight: bold;
    color: #424242;
}
table {
    border-collapse: collapse;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────
def read_upload(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file)
    else:
        st.error("Unsupported file type. Please upload .csv or .xlsx")
        return None

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    try:
        import openpyxl
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Data")
        return buf.getvalue()
    except ImportError:
        return df.to_csv(index=False).encode("utf-8")

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def safe_numeric(series):
    """Convert series to numeric safely, coercing errors."""
    return pd.to_numeric(series, errors='coerce').fillna(0)

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# ─────────────────────────────────────────────
# Password / Auth
# ─────────────────────────────────────────────
DEFAULT_ADMIN_HASH = hash_password("admin123")

def init_auth():
    if "admin_pw_hash" not in st.session_state:
        st.session_state.admin_pw_hash = DEFAULT_ADMIN_HASH
    if "sheet_unlocked" not in st.session_state:
        st.session_state.sheet_unlocked = False

def sheet_lock_widget(section_key="daily"):
    """Shows a lock/unlock widget. Returns True if unlocked."""
    if st.session_state.sheet_unlocked:
        col1, col2 = st.columns([4,1])
        with col2:
            if st.button("🔒 Lock", key=f"lock_{section_key}", use_container_width=True):
                st.session_state.sheet_unlocked = False
                st.rerun()
        st.markdown('<div class="success-box">✅ <b>UNLOCKED</b> — Admin mode active. Target & Rate fields are editable.</div>', unsafe_allow_html=True)
        return True
    else:
        st.markdown('<div class="lock-box">🔐 <b>LOCKED</b> — Target and Rate are read-only. Enter password to unlock.</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([2,2,1])
        with col1:
            pw_input = st.text_input("Admin Password", type="password", key=f"pw_{section_key}", label_visibility="collapsed", placeholder="Enter admin password")
        with col2:
            if st.button("🔓 Unlock", key=f"unlock_{section_key}"):
                if hash_password(pw_input) == st.session_state.admin_pw_hash:
                    st.session_state.sheet_unlocked = True
                    st.rerun()
                else:
                    st.error("❌ Incorrect password")
        return False

# ─────────────────────────────────────────────
# Reusable Import Widget
# ─────────────────────────────────────────────
def import_section(key, required_cols, session_key, template_df, label):
    with st.expander(f"📥 Import {label} from Excel / CSV", expanded=False):
        st.markdown(
            f'<div class="info-box">Step 1: Download template → Fill your data → Upload back. '
            f'<b>Required columns:</b> {", ".join(required_cols)}</div>',
            unsafe_allow_html=True
        )
        dl1, dl2 = st.columns(2)
        with dl1:
            try:
                import openpyxl
                st.download_button("📊 Download Excel Template",
                    data=df_to_excel_bytes(template_df),
                    file_name=f"{key}_template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_xlsx_{key}")
            except Exception:
                st.caption("Excel template unavailable — use CSV")
        with dl2:
            st.download_button("📄 Download CSV Template",
                data=df_to_csv_bytes(template_df),
                file_name=f"{key}_template.csv", mime="text/csv",
                key=f"dl_csv_{key}")
        uploaded = st.file_uploader("📂 Upload your filled file",
            type=["csv","xlsx","xls"], key=f"uploader_{key}")
        mode = st.radio("Import mode",
            ["➕ Append to existing data","🔄 Replace all existing data"],
            key=f"mode_{key}")
        if uploaded is not None:
            df_new = read_upload(uploaded)
            if df_new is not None:
                missing = [c for c in required_cols if c not in df_new.columns]
                if missing:
                    st.error(f"❌ Missing columns: {missing}"); return
                st.markdown("**Preview (first 5 rows):**")
                st.dataframe(df_new.head(), use_container_width=True, hide_index=True)
                st.info(f"✅ {len(df_new)} rows detected")
                if st.button(f"✅ Confirm Import", key=f"confirm_{key}", use_container_width=True):
                    if "Replace" in mode:
                        st.session_state[session_key] = df_new.reset_index(drop=True)
                        st.success(f"✅ Replaced! {len(df_new)} rows loaded.")
                    else:
                        st.session_state[session_key] = pd.concat(
                            [st.session_state[session_key], df_new], ignore_index=True)
                        st.success(f"✅ Appended! {len(df_new)} new rows added.")
                    st.rerun()

# ─────────────────────────────────────────────
# Templates
# ─────────────────────────────────────────────
TEMPLATES = {
    "style_master": pd.DataFrame([
        {"Style":"1065YKBLUE","Operation":"Cutting","Target":120,"Rate_Rs":2.50},
        {"Style":"1065YKBLUE","Operation":"Stitching Front","Target":80,"Rate_Rs":4.00},
    ]),
    "karigar_master": pd.DataFrame([
        {"Karigar_ID":"K001","Name":"Ramesh Kumar","Skill":"Stitching","Daily_Rate_Rs":450},
        {"Karigar_ID":"K002","Name":"Suresh Singh","Skill":"Cutting","Daily_Rate_Rs":420},
    ]),
    "challan_master": pd.DataFrame([
        {"Challan_No":"CH-001","Style":"1065YKBLUE","SKU":"YK-BLU-M","Qty":200,"Received_Qty":0,"Deposit_Rs":0.0,"Date":"2025-01-15"},
        {"Challan_No":"CH-002","Style":"1065YKBLUE","SKU":"YK-BLU-L","Qty":150,"Received_Qty":0,"Deposit_Rs":0.0,"Date":"2025-01-16"},
    ]),
    "production_log": pd.DataFrame([
        {"Date":"2025-01-15","Karigar_ID":"K001","Karigar_Name":"Ramesh Kumar",
         "Challan_No":"CH-001","Style":"1065YKBLUE","Operation":"Cutting",
         "Hour_09_10":10,"Hour_10_11":11,"Hour_11_12":9,"Hour_12_13":10,
         "Hour_14_15":11,"Hour_15_16":10,"Hour_16_17":9,"Hour_17_18":8,"Hour_18_19":7,
         "Target":120,"Rate_Rs":2.50},
    ]),
    "employee_master": pd.DataFrame([
        {"E_Code":"E001","Name":"Ramesh Kumar","Type":"Karigar","Daily_Rate_Rs":450,"Hourly_Rate_Rs":56.25},
        {"E_Code":"E101","Name":"Amit Sharma","Type":"Operating","Daily_Rate_Rs":600,"Hourly_Rate_Rs":75.00},
    ]),
    "karigar_attendance": pd.DataFrame([
        {"Date":"2025-01-15","E_Code":"E001","In_Punch":"09:00","Out_Punch":"18:30"},
        {"Date":"2025-01-15","E_Code":"E002","In_Punch":"09:00","Out_Punch":"15:00"},
    ]),
    "operating_attendance": pd.DataFrame([
        {"Date":"2025-01-15","E_Code":"E101","In_Punch":"09:00","Out_Punch":"18:00"},
    ]),
}

HOUR_COLS = [
    "Hour_09_10","Hour_10_11","Hour_11_12","Hour_12_13",
    "Hour_14_15","Hour_15_16","Hour_16_17","Hour_17_18","Hour_18_19"
]
HOUR_LABELS = [
    "09-10","10-11","11-12","12-13",
    "14-15","15-16","16-17","17-18","18-19"
]

# ─────────────────────────────────────────────
# Session State Init
# ─────────────────────────────────────────────
def init_state():
    init_auth()
    if "style_master" not in st.session_state:
        st.session_state.style_master = pd.DataFrame([
            {"Style":"1065YKBLUE","Operation":"Cutting","Target":120,"Rate_Rs":2.50},
            {"Style":"1065YKBLUE","Operation":"Stitching Front","Target":80,"Rate_Rs":4.00},
            {"Style":"1065YKBLUE","Operation":"Stitching Back","Target":80,"Rate_Rs":4.00},
            {"Style":"1065YKBLUE","Operation":"Collar Attach","Target":60,"Rate_Rs":5.50},
            {"Style":"1065YKBLUE","Operation":"Sleeve Attach","Target":60,"Rate_Rs":5.50},
            {"Style":"1065YKBLUE","Operation":"Side Seam","Target":90,"Rate_Rs":3.50},
            {"Style":"1065YKBLUE","Operation":"Hemming","Target":100,"Rate_Rs":3.00},
            {"Style":"1065YKBLUE","Operation":"Button Hole","Target":110,"Rate_Rs":2.00},
            {"Style":"1065YKBLUE","Operation":"Button Attach","Target":110,"Rate_Rs":2.00},
            {"Style":"1065YKBLUE","Operation":"Finishing","Target":70,"Rate_Rs":4.50},
        ])
    if "karigar_master" not in st.session_state:
        st.session_state.karigar_master = pd.DataFrame([
            {"Karigar_ID":"K001","Name":"Ramesh Kumar","Skill":"Stitching","Daily_Rate_Rs":450},
            {"Karigar_ID":"K002","Name":"Suresh Singh","Skill":"Cutting","Daily_Rate_Rs":420},
            {"Karigar_ID":"K003","Name":"Priya Devi","Skill":"Finishing","Daily_Rate_Rs":400},
            {"Karigar_ID":"K004","Name":"Mohan Lal","Skill":"Stitching","Daily_Rate_Rs":460},
            {"Karigar_ID":"K005","Name":"Sunita Sharma","Skill":"Hemming","Daily_Rate_Rs":410},
        ])
    if "challan_master" not in st.session_state:
        st.session_state.challan_master = pd.DataFrame([
            {"Challan_No":"CH-001","Style":"1065YKBLUE","SKU":"YK-BLU-M","Qty":200,"Received_Qty":0,"Deposit_Rs":0.0,"Date":"2025-01-15"},
            {"Challan_No":"CH-002","Style":"1065YKBLUE","SKU":"YK-BLU-L","Qty":150,"Received_Qty":0,"Deposit_Rs":0.0,"Date":"2025-01-16"},
            {"Challan_No":"CH-003","Style":"1065YKBLUE","SKU":"YK-BLU-XL","Qty":100,"Received_Qty":0,"Deposit_Rs":0.0,"Date":"2025-01-17"},
        ])
    if "production_log" not in st.session_state:
        st.session_state.production_log = pd.DataFrame(columns=[
            "Date","Karigar_ID","Karigar_Name","Challan_No","Style","Operation",
        ] + HOUR_COLS + ["Total_Pieces","Target","Rate_Rs","Efficiency_%","Piece_Value_Rs"])
    if "employee_master" not in st.session_state:
        st.session_state.employee_master = pd.DataFrame([
            {"E_Code":"E001","Name":"Ramesh Kumar","Type":"Karigar","Daily_Rate_Rs":450,"Hourly_Rate_Rs":56.25},
            {"E_Code":"E002","Name":"Suresh Singh","Type":"Karigar","Daily_Rate_Rs":420,"Hourly_Rate_Rs":52.50},
            {"E_Code":"E003","Name":"Priya Devi","Type":"Karigar","Daily_Rate_Rs":400,"Hourly_Rate_Rs":50.00},
            {"E_Code":"E004","Name":"Mohan Lal","Type":"Karigar","Daily_Rate_Rs":460,"Hourly_Rate_Rs":57.50},
            {"E_Code":"E005","Name":"Sunita Sharma","Type":"Karigar","Daily_Rate_Rs":410,"Hourly_Rate_Rs":51.25},
            {"E_Code":"E101","Name":"Amit Sharma","Type":"Operating","Daily_Rate_Rs":600,"Hourly_Rate_Rs":75.00},
            {"E_Code":"E102","Name":"Kavita Rao","Type":"Operating","Daily_Rate_Rs":550,"Hourly_Rate_Rs":68.75},
        ])
    if "karigar_attendance" not in st.session_state:
        st.session_state.karigar_attendance = pd.DataFrame(columns=[
            "Date","E_Code","Name","In_Punch","Out_Punch",
            "Total_Presence_Hrs","Lunch_Deduction_Hrs","Payable_Hrs",
            "Hourly_Rate_Rs","Normal_Pay","OT_Hours","OT_Pay","Total_Pay"
        ])
    if "operating_attendance" not in st.session_state:
        st.session_state.operating_attendance = pd.DataFrame(columns=[
            "Date","E_Code","Name","In_Punch","Out_Punch",
            "Total_Hours","Hourly_Rate_Rs","Total_Pay"
        ])

init_state()

# ─────────────────────────────────────────────
# Salary Calculation
# ─────────────────────────────────────────────
def calculate_karigar_salary(e_code, in_str, out_str, daily_rate, ot_mult=1.5):
    try:
        fmt         = "%H:%M"
        t_in        = datetime.strptime(in_str.strip(), fmt)
        t_out       = datetime.strptime(out_str.strip(), fmt)
        lunch_start = datetime.strptime("13:00", fmt)
        lunch_end   = datetime.strptime("14:00", fmt)
        shift_end   = datetime.strptime("18:00", fmt)

        presence_secs    = max(int((t_out - t_in).total_seconds()), 0)
        presence_hrs     = round(presence_secs / 3600, 4)
        was_during_lunch = (t_in < lunch_end) and (t_out > lunch_start)
        lunch_ded        = 1.0 if was_during_lunch else 0.0
        payable_hrs      = max(round(presence_hrs - lunch_ded, 4), 0.0)
        hourly_rate      = round(daily_rate / 8, 4)
        normal_pay       = round(payable_hrs * hourly_rate, 2)

        if t_out > shift_end:
            ot_hrs = round(int((t_out - shift_end).total_seconds()) / 3600, 4)
        else:
            ot_hrs = 0.0

        ot_pay    = round(ot_hrs * hourly_rate * ot_mult, 2)
        total_pay = round(normal_pay + ot_pay, 2)
        return (round(presence_hrs,2), round(lunch_ded,2), round(payable_hrs,2),
                round(hourly_rate,2), normal_pay, round(ot_hrs,2), ot_pay, total_pay)
    except Exception:
        return 0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0

# ─────────────────────────────────────────────
# Operating Cost Allocation (karigar-cost-based)
# ─────────────────────────────────────────────
def get_op_cost_allocation(report_date: str):
    """
    Returns a DataFrame: Style | Challan_No | Karigar_Cost_Rs | Karigar_Cost_Pct |
                         Allocated_Op_Cost_Rs | Total_Style_Cost_Rs
    """
    pl  = st.session_state.production_log
    att = st.session_state.karigar_attendance
    op  = st.session_state.operating_attendance

    result_empty = pd.DataFrame(columns=[
        "Challan_No","Style","Karigar_Cost_Rs","Karigar_Cost_Pct",
        "Allocated_Op_Cost_Rs","Total_Style_Cost_Rs"
    ])

    if pl.empty or att.empty:
        return result_empty, 0.0, 0.0

    pl_day  = pl[pl["Date"] == report_date].copy()
    att_day = att[att["Date"] == report_date].copy()

    if pl_day.empty or att_day.empty:
        return result_empty, 0.0, 0.0

    if "Payable_Hrs" not in att_day.columns or "Hourly_Rate_Rs" not in att_day.columns:
        return result_empty, 0.0, 0.0

    att_day["Daily_Karigar_Cost"] = (
        safe_numeric(att_day["Payable_Hrs"]) * safe_numeric(att_day["Hourly_Rate_Rs"])
    )

    karigar_cost_map = att_day.set_index("E_Code")["Daily_Karigar_Cost"].to_dict()

    pl_day["Karigar_Cost"] = safe_numeric(pl_day["Karigar_ID"].map(karigar_cost_map).fillna(0))
    karigar_total_pieces = pl_day.groupby("Karigar_ID")["Total_Pieces"].transform("sum").replace(0,1)
    pl_day["Attributed_Cost"] = (
        pl_day["Karigar_Cost"] * safe_numeric(pl_day["Total_Pieces"]) / karigar_total_pieces
    )

    style_karigar_cost = pl_day.groupby(["Challan_No","Style"])["Attributed_Cost"].sum().reset_index()
    style_karigar_cost.columns = ["Challan_No","Style","Karigar_Cost_Rs"]

    total_karigar_cost = style_karigar_cost["Karigar_Cost_Rs"].sum()
    if total_karigar_cost == 0:
        return result_empty, 0.0, 0.0

    op_day = op[op["Date"] == report_date] if not op.empty else pd.DataFrame()
    total_op_cost = safe_numeric(op_day["Total_Pay"]).sum() if not op_day.empty else 0.0

    style_karigar_cost["Karigar_Cost_Pct"] = (
        style_karigar_cost["Karigar_Cost_Rs"] / total_karigar_cost * 100
    ).round(2)
    style_karigar_cost["Allocated_Op_Cost_Rs"] = (
        style_karigar_cost["Karigar_Cost_Pct"] / 100 * total_op_cost
    ).round(2)
    style_karigar_cost["Total_Style_Cost_Rs"] = (
        style_karigar_cost["Karigar_Cost_Rs"] + style_karigar_cost["Allocated_Op_Cost_Rs"]
    ).round(2)

    return style_karigar_cost.round(2), round(total_karigar_cost,2), round(total_op_cost,2)

# ─────────────────────────────────────────────
# Style Costing Function
# ─────────────────────────────────────────────
def get_style_costing(style_code: str):
    """
    Calculate full costing for a style across all operations and challans
    """
    sm = st.session_state.style_master
    cm = st.session_state.challan_master
    
    # Get all operations for this style
    style_ops = sm[sm["Style"] == style_code].copy()
    
    if style_ops.empty:
        return None, 0.0
    
    # Total rate per garment for this style
    total_rate_per_garment = safe_numeric(style_ops["Rate_Rs"]).sum()
    
    # Get all challans for this style
    style_challans = cm[cm["Style"] == style_code].copy()
    
    return style_ops, total_rate_per_garment, style_challans

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
<div style="background:#2c5aa0;padding:20px;border-radius:8px;color:white;margin-bottom:20px">
  <h2 style="margin:0">🧵 Stitching Costing Interface</h2>
  <p style="margin:4px 0 0;opacity:0.9">Karigar Time Tracking • Challan-wise Costing • Efficiency Analysis • Style Costing • Payroll</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tabs = st.tabs([
    "🏠 Dashboard",
    "📋 Production Entry (Hour-wise + Daily)",
    "🧾 Challan Management",
    "💎 Style Costing",
    "📊 Efficiency & Costing",
    "💰 Payroll Calculator",
    "🕐 Karigar Salary & Attendance",
    "🏢 Operating Staff",
    "🌟 Employee Performance",
    "⚙️ Master Data",
])
(tab_dash, tab_prod, tab_challan, tab_style_cost, tab_efficiency,
 tab_payroll, tab_salary, tab_operating, tab_performance, tab_master) = tabs

# ════════════════════════════════════════════════════════════
# TAB 1 – DASHBOARD
# ════════════════════════════════════════════════════════════
with tab_dash:
    st.markdown('<div class="section-header">📈 Today\'s Overview</div>', unsafe_allow_html=True)
    today_str = str(date.today())
    today_pl  = st.session_state.production_log[st.session_state.production_log["Date"] == today_str] \
                if not st.session_state.production_log.empty else pd.DataFrame()

    c1,c2,c3,c4 = st.columns(4)
    with c1:
        active = today_pl["Karigar_ID"].nunique() if not today_pl.empty else 0
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Active Karigar Today</div>
            <div class="metric-value">{active}</div>
            <div class="metric-sub">of {len(st.session_state.karigar_master)} total</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        pieces = int(safe_numeric(today_pl["Total_Pieces"]).sum()) if not today_pl.empty else 0
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Pieces Done Today</div>
            <div class="metric-value">{pieces:,}</div>
            <div class="metric-sub">across all operations</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        if not today_pl.empty and "Efficiency_%" in today_pl.columns:
            avg_eff = safe_numeric(today_pl["Efficiency_%"]).mean()
        else:
            avg_eff = 0.0
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Avg Efficiency</div>
            <div class="metric-value">{avg_eff:.1f}%</div>
            <div class="metric-sub">Target: 100%</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        pv = safe_numeric(today_pl["Piece_Value_Rs"]).sum() if not today_pl.empty else 0
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Today's Piece-Rate Value</div>
            <div class="metric-value">₹{pv:,.0f}</div>
            <div class="metric-sub">direct labour value</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    cola, colb = st.columns(2)
    with cola:
        st.markdown('<div class="section-header">👷 Karigar Status</div>', unsafe_allow_html=True)
        km = st.session_state.karigar_master.copy()
        active_ids = today_pl["Karigar_ID"].unique().tolist() if not today_pl.empty else []
        km["Status"] = km["Karigar_ID"].apply(lambda x: "🟢 Working" if x in active_ids else "⚪ Idle")
        st.dataframe(km[["Karigar_ID","Name","Skill","Status"]], use_container_width=True, hide_index=True)
    with colb:
        st.markdown('<div class="section-header">🧾 Active Challans</div>', unsafe_allow_html=True)
        st.dataframe(st.session_state.challan_master, use_container_width=True, hide_index=True)

    if not today_pl.empty:
        st.markdown("---")
        st.markdown('<div class="section-header">📋 Today\'s Production Summary</div>', unsafe_allow_html=True)
        disp_cols = ["Karigar_Name","Challan_No","Style","Operation","Total_Pieces","Target","Efficiency_%","Piece_Value_Rs"]
        disp_cols = [c for c in disp_cols if c in today_pl.columns]
        st.dataframe(today_pl[disp_cols], use_container_width=True, hide_index=True)

        alloc, tot_kar, tot_op = get_op_cost_allocation(today_str)
        if not alloc.empty:
            st.markdown('<div class="section-header">💼 Today\'s Style-wise Total Cost</div>', unsafe_allow_html=True)
            m1,m2 = st.columns(2)
            m1.metric("Karigar Cost", f"₹{tot_kar:,.2f}")
            m2.metric("Operating Staff Cost", f"₹{tot_op:,.2f}")
            st.dataframe(alloc, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════
# TAB 2 – PRODUCTION ENTRY
# ════════════════════════════════════════════════════════════
with tab_prod:
    st.markdown('<div class="section-header">📋 Production Entry — Hour-wise Time Log & Daily Sheet</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-box">'
        'Unified entry captures hour-wise production (9–19) and daily totals. '
        '<b>Flow: Select Challan → Style auto-fills → Select Operation → Target & Rate auto-fetch</b>'
        '</div>', unsafe_allow_html=True
    )

    is_unlocked = sheet_lock_widget("prod")

    import_section(
        key="production_log",
        required_cols=["Date","Karigar_ID","Karigar_Name","Challan_No","Style","Operation"] + HOUR_COLS + ["Target","Rate_Rs"],
        session_key="production_log",
        template_df=TEMPLATES["production_log"],
        label="Production Log"
    )

    st.markdown("---")
    st.markdown('<div class="section-header">✏️ New Production Entry</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        pe_date = st.date_input("📅 Date", value=date.today(), key="pe_date")
    with col_b:
        karigar_map = {
            f"{r['Karigar_ID']} — {r['Name']}": r
            for _, r in st.session_state.karigar_master.iterrows()
        }
        pe_karigar_key = st.selectbox("👤 Karigar", list(karigar_map.keys()), key="pe_karigar")
        pe_karigar_row = karigar_map[pe_karigar_key]

    challan_df  = st.session_state.challan_master
    challan_list = challan_df["Challan_No"].tolist() if not challan_df.empty else []
    if not challan_list:
        st.warning("No challans found. Please add challans in Challan Management first.")
        st.stop()

    pe_challan = st.selectbox("🧾 Challan Number", challan_list, key="pe_challan")
    challan_row = challan_df[challan_df["Challan_No"] == pe_challan]
    pe_style    = challan_row["Style"].values[0] if not challan_row.empty else ""
    st.markdown(
        f'<div class="readonly-field">📦 Style: <b>{pe_style}</b> | SKU: <b>{challan_row["SKU"].values[0] if not challan_row.empty else "—"}</b> | Qty: <b>{challan_row["Qty"].values[0] if not challan_row.empty else "—"}</b></div>',
        unsafe_allow_html=True
    )

    sm_style_ops = st.session_state.style_master[
        st.session_state.style_master["Style"] == pe_style
    ][["Operation","Target","Rate_Rs"]] if pe_style else pd.DataFrame()

    if sm_style_ops.empty:
        st.warning(f"No operations found for style '{pe_style}'.")
    else:
        pe_op = st.selectbox("⚙️ Operation", sm_style_ops["Operation"].tolist(), key="pe_op")
        op_row = sm_style_ops[sm_style_ops["Operation"] == pe_op]
        tgt_val  = int(op_row["Target"].values[0])   if not op_row.empty else 0
        rate_val = float(op_row["Rate_Rs"].values[0]) if not op_row.empty else 0.0

        col_t, col_r = st.columns(2)
        with col_t:
            if is_unlocked:
                tgt_val  = st.number_input("🎯 Target (Admin editable)", value=tgt_val, min_value=0, step=1, key="pe_tgt")
            else:
                st.markdown(f'<div class="readonly-field">🎯 Target: <b>{tgt_val} pcs</b> 🔒 Locked</div>', unsafe_allow_html=True)
        with col_r:
            if is_unlocked:
                rate_val = st.number_input("💰 Rate/pc (Admin editable)", value=rate_val, min_value=0.0, step=0.25, format="%.2f", key="pe_rate")
            else:
                st.markdown(f'<div class="readonly-field">💰 Rate: <b>Rs {rate_val:.2f}/pc</b> 🔒 Locked</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="section-header">⏰ Hour-wise Pieces (9:00 – 19:00)</div>', unsafe_allow_html=True)
        st.caption("Enter pieces done in each hour slot. Lunch break 13:00–14:00 is excluded.")

        hour_vals = {}
        cols = st.columns(len(HOUR_COLS))
        for i, (hcol, hlabel) in enumerate(zip(HOUR_COLS, HOUR_LABELS)):
            with cols[i]:
                hour_vals[hcol] = st.number_input(hlabel, min_value=0, step=1, value=0, key=f"pe_{hcol}")

        total_pieces = sum(hour_vals.values())
        efficiency   = round(total_pieces / tgt_val * 100, 1) if tgt_val > 0 else 0.0
        piece_value  = round(total_pieces * rate_val, 2)

        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("Total Pieces", total_pieces)
        col_s2.metric("Efficiency", f"{efficiency}%")
        col_s3.metric("Piece-Rate Value", f"Rs {piece_value}")

        if st.button("💾 Save Production Entry", use_container_width=True, key="pe_save"):
            new_row = {
                "Date": str(pe_date),
                "Karigar_ID": pe_karigar_row["Karigar_ID"],
                "Karigar_Name": pe_karigar_row["Name"],
                "Challan_No": pe_challan,
                "Style": pe_style,
                "Operation": pe_op,
                **hour_vals,
                "Total_Pieces": total_pieces,
                "Target": tgt_val,
                "Rate_Rs": rate_val,
                "Efficiency_%": efficiency,
                "Piece_Value_Rs": piece_value,
            }
            st.session_state.production_log = pd.concat(
                [st.session_state.production_log, pd.DataFrame([new_row])], ignore_index=True
            )
            st.success(f"✅ Saved! {pe_karigar_row['Name']} | {pe_op} | {total_pieces} pcs | Eff: {efficiency}% | Rs {piece_value}")
            st.rerun()

    st.markdown("---")
    st.markdown('<div class="section-header">📄 Production Records</div>', unsafe_allow_html=True)
    if not st.session_state.production_log.empty:
        pv_filter = st.date_input("Filter by Date", value=date.today(), key="pv_filter")
        pv_df = st.session_state.production_log[
            st.session_state.production_log["Date"] == str(pv_filter)
        ].copy()

        if not pv_df.empty:
            for col in ["Total_Pieces","Target","Rate_Rs","Efficiency_%","Piece_Value_Rs"] + HOUR_COLS:
                if col in pv_df.columns:
                    pv_df[col] = safe_numeric(pv_df[col])

            rv1, rv2 = st.tabs(["📋 Daily Summary View", "🗓️ Hour-wise Heatmap"])
            with rv1:
                summary_cols = ["Karigar_Name","Challan_No","Style","Operation",
                                "Total_Pieces","Target","Efficiency_%","Piece_Value_Rs"]
                summary_cols = [c for c in summary_cols if c in pv_df.columns]
                st.dataframe(pv_df[summary_cols], use_container_width=True, hide_index=True)

                ks = pv_df.groupby("Karigar_Name").agg(
                    Ops=("Operation","count"),
                    Total_Target=("Target","sum"),
                    Total_Achieved=("Total_Pieces","sum"),
                    Total_Piece_Value_Rs=("Piece_Value_Rs","sum")
                ).reset_index()
                ks["Overall_Eff_%"] = (ks["Total_Achieved"] / ks["Total_Target"].replace(0,1) * 100).round(1)
                st.markdown('<div class="section-header">Karigar Summary</div>', unsafe_allow_html=True)
                st.dataframe(ks, use_container_width=True, hide_index=True)

            with rv2:
                try:
                    heatmap_df = pv_df[["Karigar_Name","Operation"] + [h for h in HOUR_COLS if h in pv_df.columns]].copy()
                    heatmap_melted = heatmap_df.melt(
                        id_vars=["Karigar_Name","Operation"],
                        value_vars=[h for h in HOUR_COLS if h in heatmap_df.columns],
                        var_name="Hour", value_name="Pieces"
                    )
                    heatmap_melted["Hour"] = heatmap_melted["Hour"].map(
                        dict(zip(HOUR_COLS, HOUR_LABELS))
                    )
                    pivot = heatmap_melted.pivot_table(
                        index="Karigar_Name", columns="Hour",
                        values="Pieces", aggfunc="sum", fill_value=0
                    )
                    ordered_labels = [l for l in HOUR_LABELS if l in pivot.columns]
                    pivot = pivot[ordered_labels]
                    st.markdown("**Pieces per karigar per hour slot**")
                    st.dataframe(pivot.style.background_gradient(cmap="Blues"), use_container_width=True)
                except Exception as e:
                    st.info(f"Heatmap not available: {e}")

            ex1, ex2 = st.columns(2)
            with ex1:
                st.download_button("📥 Export Excel", data=df_to_excel_bytes(pv_df),
                    file_name=f"production_{pv_filter}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with ex2:
                st.download_button("📥 Export CSV", data=df_to_csv_bytes(pv_df),
                    file_name=f"production_{pv_filter}.csv", mime="text/csv")
        else:
            st.info("No production entries for selected date.")

        with st.expander("🔑 Change Admin Password"):
            with st.form("change_pw_form", clear_on_submit=True):
                cur_pw  = st.text_input("Current Password", type="password")
                new_pw  = st.text_input("New Password", type="password")
                new_pw2 = st.text_input("Confirm New Password", type="password")
                if st.form_submit_button("Change Password"):
                    if hash_password(cur_pw) != st.session_state.admin_pw_hash:
                        st.error("❌ Current password incorrect")
                    elif new_pw != new_pw2:
                        st.error("❌ New passwords do not match")
                    elif len(new_pw) < 4:
                        st.error("❌ Password must be at least 4 characters")
                    else:
                        st.session_state.admin_pw_hash = hash_password(new_pw)
                        st.success("✅ Password changed successfully!")
    else:
        st.info("No production entries yet.")

# ════════════════════════════════════════════════════════════
# TAB 3 – CHALLAN MANAGEMENT (ENHANCED)
# ════════════════════════════════════════════════════════════
with tab_challan:
    st.markdown('<div class="section-header">🧾 Challan Management — Complete Tracking</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box"><b>Track:</b> Order Quantity | Received Quantity | Department Deposits | Complete Costing</div>', unsafe_allow_html=True)

    import_section(
        key="challan_master",
        required_cols=["Challan_No","Style","SKU","Qty","Received_Qty","Deposit_Rs","Date"],
        session_key="challan_master",
        template_df=TEMPLATES["challan_master"],
        label="Challan Master"
    )

    with st.expander("➕ Add New Challan Manually"):
        with st.form("challan_form", clear_on_submit=True):
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                c_no    = st.text_input("Challan No (e.g. CH-004)")
                c_style = st.selectbox("Style", st.session_state.style_master["Style"].unique().tolist()) \
                          if not st.session_state.style_master.empty else st.text_input("Style")
            with cc2:
                c_sku = st.text_input("SKU")
                c_qty = st.number_input("Order Quantity", min_value=1, step=1)
            with cc3:
                c_rec_qty = st.number_input("Received Quantity", min_value=0, step=1, value=0)
                c_deposit = st.number_input("Department Deposit (Rs)", min_value=0.0, step=100.0, value=0.0)
            c_date = st.date_input("Challan Date", value=date.today())
            if st.form_submit_button("Add Challan") and c_no:
                st.session_state.challan_master = pd.concat(
                    [st.session_state.challan_master, pd.DataFrame([{
                        "Challan_No":c_no,"Style":c_style,"SKU":c_sku,"Qty":int(c_qty),
                        "Received_Qty":int(c_rec_qty),"Deposit_Rs":float(c_deposit),"Date":str(c_date)
                    }])], ignore_index=True)
                st.success(f"✅ Challan {c_no} added!")
                st.rerun()

    st.markdown('<div class="section-header">Challan Register</div>', unsafe_allow_html=True)
    cm = st.session_state.challan_master.copy()
    if not cm.empty:
        cm["Pending_Qty"] = safe_numeric(cm.get("Qty", 0)) - safe_numeric(cm.get("Received_Qty", 0))
        cm["Status"] = cm["Pending_Qty"].apply(
            lambda x: "✅ Complete" if x <= 0 else f"⏳ {int(x)} pending"
        )
        display_cm = cm[["Challan_No","Style","SKU","Qty","Received_Qty","Pending_Qty","Status","Deposit_Rs","Date"]]
        st.dataframe(display_cm, use_container_width=True, hide_index=True)
        
        # Summary metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Challans", len(cm))
        c2.metric("Completed", len(cm[cm["Pending_Qty"] <= 0]))
        c3.metric("Pending", len(cm[cm["Pending_Qty"] > 0]))
        c4.metric("Total Deposits", f"₹{safe_numeric(cm['Deposit_Rs']).sum():,.2f}")

    ex1, ex2 = st.columns(2)
    with ex1:
        st.download_button("📥 Export Challan List (Excel)",
            data=df_to_excel_bytes(st.session_state.challan_master),
            file_name="challans.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with ex2:
        st.download_button("📥 Export Challan List (CSV)",
            data=df_to_csv_bytes(st.session_state.challan_master),
            file_name="challans.csv", mime="text/csv")

    st.markdown("---")
    st.markdown('<div class="section-header">📊 Challan-wise Full Costing Report</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-box">'
        '<b>Total Style Cost = Direct Karigar Cost + Allocated Operating Staff Cost + Department Deposit</b>'
        '</div>', unsafe_allow_html=True
    )

    report_date_ch = st.date_input("Select Date for Costing Report", value=date.today(), key="ch_report_date")
    alloc, tot_kar, tot_op = get_op_cost_allocation(str(report_date_ch))

    if alloc.empty:
        st.info("No costing data for this date.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Karigar Cost", f"₹{tot_kar:,.2f}")
        m2.metric("Operating Staff Cost", f"₹{tot_op:,.2f}")
        m3.metric("Grand Total", f"₹{tot_kar + tot_op:,.2f}")

        alloc_detail = alloc.merge(
            st.session_state.challan_master[["Challan_No","SKU","Qty","Received_Qty","Deposit_Rs"]],
            on="Challan_No", how="left"
        )
        alloc_detail["Qty"] = safe_numeric(alloc_detail.get("Qty", pd.Series([1]*len(alloc_detail))))
        alloc_detail["Received_Qty"] = safe_numeric(alloc_detail.get("Received_Qty", 0))
        alloc_detail["Deposit_Rs"] = safe_numeric(alloc_detail.get("Deposit_Rs", 0))
        alloc_detail["Total_With_Deposit"] = alloc_detail["Total_Style_Cost_Rs"] + alloc_detail["Deposit_Rs"]
        alloc_detail["Cost_Per_Piece_Rs"] = (
            alloc_detail["Total_With_Deposit"] / alloc_detail["Qty"].replace(0,1)
        ).round(2)

        st.dataframe(alloc_detail, use_container_width=True, hide_index=True)

        st.markdown("---")
        sel_challan = st.selectbox("Drill Down: Select Challan",
            st.session_state.challan_master["Challan_No"].tolist(), key="ch_drill")
        ch_detail = alloc_detail[alloc_detail["Challan_No"] == sel_challan]
        if not ch_detail.empty:
            row = ch_detail.iloc[0]
            dc1, dc2, dc3, dc4 = st.columns(4)
            dc1.metric("Karigar Cost", f"₹{row['Karigar_Cost_Rs']:,.2f}")
            dc2.metric("Op Staff Cost", f"₹{row['Allocated_Op_Cost_Rs']:,.2f}")
            dc3.metric("Department Deposit", f"₹{row['Deposit_Rs']:,.2f}")
            dc4.metric("Total Cost/Piece", f"₹{row['Cost_Per_Piece_Rs']:,.2f}")
            
            # Status
            if row['Received_Qty'] >= row['Qty']:
                st.markdown('<div class="success-box">✅ <b>Challan Complete</b> — All items received</div>', unsafe_allow_html=True)
            else:
                pending = int(row['Qty'] - row['Received_Qty'])
                st.markdown(f'<div class="warning-box">⏳ <b>Pending: {pending} pcs</b> — Still in production</div>', unsafe_allow_html=True)

        ex1, ex2 = st.columns(2)
        with ex1:
            st.download_button("📥 Export Costing Report (Excel)",
                data=df_to_excel_bytes(alloc_detail),
                file_name=f"costing_{report_date_ch}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with ex2:
            st.download_button("📥 Export Costing Report (CSV)",
                data=df_to_csv_bytes(alloc_detail),
                file_name=f"costing_{report_date_ch}.csv", mime="text/csv")

# ════════════════════════════════════════════════════════════
# TAB 4 – STYLE COSTING (NEW TAB)
# ════════════════════════════════════════════════════════════
with tab_style_cost:
    st.markdown('<div class="section-header">💎 Style Costing — Full Cost Breakdown</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-box">'
        'Complete cost analysis for each style including all operations, piece-rates, and challans'
        '</div>', unsafe_allow_html=True
    )

    if st.session_state.style_master.empty:
        st.warning("No styles defined yet. Please add styles in Master Data.")
    else:
        all_styles = st.session_state.style_master["Style"].unique().tolist()
        sel_style = st.selectbox("Select Style for Costing", all_styles, key="style_costing_sel")
        
        # Get style operations
        style_ops = st.session_state.style_master[st.session_state.style_master["Style"] == sel_style].copy()
        total_rate = safe_numeric(style_ops["Rate_Rs"]).sum()
        
        st.markdown(f'<div class="section-header">Style: <b>{sel_style}</b></div>', unsafe_allow_html=True)
        
        # Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Operations", len(style_ops))
        m2.metric("Total Rate/Garment", f"₹{total_rate:.2f}")
        m3.metric("Avg Rate/Operation", f"₹{total_rate/len(style_ops):.2f}" if len(style_ops) > 0 else "N/A")
        
        st.markdown('<div class="section-header">Operations Breakdown</div>', unsafe_allow_html=True)
        
        ops_detail = style_ops[["Operation","Target","Rate_Rs"]].copy()
        ops_detail["Daily_Production_Value"] = safe_numeric(ops_detail["Target"]) * safe_numeric(ops_detail["Rate_Rs"])
        ops_detail = ops_detail.round(2)
        
        st.dataframe(ops_detail, use_container_width=True, hide_index=True)
        
        st.markdown('<div class="section-header">Challan-wise Status</div>', unsafe_allow_html=True)
        
        style_challans = st.session_state.challan_master[st.session_state.challan_master["Style"] == sel_style].copy()
        
        if not style_challans.empty:
            style_challans["Pending_Qty"] = safe_numeric(style_challans["Qty"]) - safe_numeric(style_challans.get("Received_Qty", 0))
            style_challans["Status"] = style_challans["Pending_Qty"].apply(
                lambda x: "✅ Complete" if x <= 0 else f"⏳ {int(x)} pending"
            )
            style_challans["Est_Labour_Value"] = safe_numeric(style_challans["Qty"]) * total_rate
            style_challans["Total_Cost_With_Deposit"] = style_challans["Est_Labour_Value"] + safe_numeric(style_challans.get("Deposit_Rs", 0))
            
            chal_display = style_challans[["Challan_No","SKU","Qty","Received_Qty","Pending_Qty","Status",
                                           "Est_Labour_Value","Deposit_Rs","Total_Cost_With_Deposit"]].copy()
            chal_display = chal_display.round(2)
            
            st.dataframe(chal_display, use_container_width=True, hide_index=True)
            
            # Totals
            st.markdown('<div class="section-header">Style Totals</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Challans", len(style_challans))
            c2.metric("Total Order Qty", int(safe_numeric(style_challans["Qty"]).sum()))
            c3.metric("Total Received", int(safe_numeric(style_challans.get("Received_Qty", 0)).sum()))
            c4.metric("Total Pending", int(safe_numeric(style_challans["Pending_Qty"]).sum()))
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Est Labour Value", f"₹{safe_numeric(style_challans['Est_Labour_Value']).sum():,.2f}")
            m2.metric("Total Deposits", f"₹{safe_numeric(style_challans.get('Deposit_Rs', 0)).sum():,.2f}")
            m3.metric("Total Style Cost", f"₹{safe_numeric(style_challans['Total_Cost_With_Deposit']).sum():,.2f}")
        else:
            st.info("No challans created for this style yet.")
        
        # Production Summary
        st.markdown('<div class="section-header">Production Summary</div>', unsafe_allow_html=True)
        
        pl = st.session_state.production_log
        if not pl.empty:
            style_prod = pl[pl["Style"] == sel_style].copy()
            
            if not style_prod.empty:
                for col in ["Total_Pieces","Piece_Value_Rs","Efficiency_%"]:
                    if col in style_prod.columns:
                        style_prod[col] = safe_numeric(style_prod[col])
                
                prod_summary = style_prod.groupby("Operation").agg(
                    Total_Pieces=("Total_Pieces","sum"),
                    Piece_Value=("Piece_Value_Rs","sum"),
                    Avg_Efficiency=("Efficiency_%","mean"),
                    Entries=("Operation","count"),
                ).reset_index().round(2)
                
                st.dataframe(prod_summary, use_container_width=True, hide_index=True)
            else:
                st.info("No production entries for this style yet.")
        else:
            st.info("No production data available.")
        
        # Export
        st.markdown("---")
        exp1, exp2 = st.columns(2)
        with exp1:
            st.download_button("📥 Export Style Details (Excel)",
                data=df_to_excel_bytes(ops_detail),
                file_name=f"style_costing_{sel_style}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with exp2:
            st.download_button("📥 Export Style Details (CSV)",
                data=df_to_csv_bytes(ops_detail),
                file_name=f"style_costing_{sel_style}.csv", mime="text/csv")

# ════════════════════════════════════════════════════════════
# TAB 5 – EFFICIENCY & COSTING
# ════════════════════════════════════════════════════════════
with tab_efficiency:
    st.markdown('<div class="section-header">📊 Efficiency & Deep Analysis</div>', unsafe_allow_html=True)

    if st.session_state.production_log.empty:
        st.info("No data yet. Fill production entries to see analysis.")
    else:
        df = st.session_state.production_log.copy()
        for col in ["Total_Pieces","Target","Rate_Rs","Efficiency_%","Piece_Value_Rs"]:
            if col in df.columns:
                df[col] = safe_numeric(df[col])
        df["Date_dt"] = pd.to_datetime(df["Date"], errors="coerce")

        f1, f2 = st.columns(2)
        with f1:
            date_range = st.date_input("Date Range",
                value=[date.today()-timedelta(days=7), date.today()])
        with f2:
            style_filter = st.multiselect("Filter Style",
                df["Style"].unique().tolist(), default=df["Style"].unique().tolist())

        if len(date_range) == 2:
            mask = (
                (df["Date_dt"] >= pd.Timestamp(date_range[0])) &
                (df["Date_dt"] <= pd.Timestamp(date_range[1])) &
                (df["Style"].isin(style_filter))
            )
            df_f = df[mask].copy()
        else:
            df_f = df[df["Style"].isin(style_filter)].copy()

        if df_f.empty:
            st.warning("No data for selected filters.")
        else:
            c1,c2,c3 = st.columns(3)
            c1.metric("Avg Efficiency",         f"{df_f['Efficiency_%'].mean():.1f}%")
            c2.metric("Total Piece-Rate Value",  f"₹{df_f['Piece_Value_Rs'].sum():,.0f}")
            c3.metric("Total Pieces",            f"{int(df_f['Total_Pieces'].sum()):,}")

            st.markdown("---")
            st.markdown('<div class="section-header">Karigar-wise Efficiency</div>', unsafe_allow_html=True)
            karigar_eff = df_f.groupby("Karigar_Name").agg(
                Avg_Efficiency=("Efficiency_%","mean"),
                Total_Pieces=("Total_Pieces","sum"),
                Total_Piece_Value_Rs=("Piece_Value_Rs","sum"),
                Ops_Done=("Operation","count")
            ).round(2).reset_index()
            karigar_eff["Grade"] = karigar_eff["Avg_Efficiency"].apply(
                lambda x: "A – Excellent" if x>=100 else ("B – Good" if x>=85 else ("C – Average" if x>=70 else "D – Below Target"))
            )
            st.dataframe(karigar_eff, use_container_width=True, hide_index=True)

            st.markdown('<div class="section-header">Operation-wise Performance</div>', unsafe_allow_html=True)
            op_eff = df_f.groupby("Operation").agg(
                Avg_Efficiency=("Efficiency_%","mean"),
                Total_Pieces=("Total_Pieces","sum"),
                Total_Value_Rs=("Piece_Value_Rs","sum")
            ).round(2).reset_index().sort_values("Avg_Efficiency")
            st.dataframe(op_eff, use_container_width=True, hide_index=True)
            bottleneck = op_eff[op_eff["Avg_Efficiency"] < 80]
            if not bottleneck.empty:
                st.warning(f"⚠️ Bottleneck Operations (below 80%): {', '.join(bottleneck['Operation'].tolist())}")

            st.markdown('<div class="section-header">Style-wise Labour Value</div>', unsafe_allow_html=True)
            style_cost = df_f.groupby(["Style","Operation"]).agg(
                Total_Pieces=("Total_Pieces","sum"),
                Total_Value_Rs=("Piece_Value_Rs","sum")
            ).reset_index()
            st.dataframe(style_cost, use_container_width=True, hide_index=True)

            ex1, ex2 = st.columns(2)
            with ex1:
                st.download_button("📥 Export Efficiency Report (Excel)",
                    data=df_to_excel_bytes(karigar_eff),
                    file_name="efficiency_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with ex2:
                st.download_button("📥 Export Efficiency Report (CSV)",
                    data=df_to_csv_bytes(karigar_eff),
                    file_name="efficiency_report.csv", mime="text/csv")

# ════════════════════════════════════════════════════════════
# REMAINING TABS (Brief versions to save space)
# ════════════════════════════════════════════════════════════

with tab_payroll:
    st.markdown('<div class="section-header">💰 Payroll Calculator</div>', unsafe_allow_html=True)
    p1, p2 = st.columns(2)
    with p1: pay_start = st.date_input("Pay Period Start", value=date.today()-timedelta(days=6), key="pay_start")
    with p2: pay_end   = st.date_input("Pay Period End",   value=date.today(), key="pay_end")

    if st.button("📊 Calculate Payroll", use_container_width=True):
        if st.session_state.karigar_attendance.empty:
            st.warning("No attendance data available.")
        else:
            att = st.session_state.karigar_attendance.copy()
            att["Date_dt"] = pd.to_datetime(att["Date"])
            att = att[(att["Date_dt"]>=pd.Timestamp(pay_start)) & (att["Date_dt"]<=pd.Timestamp(pay_end))]
            if att.empty:
                st.warning("No records in this pay period.")
            else:
                for c in ["Payable_Hrs","Normal_Pay","OT_Hours","OT_Pay","Total_Pay"]:
                    if c in att.columns: att[c] = safe_numeric(att[c])
                payroll = att.groupby("E_Code").agg(
                    Name=("Name","first"),
                    Days_Present=("Date","nunique"),
                    Total_Payable_Hrs=("Payable_Hrs","sum"),
                    Total_Normal_Pay=("Normal_Pay","sum"),
                    Total_OT_Hours=("OT_Hours","sum"),
                    Total_OT_Pay=("OT_Pay","sum"),
                    Total_Pay=("Total_Pay","sum"),
                ).round(2).reset_index()
                st.dataframe(payroll, use_container_width=True, hide_index=True)
                st.metric("💷 Total Payroll Payout", f"₹{payroll['Total_Pay'].sum():,.2f}")
                ex1, ex2 = st.columns(2)
                with ex1:
                    st.download_button("📥 Download Payroll (Excel)",
                        data=df_to_excel_bytes(payroll),
                        file_name=f"payroll_{pay_start}_{pay_end}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="pay_xlsx")
                with ex2:
                    st.download_button("📥 Download Payroll (CSV)",
                        data=df_to_csv_bytes(payroll),
                        file_name=f"payroll_{pay_start}_{pay_end}.csv", mime="text/csv", key="pay_csv")

with tab_salary:
    st.markdown('<div class="section-header">🕐 Karigar Salary & Attendance</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-box">'
        '<b>Shift:</b> 9:00–18:00 | <b>Lunch:</b> 13:00–14:00 (unpaid) | <b>Payable:</b> 8 hrs/day max | <b>OT:</b> after 18:00'
        '</div>', unsafe_allow_html=True
    )

    ot_multiplier = st.selectbox("Overtime Multiplier",
        options=[1.0,1.5,2.0], index=1, key="ot_mult")

    import_section(
        key="karigar_attendance",
        required_cols=["Date","E_Code","In_Punch","Out_Punch"],
        session_key="karigar_attendance",
        template_df=TEMPLATES["karigar_attendance"],
        label="Karigar Attendance"
    )

    att_df = st.session_state.karigar_attendance
    if not att_df.empty and "Total_Pay" not in att_df.columns:
        emp  = st.session_state.employee_master
        rows = []
        for _, row in att_df.iterrows():
            er = emp[emp["E_Code"] == row["E_Code"]]
            if not er.empty:
                dr   = float(er["Daily_Rate_Rs"].values[0])
                name = er["Name"].values[0]
                ph,ld,pay_h,hr,np_,oth,otp,tp = calculate_karigar_salary(
                    row["E_Code"],str(row["In_Punch"]),str(row["Out_Punch"]),dr,ot_multiplier)
                rows.append({**row.to_dict(),"Name":name,"Total_Presence_Hrs":ph,
                    "Lunch_Deduction_Hrs":ld,"Payable_Hrs":pay_h,"Hourly_Rate_Rs":hr,
                    "Normal_Pay":np_,"OT_Hours":oth,"OT_Pay":otp,"Total_Pay":tp})
            else:
                rows.append(row.to_dict())
        st.session_state.karigar_attendance = pd.DataFrame(rows)
        st.rerun()

    with st.expander("✏️ Manual Attendance Entry", expanded=True):
        emp_karigar = st.session_state.employee_master[st.session_state.employee_master["Type"]=="Karigar"]
        emp_opts = {f"{r['E_Code']} – {r['Name']}": r for _,r in emp_karigar.iterrows()}
        with st.form("salary_form", clear_on_submit=True):
            c1,c2,c3 = st.columns(3)
            with c1:
                att_date = st.date_input("Date", value=date.today(), key="att_date")
                emp_sel  = st.selectbox("Employee", list(emp_opts.keys()), key="emp_sel_sal")
            with c2:
                in_punch  = st.text_input("In Punch (HH:MM)",  value="09:00", key="in_punch_sal")
                out_punch = st.text_input("Out Punch (HH:MM)", value="18:00", key="out_punch_sal")
            with c3:
                emp_row = emp_opts[emp_sel]
                dr = float(emp_row["Daily_Rate_Rs"])
                st.info(f"Daily: ₹{dr}\nHourly: ₹{dr/8:.2f}\nOT: {ot_multiplier}×")
            if st.form_submit_button("Calculate & Save", use_container_width=True, key="save_att"):
                ph,ld,pay_h,hr,np_,oth,otp,tp = calculate_karigar_salary(
                    emp_row["E_Code"],in_punch,out_punch,dr,ot_multiplier)
                new_att = {"Date":str(att_date),"E_Code":emp_row["E_Code"],"Name":emp_row["Name"],
                    "In_Punch":in_punch,"Out_Punch":out_punch,"Total_Presence_Hrs":ph,
                    "Lunch_Deduction_Hrs":ld,"Payable_Hrs":pay_h,"Hourly_Rate_Rs":hr,
                    "Normal_Pay":np_,"OT_Hours":oth,"OT_Pay":otp,"Total_Pay":tp}
                st.session_state.karigar_attendance = pd.concat(
                    [st.session_state.karigar_attendance, pd.DataFrame([new_att])], ignore_index=True)
                st.success(f"✅ Saved! Payable: {pay_h} hrs | Normal: ₹{np_} | OT: ₹{otp} | Total: ₹{tp}")

    st.markdown("---")
    if not st.session_state.karigar_attendance.empty:
        att_filter = st.date_input("Filter by Date", value=date.today(), key="att_filter")
        att_view   = st.session_state.karigar_attendance[
            st.session_state.karigar_attendance["Date"] == str(att_filter)]
        if not att_view.empty:
            st.dataframe(att_view, use_container_width=True, hide_index=True)

with tab_operating:
    st.markdown('<div class="section-header">🏢 Operating Staff — Cost Allocation Base</div>', unsafe_allow_html=True)

    import_section(
        key="operating_attendance",
        required_cols=["Date","E_Code","In_Punch","Out_Punch"],
        session_key="operating_attendance",
        template_df=TEMPLATES["operating_attendance"],
        label="Operating Staff Attendance"
    )

    emp_op  = st.session_state.employee_master[st.session_state.employee_master["Type"]=="Operating"]
    op_opts = {f"{r['E_Code']} – {r['Name']}": r for _,r in emp_op.iterrows()}

    with st.expander("✏️ Manual Entry — Operating Staff", expanded=True):
        with st.form("op_attend_form", clear_on_submit=True):
            oa1,oa2,oa3 = st.columns(3)
            with oa1:
                oa_date = st.date_input("Date", value=date.today(), key="oa_date")
                oa_emp  = st.selectbox("Employee", list(op_opts.keys()), key="oa_emp_sel")
            with oa2:
                oa_in  = st.text_input("In Punch",  value="09:00", key="oa_in")
                oa_out = st.text_input("Out Punch", value="18:00", key="oa_out")
            with oa3:
                er = op_opts[oa_emp]
                st.info(f"Hourly: ₹{er['Hourly_Rate_Rs']}")
            if st.form_submit_button("Save", use_container_width=True, key="save_op_att"):
                try:
                    fmt  = "%H:%M"
                    t_in  = datetime.strptime(oa_in.strip(), fmt)
                    t_out = datetime.strptime(oa_out.strip(), fmt)
                    hrs   = round(int((t_out-t_in).total_seconds())/3600, 2)
                except Exception:
                    hrs = 0
                hr_rate = float(er["Hourly_Rate_Rs"])
                total_p = round(hrs * hr_rate, 2)
                st.session_state.operating_attendance = pd.concat(
                    [st.session_state.operating_attendance, pd.DataFrame([{
                        "Date":str(oa_date),"E_Code":er["E_Code"],"Name":er["Name"],
                        "In_Punch":oa_in,"Out_Punch":oa_out,
                        "Total_Hours":hrs,"Hourly_Rate_Rs":hr_rate,"Total_Pay":total_p
                    }])], ignore_index=True)
                st.success(f"✅ {er['Name']} | {hrs} hrs | ₹{total_p}")

with tab_performance:
    st.markdown('<div class="section-header">🌟 Employee Performance Dashboard</div>', unsafe_allow_html=True)

    if st.session_state.production_log.empty or st.session_state.karigar_attendance.empty:
        st.info("Need production + attendance data.")
    else:
        p1,p2 = st.columns(2)
        with p1: perf_start = st.date_input("From", value=date.today()-timedelta(days=29), key="perf_start")
        with p2: perf_end   = st.date_input("To",   value=date.today(), key="perf_end")

        pl = st.session_state.production_log.copy()
        for c in ["Total_Pieces","Piece_Value_Rs","Efficiency_%"]:
            if c in pl.columns: pl[c] = safe_numeric(pl[c])
        pl["Date_dt"] = pd.to_datetime(pl["Date"])
        pl = pl[(pl["Date_dt"]>=pd.Timestamp(perf_start)) & (pl["Date_dt"]<=pd.Timestamp(perf_end))]

        piece_summary = pl.groupby("Karigar_ID").agg(
            Piece_Value_Rs=("Piece_Value_Rs","sum"),
            Total_Pieces=("Total_Pieces","sum"),
        ).reset_index()
        eff_summary = pl.groupby("Karigar_ID")["Efficiency_%"].mean().reset_index()
        eff_summary.columns = ["Karigar_ID","Avg_Efficiency_%"]
        piece_summary = piece_summary.merge(eff_summary, on="Karigar_ID", how="left")

        att = st.session_state.karigar_attendance.copy()
        att["Date_dt"] = pd.to_datetime(att["Date"])
        att = att[(att["Date_dt"]>=pd.Timestamp(perf_start)) & (att["Date_dt"]<=pd.Timestamp(perf_end))]

        if "Total_Pay" not in att.columns:
            st.warning("Attendance records lack salary data.")
        else:
            for c in ["Total_Pay","Payable_Hrs"]:
                att[c] = safe_numeric(att[c])
            salary_summary = att.groupby("E_Code").agg(
                Name=("Name","first"),
                Days_Worked=("Date","nunique"),
                Total_Payable_Hrs=("Payable_Hrs","sum"),
                Salary_Paid_Rs=("Total_Pay","sum"),
            ).round(2).reset_index()

            perf = salary_summary.merge(
                piece_summary.rename(columns={"Karigar_ID":"E_Code"}),
                on="E_Code", how="outer"
            ).fillna(0)

            perf["Piece_Value_Rs"] = perf["Piece_Value_Rs"].round(2)
            perf["Surplus_Deficit_Rs"] = (perf["Piece_Value_Rs"] - perf["Salary_Paid_Rs"]).round(2)
            perf["ROI_%"] = (perf["Piece_Value_Rs"] / perf["Salary_Paid_Rs"].replace(0,1) * 100).round(1)
            perf["Grade"] = perf["Avg_Efficiency_%"].apply(
                lambda x: "A – Excellent" if x>=100 else ("B – Good" if x>=85 else ("C – Average" if x>=70 else "D – Needs Improvement"))
            )

            c1,c2,c3 = st.columns(3)
            c1.metric("Piece Value", f"₹{perf['Piece_Value_Rs'].sum():,.0f}")
            c2.metric("Salary Paid", f"₹{perf['Salary_Paid_Rs'].sum():,.0f}")
            c3.metric("Surplus", f"₹{perf['Surplus_Deficit_Rs'].sum():,.0f}")

            st.dataframe(perf, use_container_width=True, hide_index=True)

with tab_master:
    st.markdown('<div class="section-header">⚙️ Master Data Management</div>', unsafe_allow_html=True)
    m1,m2,m3 = st.tabs(["👗 Style-Operation Master","👷 Karigar Master","🪪 Employee Master"])

    with m1:
        st.markdown('<div class="section-header">Style Operations</div>', unsafe_allow_html=True)
        import_section(key="style_master",
            required_cols=["Style","Operation","Target","Rate_Rs"],
            session_key="style_master",
            template_df=TEMPLATES["style_master"],
            label="Style Master")
        with st.expander("➕ Add Operation"):
            with st.form("style_op_form", clear_on_submit=True):
                s1,s2 = st.columns(2)
                with s1:
                    new_style  = st.text_input("Style Code", key="new_style_op")
                    new_op     = st.text_input("Operation Name", key="new_op_name")
                with s2:
                    new_target = st.number_input("Daily Target", min_value=1, step=1, key="new_tgt")
                    new_rate   = st.number_input("Rate/Piece", min_value=0.0, step=0.25, format="%.2f", key="new_rate")
                if st.form_submit_button("Add", use_container_width=True, key="add_op"):
                    st.session_state.style_master = pd.concat(
                        [st.session_state.style_master, pd.DataFrame([{
                            "Style":new_style,"Operation":new_op,"Target":new_target,"Rate_Rs":new_rate
                        }])], ignore_index=True)
                    st.success("Added!")
        st.dataframe(st.session_state.style_master, use_container_width=True, hide_index=True)

    with m2:
        st.markdown('<div class="section-header">Karigar Register</div>', unsafe_allow_html=True)
        import_section(key="karigar_master",
            required_cols=["Karigar_ID","Name","Skill","Daily_Rate_Rs"],
            session_key="karigar_master",
            template_df=TEMPLATES["karigar_master"],
            label="Karigar Master")
        with st.expander("➕ Add Karigar"):
            with st.form("karigar_form", clear_on_submit=True):
                k1,k2 = st.columns(2)
                with k1:
                    k_id   = st.text_input("Karigar ID", key="k_id")
                    k_name = st.text_input("Full Name", key="k_name")
                with k2:
                    k_skill = st.selectbox("Skill", ["Stitching","Cutting","Finishing","Hemming","Checking"], key="k_skill")
                    k_rate  = st.number_input("Daily Rate", min_value=100, step=10, key="k_rate")
                if st.form_submit_button("Add", use_container_width=True, key="add_kar"):
                    st.session_state.karigar_master = pd.concat(
                        [st.session_state.karigar_master, pd.DataFrame([{
                            "Karigar_ID":k_id,"Name":k_name,"Skill":k_skill,"Daily_Rate_Rs":k_rate
                        }])], ignore_index=True)
                    st.success("Added!")
        st.dataframe(st.session_state.karigar_master, use_container_width=True, hide_index=True)

    with m3:
        st.markdown('<div class="section-header">Employee Master (E-Code)</div>', unsafe_allow_html=True)
        import_section(key="employee_master",
            required_cols=["E_Code","Name","Type","Daily_Rate_Rs","Hourly_Rate_Rs"],
            session_key="employee_master",
            template_df=TEMPLATES["employee_master"],
            label="Employee Master")
        with st.expander("➕ Add Employee"):
            with st.form("emp_master_form", clear_on_submit=True):
                em1,em2 = st.columns(2)
                with em1:
                    em_code = st.text_input("E-Code", key="em_code")
                    em_name = st.text_input("Full Name", key="em_name")
                    em_type = st.selectbox("Type", ["Karigar","Operating"], key="em_type")
                with em2:
                    em_daily  = st.number_input("Daily Rate", min_value=100, step=10, value=400, key="em_daily")
                    em_hourly = st.number_input("Hourly Rate", value=round(400/8,2), step=0.5, format="%.2f", key="em_hourly")
                if st.form_submit_button("Add", use_container_width=True, key="add_emp"):
                    st.session_state.employee_master = pd.concat(
                        [st.session_state.employee_master, pd.DataFrame([{
                            "E_Code":em_code,"Name":em_name,"Type":em_type,
                            "Daily_Rate_Rs":em_daily,"Hourly_Rate_Rs":em_hourly
                        }])], ignore_index=True)
                    st.success("Added!")
        st.dataframe(st.session_state.employee_master, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("🧵 <b>Stitching Costing Interface</b> — Enhanced Karigar Management System v2.0", unsafe_allow_html=True)
