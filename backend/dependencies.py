from typing import Optional
from fastapi import Depends
from services.data_ingestion import DataIngestionService
from services.database import get_database

_data_ingestion_service: Optional[DataIngestionService] = None

async def get_data_ingestion_service(
    db = Depends(get_database)
) -> DataIngestionService:
    global _data_ingestion_service
    if _data_ingestion_service is None:
        _data_ingestion_service = DataIngestionService(db)
    return _data_ingestion_service