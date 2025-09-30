from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime
from app.models.search import SearchResponse, Campaign
from app.services.search import search_campaigns

router = APIRouter()

@router.get("/search", response_model=SearchResponse)
async def search(
    query: str = Query(..., description="Search query"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    channel: Optional[str] = Query(None, description="Filter by channel (email, social, display, search)"),
    date_from: Optional[datetime] = Query(None, description="Start date for search"),
    date_to: Optional[datetime] = Query(None, description="End date for search")
):
    try:
        results = await search_campaigns(query, company, channel, date_from, date_to)
        return SearchResponse(
            results=results,
            total=len(results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))