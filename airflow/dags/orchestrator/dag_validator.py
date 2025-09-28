#!/usr/bin/env python3
"""
Валидатор DAG'ов на основе успешных паттернов и исправленных ошибок
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class ValidationError:
    """Ошибка валидации DAG'а"""
    severity: str  # "error", "warning", "info"
    message: str
    suggestion: str
    example: Optional[Dict[str, Any]] = None

class DAGValidator:
    """Валидатор DAG'ов на основе проверенных паттернов"""
    
    def __init__(self):
        # HTTP методы для каждого модуля (на основе успешных тестов)
        self.module_http_methods = {
            1: "POST",  # Модуль 1 - ВСЕГДА POST
            2: "POST",  # Модуль 2 - ВСЕГДА POST  
            3: "POST",  # Модуль 3 - ВСЕГДА POST
            5: "GET/POST"  # Модуль 5 - зависит от endpoint'а
        }
        
        # Успешные паттерны (проверены тестами)
        self.successful_patterns = {
            "auto_detect_sources": {
                "module": 5,
                "method": "GET",
                "endpoint": "/api/v1/metrics/auto-detect"
            },
            "batch_validate_sources": {
                "module": 1,
                "method": "POST", 
                "endpoint": "/api/v1/data-quality/batch-validate"
            },
            "create_scenario": {
                "module": 2,
                "method": "POST",  # КРИТИЧНО: не GET!
                "endpoint": "/api/v1/aggregation/create-scenario"
            }
        }
        
        # Обязательные поля для каждого модуля
        self.required_fields = {
            "module_2_create_scenario": [
                "name", "description", "sources", "aggregations", "target_requirements"
            ],
            "module_3_optimize": [
                "analysis_id", "recommendation_ids", "confirm_application", "dry_run"
            ]
        }
    
    def validate_dag_config(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Валидация конфигурации DAG'а"""
        errors = []
        
        if "stages" not in config:
            errors.append(ValidationError(
                severity="error",
                message="Missing 'stages' in DAG configuration",
                suggestion="Add 'stages' array to configuration"
            ))
            return errors
        
        for i, stage in enumerate(config["stages"]):
            stage_errors = self._validate_stage(stage, i)
            errors.extend(stage_errors)
        
        return errors
    
    def _validate_stage(self, stage: Dict[str, Any], stage_index: int) -> List[ValidationError]:
        """Валидация отдельного этапа DAG'а"""
        errors = []
        
        # Проверка обязательных полей этапа
        required_stage_fields = ["stage_name", "stage_type", "module", "endpoint", "parameters"]
        for field in required_stage_fields:
            if field not in stage:
                errors.append(ValidationError(
                    severity="error",
                    message=f"Stage {stage_index}: Missing required field '{field}'",
                    suggestion=f"Add '{field}' to stage configuration"
                ))
        
        if "module" in stage and "endpoint" in stage:
            # Валидация HTTP методов
            method_errors = self._validate_http_method(stage)
            errors.extend(method_errors)
            
            # Валидация структуры данных
            data_errors = self._validate_data_structure(stage)
            errors.extend(data_errors)
            
            # Валидация path parameters
            path_errors = self._validate_path_parameters(stage)
            errors.extend(path_errors)
        
        return errors
    
    def _validate_http_method(self, stage: Dict[str, Any]) -> List[ValidationError]:
        """Валидация HTTP методов на основе успешных паттернов"""
        errors = []
        module = stage.get("module")
        endpoint = stage.get("endpoint", "")
        
        # Определяем правильный метод на основе модуля и endpoint'а
        if module in [1, 2, 3]:
            expected_method = "POST"
            if stage.get("method") != expected_method:
                errors.append(ValidationError(
                    severity="error",
                    message=f"Module {module} requires POST method, got {stage.get('method')}",
                    suggestion=f"Change method to 'POST' for module {module}",
                    example={"method": "POST"}
                ))
        
        elif module == 5:
            # Модуль 5: GET для auto-detect, POST для collect
            if "auto-detect" in endpoint:
                expected_method = "GET"
            elif "collect" in endpoint:
                expected_method = "POST"
            else:
                expected_method = "GET"  # По умолчанию
            
            if stage.get("method") != expected_method:
                errors.append(ValidationError(
                    severity="warning",
                    message=f"Module 5 endpoint '{endpoint}' typically uses {expected_method}",
                    suggestion=f"Consider using '{expected_method}' method",
                    example={"method": expected_method}
                ))
        
        return errors
    
    def _validate_data_structure(self, stage: Dict[str, Any]) -> List[ValidationError]:
        """Валидация структуры данных на основе Pydantic схем"""
        errors = []
        module = stage.get("module")
        endpoint = stage.get("endpoint", "")
        parameters = stage.get("parameters", {})
        
        # Валидация для модуля 2 (create-scenario)
        if module == 2 and "create-scenario" in endpoint:
            errors.extend(self._validate_module2_structure(parameters))
        
        # Валидация для модуля 3 (optimize)
        elif module == 3 and "optimize" in endpoint:
            errors.extend(self._validate_module3_structure(parameters))
        
        return errors
    
    def _validate_module2_structure(self, parameters: Dict[str, Any]) -> List[ValidationError]:
        """Валидация структуры AggregationScenarioRequest"""
        errors = []
        
        # Проверка обязательных полей
        required_fields = ["name", "description", "sources", "aggregations", "target_requirements"]
        for field in required_fields:
            if field not in parameters:
                errors.append(ValidationError(
                    severity="error",
                    message=f"Module 2 create-scenario: Missing required field '{field}'",
                    suggestion=f"Add '{field}' to parameters"
                ))
        
        # Проверка структуры sources
        if "sources" in parameters:
            sources = parameters["sources"]
            if not isinstance(sources, list) or len(sources) == 0:
                errors.append(ValidationError(
                    severity="error",
                    message="Module 2: 'sources' must be non-empty array",
                    suggestion="Add at least one source to 'sources' array"
                ))
            else:
                for i, source in enumerate(sources):
                    source_errors = self._validate_source_structure(source, i)
                    errors.extend(source_errors)
        
        # Проверка структуры aggregations
        if "aggregations" in parameters:
            aggregations = parameters["aggregations"]
            if not isinstance(aggregations, list) or len(aggregations) == 0:
                errors.append(ValidationError(
                    severity="error",
                    message="Module 2: 'aggregations' must be non-empty array",
                    suggestion="Add at least one aggregation to 'aggregations' array"
                ))
            else:
                for i, agg in enumerate(aggregations):
                    agg_errors = self._validate_aggregation_structure(agg, i)
                    errors.extend(agg_errors)
        
        return errors
    
    def _validate_source_structure(self, source: Dict[str, Any], index: int) -> List[ValidationError]:
        """Валидация структуры источника данных"""
        errors = []
        
        required_source_fields = ["source_id", "source_type", "selected_columns"]
        for field in required_source_fields:
            if field not in source:
                errors.append(ValidationError(
                    severity="error",
                    message=f"Source {index}: Missing required field '{field}'",
                    suggestion=f"Add '{field}' to source configuration"
                ))
        
        # Проверка selected_columns не пустые (частая ошибка!)
        selected_columns = source.get("selected_columns", [])
        if not selected_columns:
            errors.append(ValidationError(
                severity="error",
                message=f"Source {index}: 'selected_columns' cannot be empty",
                suggestion="Add column names to 'selected_columns' array",
                example={"selected_columns": ["sale_date", "customer_id", "amount"]}
            ))
        
        # Проверка source_type
        valid_source_types = ["file", "postgresql", "clickhouse", "hdfs"]
        source_type = source.get("source_type")
        if source_type not in valid_source_types:
            errors.append(ValidationError(
                severity="error",
                message=f"Source {index}: Invalid source_type '{source_type}'",
                suggestion=f"Use one of: {', '.join(valid_source_types)}"
            ))
        
        return errors
    
    def _validate_aggregation_structure(self, aggregation: Dict[str, Any], index: int) -> List[ValidationError]:
        """Валидация структуры агрегации"""
        errors = []
        
        if "type" not in aggregation:
            errors.append(ValidationError(
                severity="error",
                message=f"Aggregation {index}: Missing 'type' field",
                suggestion="Add 'type' field (join, group_by, window, union)"
            ))
        
        if "parameters" not in aggregation:
            errors.append(ValidationError(
                severity="error",
                message=f"Aggregation {index}: Missing 'parameters' field",
                suggestion="Add 'parameters' object with aggregation-specific fields"
            ))
        
        # Проверка соответствия parameters типу aggregation
        agg_type = aggregation.get("type")
        parameters = aggregation.get("parameters", {})
        
        if agg_type == "group_by":
            # Правильная структура согласно GroupByRule
            if "columns" not in parameters:
                errors.append(ValidationError(
                    severity="error",
                    message=f"Aggregation {index}: group_by type requires 'columns' field",
                    suggestion="Add 'columns' array to parameters (not 'group_by_columns')",
                    example={"columns": ["category"]}
                ))
            if "aggregates" not in parameters:
                errors.append(ValidationError(
                    severity="error",
                    message=f"Aggregation {index}: group_by type requires 'aggregates' field",
                    suggestion="Add 'aggregates' dict to parameters (not 'aggregation_functions')",
                    example={"aggregates": {"total_value": "SUM(value)", "count_records": "COUNT(*)"}}
                ))
            
            # Проверяем неправильные поля
            if "group_by_columns" in parameters:
                errors.append(ValidationError(
                    severity="error",
                    message=f"Aggregation {index}: 'group_by_columns' is incorrect field name",
                    suggestion="Use 'columns' instead of 'group_by_columns'"
                ))
            if "aggregation_functions" in parameters:
                errors.append(ValidationError(
                    severity="error",
                    message=f"Aggregation {index}: 'aggregation_functions' is incorrect field name",
                    suggestion="Use 'aggregates' dict instead of 'aggregation_functions' array"
                ))
        
        return errors
    
    def _validate_module3_structure(self, parameters: Dict[str, Any]) -> List[ValidationError]:
        """Валидация структуры OptimizationApplication"""
        errors = []
        
        required_fields = ["analysis_id", "recommendation_ids", "confirm_application", "dry_run"]
        for field in required_fields:
            if field not in parameters:
                errors.append(ValidationError(
                    severity="error",
                    message=f"Module 3 optimize: Missing required field '{field}'",
                    suggestion=f"Add '{field}' to parameters"
                ))
        
        # Проверка analysis_id не пустой
        analysis_id = parameters.get("analysis_id")
        if not analysis_id or analysis_id in ["weekly_analysis", "default_analysis"]:
            errors.append(ValidationError(
                severity="warning",
                message="Module 3: analysis_id should reference existing analysis",
                suggestion="Use analysis_id from previous analyze step",
                example={"analysis_id": "corrected_analysis"}
            ))
        
        return errors
    
    def _validate_path_parameters(self, stage: Dict[str, Any]) -> List[ValidationError]:
        """Валидация path parameters"""
        errors = []
        endpoint = stage.get("endpoint", "")
        parameters = stage.get("parameters", {})
        
        # Проверка {analysis_id} в endpoint
        if "{analysis_id}" in endpoint:
            if "analysis_id" not in parameters:
                errors.append(ValidationError(
                    severity="error",
                    message="Endpoint contains {analysis_id} but parameter is missing",
                    suggestion="Add 'analysis_id' to parameters"
                ))
        
        # Проверка {scenario_id} в endpoint  
        if "{scenario_id}" in endpoint:
            if "scenario_id" not in parameters:
                errors.append(ValidationError(
                    severity="error",
                    message="Endpoint contains {scenario_id} but parameter is missing",
                    suggestion="Add 'scenario_id' to parameters"
                ))
        
        return errors
    
    def generate_corrected_config(self, config: Dict[str, Any], errors: List[ValidationError]) -> Dict[str, Any]:
        """Генерация исправленной конфигурации на основе ошибок"""
        corrected_config = json.loads(json.dumps(config))  # Deep copy
        
        for error in errors:
            if error.severity == "error" and error.example:
                # Применяем исправления из примеров
                # Это упрощенная логика, в реальности нужна более сложная
                pass
        
        return corrected_config
    
    def get_successful_example(self, module: int, endpoint: str) -> Optional[Dict[str, Any]]:
        """Получение успешного примера для модуля и endpoint'а"""
        
        if module == 2 and "create-scenario" in endpoint:
            return {
                "name": "corrected_test_scenario",
                "description": "Corrected test aggregation scenario",
                "sources": [
                    {
                        "source_id": "sales_data",
                        "source_type": "file",
                        "path": "/data/raw/sales.csv",
                        "selected_columns": ["sale_date", "customer_id", "amount"]
                    }
                ],
                "aggregations": [
                    {
                        "type": "group_by",
                        "parameters": {
                            "columns": ["sale_date"],
                            "aggregates": {
                                "total_amount": "SUM(amount)",
                                "count_records": "COUNT(*)"
                            }
                        }
                    }
                ],
                "target_requirements": {
                    "expected_volume": "medium",
                    "performance_priority": "balanced"
                }
            }
        
        elif module == 3 and "optimize" in endpoint:
            return {
                "analysis_id": "corrected_analysis",
                "recommendation_ids": ["partition", "index"],
                "confirm_application": False,
                "dry_run": True
            }
        
        return None

def validate_dag_file(dag_config: Dict[str, Any]) -> Dict[str, Any]:
    """Основная функция валидации DAG файла"""
    validator = DAGValidator()
    errors = validator.validate_dag_config(dag_config)
    
    # Группировка ошибок по серьезности
    error_summary = {
        "errors": [e for e in errors if e.severity == "error"],
        "warnings": [e for e in errors if e.severity == "warning"],
        "info": [e for e in errors if e.severity == "info"]
    }
    
    return {
        "is_valid": len(error_summary["errors"]) == 0,
        "error_count": len(error_summary["errors"]),
        "warning_count": len(error_summary["warnings"]),
        "errors": error_summary,
        "corrected_config": validator.generate_corrected_config(dag_config, errors) if errors else None
    }

if __name__ == "__main__":
    # Пример использования
    test_config = {
        "stages": [
            {
                "stage_name": "test_stage",
                "stage_type": "module_call",
                "module": 2,
                "endpoint": "/api/v1/aggregation/create-scenario",
                "method": "GET",  # ❌ Ошибка: должен быть POST
                "parameters": {
                    "name": "test",
                    "sources": [{"source_id": "test", "source_type": "file", "selected_columns": []}]  # ❌ Пустые колонки
                }
            }
        ]
    }
    
    result = validate_dag_file(test_config)
    print(f"Valid: {result['is_valid']}")
    print(f"Errors: {result['error_count']}")
    print(f"Warnings: {result['warning_count']}")
    
    for error in result["errors"]["errors"]:
        print(f"ERROR: {error.message}")
        print(f"  Suggestion: {error.suggestion}")
