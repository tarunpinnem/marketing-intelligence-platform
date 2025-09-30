from fastapi import HTTPException
import aiohttp
import asyncio
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class NewsDataIngestionService:
    def __init__(self, database):
        self.db = database
        self.api_key = os.getenv('NEWS_API_KEY')
        self.base_url = "https://newsapi.org/v2"
        self.tracked_companies = json.loads(os.getenv('TRACKED_COMPANIES', '[]'))
        
    async def fetch_marketing_news(self, company: str) -> List[Dict]:
        """Fetch marketing and advertising related news for a company"""
        async with aiohttp.ClientSession() as session:
            try:
                # Create query for marketing and advertising related news
                query = f'"{company}" AND (marketing OR advertising OR campaign OR "ad campaign" OR promotion)'
                
                # Calculate date range (last 30 days, as per News API limits)
                from_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                url = f"{self.base_url}/everything"
                params = {
                    'q': query,
                    'apiKey': self.api_key,
                    'language': 'en',
                    'from': from_date,
                    'sortBy': 'publishedAt',
                    'pageSize': 100  # Maximum allowed by News API
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._transform_news_to_campaigns(data.get('articles', []), company)
                    else:
                        error_data = await response.json()
                        logger.error(f"News API error: {error_data}")
                        return []
            except Exception as e:
                logger.error(f"Error fetching news for {company}: {str(e)}")
                return []

    def _transform_news_to_campaigns(self, articles: List[Dict], company: str) -> List[Dict]:
        """Transform news articles into campaign data"""
        campaigns = []
        for article in articles:
            # Extract campaign information from news article
            campaign = {
                "id": article.get('url'),  # Use URL as unique identifier
                "company": company,
                "name": article.get('title'),
                "description": article.get('description'),
                "source": article.get('source', {}).get('name'),
                "platform": self._detect_platform(article),
                "status": "active",
                "launch_date": article.get('publishedAt'),
                "url": article.get('url'),
                "metrics": {
                    "sentiment_score": self._calculate_sentiment(article),
                },
                "raw_data": article,
                "ingestion_date": datetime.utcnow().isoformat(),
                "type": "news"
            }
            campaigns.append(campaign)
        return campaigns

    def _detect_platform(self, article: Dict) -> str:
        """Detect marketing platform from article content"""
        platforms = {
            'facebook': 'Facebook',
            'instagram': 'Instagram',
            'twitter': 'Twitter',
            'linkedin': 'LinkedIn',
            'youtube': 'YouTube',
            'tiktok': 'TikTok',
            'tv': 'Television',
            'television': 'Television',
            'print': 'Print',
            'digital': 'Digital',
            'social media': 'Social Media'
        }
        
        content = (
            (article.get('title', '') + ' ' + 
             article.get('description', '') + ' ' + 
             article.get('content', '')).lower()
        )
        
        detected_platforms = []
        for keyword, platform in platforms.items():
            if keyword in content:
                detected_platforms.append(platform)
        
        return detected_platforms[0] if detected_platforms else 'Multiple'

    def _calculate_sentiment(self, article: Dict) -> float:
        """
        Calculate sentiment score from article content
        Returns a score between 0 and 1
        This is a simple implementation - you might want to use a proper NLP service
        """
        positive_words = {'launch', 'success', 'innovative', 'growth', 'popular', 
                         'exciting', 'remarkable', 'achievement', 'excellent'}
        negative_words = {'controversy', 'problem', 'issue', 'fail', 'criticism',
                         'controversy', 'negative', 'backlash', 'poor'}
        
        content = (
            (article.get('title', '') + ' ' + 
             article.get('description', '') + ' ' + 
             article.get('content', '')).lower()
        )
        
        positive_count = sum(1 for word in positive_words if word in content)
        negative_count = sum(1 for word in negative_words if word in content)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.5  # Neutral
        
        return min(1.0, max(0.0, (positive_count / (total * 1.0)) + 0.5))

    async def ingest_data(self) -> Dict:
        """
        Ingest marketing campaign news for all tracked companies
        """
        results = {
            "total_ingested": 0,
            "companies": {},
            "errors": []
        }

        for company in self.tracked_companies:
            try:
                campaigns = await self.fetch_marketing_news(company)
                
                # Store in database
                for campaign in campaigns:
                    try:
                        # Use URL as unique identifier to avoid duplicates
                        await self.db.campaigns.update_one(
                            {"id": campaign["id"]},
                            {"$set": campaign},
                            upsert=True
                        )
                    except Exception as e:
                        logger.error(f"Error storing campaign: {str(e)}")
                        continue
                
                results["companies"][company] = len(campaigns)
                results["total_ingested"] += len(campaigns)
                
            except Exception as e:
                logger.error(f"Error processing company {company}: {str(e)}")
                results["errors"].append({
                    "company": company,
                    "error": str(e)
                })

        return results

    async def schedule_ingestion(self, interval_minutes: int = 15):
        """
        Schedule periodic data ingestion
        Default to 15 minutes to stay within News API limits
        """
        while True:
            try:
                await self.ingest_data()
                await asyncio.sleep(interval_minutes * 60)
            except Exception as e:
                logger.error(f"Scheduled ingestion error: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes on error