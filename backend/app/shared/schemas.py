from sqlalchemy import Column, Integer, String, JSON, DateTime, Text, func, UniqueConstraint
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

# Эти модели будут использоваться несколькими модулями.
# Модуль Задачи 2 будет записывать данные в AggregationScenario.
# Модуль Задачи 3 будет записывать данные в OptimizationRecommendation.
# Ваш модуль (Задача 4) будет читать данные из этих таблиц.

class AggregationScenario(Base):
    __tablename__ = 'aggregation_scenarios'

    id = Column(Integer, primary_key=True, index=True)
    scenario_name = Column(String, unique=True, nullable=False, comment="Уникальное имя сценария")
    description = Column(Text, comment="Описание сценария агрегации")
    sources = Column(JSON, comment="Список источников данных")
    aggregations = Column(JSON, comment="Конфигурация агрегаций")
    enrichments = Column(JSON, comment="Правила обогащения данных")
    target_requirements = Column(JSON, comment="Требования к целевой системе")
    status = Column(String, default="created", comment="Статус сценария")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_executed = Column(DateTime, comment="Время последнего выполнения")
    execution_stats = Column(JSON, comment="Статистика выполнения")

class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String, index=True)
    recommendation_type = Column(String)
    recommendation_details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('table_name', 'recommendation_type', name='uq_table_recommendation'),
    )


class WarehouseInstance(Base):
    __tablename__ = "warehouse_instances"

    id = Column(Integer, primary_key=True, index=True)
    design_id = Column(String, index=True, unique=True)
    target_db_type = Column(String, index=True)
    db_name = Column(String)
    table_name = Column(String)
    ddl_script = Column(Text)
    metrics = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WarehouseDesign(Base):
    __tablename__ = 'warehouse_designs'

    id = Column(Integer, primary_key=True, index=True)
    design_id = Column(String, unique=True, index=True)

    status = Column(String)
    source_profile_id = Column(Integer)
    selected_db = Column(String)  # Выбранная СУБД (clickhouse, postgres, hdfs)
    request_payload = Column(JSON)
    results = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
