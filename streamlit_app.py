import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# ==============================
# CONFIGURATION
# ==============================
SHEET_NAME = "Society_Maintenance"
WORKSHEET_NAME = "Due_Amounts"
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ==============================
# GOOGLE SHEETS AUTHENTICATION USING SECRETS
# ==============================
# Load service account info from Streamlit secrets
service_account_info = dict(st.secrets["google"])
# Replace literal \n with actual newlines in the private key
service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")

# Authenticate
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

# ==============================
# STREAMLIT UI
# ==============================
st.set_page_config(page_title="🏘️ Society Maintenance Dashboard — Dues", layout="wide")
st.title("🏘️ Brahmaputra Apartment Dashboard — Dues Overview")

# ==============================
# LOAD DATA
# ==============================
data = sheet.get_all_records()
df = pd.DataFrame(data)

if df.empty:
    st.warning("No data found in the sheet. Please add headers and some records first.")
    st.stop()

# Columns that can be edited
editable_cols = ["# of Bike", "# of Cycle", "# of Months Due"]

# Initialize session state
if "edited_df" not in st.session_state:
    st.session_state.edited_df = df.copy()
if "changed_rows" not in st.session_state:
    st.session_state.changed_rows = set()  # Track rows that were edited

# ==============================
# RECALC FUNCTION
# ==============================
def recalc_row(row):
    """Recalculate totals for a single row"""
    row["Total Amount/Month"] = (
        float(row["Regular Maintenance"])
        + int(row["# of Bike"]) * 100
        + int(row["# of Cycle"]) * 50
        + float(row["Shop Area"])
        + float(row["Parking Area"])
    )
    row["Total Outstanding Amount"] = row["Total Amount/Month"] * int(row["# of Months Due"])
    return row

# ==============================
# SAVE / DISCARD BUTTONS AT TOP
# ==============================
col_save, col_discard = st.columns(2)

with col_save:
    if st.button("💾 Save Changes"):
        try:
            updated_cells = []
            for i in st.session_state.changed_rows:
                for col in editable_cols:
                    new_value = st.session_state.edited_df.at[i, col]
                    row_index = i + 2  # header row is 1
                    col_index = list(df.columns).index(col) + 1
                    safe_value = int(new_value) if pd.notnull(new_value) else 0
                    sheet.update_cell(row_index, col_index, safe_value)
                    updated_cells.append(f"{col} row {row_index}")
            if updated_cells:
                st.success(f"✅ Updated cells: {', '.join(updated_cells)}")
                st.session_state.changed_rows.clear()  # reset
            else:
                st.info("No changes detected to save.")
        except Exception as e:
            st.error(f"❌ Failed to save data: {e}")

with col_discard:
    if st.button("❌ Discard Changes"):
        st.session_state.edited_df = df.copy()
        st.session_state.changed_rows.clear()
        st.success("🗑️ All changes discarded!")

# ==============================
# COLLAPSIBLE DATA EDITOR
# ==============================
with st.expander("📋 Edit Maintenance Dues (Click to Expand)", expanded=False):
    edited_df = st.data_editor(
        st.session_state.edited_df,
        column_config={
            col: st.column_config.NumberColumn(col, format="%d", min_value=0)
            for col in editable_cols
        },
        hide_index=True,
        key="data_editor"
    )

    # Detect changes and recalc only affected rows
    for i in range(len(edited_df)):
        for col in editable_cols:
            if edited_df.at[i, col] != st.session_state.edited_df.at[i, col]:
                st.session_state.edited_df.at[i, col] = edited_df.at[i, col]
                st.session_state.edited_df.iloc[i] = recalc_row(st.session_state.edited_df.iloc[i])
                st.session_state.changed_rows.add(i)

# Display the updated table outside the expander
st.subheader("📊 Updated Calculations")
st.dataframe(st.session_state.edited_df, use_container_width=True)
