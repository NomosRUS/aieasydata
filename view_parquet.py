"""
Удобный просмотрщик Parquet файлов.
Использование: python view_parquet.py <путь_к_файлу>
"""

import sys
import pandas as pd
from pathlib import Path

def view_parquet(file_path):
    """Просматривает Parquet файл с детальной информацией."""
    
    try:
        # Загружаем файл
        df = pd.read_parquet(file_path)
        
        print("=" * 60)
        print(f"ФАЙЛ: {file_path}")
        print("=" * 60)
        
        # Основная информация
        print(f"РАЗМЕР: {df.shape[0]} строк x {df.shape[1]} колонок")
        print(f"ПАМЯТЬ: {df.memory_usage(deep=True).sum():,} байт")
        print(f"КОЛОНКИ: {list(df.columns)}")
        
        # Типы данных
        print(f"\nТИПЫ ДАННЫХ:")
        for col, dtype in df.dtypes.items():
            null_count = df[col].isnull().sum()
            print(f"  {col}: {dtype} (null: {null_count})")
        
        # Первые строки
        print(f"\nПЕРВЫЕ 10 СТРОК:")
        print(df.head(10).to_string())
        
        # Последние строки если файл большой
        if len(df) > 10:
            print(f"\nПОСЛЕДНИЕ 5 СТРОК:")
            print(df.tail(5).to_string())
        
        # Статистика для числовых колонок
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            print(f"\nСТАТИСТИКА ЧИСЛОВЫХ КОЛОНОК:")
            print(df[numeric_cols].describe().to_string())
        
        # Уникальные значения для категориальных колонок
        categorical_cols = df.select_dtypes(include=['object']).columns
        if len(categorical_cols) > 0:
            print(f"\nУНИКАЛЬНЫЕ ЗНАЧЕНИЯ:")
            for col in categorical_cols:
                unique_vals = df[col].dropna().unique()
                if len(unique_vals) <= 10:
                    print(f"  {col}: {list(unique_vals)}")
                else:
                    print(f"  {col}: {len(unique_vals)} уникальных значений")
        
        # Информация о пропущенных значениях
        missing_info = df.isnull().sum()
        if missing_info.sum() > 0:
            print(f"\nПРОПУЩЕННЫЕ ЗНАЧЕНИЯ:")
            for col, missing_count in missing_info.items():
                if missing_count > 0:
                    percentage = (missing_count / len(df)) * 100
                    print(f"  {col}: {missing_count} ({percentage:.1f}%)")
        
        print("\n" + "=" * 60)
        print("ПРОСМОТР ЗАВЕРШЕН")
        print("=" * 60)
        
    except Exception as e:
        print(f"ОШИБКА: {str(e)}")
        return False
    
    return True

def main():
    if len(sys.argv) != 2:
        print("Использование: python view_parquet.py <путь_к_файлу>")
        print("\nПример:")
        print("python view_parquet.py data_landing_zone/aggregated/game_test_mixed_data/game_test_mixed_data.parquet")
        return
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"Файл не найден: {file_path}")
        return
    
    view_parquet(file_path)

if __name__ == "__main__":
    main()
