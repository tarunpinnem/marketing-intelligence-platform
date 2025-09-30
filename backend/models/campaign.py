from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime

class CampaignMetrics(BaseModel):
    impressions: Optional[int] = None
    engagement: Optional[float] = None
    sentiment_score: Optional[float] = None
    spend: Optional[float] = None
    clicks: Optional[int] = None
    conversions: Optional[int] = None

class Campaign(BaseModel):
    id: Optional[str] = None
    company: str
    name: str
    platform: str
    status: str = "active"
    launch_date: datetime
    end_date: Optional[datetime] = None
    metrics: Optional[CampaignMetrics] = None
    raw_data: Optional[Dict] = None
    ingestion_date: Optional[datetime] = None
    source: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }