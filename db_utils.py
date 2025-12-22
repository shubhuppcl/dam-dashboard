import duckdb
import pandas as pd

DB_FILE = 'database.db'

def get_data(block_num):
    """
    Fetch data for a specific time block directly from DuckDB.
    """
    try:
        conn = duckdb.connect(DB_FILE, read_only=True)
        query = "SELECT * FROM plant_data WHERE time_block = ?"
        df = conn.execute(query, [block_num]).df()
        conn.close()
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()
