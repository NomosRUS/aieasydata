"""
Третий игровой тест модуля 2.
Трансформирует указанные файлы в Parquet формат (первые 10 строк).
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
        self.selected_columns = selected_columns or []

class TransformRequest:
    def __init__(self, dataset_name: str, sources: List[DataSource], 
                 output_format: str = "parquet", include_metadata: bool = True):
        self.dataset_name = dataset_name
        self.sources = sources
        self.output_format = output_format
        self.include_metadata = include_metadata

# Трансформатор для третьего теста
class GameTest3Transformer:
    """Трансформатор файлов для третьего игрового теста."""
    
    def __init__(self):
        pass
    
    async def load_data_from_file(self, source: DataSource, limit: int = 10) -> pd.DataFrame:
        """Загружает данные из файла с ограничением на количество строк."""
        file_path = Path(source.path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        print(f"Загружаем из {file_path.name} (лимит: {limit} строк)")
        
        # Определяем формат файла по расширению
        if file_path.suffix.lower() == '.csv':
            # Для больших CSV файлов используем chunksize
            try:
                df = pd.read_csv(file_path, nrows=limit)
            except Exception as e:
                print(f"  Ошибка чтения CSV: {str(e)}")
                # Пробуем с другими параметрами
                try:
                    df = pd.read_csv(file_path, nrows=limit, encoding='utf-8', sep=';')
                except:
                    df = pd.read_csv(file_path, nrows=limit, encoding='latin-1')
                    
        elif file_path.suffix.lower() == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                # Пробуем загрузить как JSON Lines или обычный JSON
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        df = pd.DataFrame(data[:limit] if limit else data)
                    else:
                        df = pd.DataFrame([data])
                except json.JSONDecodeError:
                    # Пробуем JSON Lines формат
                    f.seek(0)
                    lines = []
                    for i, line in enumerate(f):
                        if i >= limit:
                            break
                        try:
                            lines.append(json.loads(line.strip()))
                        except:
                            continue
                    df = pd.DataFrame(lines)
                    
        elif file_path.suffix.lower() == '.xml':
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                
                records = []
                count = 0
                
                # Пробуем разные структуры XML
                if len(root) > 0:
                    # Если есть дочерние элементы
                    for record in root:
                        if count >= limit:
                            break
                        if len(list(record)) > 0:  # Если это запись с дочерними элементами
                            record_data = {}
                            for child in record:
                                record_data[child.tag] = child.text
                            records.append(record_data)
                            count += 1
                else:
                    # Если это плоская структура
                    record_data = {}
                    for child in root:
                        record_data[child.tag] = child.text
                    records.append(record_data)
                
                df = pd.DataFrame(records)
            except Exception as e:
                print(f"  Ошибка парсинга XML: {str(e)}")
                df = pd.DataFrame()
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_path.suffix}")
        
        print(f"  Загружено: {len(df)} строк, {len(df.columns)} колонок")
        if len(df.columns) > 0:
            print(f"  Колонки: {list(df.columns)[:5]}{'...' if len(df.columns) > 5 else ''}")
        
        return df
    
    async def transform_files(self, request: TransformRequest) -> Dict[str, Any]:
        """Трансформирует файлы в Parquet формат."""
        try:
            print(f"Трансформируем файлы: {request.dataset_name}")
            
            results = []
            
            for i, source in enumerate(request.sources):
                print(f"\nТрансформируем файл {i+1}: {source.source_id}")
                
                try:
                    # Загружаем данные (первые 10 строк)
                    df = await self.load_data_from_file(source, limit=10)
                    
                    if df.empty:
                        print(f"  Файл пустой или не удалось прочитать")
                        continue
                    
                    # Создаем имя для Parquet файла
                    parquet_name = f"{request.dataset_name}_{source.source_id}"
                    
                    # Сохраняем в Parquet
                    output_path = await self._save_parquet(df, parquet_name)
                    
                    # Генерируем метаданные
                    metadata = self._generate_metadata(source, df, parquet_name)
                    
                    result = {
                        "source_id": source.source_id,
                        "original_file": source.path,
                        "parquet_name": parquet_name,
                        "output_path": output_path,
                        "row_count": len(df),
                        "column_count": len(df.columns),
                        "columns": list(df.columns),
                        "data_size_bytes": df.memory_usage(deep=True).sum(),
                        "metadata": metadata,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    results.append(result)
                    print(f"  УСПЕШНО: Трансформирован в: {parquet_name}.parquet")
                    
                except Exception as e:
                    print(f"  ОШИБКА трансформации {source.source_id}: {str(e)}")
                    continue
            
            if not results:
                return {
                    "success": False,
                    "error": "Не удалось трансформировать ни одного файла"
                }
            
            return {
                "success": True,
                "operation": "file_transformation",
                "total_files": len(results),
                "transformations": results,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Ошибка трансформации файлов: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _save_parquet(self, df: pd.DataFrame, parquet_name: str) -> str:
        """Сохраняет DataFrame в Parquet файл."""
        output_dir = Path("data_landing_zone/transformed") / parquet_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = output_dir / f"{parquet_name}.parquet"
        df.to_parquet(file_path, index=False)
        
        return str(file_path)
    
    def _generate_metadata(self, source: DataSource, df: pd.DataFrame, parquet_name: str) -> Dict[str, Any]:
        """Генерирует метаданные для трансформации."""
        return {
            "transformation_info": {
                "parquet_name": parquet_name,
                "created_at": datetime.utcnow().isoformat(),
                "operation": "csv_json_xml_to_parquet"
            },
            "source": {
                "source_id": source.source_id,
                "original_file": source.path,
                "file_type": Path(source.path).suffix.lower()
            },
            "schema": {
                "columns": [
                    {
                        "name": col,
                        "type": str(df[col].dtype),
                        "null_count": int(df[col].isnull().sum()),
                        "sample_values": df[col].dropna().head(3).tolist()
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

def prepare_transform_sources():
    """Подготавливает источники для трансформации."""
    
    print("ПОДГОТОВКА ФАЙЛОВ ДЛЯ ТРАНСФОРМАЦИИ")
    print("=" * 50)
    
    # Указанные файлы для трансформации
    target_files = [
        {
            "path": "data_landing_zone/syn_csv/part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv",
            "source_id": "large_csv_data",
            "type": "csv"
        },
        {
            "path": "data_landing_zone/syn_json/part1.json", 
            "source_id": "large_json_data",
            "type": "json"
        },
        {
            "path": "data_landing_zone/syn_xml/part1.xml",
            "source_id": "large_xml_data", 
            "type": "xml"
        }
    ]
    
    sources = []
    
    for file_info in target_files:
        file_path = Path(file_info["path"])
        if file_path.exists():
            source = DataSource(
                source_id=file_info["source_id"],
                source_type="file",
                path=str(file_path)
            )
            sources.append(source)
            
            # Показываем информацию о файле
            file_size = file_path.stat().st_size
            print(f"НАЙДЕН {file_info['type'].upper()}: {file_path.name}")
            print(f"   Размер: {file_size:,} байт ({file_size/1024/1024:.1f} MB)")
        else:
            print(f"НЕ НАЙДЕН {file_info['type'].upper()}: {file_path}")
    
    return sources

async def test_file_transformation(sources):
    """Тестирует трансформацию файлов."""
    
    print(f"\nТРАНСФОРМАЦИЯ ФАЙЛОВ В PARQUET (первые 10 строк)")
    print("=" * 60)
    
    if not sources:
        print("Нет доступных файлов для трансформации")
        return False
    
    # Создаем запрос на трансформацию
    request = TransformRequest(
        dataset_name="game_test_3_transform",
        sources=sources,
        output_format="parquet",
        include_metadata=True
    )
    
    print(f"Параметры трансформации:")
    print(f"  Базовое имя: {request.dataset_name}")
    print(f"  Файлов: {len(request.sources)}")
    print(f"  Лимит строк: 10 из каждого файла")
    print(f"  Формат вывода: {request.output_format}")
    
    # Создаем экземпляр трансформатора
    transformer = GameTest3Transformer()
    
    # Выполняем трансформацию
    print(f"\nВыполняем трансформацию файлов...")
    result = await transformer.transform_files(request)
    
    if result.get("success"):
        print(f"\nУСПЕШНО! Трансформировано {result.get('total_files', 0)} файлов!")
        
        transformations = result.get("transformations", [])
        for transform in transformations:
            print(f"\nФайл: {Path(transform['original_file']).name}")
            print(f"   Parquet: {transform['parquet_name']}.parquet")
            print(f"   Путь: {transform['output_path']}")
            print(f"   Строк: {transform['row_count']}")
            print(f"   Колонок: {transform['column_count']}")
            print(f"   Размер: {transform['data_size_bytes']} байт")
        
        return result
    else:
        print(f"\nОШИБКА: {result.get('error', 'Неизвестная ошибка')}")
        return False

async def main():
    """Основная функция третьего игрового теста."""
    
    print("ТРЕТИЙ ИГРОВОЙ ТЕСТ МОДУЛЯ 2")
    print("=" * 70)
    print("Задача: Трансформировать указанные файлы в Parquet")
    print("        Взять первые 10 строк из каждого файла")
    print("=" * 70)
    
    # 1. Подготавливаем источники
    sources = prepare_transform_sources()
    
    if not sources:
        print("ОШИБКА: Не найдено файлов для трансформации")
        return False
    
    # 2. Тестируем трансформацию
    result = await test_file_transformation(sources)
    
    if result:
        print(f"\nТРЕТИЙ ИГРОВОЙ ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        
        # Показываем пути к созданным Parquet файлам
        transformations = result.get("transformations", [])
        print(f"\nПУТИ К СОЗДАННЫМ PARQUET ФАЙЛАМ:")
        for i, transform in enumerate(transformations, 1):
            path = Path(transform['output_path'])
            print(f"  {i}. {transform['parquet_name']}.parquet")
            print(f"     Путь: {path.absolute()}")
            print(f"     Исходный: {Path(transform['original_file']).name}")
            print(f"     Строк: {transform['row_count']}, Колонок: {transform['column_count']}")
        
        return True
    else:
        print(f"\nТРЕТИЙ ИГРОВОЙ ТЕСТ НЕ ПРОШЕЛ")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
