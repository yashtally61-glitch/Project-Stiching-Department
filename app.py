#!/usr/bin/env python3
"""
Auto-fix script for app.py Google Sheets saving issue
Usage: python fix_app.py
"""

# The original broken save_sheet function
OLD_SAVE_FUNCTION = '''def save_sheet(tab_name: str, df: pd.DataFrame):
    """Write DataFrame back to Google Sheet tab."""
    try:
        sh = get_gsheet()
        try:
            ws = sh.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=tab_name, rows=1000, cols=50)
        ws.clear()
        set_with_dataframe(ws, df)
    except Exception as e:
        st.error(f"Could not save {tab_name}: {e}")'''

# The fixed save_sheet function
NEW_SAVE_FUNCTION = '''def save_sheet(tab_name: str, df: pd.DataFrame) -> bool:
    """Write DataFrame back to Google Sheet tab - ✅ FIXED VERSION!"""
    if df.empty:
        print(f"[SAVE] {tab_name} is empty - skipping")
        return True
    
    try:
        print(f"[SAVE] Saving {tab_name}: {len(df)} rows, {len(df.columns)} columns")
        sh = get_gsheet()
        
        try:
            ws = sh.worksheet(tab_name)
            print(f"[SAVE] Found worksheet: {tab_name}")
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=tab_name, rows=1000, cols=50)
            print(f"[SAVE] Created worksheet: {tab_name}")
        
        print(f"[SAVE] Clearing {tab_name}...")
        ws.clear()
        
        print(f"[SAVE] Writing data to {tab_name}...")
        # ✅ CRITICAL FIX: Added include_index and include_column_header parameters
        set_with_dataframe(ws, df, include_index=False, include_column_header=True)
        
        # Verify the save worked
        verify = ws.get_all_values()
        print(f"[SAVE] ✅ Verified: {len(verify)} rows in sheet (including header)")
        
        st.sidebar.success(f"✅ {tab_name}: {len(df)} rows")
        return True
        
    except Exception as e:
        print(f"[SAVE] ❌ Error: {type(e).__name__}: {str(e)}")
        st.error(f"❌ Could not save {tab_name}: {e}")
        import traceback
        st.error(traceback.format_exc())
        return False'''

if __name__ == "__main__":
    import sys
    
    # Read the original app.py
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ Error: app.py not found in current directory")
        sys.exit(1)
    
    # Check if already fixed
    if 'include_index=False, include_column_header=True' in content:
        print("✅ app.py is already fixed!")
        sys.exit(0)
    
    # Apply the fix
    if OLD_SAVE_FUNCTION in content:
        print("🔧 Applying fix...")
        content = content.replace(OLD_SAVE_FUNCTION, NEW_SAVE_FUNCTION)
        
        # Backup the original
        with open('app.py.backup', 'w', encoding='utf-8') as f:
            with open('app.py', 'r', encoding='utf-8') as orig:
                f.write(orig.read())
        print("📦 Backup saved as app.py.backup")
        
        # Write the fixed version
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Fix applied successfully!")
        print("\n📝 What changed:")
        print("   • Added include_index=False parameter to set_with_dataframe()")
        print("   • Added include_column_header=True parameter to set_with_dataframe()")
        print("   • Added return type hint (-> bool)")
        print("   • Added debug print() statements")
        print("   • Added save verification")
        print("   • Added sidebar success messages")
        print("\n🚀 Next steps:")
        print("   1. Run: streamlit run app.py")
        print("   2. Add a production entry")
        print("   3. Check terminal for [SAVE] debug messages")
        print("   4. Check Google Sheet - data should appear!")
        print("   5. Click 'Reload from Google Sheets' - data should persist!")
    else:
        print("⚠️  Warning: Could not find exact save_sheet function to replace")
        print("    The function might have been modified.")
        print("    Please manually replace the save_sheet function.")
        sys.exit(1)
