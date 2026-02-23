"""
Stitching Costing Interface - Streamlit App
Textile Garments Company - Karigar Time Tracking & Costing System
With Excel/CSV Import & Template Downloads for all sections
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import io

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
# Custom CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 20px 30px; border-radius: 12px;
        margin-bottom: 20px; color: white; text-align: center;
    }
    .main-header h1 { margin: 0; font-size: 2rem; letter-spacing: 1px; }
    .main-header p  { margin: 5px 0 0; opacity: 0.75; font-size: 0.95rem; }
    .metric-card {
        background: white; border-radius: 10px; padding: 18px 20px;
        border-left: 5px solid #0f3460;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 10px;
    }
    .metric-card .label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-card .value { font-size: 1.8rem; font-weight: 700; color: #1a1a2e; }
    .metric-card .sub   { font-size: 0.85rem; color: #0f3460; }
    .efficiency-high { color: #28a745 !important; }
    .efficiency-mid  { color: #ffc107 !important; }
    .efficiency-low  { color: #dc3545 !important; }
    .section-title {
        font-size: 1.1rem; font-weight: 700; color: #0f3460;
        border-bottom: 2px solid #e0e0e0; padding-bottom: 6px; margin-bottom: 16px;
    }
    .info-box {
        background: #f0f4ff; border-radius: 8px; padding: 12px 16px;
        border: 1px solid #c5d5ff; font-size: 0.9rem;
        color: #2c3e6e; margin-bottom: 12px;
    }
    .import-box {
        background: #fff8e1; border-radius: 8px; padding: 14px 18px;
        border: 1px solid #ffe082; margin-bottom: 14px;
    }
    div[data-testid="stTabs"] button { font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Helper: coerce columns to numeric safely
# ─────────────────────────────────────────────
def coerce_numeric(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

# ─────────────────────────────────────────────
# Helper: read uploaded file (CSV or Excel)
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
        import openpyxl  # noqa: F401
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Data")
        return buf.getvalue()
    except ImportError:
        return df.to_csv(index=False).encode("utf-8")

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def excel_available() -> bool:
    try:
        import openpyxl  # noqa: F401
        return True
    except ImportError:
        return False

# ─────────────────────────────────────────────
# Reusable Import Widget
# ─────────────────────────────────────────────
def import_section(key, required_cols, session_key, template_df, label):
    with st.expander(f"📥 Import {label} from Excel / CSV", expanded=False):
        st.markdown(
            f'<div class="import-box">'
            f'<b>Step 1:</b> Download the template &rarr; fill your data &rarr; upload it back.<br>'
            f'<b>Required columns:</b> <code>{", ".join(required_cols)}</code>'
            f'</div>', unsafe_allow_html=True
        )
        dl1, dl2 = st.columns(2)
        with dl1:
            try:
                import openpyxl  # noqa
                st.download_button(
                    "⬇️ Download Excel Template",
                    data=df_to_excel_bytes(template_df),
                    file_name=f"{key}_template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_xlsx_{key}"
                )
            except Exception:
                st.caption("Excel template unavailable — use CSV")
        with dl2:
            st.download_button(
                "⬇️ Download CSV Template",
                data=df_to_csv_bytes(template_df),
                file_name=f"{key}_template.csv",
                mime="text/csv",
                key=f"dl_csv_{key}"
            )

        uploaded = st.file_uploader(
            "📂 Upload your filled file (.csv or .xlsx)",
            type=["csv", "xlsx", "xls"],
            key=f"uploader_{key}"
        )
        mode = st.radio(
            "Import mode",
            ["➕ Append to existing data", "🔄 Replace all existing data"],
            key=f"mode_{key}"
        )

        if uploaded is not None:
            df_new = read_upload(uploaded)
            if df_new is not None:
                missing = [c for c in required_cols if c not in df_new.columns]
                if missing:
                    st.error(f"❌ Missing columns: {missing}. Check your file headers.")
                    return
                st.markdown("**Preview (first 5 rows):**")
                st.dataframe(df_new.head(), use_container_width=True, hide_index=True)
                st.info(f"✅ {len(df_new)} rows | {len(df_new.columns)} columns detected")

                if st.button(f"✅ Confirm Import into {label}", key=f"confirm_{key}"):
                    if "Replace" in mode:
                        st.session_state[session_key] = df_new.reset_index(drop=True)
                        st.success(f"🔄 Replaced! {len(df_new)} rows loaded.")
                    else:
                        st.session_state[session_key] = pd.concat(
                            [st.session_state[session_key], df_new], ignore_index=True
                        )
                        st.success(f"➕ Appended! {len(df_new)} new rows added.")
                    st.rerun()

# ─────────────────────────────────────────────
# Templates (sample rows for download)
# ─────────────────────────────────────────────
TEMPLATES = {
    "style_master": pd.DataFrame([
        {"Style": "1065YKBLUE", "Operation": "Cutting",        "Target": 120, "Rate_Rs": 2.50},
        {"Style": "1065YKBLUE", "Operation": "Stitching Front","Target": 80,  "Rate_Rs": 4.00},
        {"Style": "NEWSTYLE",   "Operation": "Hemming",        "Target": 100, "Rate_Rs": 3.00},
    ]),
    "karigar_master": pd.DataFrame([
        {"Karigar_ID": "K001", "Name": "Ramesh Kumar", "Skill": "Stitching", "Daily_Rate_Rs": 450},
        {"Karigar_ID": "K002", "Name": "Suresh Singh", "Skill": "Cutting",   "Daily_Rate_Rs": 420},
    ]),
    "challan_master": pd.DataFrame([
        {"Challan_No": "CH-001", "Style": "1065YKBLUE", "SKU": "YK-BLU-M", "Qty": 200, "Date": "2025-01-15"},
        {"Challan_No": "CH-002", "Style": "1065YKBLUE", "SKU": "YK-BLU-L", "Qty": 150, "Date": "2025-01-16"},
    ]),
    "time_log": pd.DataFrame([
        {"Date": "2025-01-15", "Karigar_ID": "K001", "Karigar_Name": "Ramesh Kumar",
         "Hour_Slot": "08:00-09:00", "Style": "1065YKBLUE", "Challan_No": "CH-001",
         "Operation": "Cutting", "Pieces_Done": 12},
        {"Date": "2025-01-15", "Karigar_ID": "K002", "Karigar_Name": "Suresh Singh",
         "Hour_Slot": "09:00-10:00", "Style": "1065YKBLUE", "Challan_No": "CH-001",
         "Operation": "Stitching Front", "Pieces_Done": 8},
    ]),
    "daily_sheet": pd.DataFrame([
        {"Date": "2025-01-15", "Karigar_ID": "K001", "Karigar_Name": "Ramesh Kumar",
         "Style": "1065YKBLUE", "Challan_No": "CH-001",
         "Operation": "Cutting", "Target": 120, "Achieved": 110, "Rate_Rs": 2.50},
        {"Date": "2025-01-15", "Karigar_ID": "K002", "Karigar_Name": "Suresh Singh",
         "Style": "1065YKBLUE", "Challan_No": "CH-001",
         "Operation": "Stitching Front", "Target": 80, "Achieved": 85, "Rate_Rs": 4.00},
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
    "style_running_log": pd.DataFrame([
        {"Date":"2025-01-15","Style":"1065YKBLUE","Hours_Run":5},
        {"Date":"2025-01-15","Style":"1066YKRED","Hours_Run":3},
    ]),
}

# ─────────────────────────────────────────────
# Session State Init
# ─────────────────────────────────────────────
def init_state():
    if "style_master" not in st.session_state:
        st.session_state.style_master = pd.DataFrame([
            {"Style": "1065YKBLUE", "Operation": "Cutting",        "Target": 120, "Rate_Rs": 2.50},
            {"Style": "1065YKBLUE", "Operation": "Stitching Front","Target": 80,  "Rate_Rs": 4.00},
            {"Style": "1065YKBLUE", "Operation": "Stitching Back", "Target": 80,  "Rate_Rs": 4.00},
            {"Style": "1065YKBLUE", "Operation": "Collar Attach",  "Target": 60,  "Rate_Rs": 5.50},
            {"Style": "1065YKBLUE", "Operation": "Sleeve Attach",  "Target": 60,  "Rate_Rs": 5.50},
            {"Style": "1065YKBLUE", "Operation": "Side Seam",      "Target": 90,  "Rate_Rs": 3.50},
            {"Style": "1065YKBLUE", "Operation": "Hemming",        "Target": 100, "Rate_Rs": 3.00},
            {"Style": "1065YKBLUE", "Operation": "Button Hole",    "Target": 110, "Rate_Rs": 2.00},
            {"Style": "1065YKBLUE", "Operation": "Button Attach",  "Target": 110, "Rate_Rs": 2.00},
            {"Style": "1065YKBLUE", "Operation": "Finishing",      "Target": 70,  "Rate_Rs": 4.50},
        ])
    if "karigar_master" not in st.session_state:
        st.session_state.karigar_master = pd.DataFrame([
            {"Karigar_ID": "K001", "Name": "Ramesh Kumar",  "Skill": "Stitching", "Daily_Rate_Rs": 450},
            {"Karigar_ID": "K002", "Name": "Suresh Singh",  "Skill": "Cutting",   "Daily_Rate_Rs": 420},
            {"Karigar_ID": "K003", "Name": "Priya Devi",    "Skill": "Finishing",  "Daily_Rate_Rs": 400},
            {"Karigar_ID": "K004", "Name": "Mohan Lal",     "Skill": "Stitching", "Daily_Rate_Rs": 460},
            {"Karigar_ID": "K005", "Name": "Sunita Sharma", "Skill": "Hemming",   "Daily_Rate_Rs": 410},
        ])
    if "challan_master" not in st.session_state:
        st.session_state.challan_master = pd.DataFrame([
            {"Challan_No": "CH-001", "Style": "1065YKBLUE", "SKU": "YK-BLU-M",  "Qty": 200, "Date": "2025-01-15"},
            {"Challan_No": "CH-002", "Style": "1065YKBLUE", "SKU": "YK-BLU-L",  "Qty": 150, "Date": "2025-01-16"},
            {"Challan_No": "CH-003", "Style": "1065YKBLUE", "SKU": "YK-BLU-XL", "Qty": 100, "Date": "2025-01-17"},
        ])
    if "time_log" not in st.session_state:
        st.session_state.time_log = pd.DataFrame(columns=[
            "Date","Karigar_ID","Karigar_Name","Hour_Slot",
            "Style","Challan_No","Operation","Pieces_Done"
        ])
    if "daily_sheet" not in st.session_state:
        st.session_state.daily_sheet = pd.DataFrame(columns=[
            "Date","Karigar_ID","Karigar_Name",
            "Style","Challan_No","Operation",
            "Target","Achieved","Rate_Rs"
        ])
    if "employee_master" not in st.session_state:
        st.session_state.employee_master = pd.DataFrame([
            {"E_Code":"E001","Name":"Ramesh Kumar",  "Type":"Karigar",  "Daily_Rate_Rs":450,"Hourly_Rate_Rs":56.25},
            {"E_Code":"E002","Name":"Suresh Singh",  "Type":"Karigar",  "Daily_Rate_Rs":420,"Hourly_Rate_Rs":52.50},
            {"E_Code":"E003","Name":"Priya Devi",    "Type":"Karigar",  "Daily_Rate_Rs":400,"Hourly_Rate_Rs":50.00},
            {"E_Code":"E004","Name":"Mohan Lal",     "Type":"Karigar",  "Daily_Rate_Rs":460,"Hourly_Rate_Rs":57.50},
            {"E_Code":"E005","Name":"Sunita Sharma", "Type":"Karigar",  "Daily_Rate_Rs":410,"Hourly_Rate_Rs":51.25},
            {"E_Code":"E101","Name":"Amit Sharma",   "Type":"Operating","Daily_Rate_Rs":600,"Hourly_Rate_Rs":75.00},
            {"E_Code":"E102","Name":"Kavita Rao",    "Type":"Operating","Daily_Rate_Rs":550,"Hourly_Rate_Rs":68.75},
        ])
    if "karigar_attendance" not in st.session_state:
        st.session_state.karigar_attendance = pd.DataFrame(columns=[
            "Date","E_Code","Name","In_Punch","Out_Punch",
            "Total_Hours","Productive_Hours","Day_Type",
            "Basic_Pay","OT_Hours","OT_Pay","Total_Pay"
        ])
    if "operating_attendance" not in st.session_state:
        st.session_state.operating_attendance = pd.DataFrame(columns=[
            "Date","E_Code","Name","In_Punch","Out_Punch",
            "Total_Hours","Hourly_Rate_Rs","Total_Pay"
        ])
    if "style_running_log" not in st.session_state:
        st.session_state.style_running_log = pd.DataFrame(columns=[
            "Date","Style","Hours_Run","Percentage"
        ])

init_state()

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🧵 Stitching Costing Interface</h1>
    <p>Karigar Time Tracking · Challan-wise Costing · Efficiency Analysis · Payroll · Import/Export</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tabs = st.tabs([
    "🏠 Dashboard",
    "⏱️ Hour-wise Time Log",
    "📋 Karigar Daily Sheet",
    "🧾 Challan Management",
    "📊 Efficiency & Costing",
    "💰 Payroll Calculator",
    "🕐 Karigar Salary & Attendance",
    "🏢 Operating Staff",
    "🌟 Employee Performance",
    "⚙️ Master Data",
])
tab_dash, tab_timelog, tab_daily, tab_challan, tab_efficiency, tab_payroll, tab_salary, tab_operating, tab_performance, tab_master = tabs

# ════════════════════════════════════════════════════════════
# TAB 1 – DASHBOARD
# ════════════════════════════════════════════════════════════
with tab_dash:
    st.markdown('<div class="section-title">📈 Today\'s Overview</div>', unsafe_allow_html=True)

    today_str   = str(date.today())
    today_log   = st.session_state.time_log[st.session_state.time_log["Date"] == today_str]

    # Coerce numeric columns for daily_sheet before using
    _ds_raw = st.session_state.daily_sheet.copy()
    _ds_raw = coerce_numeric(_ds_raw, ["Target", "Achieved", "Rate_Rs"])
    today_daily = _ds_raw[_ds_raw["Date"] == today_str]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        active = today_log["Karigar_ID"].nunique() if not today_log.empty else 0
        st.markdown(f"""<div class="metric-card">
            <div class="label">Active Karigar Today</div>
            <div class="value">{active}</div>
            <div class="sub">of {len(st.session_state.karigar_master)} total</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        _tl = st.session_state.time_log.copy()
        _tl = coerce_numeric(_tl, ["Pieces_Done"])
        _tl_today = _tl[_tl["Date"] == today_str]
        pieces = int(_tl_today["Pieces_Done"].sum()) if not _tl_today.empty else 0
        st.markdown(f"""<div class="metric-card">
            <div class="label">Pieces Done Today</div>
            <div class="value">{pieces}</div>
            <div class="sub">across all operations</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        if not today_daily.empty and "Target" in today_daily and "Achieved" in today_daily:
            _targets = today_daily["Target"].replace(0, np.nan)
            avg_eff = (today_daily["Achieved"] / _targets * 100).mean()
            avg_eff = avg_eff if not np.isnan(avg_eff) else 0
            ec = "efficiency-high" if avg_eff >= 90 else ("efficiency-mid" if avg_eff >= 70 else "efficiency-low")
        else:
            avg_eff, ec = 0, "efficiency-low"
        st.markdown(f"""<div class="metric-card">
            <div class="label">Avg Efficiency</div>
            <div class="value {ec}">{avg_eff:.1f}%</div>
            <div class="sub">Target: 100%</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        cost = (today_daily["Achieved"] * today_daily["Rate_Rs"]).sum() if not today_daily.empty else 0
        st.markdown(f"""<div class="metric-card">
            <div class="label">Today's Labour Cost</div>
            <div class="value">&#8377;{cost:,.0f}</div>
            <div class="sub">piece-rate earned</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    cola, colb = st.columns(2)
    with cola:
        st.markdown('<div class="section-title">👷 Karigar Status</div>', unsafe_allow_html=True)
        km = st.session_state.karigar_master.copy()
        active_ids = today_log["Karigar_ID"].unique().tolist() if not today_log.empty else []
        km["Status"] = km["Karigar_ID"].apply(lambda x: "🟢 Working" if x in active_ids else "⚪ Idle")
        st.dataframe(km[["Karigar_ID","Name","Skill","Status"]], use_container_width=True, hide_index=True)
    with colb:
        st.markdown('<div class="section-title">🧾 Active Challans</div>', unsafe_allow_html=True)
        st.dataframe(st.session_state.challan_master, use_container_width=True, hide_index=True)

    if not today_daily.empty:
        st.markdown("---")
        st.markdown('<div class="section-title">📋 Today\'s Daily Sheet Summary</div>', unsafe_allow_html=True)
        ds = today_daily.copy()
        if "Achieved" in ds and "Target" in ds:
            ds["Efficiency_%"] = (ds["Achieved"] / ds["Target"].replace(0, np.nan) * 100).round(1).fillna(0)
            ds["Earned_Rs"]    = (ds["Achieved"] * ds["Rate_Rs"]).round(2)
        st.dataframe(ds, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════
# TAB 2 – HOUR-WISE TIME LOG
# ════════════════════════════════════════════════════════════
with tab_timelog:
    st.markdown('<div class="section-title">⏱️ Hour-wise Time Entry</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Log which karigar worked on which style/challan each hour of the 11-hour shift (8 AM to 7 PM).</div>', unsafe_allow_html=True)

    import_section(
        key="time_log",
        required_cols=["Date","Karigar_ID","Karigar_Name","Hour_Slot","Style","Challan_No","Operation","Pieces_Done"],
        session_key="time_log",
        template_df=TEMPLATES["time_log"],
        label="Hour-wise Time Log"
    )

    hour_slots   = [f"{h:02d}:00-{h+1:02d}:00" for h in range(8, 19)]
    styles_list  = st.session_state.style_master["Style"].unique().tolist()
    challan_list = st.session_state.challan_master["Challan_No"].tolist()
    karigar_options = {
        f"{r['Karigar_ID']} - {r['Name']}": (r['Karigar_ID'], r['Name'])
        for _, r in st.session_state.karigar_master.iterrows()
    }

    with st.expander("✏️ Manual Entry", expanded=True):
        with st.form("time_log_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                tl_date    = st.date_input("Date", value=date.today())
                tl_karigar = st.selectbox("Karigar", list(karigar_options.keys()))
                tl_hour    = st.selectbox("Hour Slot", hour_slots)
            with c2:
                tl_style   = st.selectbox("Style", styles_list) if styles_list else st.text_input("Style")
                tl_challan = st.selectbox("Challan No", challan_list) if challan_list else st.text_input("Challan No")
            with c3:
                ops = st.session_state.style_master[
                    st.session_state.style_master["Style"] == tl_style
                ]["Operation"].tolist() if styles_list else []
                tl_op     = st.selectbox("Operation", ops) if ops else st.text_input("Operation")
                tl_pieces = st.number_input("Pieces Done", min_value=0, step=1)

            if st.form_submit_button("Save Time Entry", use_container_width=True):
                kid, kname = karigar_options[tl_karigar]
                new_row = {
                    "Date": str(tl_date), "Karigar_ID": kid, "Karigar_Name": kname,
                    "Hour_Slot": tl_hour, "Style": tl_style, "Challan_No": tl_challan,
                    "Operation": tl_op, "Pieces_Done": tl_pieces
                }
                st.session_state.time_log = pd.concat(
                    [st.session_state.time_log, pd.DataFrame([new_row])], ignore_index=True
                )
                st.success(f"Saved: {kname} | {tl_hour} | {tl_op} | {tl_pieces} pcs")

    st.markdown("---")
    st.markdown('<div class="section-title">Time Log Records</div>', unsafe_allow_html=True)
    if not st.session_state.time_log.empty:
        tl_filter = st.date_input("Filter by Date", value=date.today(), key="tl_filter")
        _tl_all = st.session_state.time_log.copy()
        _tl_all = coerce_numeric(_tl_all, ["Pieces_Done"])
        filtered  = _tl_all[_tl_all["Date"] == str(tl_filter)]
        if not filtered.empty:
            st.dataframe(filtered, use_container_width=True, hide_index=True)
            try:
                pivot = filtered.pivot_table(
                    index="Karigar_Name", columns="Hour_Slot",
                    values="Pieces_Done", aggfunc="sum", fill_value=0
                )
                st.markdown('<div class="section-title">Hour-wise Heatmap</div>', unsafe_allow_html=True)
                st.dataframe(pivot.style.background_gradient(cmap="Blues"), use_container_width=True)
            except Exception:
                pass
            ex1, ex2 = st.columns(2)
            with ex1:
                st.download_button("📥 Export Excel", data=df_to_excel_bytes(filtered),
                    file_name="time_log_export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with ex2:
                st.download_button("📥 Export CSV", data=df_to_csv_bytes(filtered),
                    file_name="time_log_export.csv", mime="text/csv")
        else:
            st.info("No entries for selected date.")
    else:
        st.info("No time log entries yet. Use import or manual entry above.")


# ════════════════════════════════════════════════════════════
# TAB 3 – KARIGAR DAILY SHEET
# ════════════════════════════════════════════════════════════
with tab_daily:
    st.markdown('<div class="section-title">📋 Karigar Daily Sheet - Operation-wise</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Enter daily production per karigar per operation. Target and rate are auto-fetched from master data.</div>', unsafe_allow_html=True)

    import_section(
        key="daily_sheet",
        required_cols=["Date","Karigar_ID","Karigar_Name","Style","Challan_No","Operation","Target","Achieved","Rate_Rs"],
        session_key="daily_sheet",
        template_df=TEMPLATES["daily_sheet"],
        label="Karigar Daily Sheet"
    )

    karigar_opts2 = {
        f"{r['Karigar_ID']} - {r['Name']}": (r['Karigar_ID'], r['Name'])
        for _, r in st.session_state.karigar_master.iterrows()
    }
    styles_list2  = st.session_state.style_master["Style"].unique().tolist()
    challan_list2 = st.session_state.challan_master["Challan_No"].tolist()

    with st.expander("✏️ Manual Entry", expanded=True):
        with st.form("daily_sheet_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                ds_date    = st.date_input("Date", value=date.today())
                ds_karigar = st.selectbox("Karigar", list(karigar_opts2.keys()))
                ds_style   = st.selectbox("Style", styles_list2) if styles_list2 else st.text_input("Style")
            with c2:
                ds_challan = st.selectbox("Challan No", challan_list2) if challan_list2 else st.text_input("Challan")
                ds_ops = st.session_state.style_master[
                    st.session_state.style_master["Style"] == ds_style
                ][["Operation","Target","Rate_Rs"]] if styles_list2 else pd.DataFrame()
                ds_op = st.selectbox("Operation", ds_ops["Operation"].tolist()) if not ds_ops.empty else st.text_input("Operation")

            op_row   = ds_ops[ds_ops["Operation"] == ds_op] if not ds_ops.empty else pd.DataFrame()
            tgt_val  = int(op_row["Target"].values[0])    if not op_row.empty else 0
            rate_val = float(op_row["Rate_Rs"].values[0]) if not op_row.empty else 0.0
            st.info(f"Target: {tgt_val} pcs | Rate: Rs {rate_val}/pc")
            ds_achieved = st.number_input("Pieces Achieved", min_value=0, step=1)

            if st.form_submit_button("Save Daily Entry", use_container_width=True):
                kid2, kname2 = karigar_opts2[ds_karigar]
                eff = (ds_achieved / tgt_val * 100) if tgt_val > 0 else 0
                new_ds = {
                    "Date": str(ds_date), "Karigar_ID": kid2, "Karigar_Name": kname2,
                    "Style": ds_style, "Challan_No": ds_challan,
                    "Operation": ds_op, "Target": tgt_val,
                    "Achieved": ds_achieved, "Rate_Rs": rate_val
                }
                st.session_state.daily_sheet = pd.concat(
                    [st.session_state.daily_sheet, pd.DataFrame([new_ds])], ignore_index=True
                )
                st.success(f"Saved! Efficiency: {eff:.1f}% | Earned: Rs {ds_achieved * rate_val:.2f}")

    st.markdown("---")
    if not st.session_state.daily_sheet.empty:
        st.markdown('<div class="section-title">Daily Sheet Records</div>', unsafe_allow_html=True)
        ds_filter   = st.date_input("Filter by Date", value=date.today(), key="ds_filter")
        _ds_all = st.session_state.daily_sheet.copy()
        _ds_all = coerce_numeric(_ds_all, ["Target", "Achieved", "Rate_Rs"])
        ds_filtered = _ds_all[_ds_all["Date"] == str(ds_filter)].copy()

        if not ds_filtered.empty:
            ds_filtered["Efficiency_%"] = (
                ds_filtered["Achieved"] / ds_filtered["Target"].replace(0, np.nan) * 100
            ).round(1).fillna(0)
            ds_filtered["Earned_Rs"]   = (ds_filtered["Achieved"] * ds_filtered["Rate_Rs"]).round(2)
            ds_filtered["Status"] = ds_filtered["Efficiency_%"].apply(
                lambda x: "On Target" if x >= 100 else ("Near Target" if x >= 80 else "Below Target")
            )
            st.dataframe(ds_filtered, use_container_width=True, hide_index=True)

            ks = ds_filtered.groupby("Karigar_Name").agg(
                Ops=("Operation","count"),
                Total_Target=("Target","sum"),
                Total_Achieved=("Achieved","sum"),
                Total_Earned_Rs=("Earned_Rs","sum")
            ).reset_index()
            ks["Overall_Eff_%"] = (
                ks["Total_Achieved"] / ks["Total_Target"].replace(0, np.nan) * 100
            ).round(1).fillna(0)
            st.markdown('<div class="section-title">Karigar Summary</div>', unsafe_allow_html=True)
            st.dataframe(ks, use_container_width=True, hide_index=True)

            ex1, ex2 = st.columns(2)
            with ex1:
                st.download_button("📥 Export Excel", data=df_to_excel_bytes(ds_filtered),
                    file_name="daily_sheet_export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with ex2:
                st.download_button("📥 Export CSV", data=df_to_csv_bytes(ds_filtered),
                    file_name="daily_sheet_export.csv", mime="text/csv")
        else:
            st.info("No entries for selected date.")
    else:
        st.info("No daily sheet entries yet.")


# ════════════════════════════════════════════════════════════
# TAB 4 – CHALLAN MANAGEMENT
# ════════════════════════════════════════════════════════════
with tab_challan:
    st.markdown('<div class="section-title">🧾 Challan-wise Style Costing</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Each Style can have multiple Challans (batches). Track costing per challan.</div>', unsafe_allow_html=True)

    import_section(
        key="challan_master",
        required_cols=["Challan_No","Style","SKU","Qty","Date"],
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
                c_sku  = st.text_input("SKU")
                c_qty  = st.number_input("Quantity", min_value=1, step=1)
            with cc3:
                c_date = st.date_input("Challan Date", value=date.today())
            if st.form_submit_button("Add Challan") and c_no:
                new_c = {"Challan_No": c_no, "Style": c_style, "SKU": c_sku, "Qty": int(c_qty), "Date": str(c_date)}
                st.session_state.challan_master = pd.concat(
                    [st.session_state.challan_master, pd.DataFrame([new_c])], ignore_index=True
                )
                st.success(f"Challan {c_no} added!")

    st.markdown("---")
    st.dataframe(st.session_state.challan_master, use_container_width=True, hide_index=True)

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

    st.markdown('<div class="section-title">Challan-wise Costing Report</div>', unsafe_allow_html=True)
    if not st.session_state.daily_sheet.empty and not st.session_state.challan_master.empty:
        cc = st.session_state.daily_sheet.copy()
        cc = coerce_numeric(cc, ["Achieved", "Rate_Rs"])
        cc["Earned_Rs"] = cc["Achieved"] * cc["Rate_Rs"]
        ch_summary = cc.groupby(["Style","Challan_No","Operation"]).agg(
            Total_Achieved=("Achieved","sum"),
            Total_Earned_Rs=("Earned_Rs","sum")
        ).reset_index()

        sel_challan = st.selectbox("Select Challan to View Costing",
            st.session_state.challan_master["Challan_No"].tolist())
        ch_view = ch_summary[ch_summary["Challan_No"] == sel_challan]
        if not ch_view.empty:
            st.dataframe(ch_view, use_container_width=True, hide_index=True)
            total_ch = ch_view["Total_Earned_Rs"].sum()
            qty_row  = st.session_state.challan_master[st.session_state.challan_master["Challan_No"] == sel_challan]
            qty      = int(qty_row["Qty"].values[0]) if not qty_row.empty else 1
            col_x, col_y = st.columns(2)
            col_x.metric("Total Labour Cost", f"Rs {total_ch:,.2f}")
            col_y.metric("Cost per Piece",    f"Rs {total_ch / max(qty, 1):.2f}")
        else:
            st.info("No production data for this challan yet.")
    else:
        st.info("Add daily sheet entries to see challan-wise costing.")


# ════════════════════════════════════════════════════════════
# TAB 5 – EFFICIENCY & COSTING
# ════════════════════════════════════════════════════════════
with tab_efficiency:
    st.markdown('<div class="section-title">📊 Efficiency & Deep Analysis</div>', unsafe_allow_html=True)

    if st.session_state.daily_sheet.empty:
        st.info("No data yet. Fill in the Karigar Daily Sheet to see analysis here.")
    else:
        df = st.session_state.daily_sheet.copy()
        # FIX: coerce numeric columns before any calculations
        df = coerce_numeric(df, ["Achieved", "Target", "Rate_Rs"])
        df["Efficiency_%"] = (df["Achieved"] / df["Target"].replace(0, np.nan) * 100).round(1).fillna(0)
        df["Earned_Rs"]    = (df["Achieved"] * df["Rate_Rs"]).round(2)
        df["Date"]         = pd.to_datetime(df["Date"])

        f1, f2 = st.columns(2)
        with f1:
            date_range = st.date_input("Date Range",
                value=[date.today() - timedelta(days=7), date.today()])
        with f2:
            style_filter = st.multiselect("Filter Style",
                df["Style"].unique().tolist(), default=df["Style"].unique().tolist())

        if len(date_range) == 2:
            mask = (
                (df["Date"] >= pd.Timestamp(date_range[0])) &
                (df["Date"] <= pd.Timestamp(date_range[1])) &
                (df["Style"].isin(style_filter))
            )
            df_f = df[mask].copy()
        else:
            df_f = df[df["Style"].isin(style_filter)].copy()

        if df_f.empty:
            st.warning("No data for selected filters.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Avg Efficiency",  f"{df_f['Efficiency_%'].mean():.1f}%")
            c2.metric("Total Earned",    f"Rs {df_f['Earned_Rs'].sum():,.0f}")
            c3.metric("Total Pieces",    f"{int(df_f['Achieved'].sum()):,}")
            st.markdown("---")

            st.markdown('<div class="section-title">Karigar-wise Efficiency</div>', unsafe_allow_html=True)
            karigar_eff = df_f.groupby("Karigar_Name").agg(
                Avg_Efficiency=("Efficiency_%","mean"),
                Total_Achieved=("Achieved","sum"),
                Total_Earned_Rs=("Earned_Rs","sum"),
                Ops_Done=("Operation","count")
            ).round(2).reset_index()
            karigar_eff["Grade"] = karigar_eff["Avg_Efficiency"].apply(
                lambda x: "A - Excellent" if x >= 100 else ("B - Good" if x >= 85 else ("C - Average" if x >= 70 else "D - Below Target"))
            )
            st.dataframe(karigar_eff, use_container_width=True, hide_index=True)

            st.markdown('<div class="section-title">Operation-wise Performance</div>', unsafe_allow_html=True)
            op_eff = df_f.groupby("Operation").agg(
                Avg_Efficiency=("Efficiency_%","mean"),
                Total_Achieved=("Achieved","sum"),
                Total_Cost_Rs=("Earned_Rs","sum")
            ).round(2).reset_index().sort_values("Avg_Efficiency")
            st.dataframe(op_eff, use_container_width=True, hide_index=True)
            bottleneck = op_eff[op_eff["Avg_Efficiency"] < 80]
            if not bottleneck.empty:
                st.warning(f"Bottleneck Operations (below 80%): {', '.join(bottleneck['Operation'].tolist())}")

            st.markdown('<div class="section-title">Style-wise Labour Costing</div>', unsafe_allow_html=True)
            style_cost = df_f.groupby(["Style","Operation"]).agg(
                Total_Pieces=("Achieved","sum"),
                Total_Cost_Rs=("Earned_Rs","sum")
            ).reset_index()
            st.dataframe(style_cost, use_container_width=True, hide_index=True)

            total_by_style = style_cost.groupby("Style")["Total_Cost_Rs"].sum().reset_index()
            total_by_style.columns = ["Style","Total_Labour_Cost_Rs"]
            st.dataframe(total_by_style, use_container_width=True, hide_index=True)

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
# TAB 6 – PAYROLL CALCULATOR
# ════════════════════════════════════════════════════════════
with tab_payroll:
    st.markdown('<div class="section-title">💰 Karigar Payroll Calculator</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Pays the higher of piece-rate earned vs daily rate guarantee. 5% bonus if karigar earns more than 120% of guaranteed pay.</div>', unsafe_allow_html=True)

    p1, p2 = st.columns(2)
    with p1: pay_start = st.date_input("Pay Period Start", value=date.today() - timedelta(days=6))
    with p2: pay_end   = st.date_input("Pay Period End",   value=date.today())

    if st.button("Calculate Payroll", use_container_width=True):
        if st.session_state.daily_sheet.empty:
            st.warning("No daily sheet data available.")
        else:
            df_pay = st.session_state.daily_sheet.copy()
            # FIX: coerce numeric before calculations
            df_pay = coerce_numeric(df_pay, ["Achieved", "Rate_Rs"])
            df_pay["Date_dt"] = pd.to_datetime(df_pay["Date"])
            df_pay = df_pay[
                (df_pay["Date_dt"] >= pd.Timestamp(pay_start)) &
                (df_pay["Date_dt"] <= pd.Timestamp(pay_end))
            ]
            if df_pay.empty:
                st.warning("No data in this pay period.")
            else:
                df_pay["Piece_Earned"] = df_pay["Achieved"] * df_pay["Rate_Rs"]
                days = (pay_end - pay_start).days + 1
                payroll = df_pay.groupby("Karigar_ID").agg(
                    Total_Piece_Earned=("Piece_Earned","sum"),
                    Total_Pieces=("Achieved","sum")
                ).reset_index()
                km = st.session_state.karigar_master[["Karigar_ID","Name","Daily_Rate_Rs"]]
                km = km.copy()
                km = coerce_numeric(km, ["Daily_Rate_Rs"])
                payroll = payroll.merge(km, on="Karigar_ID", how="left")
                payroll["Guaranteed_Pay"]   = payroll["Daily_Rate_Rs"] * days
                payroll["Final_Pay_Rs"]     = payroll[["Total_Piece_Earned","Guaranteed_Pay"]].max(axis=1)
                payroll["Pay_Basis"]        = payroll.apply(
                    lambda r: "Piece-rate" if r["Total_Piece_Earned"] >= r["Guaranteed_Pay"] else "Daily-rate", axis=1
                )
                payroll["Efficiency_Bonus"] = 0.0
                payroll.loc[
                    payroll["Total_Piece_Earned"] > payroll["Guaranteed_Pay"] * 1.2,
                    "Efficiency_Bonus"
                ] = payroll["Final_Pay_Rs"] * 0.05
                payroll["Total_with_Bonus"] = payroll["Final_Pay_Rs"] + payroll["Efficiency_Bonus"]

                disp = payroll[["Name","Total_Pieces","Total_Piece_Earned","Guaranteed_Pay",
                                "Final_Pay_Rs","Efficiency_Bonus","Total_with_Bonus","Pay_Basis"]].round(2)
                st.dataframe(disp, use_container_width=True, hide_index=True)
                st.metric("Total Payroll", f"Rs {disp['Total_with_Bonus'].sum():,.2f}")

                ex1, ex2 = st.columns(2)
                with ex1:
                    st.download_button("📥 Download Payroll (Excel)",
                        data=df_to_excel_bytes(disp),
                        file_name=f"payroll_{pay_start}_{pay_end}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                with ex2:
                    st.download_button("📥 Download Payroll (CSV)",
                        data=df_to_csv_bytes(disp),
                        file_name=f"payroll_{pay_start}_{pay_end}.csv", mime="text/csv")


# ════════════════════════════════════════════════════════════
# TAB 7 – KARIGAR SALARY & ATTENDANCE
# ════════════════════════════════════════════════════════════
with tab_salary:
    st.markdown('<div class="section-title">🕐 Karigar Salary - Attendance & Auto Calculation</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Shift: 9 AM - 6 PM (9 hrs). Deductions: 30 min lunch + 15 min tea + 15 min non-productive = 1 hr. Salary paid on 8 hr basis.<br>Rule: Work 9 AM - 3 PM = Full Day. Work 9 AM - 1 PM = Half Day. OT after 6 PM at hourly rate.</div>', unsafe_allow_html=True)

    def calculate_karigar_salary(e_code, in_punch_str, out_punch_str, daily_rate):
        try:
            fmt = "%H:%M"
            t_in  = datetime.strptime(in_punch_str.strip(), fmt)
            t_out = datetime.strptime(out_punch_str.strip(), fmt)
            shift_end   = datetime.strptime("18:00", fmt)
            half_day_cutoff = datetime.strptime("13:00", fmt)
            full_day_cutoff = datetime.strptime("15:00", fmt)

            total_mins = max((t_out - t_in).seconds // 60, 0)
            total_hrs  = round(total_mins / 60, 2)

            productive_hrs = max(total_hrs - 1.0, 0) if total_hrs >= 8 else total_hrs

            if t_out <= half_day_cutoff:
                day_type  = "Half Day"
                basic_pay = daily_rate * 0.5
            elif t_out >= full_day_cutoff:
                day_type  = "Full Day"
                basic_pay = daily_rate
            else:
                day_type  = "Partial (between half & full)"
                basic_pay = daily_rate * 0.75

            ot_mins = max((t_out - shift_end).seconds // 60, 0) if t_out > shift_end else 0
            ot_hrs  = min(round(ot_mins / 60, 2), 3.0)
            hourly_rate = daily_rate / 8
            ot_pay  = round(ot_hrs * hourly_rate, 2)
            total_pay = round(basic_pay + ot_pay, 2)

            return total_hrs, productive_hrs, day_type, round(basic_pay,2), ot_hrs, ot_pay, total_pay
        except Exception:
            return 0, 0, "Error", 0, 0, 0, 0

    import_section(
        key="karigar_attendance",
        required_cols=["Date","E_Code","In_Punch","Out_Punch"],
        session_key="karigar_attendance",
        template_df=TEMPLATES["karigar_attendance"],
        label="Karigar Attendance (In/Out Punch)"
    )

    if not st.session_state.karigar_attendance.empty and "Total_Pay" not in st.session_state.karigar_attendance.columns:
        emp = st.session_state.employee_master.copy()
        emp = coerce_numeric(emp, ["Daily_Rate_Rs", "Hourly_Rate_Rs"])
        att = st.session_state.karigar_attendance.copy()
        rows = []
        for _, row in att.iterrows():
            emp_row = emp[emp["E_Code"] == row["E_Code"]]
            if not emp_row.empty:
                dr = float(emp_row["Daily_Rate_Rs"].values[0])
                name = emp_row["Name"].values[0]
                th, ph, dt, bp, oth, otp, tp = calculate_karigar_salary(
                    row["E_Code"], str(row["In_Punch"]), str(row["Out_Punch"]), dr
                )
                rows.append({**row, "Name": name, "Total_Hours": th, "Productive_Hours": ph,
                              "Day_Type": dt, "Basic_Pay": bp, "OT_Hours": oth, "OT_Pay": otp, "Total_Pay": tp})
            else:
                rows.append(row.to_dict())
        st.session_state.karigar_attendance = pd.DataFrame(rows)
        st.rerun()

    with st.expander("✏️ Manual Attendance Entry", expanded=True):
        emp_karigar = st.session_state.employee_master[
            st.session_state.employee_master["Type"] == "Karigar"
        ]
        emp_opts = {f"{r['E_Code']} - {r['Name']}": r for _, r in emp_karigar.iterrows()}

        with st.form("salary_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                att_date = st.date_input("Date", value=date.today())
                emp_sel  = st.selectbox("Employee (E Code)", list(emp_opts.keys()))
            with c2:
                in_punch  = st.text_input("In Punch (HH:MM)", value="09:00")
                out_punch = st.text_input("Out Punch (HH:MM)", value="18:00")
            with c3:
                emp_row = emp_opts[emp_sel]
                dr = float(emp_row["Daily_Rate_Rs"])
                st.info(f"Daily Rate: Rs {dr} | Hourly: Rs {dr/8:.2f}")

            if st.form_submit_button("Calculate & Save", use_container_width=True):
                th, ph, dt, bp, oth, otp, tp = calculate_karigar_salary(
                    emp_row["E_Code"], in_punch, out_punch, dr
                )
                new_att = {
                    "Date": str(att_date), "E_Code": emp_row["E_Code"],
                    "Name": emp_row["Name"], "In_Punch": in_punch, "Out_Punch": out_punch,
                    "Total_Hours": th, "Productive_Hours": ph, "Day_Type": dt,
                    "Basic_Pay": bp, "OT_Hours": oth, "OT_Pay": otp, "Total_Pay": tp
                }
                st.session_state.karigar_attendance = pd.concat(
                    [st.session_state.karigar_attendance, pd.DataFrame([new_att])], ignore_index=True
                )
                st.success(f"Saved! {emp_row['Name']} | {dt} | Basic: Rs {bp} | OT: Rs {otp} | Total: Rs {tp}")

    st.markdown("---")
    st.markdown('<div class="section-title">Attendance Records</div>', unsafe_allow_html=True)
    if not st.session_state.karigar_attendance.empty:
        att_filter = st.date_input("Filter by Date", value=date.today(), key="att_filter")
        _att_all = st.session_state.karigar_attendance.copy()
        _att_all = coerce_numeric(_att_all, ["Total_Hours","Productive_Hours","Basic_Pay","OT_Hours","OT_Pay","Total_Pay"])
        att_view = _att_all[_att_all["Date"] == str(att_filter)]
        if not att_view.empty:
            st.dataframe(att_view, use_container_width=True, hide_index=True)
            total_salary_day = att_view["Total_Pay"].sum() if "Total_Pay" in att_view.columns else 0
            st.metric("Total Salary Payout for Day", f"Rs {total_salary_day:,.2f}")
        else:
            st.info("No attendance for selected date.")

        st.markdown('<div class="section-title">Monthly Summary</div>', unsafe_allow_html=True)
        att_all = st.session_state.karigar_attendance.copy()
        att_all = coerce_numeric(att_all, ["Basic_Pay","OT_Hours","OT_Pay","Total_Pay"])
        if "Total_Pay" in att_all.columns and "Name" in att_all.columns:
            monthly = att_all.groupby("E_Code").agg(
                Name=("Name","first"),
                Days_Present=("Date","nunique"),
                Full_Days=("Day_Type", lambda x: (x=="Full Day").sum()),
                Half_Days=("Day_Type", lambda x: (x=="Half Day").sum()),
                Total_OT_Hrs=("OT_Hours","sum"),
                Total_Basic=("Basic_Pay","sum"),
                Total_OT_Pay=("OT_Pay","sum"),
                Total_Pay=("Total_Pay","sum"),
            ).round(2).reset_index()
            st.dataframe(monthly, use_container_width=True, hide_index=True)

        ex1, ex2 = st.columns(2)
        with ex1:
            st.download_button("📥 Export Attendance (Excel)",
                data=df_to_excel_bytes(st.session_state.karigar_attendance),
                file_name="karigar_attendance.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with ex2:
            st.download_button("📥 Export Attendance (CSV)",
                data=df_to_csv_bytes(st.session_state.karigar_attendance),
                file_name="karigar_attendance.csv", mime="text/csv")
    else:
        st.info("No attendance records yet.")


# ════════════════════════════════════════════════════════════
# TAB 8 – OPERATING STAFF
# ════════════════════════════════════════════════════════════
with tab_operating:
    st.markdown('<div class="section-title">🏢 Operating Staff Attendance & Cost Allocation</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Operating staff cost is NOT added per style directly. Cost is split across styles run that day in proportion to their running hours.</div>', unsafe_allow_html=True)

    col_op, col_style = st.columns(2)

    with col_op:
        st.markdown('<div class="section-title">Operating Staff In/Out</div>', unsafe_allow_html=True)

        import_section(
            key="operating_attendance",
            required_cols=["Date","E_Code","In_Punch","Out_Punch"],
            session_key="operating_attendance",
            template_df=TEMPLATES["operating_attendance"],
            label="Operating Staff Attendance"
        )

        emp_op = st.session_state.employee_master[
            st.session_state.employee_master["Type"] == "Operating"
        ]
        op_opts = {f"{r['E_Code']} - {r['Name']}": r for _, r in emp_op.iterrows()}

        with st.expander("✏️ Manual Entry - Operating Staff", expanded=True):
            with st.form("op_attend_form", clear_on_submit=True):
                oa_date    = st.date_input("Date", value=date.today(), key="oa_date")
                oa_emp     = st.selectbox("Employee", list(op_opts.keys()))
                oa_in      = st.text_input("In Punch (HH:MM)", value="09:00", key="oa_in")
                oa_out     = st.text_input("Out Punch (HH:MM)", value="18:00", key="oa_out")
                if st.form_submit_button("Save", use_container_width=True):
                    er = op_opts[oa_emp]
                    try:
                        fmt = "%H:%M"
                        t_in  = datetime.strptime(oa_in.strip(), fmt)
                        t_out = datetime.strptime(oa_out.strip(), fmt)
                        hrs   = round((t_out - t_in).seconds / 3600, 2)
                    except Exception:
                        hrs = 0
                    hr_rate = float(er["Hourly_Rate_Rs"])
                    total_p = round(hrs * hr_rate, 2)
                    new_op = {
                        "Date": str(oa_date), "E_Code": er["E_Code"], "Name": er["Name"],
                        "In_Punch": oa_in, "Out_Punch": oa_out,
                        "Total_Hours": hrs, "Hourly_Rate_Rs": hr_rate, "Total_Pay": total_p
                    }
                    st.session_state.operating_attendance = pd.concat(
                        [st.session_state.operating_attendance, pd.DataFrame([new_op])], ignore_index=True
                    )
                    st.success(f"Saved! {er['Name']} | {hrs} hrs | Rs {total_p}")

        if not st.session_state.operating_attendance.empty:
            op_filter = st.date_input("Filter Date", value=date.today(), key="op_filter")
            _op_all = st.session_state.operating_attendance.copy()
            _op_all = coerce_numeric(_op_all, ["Total_Hours", "Hourly_Rate_Rs", "Total_Pay"])
            op_view = _op_all[_op_all["Date"] == str(op_filter)]
            if not op_view.empty:
                st.dataframe(op_view, use_container_width=True, hide_index=True)
                st.metric("Total Operating Staff Cost", f"Rs {op_view['Total_Pay'].sum():,.2f}")

    with col_style:
        st.markdown('<div class="section-title">Style Running Hours (for Cost Allocation)</div>', unsafe_allow_html=True)

        import_section(
            key="style_running_log",
            required_cols=["Date","Style","Hours_Run"],
            session_key="style_running_log",
            template_df=TEMPLATES["style_running_log"],
            label="Style Running Log"
        )

        styles_list_op = st.session_state.style_master["Style"].unique().tolist()
        with st.expander("✏️ Add Style Running Hours", expanded=True):
            with st.form("style_run_form", clear_on_submit=True):
                sr_date  = st.date_input("Date", value=date.today(), key="sr_date")
                sr_style = st.selectbox("Style", styles_list_op) if styles_list_op else st.text_input("Style")
                sr_hrs   = st.number_input("Hours Run Today", min_value=0.0, step=0.5)
                if st.form_submit_button("Add"):
                    new_sr = {"Date": str(sr_date), "Style": sr_style, "Hours_Run": sr_hrs, "Percentage": 0}
                    st.session_state.style_running_log = pd.concat(
                        [st.session_state.style_running_log, pd.DataFrame([new_sr])], ignore_index=True
                    )
                    st.success(f"Added {sr_style}: {sr_hrs} hrs")

        if not st.session_state.style_running_log.empty:
            sr_filter = st.date_input("Filter Date", value=date.today(), key="sr_filter")
            _sr_all = st.session_state.style_running_log.copy()
            _sr_all = coerce_numeric(_sr_all, ["Hours_Run", "Percentage"])
            sr_view = _sr_all[_sr_all["Date"] == str(sr_filter)].copy()
            if not sr_view.empty:
                total_hrs_run = sr_view["Hours_Run"].sum()
                sr_view["Percentage"] = (sr_view["Hours_Run"] / max(total_hrs_run, 0.001) * 100).round(1)
                st.dataframe(sr_view, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown('<div class="section-title">📊 Operating Cost Allocation to Styles</div>', unsafe_allow_html=True)
    alloc_date = st.date_input("Allocation Date", value=date.today(), key="alloc_date")

    _op_alloc = st.session_state.operating_attendance.copy()
    _op_alloc = coerce_numeric(_op_alloc, ["Total_Pay"])
    op_day = _op_alloc[_op_alloc["Date"] == str(alloc_date)]

    _sr_alloc = st.session_state.style_running_log.copy()
    _sr_alloc = coerce_numeric(_sr_alloc, ["Hours_Run"])
    sr_day = _sr_alloc[_sr_alloc["Date"] == str(alloc_date)].copy()

    if not op_day.empty and not sr_day.empty:
        total_op_cost = op_day["Total_Pay"].sum()
        total_run_hrs = sr_day["Hours_Run"].sum()
        sr_day["Percentage"]        = (sr_day["Hours_Run"] / max(total_run_hrs, 0.001) * 100).round(2)
        sr_day["Allocated_Cost_Rs"] = (sr_day["Percentage"] / 100 * total_op_cost).round(2)
        st.metric("Total Operating Cost", f"Rs {total_op_cost:,.2f}")
        st.dataframe(sr_day[["Style","Hours_Run","Percentage","Allocated_Cost_Rs"]], use_container_width=True, hide_index=True)
        ex1, ex2 = st.columns(2)
        with ex1:
            st.download_button("📥 Export Allocation (Excel)",
                data=df_to_excel_bytes(sr_day),
                file_name="op_cost_allocation.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with ex2:
            st.download_button("📥 Export Allocation (CSV)",
                data=df_to_csv_bytes(sr_day),
                file_name="op_cost_allocation.csv", mime="text/csv")
    else:
        st.info("Add operating staff attendance AND style running hours for the same date to see allocation.")


# ════════════════════════════════════════════════════════════
# TAB 9 – EMPLOYEE PERFORMANCE
# ════════════════════════════════════════════════════════════
with tab_performance:
    st.markdown('<div class="section-title">🌟 Employee Performance Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Compare how much value each karigar produced (piece-rate earned) vs how much they were paid (salary). This is the basis for salary increment decisions.</div>', unsafe_allow_html=True)

    if st.session_state.daily_sheet.empty or st.session_state.karigar_attendance.empty:
        st.info("Need both Daily Sheet data and Karigar Attendance data to show performance analysis.")
    else:
        p1, p2 = st.columns(2)
        with p1: perf_start = st.date_input("From", value=date.today() - timedelta(days=29), key="perf_start")
        with p2: perf_end   = st.date_input("To",   value=date.today(), key="perf_end")

        ds = st.session_state.daily_sheet.copy()
        # FIX: coerce numeric columns before calculations
        ds = coerce_numeric(ds, ["Achieved", "Target", "Rate_Rs"])
        ds["Date_dt"] = pd.to_datetime(ds["Date"])
        ds = ds[(ds["Date_dt"] >= pd.Timestamp(perf_start)) & (ds["Date_dt"] <= pd.Timestamp(perf_end))]
        ds["Piece_Earned"] = ds["Achieved"] * ds["Rate_Rs"]

        piece_summary = ds.groupby("Karigar_ID").agg(
            Piece_Earned_Rs=("Piece_Earned","sum"),
            Total_Pieces=("Achieved","sum"),
        ).reset_index()

        ds["Efficiency"] = (ds["Achieved"] / ds["Target"].replace(0, np.nan) * 100).fillna(0)
        eff_summary = ds.groupby("Karigar_ID")["Efficiency"].mean().reset_index()
        eff_summary.columns = ["Karigar_ID","Avg_Efficiency_%"]
        piece_summary = piece_summary.merge(eff_summary, on="Karigar_ID", how="left")

        att = st.session_state.karigar_attendance.copy()
        att = coerce_numeric(att, ["Total_Pay", "OT_Pay"])
        att["Date_dt"] = pd.to_datetime(att["Date"])
        att = att[(att["Date_dt"] >= pd.Timestamp(perf_start)) & (att["Date_dt"] <= pd.Timestamp(perf_end))]

        salary_summary = pd.DataFrame()
        if "Total_Pay" in att.columns:
            salary_summary = att.groupby("E_Code").agg(
                Name=("Name","first"),
                Days_Worked=("Date","nunique"),
                Total_Salary_Paid=("Total_Pay","sum"),
                Total_OT_Pay=("OT_Pay","sum"),
            ).round(2).reset_index()

        if not salary_summary.empty and not piece_summary.empty:
            perf = salary_summary.merge(
                piece_summary.rename(columns={"Karigar_ID":"E_Code"}),
                on="E_Code", how="outer"
            ).fillna(0)

            perf["Value_Produced_Rs"]   = perf["Piece_Earned_Rs"].round(2)
            perf["Salary_Paid_Rs"]      = perf["Total_Salary_Paid"].round(2)
            perf["Surplus_Deficit_Rs"]  = (perf["Value_Produced_Rs"] - perf["Salary_Paid_Rs"]).round(2)
            perf["ROI_%"] = ((perf["Value_Produced_Rs"] / perf["Salary_Paid_Rs"].replace(0, np.nan)) * 100).round(1).fillna(0)
            perf["Increment_Suggestion"] = perf["ROI_%"].apply(
                lambda x: "🏆 Highly Recommended (+15%)" if x >= 150
                else ("✅ Recommended (+10%)" if x >= 120
                else ("➡️ Average (No change)" if x >= 90
                else "⚠️ Review Required"))
            )

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Value Produced", f"Rs {perf['Value_Produced_Rs'].sum():,.0f}")
            c2.metric("Total Salary Paid",    f"Rs {perf['Salary_Paid_Rs'].sum():,.0f}")
            surplus = perf["Surplus_Deficit_Rs"].sum()
            c3.metric("Surplus / Deficit",    f"Rs {surplus:,.0f}", delta=f"{surplus:+.0f}")

            st.markdown("---")
            st.markdown('<div class="section-title">Employee Performance Table</div>', unsafe_allow_html=True)

            display_cols = ["E_Code","Name","Days_Worked","Total_Pieces","Avg_Efficiency_%",
                            "Value_Produced_Rs","Salary_Paid_Rs","Surplus_Deficit_Rs","ROI_%","Increment_Suggestion"]
            display_cols = [c for c in display_cols if c in perf.columns]
            st.dataframe(perf[display_cols], use_container_width=True, hide_index=True)

            st.markdown('<div class="section-title">Individual Employee Drill-down</div>', unsafe_allow_html=True)
            emp_sel_perf = st.selectbox("Select Employee", perf["E_Code"].tolist(), key="perf_emp_sel")
            emp_perf_row = perf[perf["E_Code"] == emp_sel_perf]
            if not emp_perf_row.empty:
                row = emp_perf_row.iloc[0]
                pc1, pc2, pc3, pc4 = st.columns(4)
                pc1.metric("Value Produced",   f"Rs {row.get('Value_Produced_Rs',0):,.0f}")
                pc2.metric("Salary Paid",      f"Rs {row.get('Salary_Paid_Rs',0):,.0f}")
                pc3.metric("ROI",              f"{row.get('ROI_%',0):.1f}%")
                pc4.metric("Avg Efficiency",   f"{row.get('Avg_Efficiency_%',0):.1f}%")
                st.info(f"Increment Suggestion: {row.get('Increment_Suggestion','N/A')}")

            ex1, ex2 = st.columns(2)
            with ex1:
                st.download_button("📥 Export Performance (Excel)",
                    data=df_to_excel_bytes(perf[display_cols]),
                    file_name="employee_performance.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with ex2:
                st.download_button("📥 Export Performance (CSV)",
                    data=df_to_csv_bytes(perf[display_cols]),
                    file_name="employee_performance.csv", mime="text/csv")
        else:
            st.info("Not enough data to generate performance report. Ensure Karigar_ID in Daily Sheet matches E_Code in Attendance.")


# ════════════════════════════════════════════════════════════
# TAB 10 – MASTER DATA
# ════════════════════════════════════════════════════════════
with tab_master:
    st.markdown('<div class="section-title">⚙️ Master Data Management</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.tabs(["👗 Style-Operation Master", "👷 Karigar Master", "🪪 Employee Master (E-Code)"])

    with m1:
        st.markdown('<div class="section-title">Style Operations, Targets and Rates</div>', unsafe_allow_html=True)

        import_section(
            key="style_master",
            required_cols=["Style","Operation","Target","Rate_Rs"],
            session_key="style_master",
            template_df=TEMPLATES["style_master"],
            label="Style-Operation Master"
        )

        with st.expander("➕ Add Operation Manually"):
            with st.form("style_op_form", clear_on_submit=True):
                s1, s2 = st.columns(2)
                with s1:
                    new_style  = st.text_input("Style Code")
                    new_op     = st.text_input("Operation Name")
                with s2:
                    new_target = st.number_input("Daily Target (pcs)", min_value=1, step=1)
                    new_rate   = st.number_input("Rate/Piece (Rs)", min_value=0.0, step=0.25, format="%.2f")
                if st.form_submit_button("Add") and new_style and new_op:
                    st.session_state.style_master = pd.concat(
                        [st.session_state.style_master,
                         pd.DataFrame([{"Style": new_style, "Operation": new_op,
                                        "Target": new_target, "Rate_Rs": new_rate}])],
                        ignore_index=True
                    )
                    st.success(f"Added {new_op} for {new_style}")

        st.dataframe(st.session_state.style_master, use_container_width=True, hide_index=True)

        _sm = st.session_state.style_master.copy()
        _sm = coerce_numeric(_sm, ["Target", "Rate_Rs"])
        style_summary = _sm.groupby("Style").agg(
            Total_Operations=("Operation","count"),
            Total_Rate_Per_Garment=("Rate_Rs","sum"),
            Slowest_Operation_Target=("Target","min")
        ).reset_index()
        st.markdown('<div class="section-title">Style Summary</div>', unsafe_allow_html=True)
        st.dataframe(style_summary, use_container_width=True, hide_index=True)

        ex1, ex2 = st.columns(2)
        with ex1:
            st.download_button("📥 Export Style Master (Excel)",
                data=df_to_excel_bytes(st.session_state.style_master),
                file_name="style_master.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with ex2:
            st.download_button("📥 Export Style Master (CSV)",
                data=df_to_csv_bytes(st.session_state.style_master),
                file_name="style_master.csv", mime="text/csv")

    with m2:
        st.markdown('<div class="section-title">Karigar Register</div>', unsafe_allow_html=True)

        import_section(
            key="karigar_master",
            required_cols=["Karigar_ID","Name","Skill","Daily_Rate_Rs"],
            session_key="karigar_master",
            template_df=TEMPLATES["karigar_master"],
            label="Karigar Master"
        )

        with st.expander("➕ Add Karigar Manually"):
            with st.form("karigar_form", clear_on_submit=True):
                k1, k2 = st.columns(2)
                with k1:
                    k_id   = st.text_input("Karigar ID (e.g. K006)")
                    k_name = st.text_input("Full Name")
                with k2:
                    k_skill = st.selectbox("Skill", ["Stitching","Cutting","Finishing","Hemming","Checking","General"])
                    k_rate  = st.number_input("Daily Rate (Rs)", min_value=100, step=10)
                if st.form_submit_button("Add Karigar") and k_id and k_name:
                    st.session_state.karigar_master = pd.concat(
                        [st.session_state.karigar_master,
                         pd.DataFrame([{"Karigar_ID": k_id, "Name": k_name,
                                        "Skill": k_skill, "Daily_Rate_Rs": k_rate}])],
                        ignore_index=True
                    )
                    st.success(f"{k_name} added!")

        st.dataframe(st.session_state.karigar_master, use_container_width=True, hide_index=True)

        ex1, ex2 = st.columns(2)
        with ex1:
            st.download_button("📥 Export Karigar Master (Excel)",
                data=df_to_excel_bytes(st.session_state.karigar_master),
                file_name="karigar_master.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with ex2:
            st.download_button("📥 Export Karigar Master (CSV)",
                data=df_to_csv_bytes(st.session_state.karigar_master),
                file_name="karigar_master.csv", mime="text/csv")

    with m3:
        st.markdown('<div class="section-title">Employee Master - E-Code Register</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">E-Code is the unique system code for each employee (Karigar + Operating Staff). Used for attendance and salary calculation.</div>', unsafe_allow_html=True)

        import_section(
            key="employee_master",
            required_cols=["E_Code","Name","Type","Daily_Rate_Rs","Hourly_Rate_Rs"],
            session_key="employee_master",
            template_df=TEMPLATES["employee_master"],
            label="Employee Master (E-Code)"
        )

        with st.expander("➕ Add Employee Manually"):
            with st.form("emp_master_form", clear_on_submit=True):
                em1, em2 = st.columns(2)
                with em1:
                    em_code = st.text_input("E-Code (e.g. E006)")
                    em_name = st.text_input("Full Name")
                    em_type = st.selectbox("Type", ["Karigar","Operating"])
                with em2:
                    em_daily  = st.number_input("Daily Rate (Rs)", min_value=100, step=10, value=400)
                    em_hourly = st.number_input("Hourly Rate (Rs)", min_value=0.0, step=0.5,
                                                value=round(400/8,2), format="%.2f")
                    st.caption("Tip: Hourly Rate = Daily Rate / 8")
                if st.form_submit_button("Add Employee") and em_code and em_name:
                    st.session_state.employee_master = pd.concat(
                        [st.session_state.employee_master,
                         pd.DataFrame([{"E_Code":em_code,"Name":em_name,"Type":em_type,
                                        "Daily_Rate_Rs":em_daily,"Hourly_Rate_Rs":em_hourly}])],
                        ignore_index=True
                    )
                    st.success(f"Employee {em_name} ({em_code}) added!")

        st.dataframe(st.session_state.employee_master, use_container_width=True, hide_index=True)
        ex1, ex2 = st.columns(2)
        with ex1:
            st.download_button("📥 Export Employee Master (Excel)",
                data=df_to_excel_bytes(st.session_state.employee_master),
                file_name="employee_master.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with ex2:
            st.download_button("📥 Export Employee Master (CSV)",
                data=df_to_csv_bytes(st.session_state.employee_master),
                file_name="employee_master.csv", mime="text/csv")

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<center style='color:#aaa; font-size:0.8rem;'>🧵 Stitching Costing Interface - Karigar Management System - Excel/CSV Import and Export</center>",
    unsafe_allow_html=True
)
