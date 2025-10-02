import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

import pandas as pd
import pyarrow.parquet as pq
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

class FormatValidator:
    """Валидатор форматов данных для проверки совместимости между модулями."""

    def validate(
        self, 
        source_path: str, 
        expected_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Основной метод для валидации формата файла.

        Args:
            source_path: Путь к файлу для проверки.
            expected_schema: Ожидаемая схема в формате JSON.

        Returns:
            Результат валидации.
        """
        file_format = expected_schema.get("format")
        if not file_format:
            path = Path(source_path)
            if not path.exists():
                # Если путь не существует, предполагаем, что это могут быть сырые данные
                pass
            else:
                file_format = path.suffix.lstrip('.').lower()

        # Специальная обработка для JSON, который может быть строкой или путем
        if file_format == "json":
            try:
                # Пытаемся загрузить как JSON-строку
                data = json.loads(source_path)
                return self._validate_json(data, expected_schema)
            except (json.JSONDecodeError, TypeError):
                # Если не удалось, считаем, что это путь к файлу
                path = Path(source_path)
                if not path.exists():
                    return {"success": False, "error": f"Invalid JSON data or file path: {source_path}"}
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return self._validate_json(data, expected_schema)
                except Exception as e:
                    return {"success": False, "error": f"Invalid JSON file: {e}"}

        path = Path(source_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {source_path}"}
        
        try:
            if file_format == "parquet":
                return self._validate_parquet(path, expected_schema)
            elif file_format == "csv":
                return self._validate_csv(path, expected_schema)
            elif file_format == "json":
                return self._validate_json(path, expected_schema)
            else:
                return {"success": False, "error": f"Unsupported format: {file_format}"}
        except Exception as e:
            logger.error(f"Error validating file {source_path}: {e}")
            return {"success": False, "error": str(e)}

    def _validate_parquet(self, path: Path, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация Parquet файла."""
        try:
            metadata = pq.read_metadata(path)
            file_schema = metadata.schema.to_arrow_schema()
            
            # Проверка колонок
            actual_columns = set(file_schema.names)
            expected_columns = set(schema.get("columns", []))
            
            if not expected_columns.issubset(actual_columns):
                missing = expected_columns - actual_columns
                return {"success": False, "error": f"Missing columns in Parquet: {missing}"}

            # TODO: Добавить проверку типов данных и метаданных

            return {"success": True, "message": "Parquet format and columns are valid."}
        except Exception as e:
            return {"success": False, "error": f"Invalid Parquet file: {e}"}

    def _validate_csv(self, path: Path, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация CSV файла."""
        try:
            df = pd.read_csv(path, nrows=5)
            actual_columns = set(df.columns)
            expected_columns = set(schema.get("columns", []))

            if not expected_columns.issubset(actual_columns):
                missing = expected_columns - actual_columns
                return {"success": False, "error": f"Missing columns in CSV: {missing}"}

            return {"success": True, "message": "CSV format and columns are valid."}
        except Exception as e:
            return {"success": False, "error": f"Invalid CSV file: {e}"}

    def _validate_json(self, data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация JSON данных."""
        try:
            
            # Если данные - это список объектов, берем первый
            if isinstance(data, list) and data:
                sample = data[0]
            else:
                sample = data

            if not isinstance(sample, dict):
                 return {"success": False, "error": "JSON is not an object or array of objects."}

            actual_keys = set(sample.keys())
            expected_keys = set(schema.get("columns", []))

            if not expected_keys.issubset(actual_keys):
                missing = expected_keys - actual_keys
                return {"success": False, "error": f"Missing keys in JSON: {missing}"}

            return {"success": True, "message": "JSON format and keys are valid."}
        except Exception as e:
            return {"success": False, "error": f"Invalid JSON file: {e}"}

    def validate_with_pydantic(
        self, 
        data: Any, 
        pydantic_model: BaseModel
    ) -> Dict[str, Any]:
        """
        Валидация данных с использованием Pydantic модели.

        Args:
            data: Данные для валидации.
            pydantic_model: Pydantic модель.

        Returns:
            Результат валидации.
        """
        try:
            pydantic_model.parse_obj(data)
            return {"success": True, "message": "Data is valid against Pydantic model."}
        except ValidationError as e:
            return {"success": False, "error": "Pydantic validation failed", "details": e.errors()}
