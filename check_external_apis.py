import requests
import json
from pathlib import Path

def check_apis():
    """Checks configured external APIs and prints their tables and columns."""
    api_sources_path = Path(__file__).parent / "data_landing_zone/metadata/exports/external_api_sources.json"

    if not api_sources_path.exists():
        print(f"Error: API sources file not found at {api_sources_path}")
        return

    with open(api_sources_path, 'r', encoding='utf-8') as f:
        api_sources = json.load(f)

    print("--- Checking External API Sources ---")

    for source in api_sources:
        name = source.get("name")
        uri = source.get("uri")
        print(f"\n[+] Source: {name} ({uri})")

        try:
            # Get list of tables
            response = requests.get(uri, timeout=5)
            response.raise_for_status()
            db_info = response.json()
            tables = db_info.get('tables', [])

            if not tables:
                print("    No tables found.")
                continue

            # Get schema for each table
            for table_name in tables:
                table_url = f"{uri}/{table_name}"
                table_response = requests.get(table_url, timeout=5)
                table_response.raise_for_status()
                table_info = table_response.json()
                columns = list(table_info.get('schema', {}).keys())
                print(f"    - Table: {table_name}")
                print(f"      Columns: {', '.join(columns)}")

        except requests.exceptions.RequestException as e:
            print(f"    Error connecting to API: {e}")
        except Exception as e:
            print(f"    An unexpected error occurred: {e}")

if __name__ == "__main__":
    check_apis()
