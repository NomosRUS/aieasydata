"""
Анализатор производительности для Модуля 3
Интеграция с Модулем 5 для получения метрик и автоопределения типов данных
"""

import asyncio
import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .schemas import (
    PerformanceMetrics, 
    PerformanceAnalysisResult, 
    SourceType, 
    AnalysisStatus,
    Module5MetricsRequest,
    Module5MetricsResponse
)
from ..agent import get_llm_response

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Анализатор производительности данных с интеграцией с Модулем 5
    """
    
    def __init__(self):
        self.module5_base_url = "http://localhost:8000/api/v1/metrics"
        
    async def analyze_source(self, source: str, source_type: Optional[SourceType] = None) -> PerformanceAnalysisResult:
        """
        Основная функция анализа производительности источника данных
        
        Args:
            source: Путь к файлу/директории или строка подключения к БД
            source_type: Тип источника (если не указан, будет автоопределен)
            
        Returns:
            PerformanceAnalysisResult: Результат анализа с метриками и рекомендациями
        """
        analysis_id = f"analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        try:
            # Создаем начальный результат анализа
            result = PerformanceAnalysisResult(
                analysis_id=analysis_id,
                source=source,
                source_type=source_type or SourceType.CSV,  # Временное значение
                status=AnalysisStatus.ANALYZING
            )
            
            # Шаг 1: Получение метрик через Модуль 5
            logger.info(f"Получение метрик для источника: {source}")
            metrics_response = await self._get_metrics_from_module5(source)
            
            if not metrics_response.success:
                result.status = AnalysisStatus.ERROR
                result.error_message = f"Ошибка получения метрик: {metrics_response.error}"
                return result
            
            # Шаг 2: Преобразование метрик в наш формат
            performance_metrics = self._convert_module5_metrics(metrics_response)
            result.current_metrics = performance_metrics
            result.source_type = performance_metrics.source_type
            
            # Шаг 3: Анализ узких мест
            logger.info("Анализ узких мест производительности")
            bottlenecks = self._identify_bottlenecks(performance_metrics)
            result.bottlenecks = bottlenecks
            
            # Шаг 4: LLM анализ для получения экспертного мнения
            logger.info("Получение LLM анализа")
            llm_analysis = await self._get_llm_analysis(performance_metrics, bottlenecks)
            result.llm_analysis = llm_analysis
            
            result.status = AnalysisStatus.COMPLETED
            result.completed_at = datetime.utcnow()
            
            logger.info(f"Анализ завершен успешно: {analysis_id}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при анализе источника {source}: {str(e)}")
            result.status = AnalysisStatus.ERROR
            result.error_message = str(e)
            return result
    
    async def _get_metrics_from_module5(self, source: str) -> Module5MetricsResponse:
        """
        Получение метрик от Модуля 5 через автоопределение
        """
        try:
            async with httpx.AsyncClient() as client:
                # Используем автоопределение Модуля 5
                response = await client.get(
                    f"{self.module5_base_url}/auto-detect",
                    params={"source": source},
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return Module5MetricsResponse(
                        detected_type=data.get("detected_type", "unknown"),
                        metrics=data.get("metrics", {}),
                        structure=data.get("structure", {}),
                        processing_time=data.get("processing_time", 0.0),
                        success=True
                    )
                else:
                    return Module5MetricsResponse(
                        detected_type="unknown",
                        metrics={},
                        processing_time=0.0,
                        success=False,
                        error=f"HTTP {response.status_code}: {response.text}"
                    )
                    
        except Exception as e:
            logger.error(f"Ошибка при обращении к Модулю 5: {str(e)}")
            return Module5MetricsResponse(
                detected_type="unknown",
                metrics={},
                processing_time=0.0,
                success=False,
                error=str(e)
            )
    
    def _convert_module5_metrics(self, response: Module5MetricsResponse) -> PerformanceMetrics:
        """
        Преобразование метрик Модуля 5 в формат PerformanceMetrics
        """
        metrics_data = response.metrics
        
        # Определение типа источника на основе ответа Модуля 5
        source_type_mapping = {
            "csv": SourceType.CSV,
            "json": SourceType.JSON,
            "xml": SourceType.XML,
            "parquet": SourceType.PARQUET,
            "postgresql": SourceType.POSTGRESQL,
            "clickhouse": SourceType.CLICKHOUSE,
            "directory": SourceType.DIRECTORY
        }
        
        detected_type = response.detected_type.lower()
        source_type = source_type_mapping.get(detected_type, SourceType.CSV)
        
        return PerformanceMetrics(
            source_type=source_type,
            data_size_bytes=metrics_data.get("size_bytes", 0),
            row_count=metrics_data.get("row_count", 0),
            column_count=metrics_data.get("column_count"),
            processing_time_ms=response.processing_time * 1000,  # Конвертируем в миллисекунды
            avg_query_time_ms=metrics_data.get("avg_query_time_ms"),
            index_usage_stats=metrics_data.get("index_usage_stats"),
            partition_stats=metrics_data.get("partition_stats"),
            structure_info=response.structure
        )
    
    def _identify_bottlenecks(self, metrics: PerformanceMetrics) -> List[str]:
        """
        Выявление узких мест на основе метрик производительности
        """
        bottlenecks = []
        
        # Анализ размера данных
        if metrics.data_size_bytes > 1_000_000_000:  # > 1GB
            bottlenecks.append("Большой объем данных требует партиционирования")
        
        # Анализ количества строк
        if metrics.row_count > 10_000_000:  # > 10M строк
            bottlenecks.append("Большое количество строк требует индексирования")
        
        # Анализ времени обработки
        if metrics.processing_time_ms and metrics.processing_time_ms > 10_000:  # > 10 секунд
            bottlenecks.append("Медленная обработка данных")
        
        # Анализ времени выполнения запросов (для БД)
        if metrics.avg_query_time_ms and metrics.avg_query_time_ms > 1000:  # > 1 секунды
            bottlenecks.append("Медленные запросы к базе данных")
        
        # Анализ использования индексов
        if metrics.index_usage_stats:
            unused_indexes = [idx for idx, usage in metrics.index_usage_stats.items() if usage < 0.1]
            if unused_indexes:
                bottlenecks.append(f"Неиспользуемые индексы: {', '.join(unused_indexes)}")
        
        # Анализ структуры данных
        if metrics.source_type in [SourceType.CSV, SourceType.JSON, SourceType.XML]:
            if metrics.data_size_bytes > 100_000_000:  # > 100MB
                bottlenecks.append("Файловый формат неэффективен для больших данных")
        
        # Анализ партиций (для БД)
        if metrics.partition_stats:
            uneven_partitions = self._analyze_partition_distribution(metrics.partition_stats)
            if uneven_partitions:
                bottlenecks.append("Неравномерное распределение данных по партициям")
        
        return bottlenecks
    
    def _analyze_partition_distribution(self, partition_stats: Dict[str, Any]) -> bool:
        """
        Анализ распределения данных по партициям
        """
        if not partition_stats or "partition_sizes" not in partition_stats:
            return False
        
        sizes = list(partition_stats["partition_sizes"].values())
        if not sizes:
            return False
        
        avg_size = sum(sizes) / len(sizes)
        max_deviation = max(abs(size - avg_size) for size in sizes)
        
        # Если отклонение больше 50% от среднего размера
        return max_deviation > avg_size * 0.5
    
    async def _get_llm_analysis(self, metrics: PerformanceMetrics, bottlenecks: List[str]) -> str:
        """
        Получение анализа производительности от LLM
        """
        try:
            prompt = f"""
Проанализируй метрики производительности источника данных и предложи рекомендации по оптимизации:

МЕТРИКИ:
- Тип источника: {metrics.source_type.value}
- Размер данных: {metrics.data_size_bytes / (1024*1024):.2f} MB
- Количество строк: {metrics.row_count:,}
- Количество колонок: {metrics.column_count or 'неизвестно'}
- Время обработки: {metrics.processing_time_ms or 0:.2f} мс
- Среднее время запроса: {metrics.avg_query_time_ms or 'неизвестно'} мс

ВЫЯВЛЕННЫЕ УЗКИЕ МЕСТА:
{chr(10).join(f'- {bottleneck}' for bottleneck in bottlenecks)}

СТРУКТУРА ДАННЫХ:
{metrics.structure_info}

Предоставь:
1. Анализ текущего состояния производительности
2. Приоритетные рекомендации по оптимизации
3. Ожидаемый эффект от каждой рекомендации
4. Риски и ограничения при применении оптимизаций

Ответ должен быть структурированным и практичным.
"""
            
            llm_response = get_llm_response(prompt)
            return llm_response.get("content", "Ошибка LLM анализа")
            
        except Exception as e:
            logger.error(f"Ошибка при получении LLM анализа: {str(e)}")
            return f"Ошибка LLM анализа: {str(e)}"
    
    async def analyze_existing_warehouse(self, design_id: str) -> PerformanceAnalysisResult:
        """
        Анализ производительности существующего хранилища из Модуля 4
        """
        analysis_id = f"warehouse_analysis_{design_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Получаем метрики существующего хранилища через Модуль 5
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.module5_base_url}/collect-by-design/{design_id}",
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    return PerformanceAnalysisResult(
                        analysis_id=analysis_id,
                        source=f"design_id:{design_id}",
                        source_type=SourceType.EXISTING_WAREHOUSE,
                        status=AnalysisStatus.ERROR,
                        error_message=f"Не удалось получить метрики хранилища: {response.text}"
                    )
                
                warehouse_metrics = response.json()
                
                # Преобразуем метрики хранилища в наш формат
                performance_metrics = self._convert_warehouse_metrics(warehouse_metrics)
                
                # Анализируем производительность
                bottlenecks = self._identify_bottlenecks(performance_metrics)
                llm_analysis = await self._get_llm_analysis(performance_metrics, bottlenecks)
                
                return PerformanceAnalysisResult(
                    analysis_id=analysis_id,
                    source=f"design_id:{design_id}",
                    source_type=SourceType.EXISTING_WAREHOUSE,
                    status=AnalysisStatus.COMPLETED,
                    current_metrics=performance_metrics,
                    bottlenecks=bottlenecks,
                    llm_analysis=llm_analysis,
                    completed_at=datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Ошибка при анализе хранилища {design_id}: {str(e)}")
            return PerformanceAnalysisResult(
                analysis_id=analysis_id,
                source=f"design_id:{design_id}",
                source_type=SourceType.EXISTING_WAREHOUSE,
                status=AnalysisStatus.ERROR,
                error_message=str(e)
            )
    
    def _convert_warehouse_metrics(self, warehouse_data: Dict[str, Any]) -> PerformanceMetrics:
        """
        Преобразование метрик хранилища в формат PerformanceMetrics
        """
        # Определяем тип СУБД из метрик хранилища
        db_type = warehouse_data.get("db_type", "unknown").lower()
        source_type_mapping = {
            "clickhouse": SourceType.CLICKHOUSE,
            "postgresql": SourceType.POSTGRESQL,
            "postgres": SourceType.POSTGRESQL
        }
        
        source_type = source_type_mapping.get(db_type, SourceType.POSTGRESQL)
        
        return PerformanceMetrics(
            source_type=source_type,
            data_size_bytes=warehouse_data.get("table_size_bytes", 0),
            row_count=warehouse_data.get("row_count", 0),
            column_count=warehouse_data.get("column_count"),
            avg_query_time_ms=warehouse_data.get("avg_query_duration_ms"),
            index_usage_stats=warehouse_data.get("index_usage_stats", {}),
            partition_stats=warehouse_data.get("partition_stats", {}),
            structure_info=warehouse_data.get("table_structure", {})
        )
