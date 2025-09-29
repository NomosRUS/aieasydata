import subprocess
import time
import pytest
import requests
import sys
from pathlib import Path

# Add the backend app path to the sys.path to allow for module imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.metrics_collector.data_type_detector import DataTypeDetector

@pytest.fixture(scope="module")
def fake_api_server():
    """Fixture to start and stop the fake API server."""
    # Command to run the fake API server
    command = [sys.executable, "fake_external_api.py"]
    
    # Start the server as a background process
    server_process = subprocess.Popen(command, cwd=Path(__file__).resolve().parent.parent)
    
    # Wait for the server to be ready
    retries = 5
    while retries > 0:
        try:
            response = requests.get("http://127.0.0.1:8001/postgres_db", timeout=1)
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            retries -= 1
    
    if retries == 0:
        server_process.terminate()
        pytest.fail("Failed to start the fake API server.")

    yield
    
    # Teardown: stop the server
    server_process.terminate()
    server_process.wait()

def test_detect_postgres_api_source(fake_api_server):
    """
    Tests the detection and analysis of an external PostgreSQL source via API.
    """
    detector = DataTypeDetector()
    source_url = "http://127.0.0.1:8001/postgres_db"

    result = detector.detect_data_type(source_url)

    assert result is not None
    assert result.get('type') == 'api'
    assert result.get('name') == 'External PostgreSQL DB'
    assert result.get('db_type') == 'postgres'
    assert result.get('error') is None
    assert len(result.get('tables', [])) == 2

    # Check users table
    users_table = next((t for t in result['tables'] if t['table'] == 'users'), None)
    assert users_table is not None
    assert 'user_id' in users_table['schema']
    assert 'username' in users_table['schema']
    assert len(users_table['sample_data']) > 0

def test_detect_clickhouse_api_source(fake_api_server):
    """
    Tests the detection and analysis of an external ClickHouse source via API.
    """
    detector = DataTypeDetector()
    source_url = "http://127.0.0.1:8001/clickhouse_db"

    result = detector.detect_data_type(source_url)

    assert result is not None
    assert result.get('type') == 'api'
    assert result.get('name') == 'External ClickHouse DB'
    assert result.get('db_type') == 'clickhouse'
    assert result.get('error') is None
    assert len(result.get('tables', [])) == 2

    # Check products table
    products_table = next((t for t in result['tables'] if t['table'] == 'products'), None)
    assert products_table is not None
    assert 'product_id' in products_table['schema']
    assert 'price' in products_table['schema']
    assert len(products_table['sample_data']) > 0
