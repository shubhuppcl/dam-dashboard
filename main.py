from fastapi import FastAPI, Query
import duckdb
import pandas as pd
from typing import List, Optional

app = FastAPI(title="DAM Dashboard API")
DB_FILE = 'database.db'

@app.get("/plants")
def get_plants():
    conn = duckdb.connect(DB_FILE)
    plants = conn.execute("SELECT DISTINCT plant_name FROM plant_data ORDER BY plant_name").fetchall()
    conn.close()
    return [p[0] for p in plants]

@app.get("/data")
def get_data(
    plants: Optional[List[str]] = Query(None),
    start_block: int = 1,
    end_block: int = 96
):
    conn = duckdb.connect(DB_FILE)
    query = "SELECT * FROM plant_data WHERE time_block BETWEEN ? AND ?"
    params = [start_block, end_block]
    
    if plants:
        placeholders = ', '.join(['?'] * len(plants))
        query += f" AND plant_name IN ({placeholders})"
        params.extend(plants)
        
    df = conn.execute(query, params).df()
    conn.close()
    return df.to_dict(orient="records")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
