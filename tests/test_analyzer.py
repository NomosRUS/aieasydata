#!/usr/bin/env python3

import sys
import os
sys.path.append('backend')

from backend.app.analyzer import quick_profile

def test_analyzer():
    print("Testing improved analyzer...")
    
    # Тестируем анализ файла
    result = quick_profile({'source_path': '/data/raw/sales_extended.csv'})
    
    print("Analysis results:")
    print(f"  File: /data/raw/sales_extended.csv")
    print(f"  Estimated rows: {result.get('est_rows', 'N/A')}")
    print(f"  Columns found: {len(result.get('columns', []))}")
    
    print("\nColumn details:")
    for i, col in enumerate(result.get('columns', []), 1):
        print(f"  {i}. {col['name']} ({col['type']})")
    
    print(f"\nTime fields: {result.get('ts_fields', [])}")
    
    if 'error' in result:
        print(f"Error: {result['error']}")
    
    if 'sample' in result and result['sample']:
        print(f"\nSample data (first row): {result['sample'][0]}")
    
    return result

if __name__ == "__main__":
    test_analyzer()
