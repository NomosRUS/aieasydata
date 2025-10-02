import uvicorn
from fastapi import FastAPI, HTTPException
from pathlib import Path
import pandas as pd

app = FastAPI()

BASE_PATH = Path(__file__).parent / "data_landing_zone/raw/external/api_sources"

@app.get("/{db_type}")
async def get_db_info(db_type: str):
    db_path = BASE_PATH / db_type
    if not db_path.exists() or not db_path.is_dir():
        raise HTTPException(status_code=404, detail="Database not found")

    tables = [p.stem for p in db_path.glob("*.csv")]
    return {"database": db_type, "tables": tables}

@app.get("/{db_type}/{table_name}")
async def get_table_info(db_type: str, table_name: str):
    table_path = BASE_PATH / db_type / f"{table_name}.csv"
    if not table_path.exists():
        raise HTTPException(status_code=404, detail="Table not found")

    try:
        df = pd.read_csv(table_path)
        schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
        return {
            "table": table_name,
            "schema": schema,
            "sample_data": df.head().to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading table: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
