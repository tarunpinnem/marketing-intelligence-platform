from fastapi import APIRouter, HTTPException
from app.models.search import Campaign
from app.services.analytics import get_company_trends, get_market_insights, get_realtime_stats

router = APIRouter()

@router.get("/analytics")
async def get_analytics():
    try:
        trends = await get_company_trends()
        insights = await get_market_insights()
        return {
            "trends": trends,
            "insights": insights
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/companies")
async def get_company_analytics():
    try:
        trends = await get_company_trends()
        return {
            "companies": trends,
            "total": len(trends)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/trends")
async def get_trends():
    try:
        trends = await get_company_trends()
        insights = await get_market_insights()
        return {
            "trends": trends,
            "insights": insights,
            "weekly_data": []  # Add weekly trend data if needed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime/stats")
async def get_realtime_statistics():
    try:
        stats = await get_realtime_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))