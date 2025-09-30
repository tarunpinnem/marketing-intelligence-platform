from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Optional
from datetime import datetime
from models.campaign import Campaign
from services.data_ingestion import DataIngestionService
from dependencies import get_data_ingestion_service

router = APIRouter(prefix="/api/ingestion", tags=["data-ingestion"])

@router.post("/start")
async def start_ingestion(
    sources: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = None,
    ingestion_service: DataIngestionService = Depends(get_data_ingestion_service)
):
    """
    Start data ingestion from specified sources
    """
    try:
        # Start immediate ingestion
        results = await ingestion_service.ingest_data(sources)
        
        # Schedule background ingestion if requested
        if background_tasks:
            background_tasks.add_task(ingestion_service.schedule_ingestion)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow(),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_ingestion_status(
    ingestion_service: DataIngestionService = Depends(get_data_ingestion_service)
):
    """
    Get current ingestion status
    """
    # Add status tracking to ingestion service
    return {
        "status": "running",
        "last_ingestion": datetime.utcnow(),
        "sources": ["meta_ad_library", "google_ads", "twitter_ads", "linkedin_ads"]
    }

@router.post("/configure")
async def configure_ingestion(
    config: dict,
    ingestion_service: DataIngestionService = Depends(get_data_ingestion_service)
):
    """
    Configure data ingestion settings
    """
    # Update API keys and configuration
    ingestion_service.api_keys.update(config.get('api_keys', {}))
    return {"status": "success", "message": "Configuration updated"}