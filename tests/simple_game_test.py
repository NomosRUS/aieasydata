"""
Упрощенный игровой тест модуля 2.
Тестирует только логику CustomDatasetBuilder без зависимостей.
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
    def __init__(self, source_id: str, source_type: str, path: str, selected_columns: List[str]):
        self.source_id = source_id
        self.source_type = source_type
        self.path = path
        self.selected_columns = selected_columns

class CustomDatasetRequest:
    def __init__(self, dataset_name: str, sources: List[DataSource], 
                 join_strategy: str = "concat", output_format: str = "parquet", 
                 include_metadata: bool = True):
        self.dataset_name = dataset_name
        self.sources = sources
        self.join_strategy = join_strategy
        self.output_format = output_format
        self.include_metadata = include_metadata

# Упрощенный CustomDatasetBuilder
class SimpleCustomDatasetBuilder:
    """Упрощенная версия CustomDatasetBuilder для тестирования."""
    
    def __init__(self):
        pass
    
    async def load_data_from_file(self, source: DataSource, limit: Optional[int] = None) -> pd.DataFrame:
        """Загружает данные из файла."""
        file_path = Path(source.path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
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
        
        # Фильтруем только выбранные колонки
        if source.selected_columns:
            available_columns = [col for col in source.selected_columns if col in df.columns]
            if available_columns:
                df = df[available_columns]
            else:
                print(f"Предупреждение: Ни одна из выбранных колонок {source.selected_columns} не найдена в файле")
                print(f"Доступные колонки: {list(df.columns)}")
                # Берем все доступные колонки
                df = df
        
        return df
    
    async def create_custom_dataset(self, request: CustomDatasetRequest) -> Dict[str, Any]:
        """Создает кастомный набор данных."""
        try:
            print(f"Создаем кастомный набор данных: {request.dataset_name}")
            
            # Загружаем данные из всех источников
            dataframes = []
            total_input_rows = 0
            
            for i, source in enumerate(request.sources):
                print(f"Загружаем данные из источника {i+1}: {source.source_id}")
                try:
                    df = await self.load_data_from_file(source, limit=10)  # Ограничиваем 10 строками для теста
                    dataframes.append(df)
                    total_input_rows += len(df)
                    print(f"  Загружено {len(df)} строк, колонки: {list(df.columns)}")
                except Exception as e:
                    print(f"  Ошибка загрузки: {str(e)}")
                    continue
            
            if not dataframes:
                return {
                    "success": False,
                    "error": "Не удалось загрузить данные ни из одного источника"
                }
            
            # Объединяем данные
            if len(dataframes) == 1:
                result_df = dataframes[0]
            elif request.join_strategy == "concat":
                # Простая конкатенация
                result_df = pd.concat(dataframes, ignore_index=True, sort=False)
            else:
                # Для других стратегий тоже делаем конкатенацию
                result_df = pd.concat(dataframes, ignore_index=True, sort=False)
            
            # Сохраняем результат
            output_path = await self._save_dataset(result_df, request.dataset_name, request.output_format)
            
            # Генерируем метаданные
            metadata = self._generate_metadata(request, result_df, total_input_rows)
            
            return {
                "success": True,
                "dataset_name": request.dataset_name,
                "output_path": output_path,
                "row_count": len(result_df),
                "column_count": len(result_df.columns),
                "data_size_bytes": result_df.memory_usage(deep=True).sum(),
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Ошибка создания набора данных: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _save_dataset(self, df: pd.DataFrame, dataset_name: str, output_format: str) -> str:
        """Сохраняет набор данных."""
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
    
    def _generate_metadata(self, request: CustomDatasetRequest, df: pd.DataFrame, total_input_rows: int) -> Dict[str, Any]:
        """Генерирует метаданные."""
        return {
            "dataset_info": {
                "name": request.dataset_name,
                "created_at": datetime.utcnow().isoformat(),
                "format": request.output_format
            },
            "sources": [
                {
                    "source_id": source.source_id,
                    "source_type": source.source_type,
                    "path": source.path,
                    "selected_columns": source.selected_columns
                }
                for source in request.sources
            ],
            "result_schema": {
                "columns": [
                    {
                        "name": col,
                        "type": str(df[col].dtype),
                        "null_count": int(df[col].isnull().sum())
                    }
                    for col in df.columns
                ],
                "total_rows": len(df),
                "total_columns": len(df.columns)
            },
            "processing_stats": {
                "input_rows": total_input_rows,
                "output_rows": len(df),
                "data_reduction_ratio": len(df) / max(total_input_rows, 1)
            }
        }

def analyze_test_files():
    """Анализирует тестовые файлы."""
    
    print("АНАЛИЗ ТЕСТОВЫХ ФАЙЛОВ")
    print("=" * 40)
    
    files_info = {}
    
    # CSV файл
    csv_file = Path("test_sales.csv")
    if csv_file.exists():
        df_csv = pd.read_csv(csv_file)
        csv_columns = list(df_csv.columns)
        csv_selected = csv_columns[-2:]  # Последние 2 колонки
        files_info["csv"] = {
            "file": str(csv_file),
            "columns": csv_selected,
            "all_columns": csv_columns
        }
        print(f"\nCSV файл ({csv_file.name}):")
        print(f"  Всего колонок: {len(csv_columns)}")
        print(f"  Все колонки: {csv_columns}")
        print(f"  Выбранные: {csv_selected}")
        print(f"  Первые строки выбранных колонок:")
        print(df_csv[csv_selected].head(3).to_string())
    
    # JSON файл
    json_file = Path("test_customers.json")
    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            data_json = json.load(f)
        json_columns = list(data_json[0].keys()) if data_json else []
        json_selected = json_columns[-2:]  # Последние 2 колонки
        files_info["json"] = {
            "file": str(json_file),
            "columns": json_selected,
            "all_columns": json_columns
        }
        print(f"\nJSON файл ({json_file.name}):")
        print(f"  Всего колонок: {len(json_columns)}")
        print(f"  Все колонки: {json_columns}")
        print(f"  Выбранные: {json_selected}")
        print(f"  Первые записи выбранных колонок:")
        for i, item in enumerate(data_json[:3]):
            selected_data = {col: item.get(col) for col in json_selected}
            print(f"    {i+1}: {selected_data}")
    
    # XML файл
    xml_file = Path("test_products.xml")
    if xml_file.exists():
        tree = ET.parse(xml_file)
        root = tree.getroot()
        first_product = root[0] if len(root) > 0 else None
        xml_columns = [child.tag for child in first_product] if first_product is not None else []
        xml_selected = xml_columns[-2:]  # Последние 2 колонки
        files_info["xml"] = {
            "file": str(xml_file),
            "columns": xml_selected,
            "all_columns": xml_columns
        }
        print(f"\nXML файл ({xml_file.name}):")
        print(f"  Всего колонок: {len(xml_columns)}")
        print(f"  Все колонки: {xml_columns}")
        print(f"  Выбранные: {xml_selected}")
        print(f"  Первые записи выбранных колонок:")
        for i, product in enumerate(root[:3]):
            selected_data = {}
            for col in xml_selected:
                element = product.find(col)
                selected_data[col] = element.text if element is not None else None
            print(f"    {i+1}: {selected_data}")
    
    return files_info

async def test_custom_dataset_creation(files_info):
    """Тестирует создание кастомного набора данных."""
    
    print("\nСОЗДАНИЕ КАСТОМНОГО НАБОРА ДАННЫХ")
    print("=" * 40)
    
    # Создаем источники данных
    sources = []
    
    for source_type, info in files_info.items():
        if info:
            source = DataSource(
                source_id=f"{source_type}_source",
                source_type="file",
                path=info["file"],
                selected_columns=info["columns"]
            )
            sources.append(source)
            print(f"Добавлен источник: {source_type} - колонки: {info['columns']}")
    
    if not sources:
        print("Нет доступных источников для тестирования")
        return False
    
    # Создаем запрос на кастомный набор данных
    request = CustomDatasetRequest(
        dataset_name="game_test_mixed_data",
        sources=sources,
        join_strategy="concat",
        output_format="parquet",
        include_metadata=True
    )
    
    print(f"\nПараметры создания набора данных:")
    print(f"  Имя: {request.dataset_name}")
    print(f"  Источников: {len(request.sources)}")
    print(f"  Стратегия: {request.join_strategy}")
    print(f"  Формат: {request.output_format}")
    
    # Создаем экземпляр построителя
    builder = SimpleCustomDatasetBuilder()
    
    # Выполняем создание кастомного набора данных
    print(f"\nВыполняем создание кастомного набора данных...")
    result = await builder.create_custom_dataset(request)
    
    if result.get("success"):
        print(f"\nУСПЕШНО! Кастомный набор данных создан!")
        print(f"  Путь: {result.get('output_path', 'N/A')}")
        print(f"  Строк: {result.get('row_count', 'N/A')}")
        print(f"  Колонок: {result.get('column_count', 'N/A')}")
        print(f"  Размер: {result.get('data_size_bytes', 'N/A')} байт")
        
        # Показываем метаданные
        if result.get('metadata'):
            metadata = result['metadata']
            print(f"\nМетаданные:")
            print(f"  Источников: {len(metadata.get('sources', []))}")
            print(f"  Создан: {metadata.get('dataset_info', {}).get('created_at', 'N/A')}")
            
            # Показываем схему результата
            if 'result_schema' in metadata:
                schema = metadata['result_schema']
                print(f"  Схема результата:")
                for col_info in schema.get('columns', []):
                    print(f"    - {col_info['name']}: {col_info['type']} (null: {col_info['null_count']})")
        
        return result
    else:
        print(f"\nОШИБКА: {result.get('error', 'Неизвестная ошибка')}")
        return False

async def main():
    """Основная функция теста."""
    
    print("УПРОЩЕННЫЙ ИГРОВОЙ ТЕСТ МОДУЛЯ 2")
    print("=" * 50)
    
    # 1. Анализируем тестовые файлы
    files_info = analyze_test_files()
    
    # 2. Тестируем создание кастомного набора данных
    result = await test_custom_dataset_creation(files_info)
    
    if result:
        print(f"\nИГРОВОЙ ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        
        # Проверяем созданный файл
        output_path = Path(result.get('output_path', ''))
        if output_path.exists():
            print(f"\nПУТЬ К СОЗДАННОЙ БАЗЕ: {output_path.absolute()}")
            
            # Читаем и показываем содержимое
            try:
                df_result = pd.read_parquet(output_path)
                print(f"\nСОДЕРЖИМОЕ СОЗДАННОЙ БАЗЫ:")
                print(f"  Размер: {df_result.shape}")
                print(f"  Колонки: {list(df_result.columns)}")
                print(f"\nПервые строки:")
                print(df_result.head().to_string())
                
                # Показываем статистику по источникам
                print(f"\nСТАТИСТИКА ПО ИСТОЧНИКАМ:")
                if 'source' in df_result.columns:
                    print(df_result['source'].value_counts())
                else:
                    print("Колонка источника не найдена - данные объединены без маркировки")
                
            except Exception as e:
                print(f"Ошибка чтения результата: {str(e)}")
        else:
            print(f"Файл результата не найден: {output_path}")
        
        return True
    else:
        print(f"\nИГРОВОЙ ТЕСТ НЕ ПРОШЕЛ")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
