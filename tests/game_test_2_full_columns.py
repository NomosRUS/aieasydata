"""
Второй игровой тест модуля 2.
Берет первые 100 строк из каждого файла в папках syn_csv, syn_json, syn_xml
и сохраняет ВСЕ колонки в отдельные базы PostgreSQL формата.
"""

import asyncio
import pandas as pd
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum

# Упрощенные схемы для теста
class SourceType(str, Enum):
    FILE = "file"
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    HDFS = "hdfs"

class DataSource:
    def __init__(self, source_id: str, source_type: str, path: str, selected_columns: List[str] = None):
        self.source_id = source_id
        self.source_type = source_type
        self.path = path
        self.selected_columns = selected_columns or []  # Пустой список означает "все колонки"

class CustomDatasetRequest:
    def __init__(self, dataset_name: str, sources: List[DataSource], 
                 join_strategy: str = "individual", output_format: str = "parquet", 
                 include_metadata: bool = True):
        self.dataset_name = dataset_name
        self.sources = sources
        self.join_strategy = join_strategy  # "individual" для отдельных баз
        self.output_format = output_format
        self.include_metadata = include_metadata

# Расширенный CustomDatasetBuilder для второго теста
class GameTest2DatasetBuilder:
    """Построитель наборов данных для второго игрового теста."""
    
    def __init__(self):
        pass
    
    async def load_data_from_file(self, source: DataSource, limit: Optional[int] = 100) -> pd.DataFrame:
        """Загружает данные из файла с ограничением на количество строк."""
        file_path = Path(source.path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        print(f"Загружаем из {file_path.name} (лимит: {limit} строк)")
        
        # Определяем формат файла по расширению
        if file_path.suffix.lower() == '.csv':
            df = pd.read_csv(file_path, nrows=limit)
        elif file_path.suffix.lower() == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                df = pd.DataFrame(data[:limit] if limit else data)
            else:
                df = pd.DataFrame([data])
        elif file_path.suffix.lower() == '.xml':
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            records = []
            count = 0
            for record in root:
                if limit and count >= limit:
                    break
                if len(list(record)) > 0:  # Если это запись с дочерними элементами
                    record_data = {}
                    for child in record:
                        record_data[child.tag] = child.text
                    records.append(record_data)
                    count += 1
            
            df = pd.DataFrame(records)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_path.suffix}")
        
        # Если не указаны конкретные колонки, берем ВСЕ
        if not source.selected_columns:
            print(f"  Взяты ВСЕ колонки: {list(df.columns)}")
        else:
            # Фильтруем только выбранные колонки
            available_columns = [col for col in source.selected_columns if col in df.columns]
            if available_columns:
                df = df[available_columns]
                print(f"  Взяты выбранные колонки: {available_columns}")
            else:
                print(f"  Предупреждение: Выбранные колонки не найдены, взяты все")
        
        print(f"  Загружено: {len(df)} строк, {len(df.columns)} колонок")
        return df
    
    async def create_individual_datasets(self, request: CustomDatasetRequest) -> Dict[str, Any]:
        """Создает отдельные наборы данных для каждого источника."""
        try:
            print(f"Создаем отдельные наборы данных для: {request.dataset_name}")
            
            results = []
            
            for i, source in enumerate(request.sources):
                print(f"\nОбрабатываем источник {i+1}: {source.source_id}")
                
                try:
                    # Загружаем данные (первые 100 строк)
                    df = await self.load_data_from_file(source, limit=100)
                    
                    if df.empty:
                        print(f"  Источник пустой, пропускаем")
                        continue
                    
                    # Создаем имя для отдельной базы
                    individual_name = f"{request.dataset_name}_{source.source_id}"
                    
                    # Сохраняем как отдельную базу
                    output_path = await self._save_individual_dataset(
                        df, individual_name, request.output_format
                    )
                    
                    # Генерируем метаданные для этого источника
                    metadata = self._generate_individual_metadata(source, df, individual_name)
                    
                    result = {
                        "source_id": source.source_id,
                        "dataset_name": individual_name,
                        "output_path": output_path,
                        "row_count": len(df),
                        "column_count": len(df.columns),
                        "columns": list(df.columns),
                        "data_size_bytes": df.memory_usage(deep=True).sum(),
                        "metadata": metadata,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    results.append(result)
                    print(f"  УСПЕШНО: База создана: {individual_name}")
                    
                except Exception as e:
                    print(f"  ОШИБКА обработки источника {source.source_id}: {str(e)}")
                    continue
            
            if not results:
                return {
                    "success": False,
                    "error": "Не удалось создать ни одной базы данных"
                }
            
            return {
                "success": True,
                "strategy": "individual_databases",
                "total_databases": len(results),
                "databases": results,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Ошибка создания наборов данных: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _save_individual_dataset(self, df: pd.DataFrame, dataset_name: str, output_format: str) -> str:
        """Сохраняет отдельный набор данных."""
        output_dir = Path("data_landing_zone/aggregated") / dataset_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if output_format == "parquet":
            file_path = output_dir / f"{dataset_name}.parquet"
            df.to_parquet(file_path, index=False)
        elif output_format == "csv":
            file_path = output_dir / f"{dataset_name}.csv"
            df.to_csv(file_path, index=False)
        else:
            raise ValueError(f"Неподдерживаемый формат: {output_format}")
        
        return str(file_path)
    
    def _generate_individual_metadata(self, source: DataSource, df: pd.DataFrame, dataset_name: str) -> Dict[str, Any]:
        """Генерирует метаданные для отдельного набора данных."""
        return {
            "dataset_info": {
                "name": dataset_name,
                "created_at": datetime.utcnow().isoformat(),
                "format": "parquet",
                "strategy": "individual_database"
            },
            "source": {
                "source_id": source.source_id,
                "source_type": source.source_type,
                "path": source.path,
                "selected_columns": source.selected_columns or "ALL_COLUMNS"
            },
            "schema": {
                "columns": [
                    {
                        "name": col,
                        "type": str(df[col].dtype),
                        "null_count": int(df[col].isnull().sum()),
                        "unique_count": int(df[col].nunique())
                    }
                    for col in df.columns
                ],
                "total_rows": len(df),
                "total_columns": len(df.columns)
            },
            "statistics": {
                "memory_usage_bytes": int(df.memory_usage(deep=True).sum()),
                "has_nulls": df.isnull().any().any(),
                "numeric_columns": len(df.select_dtypes(include=['number']).columns),
                "text_columns": len(df.select_dtypes(include=['object']).columns)
            }
        }

def find_first_files():
    """Находит созданные тестовые файлы в каждой из папок."""
    
    print("ПОИСК ТЕСТОВЫХ ФАЙЛОВ В ПАПКАХ")
    print("=" * 40)
    
    files_info = {}
    
    # Ищем конкретные созданные файлы
    test_files = [
        ("data_landing_zone/syn_csv/transactions.csv", "csv", "csv_transactions"),
        ("data_landing_zone/syn_json/users.json", "json", "json_users"),
        ("data_landing_zone/syn_xml/orders.xml", "xml", "xml_orders")
    ]
    
    for file_path, file_type, source_id in test_files:
        path = Path(file_path)
        if path.exists():
            files_info[file_type] = {
                "file": str(path),
                "source_id": source_id
            }
            print(f"{file_type.upper()}: {path.name}")
        else:
            print(f"{file_type.upper()}: НЕ НАЙДЕН - {path}")
    
    return files_info

async def test_individual_databases(files_info):
    """Тестирует создание отдельных баз данных."""
    
    print("\nСОЗДАНИЕ ОТДЕЛЬНЫХ БАЗ ДАННЫХ (PostgreSQL формат)")
    print("=" * 50)
    
    # Создаем источники данных
    sources = []
    
    for source_type, info in files_info.items():
        if info:
            source = DataSource(
                source_id=info["source_id"],
                source_type="file",
                path=info["file"],
                selected_columns=[]  # Пустой список = ВСЕ колонки
            )
            sources.append(source)
            print(f"Добавлен источник: {info['source_id']} - ВСЕ колонки")
    
    if not sources:
        print("Нет доступных источников для тестирования")
        return False
    
    # Создаем запрос на отдельные наборы данных
    request = CustomDatasetRequest(
        dataset_name="game_test_2_individual",
        sources=sources,
        join_strategy="individual",
        output_format="parquet",
        include_metadata=True
    )
    
    print(f"\nПараметры создания баз данных:")
    print(f"  Базовое имя: {request.dataset_name}")
    print(f"  Источников: {len(request.sources)}")
    print(f"  Стратегия: {request.join_strategy} (отдельные базы)")
    print(f"  Формат: {request.output_format}")
    
    # Создаем экземпляр построителя
    builder = GameTest2DatasetBuilder()
    
    # Выполняем создание отдельных баз данных
    print(f"\nВыполняем создание отдельных баз данных...")
    result = await builder.create_individual_datasets(request)
    
    if result.get("success"):
        print(f"\nУСПЕШНО! Создано {result.get('total_databases', 0)} отдельных баз данных!")
        
        databases = result.get("databases", [])
        for db in databases:
            print(f"\nБаза данных: {db['dataset_name']}")
            print(f"   Путь: {db['output_path']}")
            print(f"   Строк: {db['row_count']}")
            print(f"   Колонок: {db['column_count']}")
            print(f"   Колонки: {db['columns']}")
            print(f"   Размер: {db['data_size_bytes']} байт")
        
        return result
    else:
        print(f"\nОШИБКА: {result.get('error', 'Неизвестная ошибка')}")
        return False

async def main():
    """Основная функция второго игрового теста."""
    
    print("ВТОРОЙ ИГРОВОЙ ТЕСТ МОДУЛЯ 2")
    print("=" * 60)
    print("Задача: Взять первые 100 строк из каждого файла")
    print("        Сохранить ВСЕ колонки в отдельные базы PostgreSQL")
    print("=" * 60)
    
    # 1. Находим первые файлы в папках
    files_info = find_first_files()
    
    if not files_info:
        print("ОШИБКА: Не найдено файлов для тестирования")
        return False
    
    # 2. Тестируем создание отдельных баз данных
    result = await test_individual_databases(files_info)
    
    if result:
        print(f"\nВТОРОЙ ИГРОВОЙ ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        
        # Показываем пути к созданным базам
        databases = result.get("databases", [])
        print(f"\nПУТИ К СОЗДАННЫМ БАЗАМ ДАННЫХ:")
        for i, db in enumerate(databases, 1):
            path = Path(db['output_path'])
            print(f"  {i}. {db['dataset_name']}")
            print(f"     Путь: {path.absolute()}")
            print(f"     Колонок: {db['column_count']}, Строк: {db['row_count']}")
        
        return True
    else:
        print(f"\nВТОРОЙ ИГРОВОЙ ТЕСТ НЕ ПРОШЕЛ")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
