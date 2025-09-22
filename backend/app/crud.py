from sqlalchemy.orm import Session
from . import models, schemas

def get_connection(db: Session, connection_id: int):
    return db.query(models.Connection).filter(models.Connection.id == connection_id).first()

def get_connection_by_name(db: Session, name: str):
    return db.query(models.Connection).filter(models.Connection.name == name).first()

def get_connections(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Connection).offset(skip).limit(limit).all()

def create_connection(db: Session, connection: schemas.ConnectionCreate):
    db_connection = models.Connection(**connection.model_dump())
    db.add(db_connection)
    db.commit()
    db.refresh(db_connection)
    return db_connection
