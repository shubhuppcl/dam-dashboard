import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db_utils import get_data

st.set_page_config(page_title="DAM Merit Plants - Operational View", layout="wide")

# Custom CSS for Black-and-Green Aesthetic with White Borders
st.markdown("""
    <style>
    /* Main Background and Text Color */
    .stApp, .main, .stApp > header {
        background-color: #000000 !important;
        color: #00FF00 !important;
    }
    
    /* Global Text and Header Color */
    h1, h2, h3, h4, p, span, div, label {
        color: #00FF00 !important;
        font-family: 'Courier New', Courier, monospace;
    }

    /* Buttons / Grid Selector */
    .stButton>button {
        width: 100%;
        padding: 2px;
        font-size: 10px;
        border-radius: 4px;
        background-color: #000000 !important;
        color: #00FF00 !important;
        border: 1px solid #FFFFFF !important;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #00FF00 !important;
        color: #000000 !important;
        border-color: #00FF00 !important;
    }

    /* Selected Block Button */
    div.stButton > button[kind="primary"] {
        background-color: #00FF00 !important;
        color: #000000 !important;
        border: 2px solid #FFFFFF !important;
        font-weight: bold;
    }

    /* Tables */
    .stDataFrame, div[data-testid="stTable"] {
        border: 1px solid #FFFFFF !important;
        background-color: #000000 !important;
    }
    
    [data-testid="stDataFrameResizable"] div {
        color: #00FF00 !important;
        background-color: #000000 !important;
    }
    
    /* Metadata/Sidebar Filters */
    section[data-testid="stSidebar"] {
        background-color: #000000 !important;
        border-right: 1px solid #FFFFFF !important;
    }
    
    /* Detailed Table Borders and Visibility */
    [data-testid="stDataFrameResizable"] {
        border: 1px solid #FFFFFF !important;
    }
    
    /* Ensuring headers and cells have clear structure and green text */
    /* Streamlit's new dataframe (Glide Data Grid) uses canvas, but we can target the containers */
    [data-testid="stDataFrame"] {
        background-color: #000000 !important;
    }

    /* Target the actual data grid elements if they are HTML based */
    .stDataFrame div, .stDataFrame span, .stDataFrame td, .stDataFrame th {
        color: #00FF00 !important;
    }

    /* If it's the legacy table */
    [data-testid="stTable"] td, [data-testid="stTable"] th {
        color: #00FF00 !important;
        border: 1px solid #FFFFFF !important;
    }

    /* Forcing visibility on the dataframe rows */
    div[data-testid="stDataFrameResizable"] [role="gridcell"] {
        color: #00FF00 !important;
    }

    /* Metric Card Glow/Border */
    .metric-card {
        background-color: #000000;
        border: 2px solid #FFFFFF;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
        margin-bottom: 20px;
    }

    /* Info and Warning boxes */
    .stAlert {
        background-color: #000000 !important;
        color: #00FF00 !important;
        border: 1px solid #FFFFFF !important;
    }
    
    /* Scrollbars (Chrome/Safari) */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #000000;
    }
    ::-webkit-scrollbar-thumb {
        background: #FFFFFF;
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #00FF00;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div style="font-size: 32px; font-weight: bold; border-bottom: 2px solid #FFFFFF; padding-bottom: 10px; margin-bottom: 20px;">⚡ MERIT PLANT OPERATIONAL SYSTEM</div>', unsafe_allow_html=True)

# Helper for Time Range
def get_time_range(block):
    start_min = (block - 1) * 15
    start_time = datetime(2025, 1, 1, 0, 0) + timedelta(minutes=start_min)
    end_time = start_time + timedelta(minutes=15)
    return f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"

# Session State for Selection
if 'selected_block' not in st.session_state:
    st.session_state.selected_block = 1

# Grid Selector Section
st.subheader("🕒 GRID SELECTOR (TIME RANGES)")

# Create 6x16 Grid
for r in range(6):
    cols = st.columns(16)
    for c in range(16):
        block_num = r * 16 + c + 1
        is_selected = st.session_state.selected_block == block_num
        # Use full time range label
        time_label = get_time_range(block_num)
        
        if cols[c].button(time_label, key=f"btn_{block_num}", type="primary" if is_selected else "secondary"):
            st.session_state.selected_block = block_num
            st.rerun()

st.info(f"MONITORING: **BLOCK {st.session_state.selected_block}** | **TIME: {get_time_range(st.session_state.selected_block)}**")

# Sidebar Filters
st.sidebar.markdown("<h2 style='color: #00FF00;'>CONTROLS</h2>", unsafe_allow_html=True)
remove_zero_dc = st.sidebar.checkbox("Remove plants with DC = 0", value=False)

# Fetch Data for specific block
@st.cache_data(ttl=60)
def fetch_block_data(block_num):
    return get_data(block_num)

df = fetch_block_data(st.session_state.selected_block)

if not df.empty:
    # Sorting by Variable Cost (bid_price_mwh) in Decreasing Order
    df = df.sort_values(by='bid_price_mwh', ascending=False)
    
    # Filter for DC > 0 if requested
    if remove_zero_dc:
        df = df[df['dc_mw'] > 0]
    
    # Selection of required columns
    display_df = df[['plant_name', 'plant_type', 'dc_mw', 'sg_mw', 'bid_price_mwh']]
    display_df.columns = ['Plant', 'Type', 'DC (MW)', 'SG (MW)', 'Variable Cost (Rs/MWh)']
    
    # Calculate Thermal Backing
    # state plants are all plants in uprvunl file and ipp file.
    # central plants consists of all plants in entvssdl menukh and trader file.
    
    state_df = df[df['category'] == 'State']
    central_df = df[df['category'] == 'Central']
    
    def calculate_backing(df_cat):
        if df_cat.empty:
            return "None", 0.0
        
        # Ignore plants whose SG=0 in these calculations as requested
        active_df = df_cat[df_cat['sg_mw'] > 0]
        
        if active_df.empty:
            return "None", 0.0
            
        # Cumulative backing quantum = Sum of (DC - SG)
        total_quantum = (active_df['dc_mw'] - active_df['sg_mw']).sum()
        
        # Filter for plants whose SG < 0.98 * DC
        backing_candidates = active_df[active_df['sg_mw'] < 0.98 * active_df['dc_mw']]
        
        if not backing_candidates.empty:
            # Lowest Variable Cost plant
            lowest_vc_plant = backing_candidates.sort_values(by='bid_price_mwh', ascending=True).iloc[0]
            return lowest_vc_plant['plant_name'], total_quantum
        
        return "None", total_quantum

    state_plant, state_quantum = calculate_backing(state_df)
    central_plant, central_quantum = calculate_backing(central_df)
    
    # Metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f'<div class="metric-card"><h3>TOTAL DC</h3><h2 style="color: #00FF00 !important;">{df["dc_mw"].sum():,.2f} MW</h2></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><h3>TOTAL SG</h3><h2 style="color: #00FF00 !important;">{df["sg_mw"].sum():,.2f} MW</h2></div>', unsafe_allow_html=True)
    with m3:
        backing_html = f"""
        <div class="metric-card">
            <h3>THERMAL BACKING</h3>
            <p style="margin:0; font-size:12px; color:#FFFFFF !important;">STATE: <span style="color:#00FF00;">{state_plant}</span> ({state_quantum/1000:,.2f} GW)</p>
            <p style="margin:0; font-size:12px; color:#FFFFFF !important;">CENTRAL: <span style="color:#00FF00;">{central_plant}</span> ({central_quantum/1000:,.2f} GW)</p>
        </div>
        """
        st.markdown(backing_html, unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 1px solid #FFFFFF;'>", unsafe_allow_html=True)
    
    # Detailed Table
    st.subheader(f"📊 MERIT ORDER DATA - BLOCK {st.session_state.selected_block}")
    
    # Custom HTML Table implementation for 100% style control
    def render_custom_table(df):
        html = """
        <div style="overflow-x:auto;">
            <table style="width:100%; border-collapse: collapse; border: 1px solid #FFFFFF; background-color: #000000; color: #00FF00; font-family: 'Courier New', Courier, monospace;">
                <thead>
                    <tr style="border-bottom: 2px solid #FFFFFF;">
                        <th style="padding: 12px; text-align: left; border-right: 1px solid #FFFFFF;">Plant</th>
                        <th style="padding: 12px; text-align: left; border-right: 1px solid #FFFFFF;">Type</th>
                        <th style="padding: 12px; text-align: right; border-right: 1px solid #FFFFFF;">DC (MW)</th>
                        <th style="padding: 12px; text-align: right; border-right: 1px solid #FFFFFF;">SG (MW)</th>
                        <th style="padding: 12px; text-align: right;">Variable Cost (Rs/MWh)</th>
                    </tr>
                </thead>
                <tbody>
        """
        for _, row in df.iterrows():
            html += f"""
                    <tr style="border-bottom: 1px solid #FFFFFF;">
                        <td style="padding: 8px; border-right: 1px solid #FFFFFF;">{row['Plant']}</td>
                        <td style="padding: 8px; border-right: 1px solid #FFFFFF;">{row['Type']}</td>
                        <td style="padding: 8px; text-align: right; border-right: 1px solid #FFFFFF;">{row['DC (MW)']:,.2f}</td>
                        <td style="padding: 8px; text-align: right; border-right: 1px solid #FFFFFF;">{row['SG (MW)']:,.2f}</td>
                        <td style="padding: 8px; text-align: right;">{row['Variable Cost (Rs/MWh)']:,.2f}</td>
                    </tr>
            """
        html += """
                </tbody>
            </table>
        </div>
        """
        return html

    st.html(render_custom_table(display_df))

else:
    st.warning(f"SYSTEM ALERT: No data available for Time Block {st.session_state.selected_block}")

st.sidebar.markdown("<hr style='border: 1px solid #FFFFFF;'>", unsafe_allow_html=True)
st.sidebar.caption("SYS_SOURCE: merit_order_report.csv | entvsdl.csv")
