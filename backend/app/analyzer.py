def quick_profile(cfg: dict):
    """Real CSV profiler that analyzes actual file structure."""
    import pandas as pd
    import os
    from pathlib import Path
    
    source_path = cfg.get("source_path", "")
    
    # Конвертируем путь для доступа к файлу
    if source_path.startswith("/data/"):
        # В контейнере файлы монтируются в /data/, локально в data_landing_zone/
        if os.path.exists(source_path):
            # Мы в контейнере, используем прямой путь
            local_path = source_path
        else:
            # Мы локально, конвертируем путь
            local_path = source_path.replace("/data/", "data_landing_zone/")
    else:
        local_path = source_path
    
    # Проверяем существование файла
    if not os.path.exists(local_path):
        # Возвращаем заглушку если файл не найден
        return {
            "columns": [{"name":"dt","type":"Date"},{"name":"amount","type":"Int64"}], 
            "est_rows": 0, 
            "ts_fields":["dt"], 
            "sample": [],
            "error": f"File not found: {local_path}"
        }
    
    try:
        # Читаем CSV файл
        df = pd.read_csv(local_path)
        
        # Анализируем колонки и их типы
        columns = []
        for col_name in df.columns:
            # Определяем тип данных
            dtype = df[col_name].dtype
            
            if pd.api.types.is_integer_dtype(dtype):
                col_type = "Int64"
            elif pd.api.types.is_float_dtype(dtype):
                col_type = "Float64"
            elif pd.api.types.is_bool_dtype(dtype):
                col_type = "Boolean"
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                col_type = "DateTime"
            elif col_name.lower() in ['date', 'dt', 'sale_date', 'created_at', 'updated_at']:
                col_type = "Date"  # Эвристика для дат
            else:
                col_type = "String"
            
            columns.append({"name": col_name, "type": col_type})
        
        # Создаем образец данных (первые 3 строки)
        sample_data = []
        for _, row in df.head(3).iterrows():
            sample_row = {}
            for col in columns:
                value = row[col["name"]]
                # Конвертируем NaN в None
                if pd.isna(value):
                    sample_row[col["name"]] = None
                else:
                    sample_row[col["name"]] = str(value)
            sample_data.append(sample_row)
        
        # Определяем поля времени
        ts_fields = [col["name"] for col in columns if col["type"] in ["Date", "DateTime"]]
        
        return {
            "columns": columns,
            "est_rows": len(df),
            "ts_fields": ts_fields,
            "sample": sample_data,
            "file_size": os.path.getsize(local_path)
        }
        
    except Exception as e:
        # В случае ошибки возвращаем заглушку с информацией об ошибке
        return {
            "columns": [{"name":"dt","type":"Date"},{"name":"amount","type":"Int64"}], 
            "est_rows": 0, 
            "ts_fields":["dt"], 
            "sample": [],
            "error": f"Failed to analyze file: {str(e)}"
        }
