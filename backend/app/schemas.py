from pydantic import BaseModel
from typing import Literal
import datetime

class ConnectionBase(BaseModel):
    name: str
    type: Literal["postgres", "clickhouse", "hdfs", "s3", "csv", "json", "xml"]
    uri: str

class ConnectionCreate(ConnectionBase):
    pass

class Connection(ConnectionBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True # В Pydantic v2 это называется from_attributes
