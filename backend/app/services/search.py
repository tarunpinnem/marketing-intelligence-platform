from typing import List, Optional
from datetime import datetime
from elasticsearch import AsyncElasticsearch
from app.models.search import Campaign
from app.config import ELASTIC_URL

es = AsyncElasticsearch([ELASTIC_URL])

async def search_campaigns(
    query: str,
    company: Optional[str] = None,
    channel: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> List[Campaign]:
    must = [{"multi_match": {"query": query, "fields": ["title", "content", "subject_line"]}}]
    
    if company:
        must.append({"match": {"company_name": company}})
    if channel:
        must.append({"match": {"channel": channel}})
    
    date_range = {}
    if date_from:
        date_range["gte"] = date_from.isoformat()
    if date_to:
        date_range["lte"] = date_to.isoformat()
    if date_range:
        must.append({"range": {"launch_date": date_range}})
    
    search_body = {
        "query": {
            "bool": {
                "must": must
            }
        },
        "size": 50,  # Limit results
        "sort": [
            {"score": {"order": "desc"}},
            {"launch_date": {"order": "desc"}}
        ]
    }
    
    try:
        response = await es.search(index="campaigns", body=search_body)
        hits = response["hits"]["hits"]
        
        campaigns = []
        for hit in hits:
            source = hit["_source"]
            campaign = Campaign(
                id=hit["_id"],
                score=hit["_score"],
                **source
            )
            campaigns.append(campaign)
            
        return campaigns
        
    except Exception as e:
        print(f"Error searching campaigns: {str(e)}")
        return []