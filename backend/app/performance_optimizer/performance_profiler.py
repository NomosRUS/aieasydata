"""
Профилировщик производительности для модуля 3.
Специализируется на анализе производительности хранилищ и запросов.
"""

from typing import Dict, Any, List, Optional
import time
import psutil
import os
from pathlib import Path
from ..shared.base_profiler import get_basic_file_info, get_basic_schema_info

class PerformanceProfiler:
    """
    Профилировщик производительности для анализа хранилищ данных.
    Специализируется на метриках производительности, а не на качестве данных.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_storage_performance(self, source_path: str) -> Dict[str, Any]:
        """
        Анализирует производительность хранилища данных.
        Фокус на скорости доступа, размере данных, оптимизации запросов.
        """
        start_time = time.time()
        
        try:
            # Базовая информация через общий компонент
            basic_info = get_basic_file_info(source_path)
            schema_info = get_basic_schema_info(source_path, sample_size=1000)
            
            # Специализированный анализ производительности
            performance_metrics = {
                "source_path": source_path,
                "analysis_timestamp": time.time(),
                "basic_info": basic_info,
                "schema_info": schema_info,
                "performance_analysis": {}
            }
            
            # Анализ производительности чтения
            read_performance = self._analyze_read_performance(source_path)
            performance_metrics["performance_analysis"]["read_performance"] = read_performance
            
            # Анализ размера и сжатия
            compression_analysis = self._analyze_compression_potential(source_path, schema_info)
            performance_metrics["performance_analysis"]["compression_potential"] = compression_analysis
            
            # Анализ индексирования
            indexing_analysis = self._analyze_indexing_potential(schema_info)
            performance_metrics["performance_analysis"]["indexing_potential"] = indexing_analysis
            
            # Анализ партиционирования
            partitioning_analysis = self._analyze_partitioning_potential(schema_info)
            performance_metrics["performance_analysis"]["partitioning_potential"] = partitioning_analysis
            
            # Общие метрики производительности
            analysis_time = time.time() - start_time
            performance_metrics["analysis_duration_seconds"] = round(analysis_time, 3)
            
            return performance_metrics
            
        except Exception as e:
            return {
                "source_path": source_path,
                "error": f"Performance analysis failed: {str(e)}",
                "analysis_duration_seconds": round(time.time() - start_time, 3)
            }
    
    def _analyze_read_performance(self, source_path: str) -> Dict[str, Any]:
        """Анализирует производительность чтения файла."""
        try:
            file_size = os.path.getsize(source_path)
            
            # Тестируем скорость чтения
            start_time = time.time()
            
            # Читаем первые 10MB или весь файл, если он меньше
            chunk_size = min(10 * 1024 * 1024, file_size)  # 10MB
            
            with open(source_path, 'rb') as f:
                data = f.read(chunk_size)
            
            read_time = time.time() - start_time
            read_speed_mbps = (len(data) / (1024 * 1024)) / read_time if read_time > 0 else 0
            
            return {
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "test_chunk_size_mb": round(len(data) / (1024 * 1024), 2),
                "read_time_seconds": round(read_time, 3),
                "read_speed_mbps": round(read_speed_mbps, 2),
                "performance_category": self._categorize_read_performance(read_speed_mbps)
            }
            
        except Exception as e:
            return {"error": f"Read performance analysis failed: {str(e)}"}
    
    def _analyze_compression_potential(self, source_path: str, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует потенциал сжатия данных."""
        try:
            file_ext = os.path.splitext(source_path)[1].lower()
            file_size = os.path.getsize(source_path)
            
            compression_potential = {
                "current_format": file_ext,
                "current_size_mb": round(file_size / (1024 * 1024), 2),
                "recommendations": []
            }
            
            # Рекомендации по сжатию на основе формата
            if file_ext == '.csv':
                compression_potential["recommendations"].append({
                    "format": "parquet",
                    "estimated_compression": "60-80%",
                    "reason": "Parquet обеспечивает лучшее сжатие для структурированных данных"
                })
                compression_potential["recommendations"].append({
                    "format": "csv.gz",
                    "estimated_compression": "70-90%",
                    "reason": "Gzip сжатие для CSV файлов"
                })
            
            elif file_ext == '.json':
                compression_potential["recommendations"].append({
                    "format": "parquet",
                    "estimated_compression": "70-85%",
                    "reason": "Конвертация JSON в Parquet для лучшего сжатия"
                })
            
            # Анализ типов данных для сжатия
            if schema_info and "columns" in schema_info:
                text_columns = [col for col in schema_info["columns"] if "str" in col.get("type", "").lower()]
                numeric_columns = [col for col in schema_info["columns"] if any(t in col.get("type", "").lower() for t in ["int", "float"])]
                
                if len(text_columns) > len(numeric_columns):
                    compression_potential["data_type_analysis"] = "Много текстовых данных - высокий потенциал сжатия"
                else:
                    compression_potential["data_type_analysis"] = "Преимущественно числовые данные - средний потенциал сжатия"
            
            return compression_potential
            
        except Exception as e:
            return {"error": f"Compression analysis failed: {str(e)}"}
    
    def _analyze_indexing_potential(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует потенциал для создания индексов."""
        try:
            if not schema_info or "columns" not in schema_info:
                return {"error": "No schema information available"}
            
            indexing_recommendations = []
            
            for col in schema_info["columns"]:
                col_name = col.get("name", "")
                col_type = col.get("type", "").lower()
                
                # Рекомендации по индексам на основе имени и типа колонки
                if any(keyword in col_name.lower() for keyword in ["id", "key", "code"]):
                    indexing_recommendations.append({
                        "column": col_name,
                        "index_type": "unique" if "id" in col_name.lower() else "regular",
                        "reason": "Идентификатор или ключевое поле",
                        "priority": "high"
                    })
                
                elif any(keyword in col_name.lower() for keyword in ["date", "time", "created", "updated"]):
                    indexing_recommendations.append({
                        "column": col_name,
                        "index_type": "btree",
                        "reason": "Временное поле для диапазонных запросов",
                        "priority": "high"
                    })
                
                elif "int" in col_type or "float" in col_type:
                    indexing_recommendations.append({
                        "column": col_name,
                        "index_type": "btree",
                        "reason": "Числовое поле для фильтрации",
                        "priority": "medium"
                    })
                
                elif "str" in col_type and len(col.get("sample_values", [])) > 0:
                    # Анализируем кардинальность по образцам
                    sample_values = col.get("sample_values", [])
                    unique_values = len(set(sample_values))
                    if unique_values < len(sample_values) * 0.8:  # Низкая кардинальность
                        indexing_recommendations.append({
                            "column": col_name,
                            "index_type": "hash",
                            "reason": "Категориальное поле с низкой кардинальностью",
                            "priority": "medium"
                        })
            
            return {
                "total_columns": len(schema_info["columns"]),
                "recommended_indexes": len(indexing_recommendations),
                "recommendations": indexing_recommendations
            }
            
        except Exception as e:
            return {"error": f"Indexing analysis failed: {str(e)}"}
    
    def _analyze_partitioning_potential(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует потенциал для партиционирования."""
        try:
            if not schema_info or "columns" not in schema_info:
                return {"error": "No schema information available"}
            
            partitioning_recommendations = []
            
            for col in schema_info["columns"]:
                col_name = col.get("name", "")
                col_type = col.get("type", "").lower()
                
                # Рекомендации по партиционированию
                if any(keyword in col_name.lower() for keyword in ["date", "time", "year", "month"]):
                    partitioning_recommendations.append({
                        "column": col_name,
                        "partition_type": "range",
                        "partition_strategy": "monthly" if "date" in col_name.lower() else "yearly",
                        "reason": "Временное поле для временного партиционирования",
                        "priority": "high"
                    })
                
                elif any(keyword in col_name.lower() for keyword in ["region", "country", "category", "type"]):
                    partitioning_recommendations.append({
                        "column": col_name,
                        "partition_type": "hash",
                        "partition_strategy": "by_value",
                        "reason": "Категориальное поле для распределения нагрузки",
                        "priority": "medium"
                    })
            
            return {
                "partitioning_potential": len(partitioning_recommendations) > 0,
                "recommended_partitions": len(partitioning_recommendations),
                "recommendations": partitioning_recommendations
            }
            
        except Exception as e:
            return {"error": f"Partitioning analysis failed: {str(e)}"}
    
    def _categorize_read_performance(self, speed_mbps: float) -> str:
        """Категоризирует производительность чтения."""
        if speed_mbps > 100:
            return "excellent"
        elif speed_mbps > 50:
            return "good"
        elif speed_mbps > 20:
            return "average"
        elif speed_mbps > 5:
            return "poor"
        else:
            return "very_poor"

import logging
