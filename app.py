"""
Stitching Costing Interface v5.0 — Yash Gallery Pvt Ltd
MAJOR REDESIGN v5.0:
- Reorganized tabs: Live Dashboard, Production & Work, Analytics & Growth, Performance, Master Data
- Vertical layout for mobile
- Real-time live monitoring for management
- Growth charts and graphs
- Salary increment recommendations based on performance
- Enhanced analytics with visual charts
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import io, hashlib, zipfile

st.set_page_config(page_title="Stitching Costing — Yash Gallery", page_icon="🧵", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
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
.live-card{background:#fff;border:2px solid #e0e0e0;border-radius:8px;padding:16px;margin:8px 0;box-shadow:0 2px 4px rgba(0,0,0,0.1);}
.live-good{border-color:#2e7d32;background:#f1f8f4;}
.live-avg{border-color:#f57c00;background:#fff8f0;}
.live-bad{border-color:#c62828;background:#ffebee;}
.metric-big{font-size:2.5rem;font-weight:700;font-family:'IBM Plex Mono',monospace;margin:8px 0;}
.metric-label{font-size:.8rem;opacity:.7;text-transform:uppercase;letter-spacing:.05em;}
.chart-container{background:#fafafa;padding:16px;border-radius:8px;margin:12px 0;}
</style>
""", unsafe_allow_html=True)

# Constants
HOUR_COLS = ["H_09_10","H_10_11","H_11_12","H_12_13","H_13_14",
             "H_14_15","H_15_16","H_16_17","H_17_18","H_18_19","H_19_20","H_20_21"]
HOUR_LBLS = ["9:00-10:00","10:00-11:00","11:00-12:00","12:00-13:00","13:00-14:00",
             "14:00-15:00","15:00-16:00","16:00-17:00","17:00-18:00","18:00-19:00","19:00-20:00","20:00-21:00"]
DATA_KEYS  = ["style_master","karigar_master","challan_master","production_log",
              "employee_master","karigar_attendance"]
DEFAULT_PW = hashlib.sha256("admin123".encode()).hexdigest()

# Check Excel libraries
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
        pass

# Helper functions
def safe_num(s): return pd.to_numeric(s, errors='coerce').fillna(0)
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def to_excel_bytes(df: pd.DataFrame) -> tuple:
    if not EXCEL_AVAILABLE:
        return (df.to_csv(index=False).encode(), ".csv", "text/csv")
    
    buf = io.BytesIO()
    try:
        if EXCEL_ENGINE == "xlsxwriter":
            with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Data")
                workbook = writer.book
                worksheet = writer.sheets["Data"]
                header_format = workbook.add_format({
                    'bold': True, 'bg_color': '#2c5aa0', 'font_color': 'white',
                    'border': 1, 'align': 'center', 'valign': 'vcenter'
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
    except:
        return (df.to_csv(index=False).encode(), ".csv", "text/csv")

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode()

def export_zip() -> bytes:
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as zf:
        for k in DATA_KEYS:
            df=st.session_state.get(k, pd.DataFrame())
            if not isinstance(df, pd.DataFrame): df=pd.DataFrame()
            zf.writestr(f"{k}.csv", df.to_csv(index=False))
    return buf.getvalue()

# Initialize session state
def init_state():
    if "admin_pw_hash" not in st.session_state:
        st.session_state.admin_pw_hash = DEFAULT_PW
    if "sheet_unlocked" not in st.session_state:
        st.session_state.sheet_unlocked = False
    
    if "style_master" not in st.session_state:
        st.session_state.style_master = pd.DataFrame([
            {"Style":"1894YKDGREEN","Operation":"Cutting","Target":120,"Rate_Rs":2.50},
            {"Style":"1894YKDGREEN","Operation":"Stitching Front","Target":80,"Rate_Rs":4.00},
            {"Style":"1894YKDGREEN","Operation":"Side Seam","Target":90,"Rate_Rs":3.50},
        ])
    
    if "karigar_master" not in st.session_state:
        st.session_state.karigar_master = pd.DataFrame([
            {"Karigar_ID":"K001","Name":"Ramesh Kumar","Skill":"Stitching","Daily_Rate_Rs":450},
            {"Karigar_ID":"K002","Name":"Suresh Singh","Skill":"Cutting","Daily_Rate_Rs":420},
            {"Karigar_ID":"K003","Name":"Priya Devi","Skill":"Finishing","Daily_Rate_Rs":400},
        ])
    
    if "challan_master" not in st.session_state:
        st.session_state.challan_master = pd.DataFrame([
            {"Challan_No":"10220-2526","Style":"1894YKDGREEN","Party":"Aashirwad Garments",
             "Total_Qty":376,"Received_Qty":0,"Deposit_Rs":0.0,"Rate_Per_Pc":35,
             "Date":"2026-02-25","Delivery_By":"2026-03-07"},
        ])
    
    if "production_log" not in st.session_state:
        st.session_state.production_log = pd.DataFrame(columns=[
            "Date","Karigar_ID","Karigar_Name","Challan_No","Style","Operation",
        ] + HOUR_COLS + ["Total_Pieces","Target","Rate_Rs","Efficiency_%","Piece_Value_Rs"])
    
    if "employee_master" not in st.session_state:
        st.session_state.employee_master = pd.DataFrame([
            {"E_Code":"E001","Name":"Ramesh Kumar","Type":"Karigar","Daily_Rate_Rs":450,"Hourly_Rate_Rs":56.25},
            {"E_Code":"E002","Name":"Suresh Singh","Type":"Karigar","Daily_Rate_Rs":420,"Hourly_Rate_Rs":52.50},
        ])
    
    if "karigar_attendance" not in st.session_state:
        st.session_state.karigar_attendance = pd.DataFrame(columns=[
            "Date","E_Code","Name","In_Punch","Out_Punch","Total_Presence_Hrs",
            "Lunch_Deduction_Hrs","Payable_Hrs","Hourly_Rate_Rs","Normal_Pay",
            "OT_Hours","OT_Pay","Total_Pay"])

init_state()
today_str = str(date.today())

# Header
st.markdown(f"""
<div class="main-hdr">
  <h2>🧵 Stitching Costing Interface v5.0 — Yash Gallery Pvt Ltd</h2>
  <p>Live Monitoring · Production Tracking · Analytics & Growth · Performance Management &nbsp;|&nbsp; {date.today().strftime("%d %b %Y")}</p>
</div>""", unsafe_allow_html=True)

if not EXCEL_AVAILABLE:
    st.warning("⚠️ **Excel Export Not Available** - Run: `pip install xlsxwriter openpyxl`", icon="⚠️")

# Sidebar
with st.sidebar:
    st.markdown("### 💾 Backup & Restore")
    st.download_button("📦 Export All Data (.zip)",
        data=export_zip(), file_name=f"yashgallery_{today_str}.zip",
        mime="application/zip", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    pl_all = st.session_state.production_log
    tdpl = pl_all[pl_all["Date"]==today_str] if not pl_all.empty else pd.DataFrame()
    st.metric("Today's Entries", len(tdpl))
    st.metric("Total Karigar", len(st.session_state.karigar_master))
    if not tdpl.empty:
        st.metric("Today's Pieces", int(safe_num(tdpl["Total_Pieces"]).sum()))
        st.metric("Avg Efficiency", f"{safe_num(tdpl['Efficiency_%']).mean():.1f}%")

# TABS - Reorganized
tabs = st.tabs([
    "📊 Live Dashboard",
    "📋 Production & Work", 
    "📈 Analytics & Growth",
    "🌟 Performance Rankings",
    "⚙️ Master Data & Settings"
])

# ═══════════════════════════════════════════════════════════════════
# TAB 1: LIVE DASHBOARD (for Boss to monitor in real-time)
# ═══════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown('<div class="sec-hdr">📊 Live Production Monitoring</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Real-time view of today\'s production. Auto-refreshes to show latest status.</div>', unsafe_allow_html=True)
    
    # Auto-refresh button
    col_ref1, col_ref2 = st.columns([4, 1])
    with col_ref2:
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.rerun()
    
    pl_today = st.session_state.production_log
    if not pl_today.empty:
        pl_today = pl_today[pl_today["Date"] == today_str].copy()
        for c in ["Total_Pieces", "Efficiency_%", "Piece_Value_Rs"]:
            if c in pl_today.columns:
                pl_today[c] = safe_num(pl_today[c])
    
    if pl_today.empty:
        st.info("🕐 No production entries yet today. Waiting for data...")
    else:
        # Summary metrics
        total_workers = pl_today["Karigar_ID"].nunique()
        total_pieces = int(pl_today["Total_Pieces"].sum())
        avg_eff = pl_today["Efficiency_%"].mean()
        total_value = pl_today["Piece_Value_Rs"].sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("👷 Active Workers", total_workers)
        m2.metric("📦 Pieces Done", f"{total_pieces:,}")
        m3.metric("⚡ Avg Efficiency", f"{avg_eff:.1f}%", 
                 delta=f"{avg_eff-100:.1f}% vs target" if avg_eff < 100 else f"+{avg_eff-100:.1f}%")
        m4.metric("💰 Production Value", f"₹{total_value:,.0f}")
        
        st.markdown("---")
        st.markdown('<div class="sec-hdr">👷 Live Karigar Status</div>', unsafe_allow_html=True)
        
        # Group by karigar
        kar_summary = pl_today.groupby(["Karigar_ID", "Karigar_Name"]).agg(
            Operations=("Operation", "count"),
            Total_Pieces=("Total_Pieces", "sum"),
            Avg_Efficiency=("Efficiency_%", "mean"),
            Total_Value=("Piece_Value_Rs", "sum")
        ).reset_index().sort_values("Avg_Efficiency", ascending=False)
        
        # Display each karigar as a card
        for _, row in kar_summary.iterrows():
            eff = row["Avg_Efficiency"]
            if eff >= 100:
                card_class = "live-good"
                status_icon = "✅"
                status_text = "Excellent Performance"
                status_color = "#2e7d32"
            elif eff >= 80:
                card_class = "live-avg"
                status_icon = "⚡"
                status_text = "Good Performance"
                status_color = "#f57c00"
            else:
                card_class = "live-bad"
                status_icon = "⚠️"
                status_text = "Needs Attention"
                status_color = "#c62828"
            
            st.markdown(f"""
            <div class="live-card {card_class}">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <h3 style="margin:0;font-size:1.1rem;">{status_icon} {row['Karigar_Name']}</h3>
                        <p style="margin:4px 0;color:#666;font-size:.85rem;">{row['Karigar_ID']} • {row['Operations']} operations</p>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:2rem;font-weight:700;color:{status_color};">{eff:.0f}%</div>
                        <div style="font-size:.75rem;color:{status_color};font-weight:600;">{status_text}</div>
                    </div>
                </div>
                <div style="margin-top:12px;padding-top:12px;border-top:1px solid #e0e0e0;display:flex;justify-content:space-between;">
                    <div><span style="color:#666;">Pieces:</span> <b>{int(row['Total_Pieces'])}</b></div>
                    <div><span style="color:#666;">Value:</span> <b>₹{row['Total_Value']:,.0f}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown('<div class="sec-hdr">📋 Latest Entries</div>', unsafe_allow_html=True)
        recent = pl_today.sort_values("Date", ascending=False).head(10)
        st.dataframe(recent[["Karigar_Name", "Operation", "Total_Pieces", "Efficiency_%", "Piece_Value_Rs"]], 
                    use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════
# TAB 2: PRODUCTION & WORK (Combined production entry + attendance)
# ═══════════════════════════════════════════════════════════════════
with tabs[1]:
    work_tabs = st.tabs(["📋 Production Entry", "🕐 Attendance"])
    
    # Production Entry Sub-tab
    with work_tabs[0]:
        st.markdown('<div class="sec-hdr">📋 Production Entry</div>', unsafe_allow_html=True)
        st.markdown("**Simple vertical entry form - optimized for mobile**")
        
        # Vertical form
        pe_date = st.date_input("📅 Date", value=date.today(), key="pe_date")
        
        # Karigar selection
        kdf = st.session_state.karigar_master
        k_options = [f"{r['Karigar_ID']} — {r['Name']}" for _, r in kdf.iterrows()]
        sel_k = st.selectbox("👷 Select Karigar", k_options, key="sel_kar_v5")
        k_id = sel_k.split(" — ")[0]
        k_row = kdf[kdf["Karigar_ID"] == k_id].iloc[0]
        
        # Style selection
        sm = st.session_state.style_master
        all_styles = sm["Style"].unique().tolist() if not sm.empty else []
        pe_style = st.selectbox("👗 Select Style", all_styles, key="pe_style_v5")
        
        # Challan selection
        ch_df = st.session_state.challan_master
        s_chall = ch_df[ch_df["Style"] == pe_style] if not ch_df.empty else pd.DataFrame()
        if not s_chall.empty:
            ch_options = [f"{r['Challan_No']} ({r.get('Party', '—')})" for _, r in s_chall.iterrows()]
            sel_ch = st.selectbox("🧾 Select Challan", ch_options, key="sel_ch_v5")
            challan_no = sel_ch.split(" (")[0]
        else:
            st.warning(f"No challans for style '{pe_style}'")
            st.stop()
        
        # Operation selection
        style_ops = sm[sm["Style"] == pe_style][["Operation", "Target", "Rate_Rs"]]
        if not style_ops.empty:
            op_list = style_ops["Operation"].tolist()
            sel_op = st.selectbox("⚙️ Select Operation", op_list, key="sel_op_v5")
            op_row = style_ops[style_ops["Operation"] == sel_op].iloc[0]
            
            st.info(f"🎯 Target: {op_row['Target']} pcs/day | Rate: ₹{op_row['Rate_Rs']}/pc")
            
            # Pieces input
            pieces = st.number_input("📦 Total Pieces Done Today", min_value=0, step=1, value=0, key="pieces_v5")
            
            if pieces > 0:
                eff = (pieces / op_row['Target'] * 100) if op_row['Target'] > 0 else 0
                value = pieces * op_row['Rate_Rs']
                
                st.success(f"⚡ Efficiency: {eff:.1f}% | 💰 Value: ₹{value:.2f}")
                
                if st.button("💾 Save Entry", use_container_width=True, type="primary"):
                    new_row = {
                        "Date": str(pe_date),
                        "Karigar_ID": k_id,
                        "Karigar_Name": k_row["Name"],
                        "Challan_No": challan_no,
                        "Style": pe_style,
                        "Operation": sel_op,
                        **{h: 0 for h in HOUR_COLS},
                        "Total_Pieces": pieces,
                        "Target": int(op_row['Target']),
                        "Rate_Rs": float(op_row['Rate_Rs']),
                        "Efficiency_%": eff,
                        "Piece_Value_Rs": value,
                    }
                    st.session_state.production_log = pd.concat([
                        st.session_state.production_log,
                        pd.DataFrame([new_row])
                    ], ignore_index=True)
                    st.success(f"✅ Saved: {k_row['Name']} - {sel_op} - {pieces} pcs ({eff:.1f}%)")
                    st.balloons()
                    st.rerun()
    
    # Attendance Sub-tab
    with work_tabs[1]:
        st.markdown('<div class="sec-hdr">🕐 Attendance Entry</div>', unsafe_allow_html=True)
        
        att_date = st.date_input("📅 Date", value=date.today(), key="att_date_v5")
        
        ek = st.session_state.employee_master[st.session_state.employee_master["Type"] == "Karigar"]
        emp_options = [f"{r['E_Code']} — {r['Name']}" for _, r in ek.iterrows()]
        sel_emp = st.selectbox("👷 Select Employee", emp_options, key="sel_emp_v5")
        e_code = sel_emp.split(" — ")[0]
        e_row = ek[ek["E_Code"] == e_code].iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            in_time = st.text_input("⏰ In Time (HH:MM)", value="09:00", key="in_v5")
        with col2:
            out_time = st.text_input("⏱ Out Time (HH:MM)", value="18:00", key="out_v5")
        
        if st.button("💾 Save Attendance", use_container_width=True, type="primary"):
            # Simple calculation: hours worked * hourly rate
            try:
                in_dt = datetime.strptime(in_time, "%H:%M")
                out_dt = datetime.strptime(out_time, "%H:%M")
                hours = (out_dt - in_dt).total_seconds() / 3600
                pay = hours * e_row["Hourly_Rate_Rs"]
                
                new_att = {
                    "Date": str(att_date),
                    "E_Code": e_code,
                    "Name": e_row["Name"],
                    "In_Punch": in_time,
                    "Out_Punch": out_time,
                    "Total_Presence_Hrs": hours,
                    "Lunch_Deduction_Hrs": 1.0,
                    "Payable_Hrs": max(hours - 1, 0),
                    "Hourly_Rate_Rs": e_row["Hourly_Rate_Rs"],
                    "Normal_Pay": pay,
                    "OT_Hours": 0,
                    "OT_Pay": 0,
                    "Total_Pay": pay
                }
                st.session_state.karigar_attendance = pd.concat([
                    st.session_state.karigar_attendance,
                    pd.DataFrame([new_att])
                ], ignore_index=True)
                st.success(f"✅ Saved attendance for {e_row['Name']} - {hours:.1f} hrs - ₹{pay:.2f}")
                st.rerun()
            except:
                st.error("Invalid time format. Use HH:MM (e.g., 09:00)")

# ═══════════════════════════════════════════════════════════════════
# TAB 3: ANALYTICS & GROWTH (Charts, trends, salary recommendations)
# ═══════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="sec-hdr">📈 Analytics & Growth Tracking</div>', unsafe_allow_html=True)
    
    # Date range selector
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("From", value=date.today()-timedelta(days=30), key="analytics_start")
    with col_d2:
        end_date = st.date_input("To", value=date.today(), key="analytics_end")
    
    pl_analytics = st.session_state.production_log.copy()
    if not pl_analytics.empty:
        pl_analytics["Date_dt"] = pd.to_datetime(pl_analytics["Date"], errors='coerce')
        pl_analytics = pl_analytics[
            (pl_analytics["Date_dt"] >= pd.Timestamp(start_date)) &
            (pl_analytics["Date_dt"] <= pd.Timestamp(end_date))
        ]
        
        for c in ["Total_Pieces", "Efficiency_%", "Piece_Value_Rs"]:
            if c in pl_analytics.columns:
                pl_analytics[c] = safe_num(pl_analytics[c])
    
    if pl_analytics.empty:
        st.info("No data for selected period")
    else:
        # Karigar-wise growth analysis
        st.markdown('<div class="sec-hdr">📊 Karigar Performance Analysis</div>', unsafe_allow_html=True)
        
        kar_growth = pl_analytics.groupby("Karigar_Name").agg(
            Total_Days=("Date", "nunique"),
            Total_Pieces=("Total_Pieces", "sum"),
            Avg_Efficiency=("Efficiency_%", "mean"),
            Total_Value=("Piece_Value_Rs", "sum"),
            Operations=("Operation", "count")
        ).reset_index().sort_values("Avg_Efficiency", ascending=False)
        
        # Calculate daily average
        kar_growth["Avg_Pieces_Per_Day"] = (kar_growth["Total_Pieces"] / kar_growth["Total_Days"]).round(0)
        kar_growth["Avg_Value_Per_Day"] = (kar_growth["Total_Value"] / kar_growth["Total_Days"]).round(2)
        
        # Salary increment recommendations
        kar_growth["Recommendation"] = kar_growth["Avg_Efficiency"].apply(
            lambda x: "🏆 Increment: +₹50/day" if x >= 100 else 
                     ("⭐ Increment: +₹25/day" if x >= 90 else
                      ("✅ Maintain current" if x >= 80 else "⚠️ Training needed"))
        )
        
        st.dataframe(kar_growth, use_container_width=True, hide_index=True)
        
        # Charts
        st.markdown("---")
        st.markdown('<div class="sec-hdr">📉 Efficiency Trends</div>', unsafe_allow_html=True)
        
        # Daily trend chart (simple bar chart using Streamlit's built-in)
        daily_eff = pl_analytics.groupby("Date")["Efficiency_%"].mean().reset_index()
        daily_eff = daily_eff.sort_values("Date")
        
        st.bar_chart(daily_eff.set_index("Date")["Efficiency_%"])
        
        # Karigar comparison
        st.markdown("---")
        st.markdown('<div class="sec-hdr">📊 Karigar Efficiency Comparison</div>', unsafe_allow_html=True)
        kar_comparison = pl_analytics.groupby("Karigar_Name")["Efficiency_%"].mean().reset_index()
        kar_comparison = kar_comparison.sort_values("Efficiency_%", ascending=False)
        
        st.bar_chart(kar_comparison.set_index("Karigar_Name")["Efficiency_%"])
        
        # Export analytics
        st.markdown("---")
        excel_data, excel_ext, excel_mime = to_excel_bytes(kar_growth)
        st.download_button("📥 Download Analytics Report", 
                          excel_data, f"analytics_{start_date}_{end_date}{excel_ext}",
                          mime=excel_mime)

# ═══════════════════════════════════════════════════════════════════
# TAB 4: PERFORMANCE RANKINGS
# ═══════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown('<div class="sec-hdr">🌟 Performance Rankings & Leaderboard</div>', unsafe_allow_html=True)
    
    # Period selector
    period = st.selectbox("📅 Select Period", 
                         ["Today", "This Week", "This Month", "Last 30 Days", "All Time"],
                         key="perf_period")
    
    pl_perf = st.session_state.production_log.copy()
    if not pl_perf.empty:
        pl_perf["Date_dt"] = pd.to_datetime(pl_perf["Date"], errors='coerce')
        
        if period == "Today":
            pl_perf = pl_perf[pl_perf["Date"] == today_str]
        elif period == "This Week":
            week_start = date.today() - timedelta(days=date.today().weekday())
            pl_perf = pl_perf[pl_perf["Date_dt"] >= pd.Timestamp(week_start)]
        elif period == "This Month":
            month_start = date.today().replace(day=1)
            pl_perf = pl_perf[pl_perf["Date_dt"] >= pd.Timestamp(month_start)]
        elif period == "Last 30 Days":
            pl_perf = pl_perf[pl_perf["Date_dt"] >= pd.Timestamp(date.today() - timedelta(days=30))]
        
        for c in ["Total_Pieces", "Efficiency_%", "Piece_Value_Rs"]:
            if c in pl_perf.columns:
                pl_perf[c] = safe_num(pl_perf[c])
    
    if pl_perf.empty:
        st.info(f"No data for {period}")
    else:
        # Rankings
        rankings = pl_perf.groupby("Karigar_Name").agg(
            Total_Pieces=("Total_Pieces", "sum"),
            Avg_Efficiency=("Efficiency_%", "mean"),
            Total_Value=("Piece_Value_Rs", "sum"),
            Days_Worked=("Date", "nunique")
        ).reset_index().sort_values("Avg_Efficiency", ascending=False)
        
        rankings["Rank"] = range(1, len(rankings) + 1)
        rankings["Grade"] = rankings["Avg_Efficiency"].apply(
            lambda x: "🏆 A+" if x >= 110 else
                     ("⭐ A" if x >= 100 else
                      ("✅ B" if x >= 85 else
                       ("⚡ C" if x >= 70 else "⚠️ D")))
        )
        
        # Display rankings as cards
        for _, row in rankings.iterrows():
            rank = row["Rank"]
            if rank == 1:
                medal = "🥇"
                bg_color = "#fff9e6"
                border_color = "#ffd700"
            elif rank == 2:
                medal = "🥈"
                bg_color = "#f5f5f5"
                border_color = "#c0c0c0"
            elif rank == 3:
                medal = "🥉"
                bg_color = "#fff4e6"
                border_color = "#cd7f32"
            else:
                medal = f"#{rank}"
                bg_color = "#fafafa"
                border_color = "#e0e0e0"
            
            st.markdown(f"""
            <div style="background:{bg_color};border:2px solid {border_color};border-radius:8px;padding:16px;margin:8px 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <h3 style="margin:0;font-size:1.2rem;">{medal} {row['Karigar_Name']}</h3>
                        <p style="margin:4px 0;color:#666;font-size:.9rem;">{row['Grade']} • {row['Days_Worked']} days worked</p>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:2rem;font-weight:700;color:#2c5aa0;">{row['Avg_Efficiency']:.1f}%</div>
                        <div style="font-size:.75rem;color:#666;">efficiency</div>
                    </div>
                </div>
                <div style="margin-top:12px;padding-top:12px;border-top:1px solid {border_color};display:flex;justify-content:space-between;">
                    <div><span style="color:#666;">Pieces:</span> <b>{int(row['Total_Pieces']):,}</b></div>
                    <div><span style="color:#666;">Value:</span> <b>₹{row['Total_Value']:,.0f}</b></div>
                    <div><span style="color:#666;">Avg/Day:</span> <b>{int(row['Total_Pieces']/row['Days_Worked']):,}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# TAB 5: MASTER DATA & SETTINGS
# ═══════════════════════════════════════════════════════════════════
with tabs[4]:
    master_tabs = st.tabs(["👗 Styles", "👷 Karigars", "🧾 Challans", "⚙️ Settings"])
    
    # Styles
    with master_tabs[0]:
        st.markdown('<div class="sec-hdr">👗 Style Master</div>', unsafe_allow_html=True)
        
        with st.expander("➕ Add New Operation"):
            col1, col2 = st.columns(2)
            with col1:
                new_style = st.text_input("Style Code", key="new_style")
                new_op = st.text_input("Operation Name", key="new_op")
            with col2:
                new_target = st.number_input("Target (pcs/day)", min_value=1, value=100, key="new_target")
                new_rate = st.number_input("Rate/pc (₹)", min_value=0.0, value=3.0, step=0.25, key="new_rate")
            
            if st.button("✅ Add Operation"):
                st.session_state.style_master = pd.concat([
                    st.session_state.style_master,
                    pd.DataFrame([{
                        "Style": new_style,
                        "Operation": new_op,
                        "Target": new_target,
                        "Rate_Rs": new_rate
                    }])
                ], ignore_index=True)
                st.success(f"✅ Added: {new_style} - {new_op}")
                st.rerun()
        
        st.dataframe(st.session_state.style_master, use_container_width=True, hide_index=True)
    
    # Karigars
    with master_tabs[1]:
        st.markdown('<div class="sec-hdr">👷 Karigar Master</div>', unsafe_allow_html=True)
        
        with st.expander("➕ Add New Karigar"):
            col1, col2 = st.columns(2)
            with col1:
                new_kid = st.text_input("Karigar ID", key="new_kid")
                new_kname = st.text_input("Name", key="new_kname")
            with col2:
                new_skill = st.selectbox("Skill", ["Stitching", "Cutting", "Finishing", "Hemming"], key="new_skill")
                new_rate = st.number_input("Daily Rate (₹)", min_value=100, value=450, step=10, key="new_krate")
            
            if st.button("✅ Add Karigar"):
                st.session_state.karigar_master = pd.concat([
                    st.session_state.karigar_master,
                    pd.DataFrame([{
                        "Karigar_ID": new_kid,
                        "Name": new_kname,
                        "Skill": new_skill,
                        "Daily_Rate_Rs": new_rate
                    }])
                ], ignore_index=True)
                st.success(f"✅ Added: {new_kname}")
                st.rerun()
        
        st.dataframe(st.session_state.karigar_master, use_container_width=True, hide_index=True)
    
    # Challans
    with master_tabs[2]:
        st.markdown('<div class="sec-hdr">🧾 Challan Master</div>', unsafe_allow_html=True)
        st.dataframe(st.session_state.challan_master, use_container_width=True, hide_index=True)
    
    # Settings
    with master_tabs[3]:
        st.markdown('<div class="sec-hdr">⚙️ System Settings</div>', unsafe_allow_html=True)
        
        st.markdown("**Change Admin Password:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            curr_pw = st.text_input("Current Password", type="password", key="curr_pw")
        with col2:
            new_pw1 = st.text_input("New Password", type="password", key="new_pw1")
        with col3:
            new_pw2 = st.text_input("Confirm New", type="password", key="new_pw2")
        
        if st.button("🔐 Change Password"):
            if hash_pw(curr_pw) != st.session_state.admin_pw_hash:
                st.error("Wrong current password")
            elif new_pw1 != new_pw2:
                st.error("Passwords don't match")
            elif len(new_pw1) < 4:
                st.error("Minimum 4 characters")
            else:
                st.session_state.admin_pw_hash = hash_pw(new_pw1)
                st.success("✅ Password changed!")

st.markdown("---")
st.markdown("🧵 <b>Stitching Costing Interface v5.0</b> — Yash Gallery Pvt Ltd", unsafe_allow_html=True)
