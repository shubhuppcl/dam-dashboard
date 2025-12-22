import pandas as pd
import os
import re

data_dir = 'data'
mod_file = os.path.join(data_dir, 'MOD List Dec_16-12-2025.xlsx')
df_mod = pd.read_excel(mod_file)

# Filter for Merit plants
merit_plants = df_mod[df_mod['Merit/Must'] == 'Merit']['Plant Name'].tolist()
print(f"Total Merit Plants found: {len(merit_plants)}")

csv_files = {
    'entvsdl.csv': {'header': [0, 1, 2]},
    'ipp.csv': {'header': 0},
    'trader.csv': {'header': 0},
    'uprvunl.csv': {'header': 0}
}

mapping_report = []

def clean_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '', str(name)).upper()

for filename, config in csv_files.items():
    path = os.path.join(data_dir, filename)
    if not os.path.exists(path):
        print(f"Warning: {filename} not found.")
        continue
    
    if filename == 'entvsdl.csv':
        df = pd.read_csv(path, header=config['header'], nrows=0)
        cols = [' | '.join(col).strip() for col in df.columns.values]
    else:
        df = pd.read_csv(path, nrows=0)
        cols = df.columns.tolist()

    print(f"\nAnalyzing {filename}...")
    for plant in merit_plants:
        plant_clean = clean_name(plant)
        
        found_dc = []
        found_sg = []
        
        for col in cols:
            col_clean = clean_name(col)
            
            # Heuristics for matching
            if plant_clean in col_clean:
                # Identification of DC vs SG
                if filename == 'entvsdl.csv':
                    # User said: DC is "Onbar Final Ent Amount" or "Final Ent Amount"
                    # User said: SG is "Schedule Amount"
                    if 'Final Ent Amount' in col and 'Onbar' in col:
                        found_dc.append(col)
                    elif 'Final Ent Amount' in col and 'Onbar' not in col and 'Offbar' not in col:
                        # For those without Onbar/Offbar distinction
                        found_dc.append(col)
                    elif 'Schedule Amount' in col:
                        found_sg.append(col)
                else:
                    # Other CSVs: "DC/ Entitlement" and "SG"
                    if 'DC/' in col:
                        found_dc.append(col)
                    elif 'SG' in col:
                        found_sg.append(col)
        
        if found_dc or found_sg:
            mapping_report.append({
                'MOD Plant': plant,
                'File': filename,
                'DC Columns': list(set(found_dc)),
                'SG Columns': list(set(found_sg))
            })

report_df = pd.DataFrame(mapping_report)
report_df.to_csv('mapping_report.csv', index=False)
print("\nMapping report saved to mapping_report.csv")

# Identify Missing Plants
mapped_plants = set(report_df['MOD Plant'].tolist())
missing_plants = [p for p in merit_plants if p not in mapped_plants]
print(f"\nMissing Plants ({len(missing_plants)}):")
for p in missing_plants:
    print(f"- {p}")
