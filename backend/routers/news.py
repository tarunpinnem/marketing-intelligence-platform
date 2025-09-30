from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Optional
from datetime import datetime
from services.news_ingestion import NewsDataIngestionService
from dependencies import get_news_ingestion_service

router = APIRouter(prefix="/api/news", tags=["news"])

@router.post("/ingest")
async def start_news_ingestion(
    background_tasks: BackgroundTasks,
    ingestion_service: NewsDataIngestionService = Depends(get_news_ingestion_service)
):
    """
    Start news data ingestion for marketing campaigns
    """
    try:
        # Start immediate ingestion
        results = await ingestion_service.ingest_data()
        
        # Schedule background ingestion
        background_tasks.add_task(ingestion_service.schedule_ingestion)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaigns")
async def get_news_campaigns(
    company: Optional[str] = None,
    platform: Optional[str] = None,
    days: Optional[int] = 30,
    ingestion_service: NewsDataIngestionService = Depends(get_news_ingestion_service)
):
    """
    Get marketing campaigns from news data
    """
    try:
        query = {"type": "news"}
        
        if company:
            query["company"] = company
        if platform:
            query["platform"] = platform
        
        # Filter by date
        min_date = datetime.utcnow() - timedelta(days=days)
        query["launch_date"] = {"$gte": min_date.isoformat()}
        
        campaigns = await ingestion_service.db.campaigns.find(query).sort("launch_date", -1).to_list(1000)
        
        return {
            "status": "success",
            "total": len(campaigns),
            "campaigns": campaigns
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/companies")
async def get_tracked_companies(
    ingestion_service: NewsDataIngestionService = Depends(get_news_ingestion_service)
):
    """
    Get list of companies being tracked
    """
    return {
        "companies": ingestion_service.tracked_companies
    }

@router.post("/companies")
async def update_tracked_companies(
    companies: List[str],
    ingestion_service: NewsDataIngestionService = Depends(get_news_ingestion_service)
):
    """
    Update the list of companies to track
    """
    ingestion_service.tracked_companies = companies
    return {
        "status": "success",
        "companies": companies
    }