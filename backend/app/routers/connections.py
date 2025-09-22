from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/connections",
    tags=["connections"],
)

@router.post("/", response_model=schemas.Connection)
def create_connection(connection: schemas.ConnectionCreate, db: Session = Depends(get_db)):
    db_connection = crud.get_connection_by_name(db, name=connection.name)
    if db_connection:
        raise HTTPException(status_code=400, detail="Connection with this name already registered")
    return crud.create_connection(db=db, connection=connection)

@router.get("/", response_model=List[schemas.Connection])
def read_connections(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    connections = crud.get_connections(db, skip=skip, limit=limit)
    return connections

@router.get("/{connection_id}", response_model=schemas.Connection)
def read_connection(connection_id: int, db: Session = Depends(get_db)):
    db_connection = crud.get_connection(db, connection_id=connection_id)
    if db_connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    return db_connection
