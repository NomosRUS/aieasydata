import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class ErrorAnalyzer:
    """Анализатор ошибок для классификации и предложения решений."""
    
    def __init__(self, knowledge_base_path: str = "tests/intelligent_scenarios/knowledge_base"):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.error_patterns_path = self.knowledge_base_path / "error_patterns"
        self.error_patterns_path.mkdir(parents=True, exist_ok=True)
        
        # Загрузка существующих паттернов ошибок
        self.error_patterns = self._load_error_patterns()
    
    def analyze_error(
        self, 
        error_message: str, 
        context: Dict[str, Any],
        step_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Анализирует ошибку и предлагает решения.
        
        Args:
            error_message: Текст ошибки
            context: Контекст выполнения (модуль, endpoint, параметры)
            step_info: Информация о шаге сценария
            
        Returns:
            Результат анализа с классификацией и рекомендациями
        """
        analysis = {
            "error_message": error_message,
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "classification": self._classify_error(error_message, context),
            "severity": self._assess_severity(error_message, context),
            "suggestions": self._generate_suggestions(error_message, context),
            "similar_errors": self._find_similar_errors(error_message),
            "recovery_actions": self._suggest_recovery_actions(error_message, context)
        }
        
        # Сохранение нового паттерна ошибки
        self._save_error_pattern(analysis)
        
        return analysis
    
    def _classify_error(self, error_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Классифицирует ошибку по типу и категории."""
        error_lower = error_message.lower()
        
        # Определение типа ошибки
        error_type = "unknown"
        category = "general"
        
        # HTTP ошибки
        if "404" in error_message or "not found" in error_lower:
            error_type = "http_not_found"
            category = "api"
        elif "500" in error_message or "internal server error" in error_lower:
            error_type = "http_server_error"
            category = "api"
        elif "422" in error_message or "unprocessable entity" in error_lower:
            error_type = "http_validation_error"
            category = "api"
        elif "timeout" in error_lower:
            error_type = "timeout"
            category = "network"
        
        # Ошибки подключения
        elif "connection" in error_lower and ("refused" in error_lower or "failed" in error_lower):
            error_type = "connection_error"
            category = "network"
        
        # Ошибки валидации данных
        elif "validation" in error_lower or "invalid" in error_lower:
            error_type = "validation_error"
            category = "data"
        
        # Ошибки формата
        elif "format" in error_lower or "parse" in error_lower or "json" in error_lower:
            error_type = "format_error"
            category = "data"
        
        # Ошибки файловой системы
        elif "file not found" in error_lower or "no such file" in error_lower:
            error_type = "file_not_found"
            category = "filesystem"
        elif "permission denied" in error_lower:
            error_type = "permission_error"
            category = "filesystem"
        
        # Ошибки базы данных
        elif "database" in error_lower or "sql" in error_lower:
            error_type = "database_error"
            category = "database"
        
        return {
            "type": error_type,
            "category": category,
            "confidence": self._calculate_confidence(error_message, error_type)
        }
    
    def _assess_severity(self, error_message: str, context: Dict[str, Any]) -> str:
        """Оценивает серьезность ошибки."""
        error_lower = error_message.lower()
        
        # Критические ошибки
        if any(keyword in error_lower for keyword in [
            "fatal", "critical", "crash", "abort", "panic"
        ]):
            return "critical"
        
        # Высокая серьезность
        if any(keyword in error_lower for keyword in [
            "500", "internal server error", "database", "connection refused"
        ]):
            return "high"
        
        # Средняя серьезность
        if any(keyword in error_lower for keyword in [
            "422", "404", "validation", "timeout"
        ]):
            return "medium"
        
        # Низкая серьезность
        return "low"
    
    def _generate_suggestions(self, error_message: str, context: Dict[str, Any]) -> List[str]:
        """Генерирует предложения по устранению ошибки."""
        suggestions = []
        error_lower = error_message.lower()
        
        # Предложения для HTTP ошибок
        if "404" in error_message:
            suggestions.extend([
                "Проверьте правильность URL endpoint",
                "Убедитесь, что сервис запущен",
                "Проверьте версию API в URL"
            ])
        
        elif "422" in error_message:
            suggestions.extend([
                "Проверьте формат передаваемых данных",
                "Сверьте параметры с API документацией",
                "Убедитесь в корректности типов данных"
            ])
        
        elif "500" in error_message:
            suggestions.extend([
                "Проверьте логи сервера",
                "Убедитесь в корректности конфигурации",
                "Проверьте доступность зависимых сервисов"
            ])
        
        # Предложения для ошибок подключения
        elif "connection" in error_lower and "refused" in error_lower:
            suggestions.extend([
                "Проверьте, что сервис запущен",
                "Убедитесь в правильности порта",
                "Проверьте настройки брандмауэра"
            ])
        
        # Предложения для ошибок валидации
        elif "validation" in error_lower:
            suggestions.extend([
                "Проверьте обязательные поля",
                "Убедитесь в корректности типов данных",
                "Сверьте схему данных с требованиями API"
            ])
        
        # Предложения для ошибок формата
        elif "format" in error_lower or "parse" in error_lower:
            suggestions.extend([
                "Проверьте формат входных данных",
                "Убедитесь в корректности JSON/XML структуры",
                "Проверьте кодировку файла"
            ])
        
        # Предложения для файловых ошибок
        elif "file not found" in error_lower:
            suggestions.extend([
                "Проверьте существование файла",
                "Убедитесь в правильности пути",
                "Проверьте права доступа к файлу"
            ])
        
        # Общие предложения если специфичных нет
        if not suggestions:
            suggestions.extend([
                "Проверьте логи для дополнительной информации",
                "Убедитесь в корректности конфигурации",
                "Попробуйте повторить операцию"
            ])
        
        return suggestions
    
    def _suggest_recovery_actions(self, error_message: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Предлагает действия для восстановления после ошибки."""
        actions = []
        error_lower = error_message.lower()
        
        # Действия для разных типов ошибок
        if "timeout" in error_lower:
            actions.append({
                "action": "retry_with_increased_timeout",
                "description": "Повторить запрос с увеличенным таймаутом",
                "parameters": {"timeout": 600}
            })
        
        elif "connection" in error_lower and "refused" in error_lower:
            actions.extend([
                {
                    "action": "wait_and_retry",
                    "description": "Подождать и повторить попытку",
                    "parameters": {"wait_seconds": 30, "max_retries": 3}
                },
                {
                    "action": "check_service_health",
                    "description": "Проверить состояние сервиса",
                    "parameters": {"health_endpoint": "/health-check"}
                }
            ])
        
        elif "422" in error_message:
            actions.append({
                "action": "validate_input_data",
                "description": "Проверить и исправить входные данные",
                "parameters": {"strict_validation": True}
            })
        
        elif "404" in error_message:
            actions.append({
                "action": "verify_endpoint",
                "description": "Проверить корректность endpoint",
                "parameters": {"check_api_docs": True}
            })
        
        return actions
    
    def _find_similar_errors(self, error_message: str) -> List[Dict[str, Any]]:
        """Находит похожие ошибки в базе знаний."""
        similar_errors = []
        
        # Поиск в сохраненных паттернах ошибок
        for pattern_file in self.error_patterns_path.glob("*.json"):
            try:
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    pattern_data = json.load(f)
                
                # Простое сравнение по ключевым словам
                similarity = self._calculate_similarity(error_message, pattern_data.get("error_message", ""))
                
                if similarity > 0.5:  # Порог схожести
                    similar_errors.append({
                        "pattern_id": pattern_file.stem,
                        "error_message": pattern_data.get("error_message"),
                        "similarity": similarity,
                        "resolution": pattern_data.get("resolution"),
                        "success_rate": pattern_data.get("success_rate", 0)
                    })
            
            except Exception as e:
                logger.warning(f"Failed to load error pattern {pattern_file}: {e}")
        
        # Сортировка по схожести
        similar_errors.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_errors[:5]  # Топ 5 похожих ошибок
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Вычисляет схожесть между двумя текстами ошибок."""
        if not text1 or not text2:
            return 0.0
        
        # Простой алгоритм на основе общих слов
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _calculate_confidence(self, error_message: str, error_type: str) -> float:
        """Вычисляет уверенность в классификации ошибки."""
        # Простая эвристика на основе ключевых слов
        confidence_map = {
            "http_not_found": 0.9 if "404" in error_message else 0.7,
            "http_server_error": 0.9 if "500" in error_message else 0.7,
            "http_validation_error": 0.9 if "422" in error_message else 0.7,
            "timeout": 0.8 if "timeout" in error_message.lower() else 0.6,
            "connection_error": 0.8 if "connection" in error_message.lower() else 0.6
        }
        
        return confidence_map.get(error_type, 0.5)
    
    def _save_error_pattern(self, analysis: Dict[str, Any]):
        """Сохраняет паттерн ошибки в базу знаний."""
        try:
            pattern_id = f"error_{int(datetime.now().timestamp())}"
            pattern_file = self.error_patterns_path / f"{pattern_id}.json"
            
            pattern_data = {
                "pattern_id": pattern_id,
                "error_message": analysis["error_message"],
                "classification": analysis["classification"],
                "severity": analysis["severity"],
                "suggestions": analysis["suggestions"],
                "recovery_actions": analysis["recovery_actions"],
                "context": analysis["context"],
                "timestamp": analysis["timestamp"],
                "resolution": None,  # Будет заполнено при успешном решении
                "success_rate": 0.0
            }
            
            with open(pattern_file, 'w', encoding='utf-8') as f:
                json.dump(pattern_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Error pattern saved: {pattern_id}")
            
        except Exception as e:
            logger.error(f"Failed to save error pattern: {e}")
    
    def _load_error_patterns(self) -> Dict[str, Any]:
        """Загружает существующие паттерны ошибок."""
        patterns = {}
        
        if not self.error_patterns_path.exists():
            return patterns
        
        for pattern_file in self.error_patterns_path.glob("*.json"):
            try:
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    pattern_data = json.load(f)
                    patterns[pattern_file.stem] = pattern_data
            except Exception as e:
                logger.warning(f"Failed to load error pattern {pattern_file}: {e}")
        
        return patterns
    
    def update_pattern_resolution(self, pattern_id: str, resolution: str, success: bool):
        """Обновляет информацию о решении паттерна ошибки."""
        pattern_file = self.error_patterns_path / f"{pattern_id}.json"
        
        if pattern_file.exists():
            try:
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    pattern_data = json.load(f)
                
                pattern_data["resolution"] = resolution
                if success:
                    pattern_data["success_rate"] = pattern_data.get("success_rate", 0) + 0.1
                
                with open(pattern_file, 'w', encoding='utf-8') as f:
                    json.dump(pattern_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Updated error pattern resolution: {pattern_id}")
                
            except Exception as e:
                logger.error(f"Failed to update error pattern {pattern_id}: {e}")
