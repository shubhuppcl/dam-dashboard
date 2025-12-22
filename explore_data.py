import pandas as pd
import os
import sys

# Save output to a file
with open('data_exploration_results.txt', 'w', encoding='utf-8') as f:
    sys.stdout = f
    
    data_dir = r'data'
    mod_file = os.path.join(data_dir, 'MOD List Dec_16-12-2025.xlsx')

    print("--- MOD List ---")
    try:
        df_mod = pd.read_excel(mod_file)
        print("Columns:", df_mod.columns.tolist())
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(df_mod.head(30))
        print("\nAll Plants in MOD file:")
        print(df_mod['Plant Name'].tolist())
    except Exception as e:
        print(f"Error reading MOD file: {e}")

    csv_files = ['entvsdl.csv', 'ipp.csv', 'uprvunl.csv', 'upjvnl.csv', 'cpp.csv', 'trader.csv']

    for file in csv_files:
        print(f"\n--- {file} ---")
        path = os.path.join(data_dir, file)
        try:
            if file == 'entvsdl.csv':
                # Read multiple headers
                df = pd.read_csv(path, header=[0, 1, 2], nrows=5)
                # Flatten multi-index columns for easier reading in the text file
                print("Flattened Columns:", [' | '.join(col).strip() for col in df.columns.values])
                print(df.head())
            else:
                df = pd.read_csv(path, nrows=5)
                print("Columns:", df.columns.tolist())
                print(df.head())
        except Exception as e:
            print(f"Error reading {file}: {e}")

sys.stdout = sys.__stdout__
print("Exploration completed. Results saved to data_exploration_results.txt")
