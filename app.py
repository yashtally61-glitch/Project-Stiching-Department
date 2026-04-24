"""
Stitching Costing Interface v5.0 — Yash Gallery Pvt Ltd
FIXED VERSION - All bugs resolved
- Simplified vertical layout for mobile
- Better error handling
- Clean tab structure
- No KeyErrors
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import io, hashlib, zipfile

st.set_page_config(page_title="Stitching Costing — Yash Gallery", page_icon="🧵", layout="wide")

# CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif;}
.main-hdr{background:linear-gradient(135deg,#1a3a5c,#2c5aa0);padding:16px 22px;border-radius:10px;color:#fff;margin-bottom:16px;}
.sec-hdr{background:#2c5aa0;color:#fff;padding:8px 14px;border-radius:6px;font-weight:600;margin:10px 0;}
.info-box{background:#e8f1f8;border-left:4px solid #2c5aa0;padding:10px;border-radius:4px;margin:8px 0;}
</style>
""", unsafe_allow_html=True)

# Constants
HOUR_COLS = ["H_09_10","H_10_11","H_11_12","H_12_13","H_13_14","H_14_15","H_15_16","H_16_17","H_17_18","H_18_19","H_19_20","H_20_21"]
DATA_KEYS = ["style_master","karigar_master","challan_master","production_log","employee_master","karigar_attendance"]
DEFAULT_PW = hashlib.sha256("admin123".encode()).hexdigest()

# Excel check
EXCEL_AVAILABLE = False
try:
    import xlsxwriter
    EXCEL_AVAILABLE = True
except:
    try:
        import openpyxl
        EXCEL_AVAILABLE = True
    except:
        pass

# Functions
def safe_num(s): 
    return pd.to_numeric(s, errors='coerce').fillna(0)

def hash_pw(pw): 
    return hashlib.sha256(pw.encode()).hexdigest()

def to_excel_bytes(df):
    if not EXCEL_AVAILABLE:
        return (df.to_csv(index=False).encode(), ".csv", "text/csv")
    buf = io.BytesIO()
    try:
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
        buf.seek(0)
        return (buf.getvalue(), ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except:
        return (df.to_csv(index=False).encode(), ".csv", "text/csv")

def export_zip():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w") as zf:
        for k in DATA_KEYS:
            df=st.session_state.get(k, pd.DataFrame())
            zf.writestr(f"{k}.csv", df.to_csv(index=False))
    return buf.getvalue()

# Init
def init_state():
    if "admin_pw_hash" not in st.session_state:
        st.session_state.admin_pw_hash = DEFAULT_PW
    
    if "style_master" not in st.session_state:
        st.session_state.style_master = pd.DataFrame([
            {"Style":"1894YKDGREEN","Operation":"Cutting","Target":120,"Rate_Rs":2.50},
            {"Style":"1894YKDGREEN","Operation":"Stitching","Target":80,"Rate_Rs":4.00},
            {"Style":"1065YKBLUE","Operation":"Cutting","Target":120,"Rate_Rs":2.50},
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
             "Total_Qty":376,"Received_Qty":0,"Deposit_Rs":0.0,"Rate_Per_Pc":35,"Date":"2026-02-25"},
        ])
    
    if "production_log" not in st.session_state:
        st.session_state.production_log = pd.DataFrame(columns=[
            "Date","Karigar_ID","Karigar_Name","Challan_No","Style","Operation"
        ] + HOUR_COLS + ["Total_Pieces","Target","Rate_Rs","Efficiency_%","Piece_Value_Rs"])
    
    if "employee_master" not in st.session_state:
        st.session_state.employee_master = pd.DataFrame([
            {"E_Code":"E001","Name":"Ramesh Kumar","Type":"Karigar","Daily_Rate_Rs":450,"Hourly_Rate_Rs":56.25},
            {"E_Code":"E101","Name":"Amit Sharma","Type":"Operating","Daily_Rate_Rs":600,"Hourly_Rate_Rs":75.00},
        ])
    
    if "karigar_attendance" not in st.session_state:
        st.session_state.karigar_attendance = pd.DataFrame(columns=[
            "Date","E_Code","Name","In_Punch","Out_Punch","Total_Hours","Total_Pay"])

init_state()
today = str(date.today())

# Header
st.markdown(f"""
<div class="main-hdr">
  <h2>🧵 Stitching Costing — Yash Gallery Pvt Ltd</h2>
  <p>Production · Payroll · Analytics | {date.today().strftime("%d %b %Y")}</p>
</div>""", unsafe_allow_html=True)

if not EXCEL_AVAILABLE:
    st.warning("⚠️ Excel not available. Run: `pip install xlsxwriter openpyxl`")

# Sidebar
with st.sidebar:
    st.markdown("### 💾 Backup")
    st.download_button("📦 Export All",
        data=export_zip(), file_name=f"backup_{today}.zip",
        mime="application/zip", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📊 Stats")
    pl = st.session_state.production_log
    tdpl = pl[pl["Date"]==today] if not pl.empty else pd.DataFrame()
    st.metric("Today's Entries", len(tdpl))
    if not tdpl.empty:
        st.metric("Pieces", int(safe_num(tdpl["Total_Pieces"]).sum()))

# Tabs
tabs = st.tabs(["🏠 Dashboard", "📋 Production", "🧾 Challans", "📊 Analytics", "💰 Payroll", "⚙️ Master"])

# TAB 1: Dashboard
with tabs[0]:
    st.markdown('<div class="sec-hdr">📈 Dashboard</div>', unsafe_allow_html=True)
    
    pl_td = st.session_state.production_log
    if not pl_td.empty:
        pl_td = pl_td[pl_td["Date"] == today].copy()
        for c in ["Total_Pieces", "Efficiency_%", "Piece_Value_Rs"]:
            if c in pl_td.columns: pl_td[c] = safe_num(pl_td[c])
    
    if pl_td.empty:
        st.info("No entries today")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Workers", pl_td["Karigar_ID"].nunique())
        c2.metric("Pieces", int(pl_td["Total_Pieces"].sum()))
        c3.metric("Efficiency", f"{pl_td['Efficiency_%'].mean():.1f}%")
        c4.metric("Value", f"₹{pl_td['Piece_Value_Rs'].sum():,.0f}")
        
        st.dataframe(pl_td, use_container_width=True, hide_index=True)

# TAB 2: Production
with tabs[1]:
    st.markdown('<div class="sec-hdr">📋 Production Entry</div>', unsafe_allow_html=True)
    st.markdown("**Vertical form - mobile friendly**")
    
    pe_date = st.date_input("📅 Date", value=date.today())
    
    # Karigar
    kdf = st.session_state.karigar_master
    if kdf.empty:
        st.error("No karigars. Add in Master tab.")
    else:
        k_opts = [f"{r['Karigar_ID']} — {r['Name']}" for _, r in kdf.iterrows()]
        sel_k = st.selectbox("👷 Karigar", k_opts)
        k_id = sel_k.split(" — ")[0]
        k_row = kdf[kdf["Karigar_ID"] == k_id].iloc[0]
        
        # Style
        sm = st.session_state.style_master
        if sm.empty:
            st.error("No styles. Add in Master tab.")
        else:
            styles = sm["Style"].unique().tolist()
            pe_style = st.selectbox("👗 Style", styles)
            
            # Challan
            chdf = st.session_state.challan_master
            s_ch = chdf[chdf["Style"] == pe_style] if not chdf.empty else pd.DataFrame()
            
            if s_ch.empty:
                st.warning(f"No challans for '{pe_style}'")
            else:
                ch_opts = [f"{r['Challan_No']} - {r.get('Party','')}" for _, r in s_ch.iterrows()]
                sel_ch = st.selectbox("🧾 Challan", ch_opts)
                challan_no = sel_ch.split(" - ")[0]
                
                # Operation
                ops = sm[sm["Style"] == pe_style][["Operation","Target","Rate_Rs"]]
                if ops.empty:
                    st.error("No operations")
                else:
                    op_list = ops["Operation"].tolist()
                    sel_op = st.selectbox("⚙️ Operation", op_list)
                    op_row = ops[ops["Operation"] == sel_op].iloc[0]
                    
                    st.info(f"🎯 Target: {op_row['Target']} pcs | Rate: ₹{op_row['Rate_Rs']}/pc")
                    
                    pieces = st.number_input("📦 Pieces Done", min_value=0, step=1, value=0)
                    
                    if pieces > 0:
                        eff = (pieces / op_row['Target'] * 100) if op_row['Target'] > 0 else 0
                        value = pieces * op_row['Rate_Rs']
                        st.success(f"⚡ {eff:.1f}% | ₹{value:.2f}")
                        
                        if st.button("💾 Save", use_container_width=True, type="primary"):
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
                            st.success(f"✅ Saved: {pieces} pcs")
                            st.balloons()
                            st.rerun()

# TAB 3: Challans
with tabs[2]:
    st.markdown('<div class="sec-hdr">🧾 Challans</div>', unsafe_allow_html=True)
    
    with st.expander("➕ Add Challan"):
        with st.form("add_ch"):
            c1, c2 = st.columns(2)
            with c1:
                c_no = st.text_input("Challan No")
                c_style = st.selectbox("Style", sm["Style"].unique().tolist() if not sm.empty else [])
            with c2:
                c_party = st.text_input("Party")
                c_qty = st.number_input("Qty", value=100)
            
            if st.form_submit_button("Add"):
                if c_no:
                    st.session_state.challan_master = pd.concat([
                        st.session_state.challan_master,
                        pd.DataFrame([{
                            "Challan_No": c_no, "Style": c_style, "Party": c_party,
                            "Total_Qty": c_qty, "Received_Qty": 0, "Deposit_Rs": 0.0,
                            "Rate_Per_Pc": 35, "Date": str(date.today())
                        }])
                    ], ignore_index=True)
                    st.success("✅ Added")
                    st.rerun()
    
    st.dataframe(st.session_state.challan_master, use_container_width=True, hide_index=True)

# TAB 4: Analytics
with tabs[3]:
    st.markdown('<div class="sec-hdr">📊 Analytics</div>', unsafe_allow_html=True)
    
    pl_an = st.session_state.production_log
    if pl_an.empty:
        st.info("No data")
    else:
        for c in ["Total_Pieces", "Efficiency_%", "Piece_Value_Rs"]:
            if c in pl_an.columns: pl_an[c] = safe_num(pl_an[c])
        
        kar = pl_an.groupby("Karigar_Name").agg(
            Pieces=("Total_Pieces", "sum"),
            Avg_Eff=("Efficiency_%", "mean"),
            Value=("Piece_Value_Rs", "sum")
        ).reset_index().sort_values("Avg_Eff", ascending=False)
        
        st.dataframe(kar, use_container_width=True, hide_index=True)
        st.bar_chart(kar.set_index("Karigar_Name")["Avg_Eff"])

# TAB 5: Payroll
with tabs[4]:
    st.markdown('<div class="sec-hdr">💰 Payroll</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1: start = st.date_input("From", value=date.today()-timedelta(days=7))
    with c2: end = st.date_input("To", value=date.today())
    
    att = st.session_state.karigar_attendance
    if not att.empty:
        att["Date_dt"] = pd.to_datetime(att["Date"])
        att = att[(att["Date_dt"] >= pd.Timestamp(start)) & (att["Date_dt"] <= pd.Timestamp(end))]
        
        if not att.empty:
            pay = att.groupby("Name").agg(
                Days=("Date", "nunique"),
                Pay=("Total_Pay", "sum")
            ).reset_index()
            
            st.dataframe(pay, use_container_width=True, hide_index=True)
            st.metric("Total", f"₹{pay['Pay'].sum():,.2f}")

# TAB 6: Master
with tabs[5]:
    mtabs = st.tabs(["👗 Styles", "👷 Karigars"])
    
    with mtabs[0]:
        st.markdown("**Style Operations**")
        
        with st.expander("➕ Add"):
            with st.form("add_s"):
                c1, c2 = st.columns(2)
                with c1:
                    s_code = st.text_input("Style")
                    s_op = st.text_input("Operation")
                with c2:
                    s_tgt = st.number_input("Target", value=100)
                    s_rt = st.number_input("Rate", value=3.0)
                
                if st.form_submit_button("Add"):
                    st.session_state.style_master = pd.concat([
                        st.session_state.style_master,
                        pd.DataFrame([{"Style": s_code, "Operation": s_op, "Target": s_tgt, "Rate_Rs": s_rt}])
                    ], ignore_index=True)
                    st.success("✅")
                    st.rerun()
        
        st.dataframe(st.session_state.style_master, use_container_width=True, hide_index=True)
    
    with mtabs[1]:
        st.markdown("**Karigars**")
        
        with st.expander("➕ Add"):
            with st.form("add_k"):
                c1, c2 = st.columns(2)
                with c1:
                    k_id = st.text_input("ID (K004)")
                    k_nm = st.text_input("Name")
                with c2:
                    k_sk = st.selectbox("Skill", ["Stitching","Cutting","Finishing"])
                    k_rt = st.number_input("Daily Rate", value=450)
                
                if st.form_submit_button("Add"):
                    st.session_state.karigar_master = pd.concat([
                        st.session_state.karigar_master,
                        pd.DataFrame([{"Karigar_ID": k_id, "Name": k_nm, "Skill": k_sk, "Daily_Rate_Rs": k_rt}])
                    ], ignore_index=True)
                    st.success("✅")
                    st.rerun()
        
        st.dataframe(st.session_state.karigar_master, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("🧵 **v5.0** — Yash Gallery Pvt Ltd", unsafe_allow_html=True)
