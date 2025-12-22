import pandas as pd
import os

csv_files = ['entvsdl.csv', 'ipp.csv', 'trader.csv', 'uprvunl.csv']
data_dir = 'data'

with open('all_columns.txt', 'w', encoding='utf-8') as f:
    for file in csv_files:
        f.write(f"--- {file} ---\n")
        path = os.path.join(data_dir, file)
        if not os.path.exists(path):
            f.write(f"File not found: {path}\n\n")
            continue
            
        try:
            if file == 'entvsdl.csv':
                df = pd.read_csv(path, header=[0, 1, 2], nrows=0)
                cols = [' | '.join(col).strip() for col in df.columns.values]
            else:
                df = pd.read_csv(path, nrows=0)
                cols = df.columns.tolist()
            
            for c in cols:
                f.write(c + '\n')
        except Exception as e:
            f.write(f"Error reading {file}: {e}\n")
        f.write('\n')

print("Columns listed in all_columns.txt")
