import pandas as pd
import duckdb
import os
import json
import re

# Configuration
DATA_DIR = 'data'
MOD_FILE = os.path.join(DATA_DIR, 'MOD List Dec_16-12-2025.xlsx')
MAPPING_FILE = 'plant_mappings.json'
DB_FILE = 'database.db'

CSV_CONFIGS = {
    'entvsdl.csv': {'header': [0, 1, 2]},
    'ipp.csv': {'header': 0},
    'trader.csv': {'header': 0},
    'uprvunl.csv': {'header': 0},
    'menukhdc.csv': {'header': [0, 1], 'encoding': 'utf-16le'},
    'menukhsg.csv': {'header': 6, 'encoding': 'utf-16le', 'special_sg': True}
}

def clean_col_name(col):
    if isinstance(col, tuple):
        return ' | '.join([str(c).strip() for c in col if 'Unnamed' not in str(c)])
    return str(col).strip()

def ingest():
    print("Starting ingestion...")
    
    # 1. Load Mappings
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        plant_mappings = json.load(f)
    
    # 2. Load MOD List (Merit Plants)
    df_mod = pd.read_excel(MOD_FILE)
    # Identifies the column containing the price (Rs/MWH or similar)
    price_col = next((c for c in df_mod.columns if 'Variable Cost' in c or 'Bid Price' in c), None)
    plant_col = next((c for c in df_mod.columns if 'Plant Name' in c), 'Plant Name')
    type_col = next((c for c in df_mod.columns if 'Type' in c), 'Type')
    
    # 3. Initialize DuckDB
    conn = duckdb.connect(DB_FILE)
    conn.execute("DROP TABLE IF EXISTS plant_data")
    conn.execute("""
        CREATE TABLE plant_data (
            time_block INTEGER,
            time_desc VARCHAR,
            plant_name VARCHAR,
            plant_type VARCHAR,
            category VARCHAR,
            dc_mw DOUBLE,
            sg_mw DOUBLE,
            bid_price_mwh DOUBLE
        )
    """)
    
    # 4. Process CSVs
    final_records = []
    
    for filename, config in CSV_CONFIGS.items():
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            print(f"Warning: {filename} not found.")
            continue
            
        print(f"Processing {filename}...")
        read_kwargs = {'header': config['header']}
        if 'encoding' in config:
            read_kwargs['encoding'] = config['encoding']
            
        df = pd.read_csv(path, **read_kwargs)
        
        # Flatten columns
        if isinstance(df.columns, pd.MultiIndex):
            cols = [clean_col_name(c) for c in df.columns]
        else:
            cols = df.columns.tolist()
        df.columns = cols

        # Specialized logic for menukhsg.csv header mapping
        if config.get('special_sg'):
            # Utility names are in Row 2 of the original file (which is Row -4 relative to header=6)
            # but simpler to just use Row 0 of the df columns if we skipped correctly
            # Actually, let's use the explicit row 2 from file
            df_header = pd.read_csv(path, encoding=config['encoding'], header=None, nrows=5)
            utility_row = df_header.iloc[2].tolist()
            sg_mapping_override = {}
            for i, val in enumerate(utility_row):
                if pd.notna(val) and str(val).strip():
                    sg_mapping_override[str(val).strip()] = df.columns[i]

        # Extract Time Block and Time
        tb_col = next((c for c in cols if 'TIME BLOCK' in str(c).upper() or 'TIMEBLOCK' in str(c).upper().replace(' ', '')), None)
        td_col = next((c for c in cols if 'TIME DESC' in str(c).upper() or 'TIME' == str(c).upper().strip() or 'TIME' in str(c).upper()), None)
        
        # Fallback for menukhsg logic where Time Block might be in row 0
        if tb_col is None:
            first_row = df.iloc[0].astype(str).tolist()
            for i, val in enumerate(first_row):
                if 'TIME BLOCK' in val.upper():
                    tb_col = df.columns[i]
                elif 'TIME DESC' in val.upper() or '00:00-00:15' in val:
                    td_col = df.columns[i]
        
        if tb_col is None or td_col is None:
            print(f"Error: Could not find Time Block/Desc columns in {filename}")
            continue

        # Assign category
        category = 'State' if filename in ['uprvunl.csv', 'ipp.csv'] else 'Central'

        # DEFENSIVE: If multiple columns have the same name, take the first one
        if isinstance(df[tb_col], pd.DataFrame):
            df_tb = df[tb_col].iloc[:, 0]
        else:
            df_tb = df[tb_col]
            
        if isinstance(df[td_col], pd.DataFrame):
            df_td = df[td_col].iloc[:, 0]
        else:
            df_td = df[td_col]
            
        # Re-assign to a temporary series to avoid name clashes during filter
        df['__tb'] = pd.to_numeric(df_tb, errors='coerce')
        df['__td'] = df_td.astype(str).str.strip()
        
        # Clean-up rows: drop rows with NaN in time block or time desc
        df = df.dropna(subset=['__tb', '__td']).reset_index(drop=True)

        # In files where Row 0 is just repeat labels or empty
        if len(df) > 0 and 'TIME BLOCK' in str(df['__tb'].iloc[0]).upper():
            df = df.iloc[1:].reset_index(drop=True)
            
        # Refine type and filter
        df['__tb'] = pd.to_numeric(df['__tb'], errors='coerce').fillna(0).astype(int)
        
        # We only want blocks 1-96
        df = df[(df['__tb'] >= 1) & (df['__tb'] <= 96)]
        
        # Override original cols with cleaned ones for loop below
        df[tb_col] = df['__tb']
        df[td_col] = df['__td']

        for mod_name, aliases in plant_mappings.items():
            # Get Bid Price and Type from MOD
            try:
                mod_row = df_mod[df_mod[plant_col] == mod_name].iloc[0]
                bid_price = mod_row[price_col]
                # If Rs/kWh, convert to Rs/MWh
                if 'Rs/kWh' in str(price_col):
                    bid_price = float(bid_price) * 1000
                plant_type = str(mod_row[type_col])
            except:
                bid_price = 0.0
                plant_type = "Unknown"
                
            dc_cols = []
            sg_cols = []
            
            for alias in aliases:
                # User confirmed Ghatampur in ipp.csv is a duplicate and should be ignored
                if filename == 'ipp.csv' and mod_name == 'GHATAMPUR':
                    continue
                    
                # Use special SG mapping for menukhsg if alias matches
                if config.get('special_sg'):
                    for util_name, col_name in sg_mapping_override.items():
                        if alias.upper() in util_name.upper():
                            sg_cols.append(col_name)
                
                for col in cols:
                    if alias in col:
                        # Logic to distinguish DC vs SG
                        if filename == 'entvsdl.csv':
                            if 'Final Ent Amount' in col and 'Onbar' in col:
                                dc_cols.append(col)
                            elif 'Schedule Amount' in col:
                                sg_cols.append(col)
                        elif filename == 'menukhdc.csv':
                            # DC for these plants is strictly under "Total Ent"
                            # We check the last part of the flattened column name
                            if col.split(' | ')[-1] == 'Total Ent':
                                dc_cols.append(col)
                        else:
                            if 'DC/' in col:
                                dc_cols.append(col)
                            elif 'SG' in col and filename != 'menukhsg.csv': # Skip general SG check if already handled by override
                                sg_cols.append(col)
            
            # Deduplicate columns if they were matched multiple times
            dc_cols = list(set(dc_cols))
            sg_cols = list(set(sg_cols))

            if dc_cols or sg_cols:
                # Sum columns if multiple matches (e.g. multi-unit)
                temp_df = pd.DataFrame()
                temp_df['time_block'] = df[tb_col]
                temp_df['time_desc'] = df[td_col]
                temp_df['plant_name'] = mod_name
                temp_df['plant_type'] = plant_type
                temp_df['category'] = category
                
                if dc_cols:
                    temp_df['dc_mw'] = pd.to_numeric(df[dc_cols].stack(), errors='coerce').unstack().sum(axis=1)
                else:
                    temp_df['dc_mw'] = 0.0
                    
                if sg_cols:
                    # Values might have '+' or characters in menukhsg
                    for c in sg_cols:
                        df[c] = df[c].astype(str).str.replace('+', '', regex=False)
                    temp_df['sg_mw'] = pd.to_numeric(df[sg_cols].stack(), errors='coerce').unstack().sum(axis=1)
                else:
                    temp_df['sg_mw'] = 0.0

                temp_df['bid_price_mwh'] = bid_price
                
                final_records.append(temp_df)

    if final_records:
        df_final = pd.concat(final_records, ignore_index=True)
        # Aggregate to prevent duplicates if a plant is in multiple files (e.g., Tanda Stage II, Meja)
        
        # EXPLICITLY CLEAN keys before groupby
        df_final['time_block'] = pd.to_numeric(df_final['time_block'], errors='coerce').fillna(0).astype(int)
        df_final['plant_name'] = df_final['plant_name'].astype(str).str.strip()
        df_final['bid_price_mwh'] = pd.to_numeric(df_final['bid_price_mwh'], errors='coerce').fillna(0.0)
        
        # print(f"DEBUG: Pre-aggregation rows: {len(df_final)}")
        
        # Group by the invariant keys
        df_final = df_final.groupby(['time_block', 'plant_name'], as_index=False).agg({
            'time_desc': 'first',
            'plant_type': 'first',
            'category': 'first',
            'dc_mw': 'sum',
            'sg_mw': 'sum',
            'bid_price_mwh': 'max'
        })
        
        # EXPLICITLY REORDER columns to match DuckDB schema
        df_final = df_final[['time_block', 'time_desc', 'plant_name', 'plant_type', 'category', 'dc_mw', 'sg_mw', 'bid_price_mwh']]
        
        # print(f"DEBUG: Post-aggregation rows: {len(df_final)}")
        conn.append('plant_data', df_final)
        print(f"Ingested {len(df_final)} rows.")
    else:
        print("No data found to ingest.")
        
    conn.close()

if __name__ == "__main__":
    ingest()
