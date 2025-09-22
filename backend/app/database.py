import os
from datetime import datetime
from typing import Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, DateTime, BigInteger, Text
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Получаем DSN из переменных окружения, как настроено в docker-compose.yml
SQLALCHEMY_DATABASE_URL = os.environ.get("POSTGRES_DSN", "postgresql://user:password@localhost:5432/aieasydata")

# Создаем "движок" SQLAlchemy
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Создаем фабрику сессий, которая будет создавать сессии для каждого запроса
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()

class DataProfile(Base):
    __tablename__ = "data_profiles"

    id = Column(Integer, primary_key=True, index=True)
    source_path = Column(String, unique=True, index=True, nullable=False)
    kind = Column(String, nullable=True)
    total_row_count = Column(BigInteger, nullable=True)
    file_count = Column(Integer, nullable=True)
    columns = Column(JSONB, nullable=True)
    sample_data = Column(JSONB, nullable=True)
    llm_summary = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def upsert_data_profile(db: Session, profile_data: Dict[str, Any]):
    """
    Inserts or updates a data profile in the database using the source_path as the key.
    """
    stmt = insert(DataProfile).values(
        source_path=profile_data["source_path"],
        kind=profile_data.get("kind"),
        total_row_count=profile_data.get("total_row_count"),
        file_count=profile_data.get("file_count"),
        columns=profile_data.get("columns"),
        sample_data=profile_data.get("sample_data"),
        error=profile_data.get("error"),
        updated_at=datetime.utcnow()
    )

    on_conflict_stmt = stmt.on_conflict_do_update(
        index_elements=['source_path'],
        set_=dict(
            kind=stmt.excluded.kind,
            total_row_count=stmt.excluded.total_row_count,
            file_count=stmt.excluded.file_count,
            columns=stmt.excluded.columns,
            sample_data=stmt.excluded.sample_data,
            error=stmt.excluded.error,
            updated_at=datetime.utcnow()
        )
    )
    db.execute(on_conflict_stmt)
    # The commit will be handled by the calling function (e.g., in the DAG)


# Функция-зависимость для получения сессии БД в эндпоинтах FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Утилита для создания таблицы (можно вызывать отдельно при инициализации приложения)
def create_tables():
    Base.metadata.create_all(bind=engine)
