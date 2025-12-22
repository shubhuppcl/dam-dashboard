import pandas as pd
import os
import json

# Paths
data_dir = 'data'
mod_file = os.path.join(data_dir, 'MOD List Dec_16-12-2025.xlsx')
mapping_file = 'plant_mappings.json'

# Load data
df_mod = pd.read_excel(mod_file)
merit_plants = df_mod[df_mod['Merit/Must'] == 'Merit']['Plant Name'].tolist()

with open(mapping_file, 'r', encoding='utf-8') as f:
    plant_mappings = json.load(f)

# CSV headers
csv_files = {
    'entvsdl.csv': {'header': [0, 1, 2]},
    'ipp.csv': {'header': 0},
    'trader.csv': {'header': 0},
    'uprvunl.csv': {'header': 0}
}

all_cols = {}
for filename, config in csv_files.items():
    path = os.path.join(data_dir, filename)
    if not os.path.exists(path):
        continue
    if filename == 'entvsdl.csv':
        df = pd.read_csv(path, header=config['header'], nrows=0)
        cols = [' | '.join(col).strip() for col in df.columns.values]
    else:
        df = pd.read_csv(path, nrows=0)
        cols = df.columns.tolist()
    all_cols[filename] = cols

# Verify
missing_in_json = [p for p in merit_plants if p not in plant_mappings]
print(f"Total Merit Plants: {len(merit_plants)}")
print(f"Missing in JSON: {len(missing_in_json)}")
for p in missing_in_json:
    print(f"- {p}")

mapping_coverage = {}
for plant in merit_plants:
    if plant in plant_mappings:
        keywords = plant_mappings[plant]
        found_match = False
        for filename, cols in all_cols.items():
            for col in cols:
                for kw in keywords:
                    if kw in col:
                        found_match = True
                        break
                if found_match: break
            if found_match: break
        mapping_coverage[plant] = found_match

not_found_in_csv = [p for p, found in mapping_coverage.items() if not found]
print(f"\nNot found in CSV columns: {len(not_found_in_csv)}")
for p in not_found_in_csv:
    print(f"- {p}")
