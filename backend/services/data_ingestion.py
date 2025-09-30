from fastapi import HTTPException
import aiohttp
import asyncio
from datetime import datetime
import json
from typing import Dict, List, Optional
import logging
from .database import Database
from models.campaign import Campaign

logger = logging.getLogger(__name__)

class DataIngestionService:
    def __init__(self, database: Database):
        self.db = database
        self.api_keys = {
            'meta_ad_library': None,  # Add your Meta Ad Library API key
            'google_ads': None,       # Add your Google Ads API key
            'twitter_ads': None       # Add your Twitter Ads API key
        }
        self.sources = {
            'meta_ad_library': self._fetch_meta_ads,
            'google_ads': self._fetch_google_ads,
            'twitter_ads': self._fetch_twitter_ads,
            'linkedin_ads': self._fetch_linkedin_ads
        }

    async def _fetch_meta_ads(self, params: Dict) -> List[Dict]:
        """Fetch ads from Meta Ad Library API"""
        async with aiohttp.ClientSession() as session:
            try:
                url = "https://graph.facebook.com/v18.0/ads_archive"
                params.update({
                    "access_token": self.api_keys['meta_ad_library'],
                    "fields": "ad_creation_time,ad_creative_body,page_name,platform,status,demographic_distribution",
                    "limit": 100
                })
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._transform_meta_ads(data.get('data', []))
                    else:
                        logger.error(f"Meta API error: {response.status}")
                        return []
            except Exception as e:
                logger.error(f"Error fetching Meta ads: {str(e)}")
                return []

    def _transform_meta_ads(self, ads: List[Dict]) -> List[Dict]:
        """Transform Meta ads into standard format"""
        transformed = []
        for ad in ads:
            campaign = {
                "platform": "Facebook",
                "company": ad.get("page_name"),
                "name": ad.get("ad_creative_body", "")[:100],
                "status": ad.get("status", "active").lower(),
                "launch_date": ad.get("ad_creation_time"),
                "metrics": {
                    "impressions": None,
                    "engagement": None,
                    "sentiment_score": None
                },
                "raw_data": ad
            }
            transformed.append(campaign)
        return transformed

    async def _fetch_google_ads(self, params: Dict) -> List[Dict]:
        """Placeholder for Google Ads API integration"""
        # Implement Google Ads API integration
        return []

    async def _fetch_twitter_ads(self, params: Dict) -> List[Dict]:
        """Placeholder for Twitter Ads API integration"""
        # Implement Twitter Ads API integration
        return []

    async def _fetch_linkedin_ads(self, params: Dict) -> List[Dict]:
        """Placeholder for LinkedIn Ads API integration"""
        # Implement LinkedIn Ads API integration
        return []

    async def ingest_data(self, sources: List[str] = None, params: Dict = None) -> Dict:
        """
        Ingest data from specified sources
        """
        if sources is None:
            sources = list(self.sources.keys())
        if params is None:
            params = {}

        results = {
            "total_ingested": 0,
            "sources": {},
            "errors": []
        }

        tasks = []
        for source in sources:
            if source in self.sources:
                tasks.append(self.sources[source](params))

        try:
            campaign_lists = await asyncio.gather(*tasks, return_exceptions=True)
            
            for source, campaigns in zip(sources, campaign_lists):
                if isinstance(campaigns, Exception):
                    results["errors"].append({
                        "source": source,
                        "error": str(campaigns)
                    })
                    continue
                
                results["sources"][source] = len(campaigns)
                results["total_ingested"] += len(campaigns)
                
                # Store campaigns in database
                for campaign in campaigns:
                    try:
                        await self.db.campaigns.insert_one({
                            **campaign,
                            "ingestion_date": datetime.utcnow(),
                            "source": source
                        })
                    except Exception as e:
                        logger.error(f"Error storing campaign: {str(e)}")
                        results["errors"].append({
                            "source": source,
                            "error": f"Storage error: {str(e)}"
                        })

        except Exception as e:
            logger.error(f"Ingestion error: {str(e)}")
            results["errors"].append({
                "source": "general",
                "error": str(e)
            })

        return results

    async def schedule_ingestion(self, interval_minutes: int = 60):
        """
        Schedule periodic data ingestion
        """
        while True:
            try:
                await self.ingest_data()
                await asyncio.sleep(interval_minutes * 60)
            except Exception as e:
                logger.error(f"Scheduled ingestion error: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes on error