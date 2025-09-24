from sqlalchemy import Column, Integer, String, JSON, DateTime, Text, func
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
    source_id = Column(Integer, comment="ID источника данных из таблицы data_profiles")
    aggregation_type = Column(String, comment="Типы агрегаций, например, GROUP BY, JOIN")
    target_schema = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String, index=True)
    recommendation_type = Column(String)
    recommendation_details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
