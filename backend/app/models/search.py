from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class Campaign(BaseModel):
    id: str
    title: str
    company_name: str
    subject_line: Optional[str]
    content: Optional[str]
    channel: Optional[str]
    classification: Optional[str]
    launch_date: Optional[datetime]
    score: Optional[float]
    sentiment_score: Optional[float]
    keywords: Optional[List[str]]

class SearchResponse(BaseModel):
    results: List[Campaign]
    total: int