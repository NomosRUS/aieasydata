"""
Unit-тесты для функции generate_ddl и связанных компонентов.
"""
import pytest
from unittest.mock import Mock, patch
from .main import (
    generate_ddl, 
    _extract_table_name, 
    _convert_columns_for_template,
    _parse_optimization_recommendations
)


class TestExtractTableName:
    """Тесты для функции извлечения имени таблицы."""
    
    def test_simple_filename(self):
        assert _extract_table_name("/path/to/sales_data.csv") == "sales_data"
    
    def test_complex_filename(self):
        assert _extract_table_name("/path/to/Sales-Data_2023.xlsx") == "sales_data_2023"
    
    def test_filename_with_spaces(self):
        assert _extract_table_name("/path/to/Sales Data 2023.json") == "sales_data_2023"
    
    def test_filename_starting_with_digit(self):
        assert _extract_table_name("/path/to/2023_sales.csv") == "table_2023_sales"
    
    def test_empty_or_invalid_filename(self):
        assert _extract_table_name("") == "table_"
        assert _extract_table_name("/path/to/.csv") == "table_"


class TestConvertColumnsForTemplate:
    """Тесты для преобразования колонок."""
    
    def test_clickhouse_column_conversion(self):
        columns = [
            {"column_name": "id", "column_type": "Int64"},
            {"column_name": "name", "column_type": "String"},
            {"column_name": "created_at", "column_type": "Datetime"}
        ]
        
        result = _convert_columns_for_template(columns, "clickhouse")
        
        expected = [
            {"name": "id", "type": "Int64"},
            {"name": "name", "type": "String"},
            {"name": "created_at", "type": "DateTime"}
        ]
        assert result == expected
    
    def test_postgres_column_conversion(self):
        columns = [
            {"column_name": "id", "column_type": "Int64"},
            {"column_name": "name", "column_type": "String"},
            {"column_name": "is_active", "column_type": "Boolean"}
        ]
        
        result = _convert_columns_for_template(columns, "postgres")
        
        expected = [
            {"name": "id", "type": "BIGINT"},
            {"name": "name", "type": "TEXT"},
            {"name": "is_active", "type": "BOOLEAN"}
        ]
        assert result == expected


class TestParseOptimizationRecommendations:
    """Тесты для парсинга рекомендаций оптимизации."""
    
    def test_clickhouse_partition_recommendation(self):
        recommendations = [
            {
                "recommendation_type": "partition",
                "recommendation_details": {"partition_by": "toYYYYMM(created_at)"}
            }
        ]
        
        result = _parse_optimization_recommendations(recommendations, "clickhouse")
        
        assert result == {"partition_by": "toYYYYMM(created_at)"}
    
    def test_clickhouse_order_by_recommendation(self):
        recommendations = [
            {
                "recommendation_type": "order_by",
                "recommendation_details": {"columns": ["created_at", "id"]}
            }
        ]
        
        result = _parse_optimization_recommendations(recommendations, "clickhouse")
        
        assert result == {"order_by": ["created_at", "id"]}
    
    def test_postgres_index_recommendation(self):
        recommendations = [
            {
                "recommendation_type": "index",
                "recommendation_details": {"columns": ["user_id", "created_at"]}
            }
        ]
        
        result = _parse_optimization_recommendations(recommendations, "postgres")
        
        assert result == {"indexes": ["user_id", "created_at"]}
    
    def test_empty_recommendations(self):
        result = _parse_optimization_recommendations([], "clickhouse")
        assert result == {}
    
    def test_mixed_recommendations_clickhouse(self):
        recommendations = [
            {
                "recommendation_type": "partition",
                "recommendation_details": {"partition_by": "toYYYYMM(date)"}
            },
            {
                "recommendation_type": "order_by", 
                "recommendation_details": {"columns": ["date", "id"]}
            }
        ]
        
        result = _parse_optimization_recommendations(recommendations, "clickhouse")
        
        expected = {
            "partition_by": "toYYYYMM(date)",
            "order_by": ["date", "id"]
        }
        assert result == expected


class TestGenerateDDL:
    """Тесты для основной функции generate_ddl."""
    
    @patch('warehouse_designer.main.agent.generate_ddl_with_explanation')
    def test_generate_ddl_clickhouse_with_optimizations(self, mock_agent):
        """Тест генерации DDL для ClickHouse с оптимизациями."""
        # Подготавливаем mock
        mock_agent.return_value = {
            "ddl": "CREATE TABLE analytics.sales_data (id Int64, amount Float64) ENGINE = MergeTree PARTITION BY toYYYYMM(date) ORDER BY (date, id);"
        }
        
        # Подготавливаем контекст
        context = {
            "data_profile": {
                "source_path": "/data/sales_data.csv",
                "columns": [
                    {"column_name": "id", "column_type": "Int64"},
                    {"column_name": "amount", "column_type": "Float64"}
                ]
            },
            "optimization_recommendations": [
                {
                    "recommendation_type": "partition",
                    "recommendation_details": {"partition_by": "toYYYYMM(date)"}
                },
                {
                    "recommendation_type": "order_by",
                    "recommendation_details": {"columns": ["date", "id"]}
                }
            ]
        }
        
        # Вызываем функцию
        result = generate_ddl(context, "clickhouse")
        
        # Проверяем результат
        assert "PARTITION BY toYYYYMM(date)" in result
        assert "ORDER BY (date, id)" in result
        assert "CREATE TABLE analytics.sales_data" in result
        
        # Проверяем, что agent был вызван с правильными параметрами
        mock_agent.assert_called_once()
        call_args = mock_agent.call_args[0][0]
        assert call_args["target_system"] == "clickhouse"
        assert call_args["partition_by"] == "toYYYYMM(date)"
        assert call_args["order_by"] == ["date", "id"]
    
    @patch('warehouse_designer.main.agent.generate_ddl_with_explanation')
    def test_generate_ddl_postgres_with_indexes(self, mock_agent):
        """Тест генерации DDL для PostgreSQL с индексами."""
        mock_agent.return_value = {
            "ddl": "CREATE TABLE analytics.users (id BIGINT, email TEXT); CREATE INDEX idx_users_email ON analytics.users(email);"
        }
        
        context = {
            "data_profile": {
                "source_path": "/data/users.json",
                "columns": [
                    {"column_name": "id", "column_type": "Int64"},
                    {"column_name": "email", "column_type": "String"}
                ]
            },
            "optimization_recommendations": [
                {
                    "recommendation_type": "index",
                    "recommendation_details": {"columns": ["email"]}
                }
            ]
        }
        
        result = generate_ddl(context, "postgres")
        
        assert "CREATE INDEX" in result
        assert "analytics.users" in result
        
        call_args = mock_agent.call_args[0][0]
        assert call_args["target_system"] == "postgres"
        assert call_args["indexes"] == ["email"]
    
    def test_generate_ddl_missing_columns(self):
        """Тест обработки ошибки при отсутствии колонок."""
        context = {
            "data_profile": {
                "source_path": "/data/empty.csv"
                # columns отсутствует
            },
            "optimization_recommendations": []
        }
        
        with pytest.raises(ValueError, match="Отсутствует схема данных в профиле"):
            generate_ddl(context, "clickhouse")


if __name__ == "__main__":
    pytest.main([__file__])
