"""
Data Ingestion Microservice
Handles real-time data ingestion from external sources and Kafka publishing
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

import asyncpg
import httpx
import redis.asyncio as redis
from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Ingestion Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from environment
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/competiscan")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "deedb115cd3648b8b8bbe8c0933afce5")

# Global connections
kafka_producer = None
db_pool = None
redis_client = None

class CampaignModel(BaseModel):
    external_id: str
    name: str
    company: str
    platform: str
    content: Optional[str] = None
    sentiment_score: float = 0.5
    budget: Optional[float] = None
    impressions: Optional[int] = None
    clicks: Optional[int] = None
    conversions: Optional[int] = None
    ctr: Optional[float] = None
    status: str = "active"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metadata: Optional[Dict] = None

class KafkaMessage(BaseModel):
    topic: str
    event_type: str
    data: Dict
    timestamp: datetime = None

    def __init__(self, **data):
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    global kafka_producer, db_pool, redis_client
    
    try:
        # Initialize PostgreSQL connection pool
        db_pool = await asyncpg.create_pool(
            POSTGRES_URL,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("✅ PostgreSQL connection pool created")
        
        # Initialize Redis connection
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("✅ Redis connection established")
        
        # Initialize Kafka producer
        kafka_producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            compression_type="gzip"
        )
        await kafka_producer.start()
        logger.info("✅ Kafka producer started")
        
        # Start background ingestion task
        asyncio.create_task(continuous_data_ingestion())
        logger.info("✅ Background data ingestion started")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global kafka_producer, db_pool, redis_client
    
    if kafka_producer:
        await kafka_producer.stop()
        logger.info("Kafka producer stopped")
    
    if db_pool:
        await db_pool.close()
        logger.info("PostgreSQL pool closed")
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

async def fetch_news_campaigns() -> List[Dict]:
    """Fetch campaign data from News API"""
    try:
        marketing_queries = [
            "product launch marketing campaign",
            "brand awareness advertising",
            "digital marketing strategy",
            "social media campaign",
            "promotional marketing"
        ]
        
        all_campaigns = []
        
        async with httpx.AsyncClient(timeout=30) as client:
            for query in marketing_queries[:2]:  # Limit to 2 queries to avoid rate limits
                url = "https://newsapi.org/v2/everything"
                params = {
                    'q': query,
                    'apiKey': NEWS_API_KEY,
                    'pageSize': 20,
                    'sortBy': 'publishedAt',
                    'language': 'en'
                }
                
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get('articles', [])
                    
                    for article in articles:
                        campaign = transform_article_to_campaign(article, query)
                        if campaign:
                            all_campaigns.append(campaign)
                
                # Rate limiting - wait between requests
                await asyncio.sleep(1)
        
        logger.info(f"📰 Fetched {len(all_campaigns)} campaigns from News API")
        return all_campaigns
        
    except Exception as e:
        logger.error(f"❌ Error fetching news campaigns: {e}")
        return []

def transform_article_to_campaign(article: Dict, query: str) -> Optional[Dict]:
    """Transform news article to campaign format"""
    try:
        # Extract company from source or title
        source_name = article.get('source', {}).get('name', 'Unknown')
        title = article.get('title', '')
        
        # Map news sources to companies
        company_mapping = {
            'Forbes': 'Forbes Media',
            'TechCrunch': 'TechCrunch',
            'Reuters': 'Reuters',
            'Bloomberg': 'Bloomberg',
            'CNN': 'CNN Business',
            'CNBC': 'CNBC'
        }
        
        company = company_mapping.get(source_name, source_name)
        
        # Determine platform based on content
        platform_keywords = {
            'Facebook': ['facebook', 'meta', 'social media'],
            'Google Ads': ['google', 'search', 'advertising'],
            'LinkedIn': ['linkedin', 'professional', 'b2b'],
            'Twitter': ['twitter', 'tweet', 'social'],
            'Instagram': ['instagram', 'visual', 'photo'],
            'YouTube': ['youtube', 'video', 'streaming'],
            'News Media': ['news', 'media', 'press', 'announcement']
        }
        
        platform = 'News Media'  # Default
        content_lower = (title + ' ' + article.get('description', '')).lower()
        
        for plat, keywords in platform_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                platform = plat
                break
        
        # Calculate sentiment (simple heuristic)
        positive_words = ['growth', 'success', 'innovative', 'leading', 'best', 'improved', 'excellent']
        negative_words = ['decline', 'loss', 'failed', 'worst', 'poor', 'disappointing']
        
        pos_count = sum(1 for word in positive_words if word in content_lower)
        neg_count = sum(1 for word in negative_words if word in content_lower)
        
        sentiment_score = 0.5 + (pos_count - neg_count) * 0.1
        sentiment_score = max(0.1, min(0.9, sentiment_score))  # Clamp between 0.1 and 0.9
        
        # Handle datetime properly
        published_at = article.get('publishedAt', '')
        if published_at:
            try:
                start_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                # Convert to UTC and make naive for PostgreSQL
                start_date = start_date.utctimetuple()
                start_date = datetime(*start_date[:6])
            except:
                start_date = datetime.utcnow()
        else:
            start_date = datetime.utcnow()

        return {
            'external_id': f"news_{hash(article.get('url', ''))}_{int(datetime.utcnow().timestamp())}",
            'name': title[:500],
            'company': company,
            'platform': platform,
            'content': article.get('description', '')[:1000],
            'sentiment_score': sentiment_score,
            'budget': float(5000 + (hash(title) % 50000)),  # Simulated budget
            'impressions': 1000 + (hash(company) % 100000),  # Simulated impressions
            'clicks': 50 + (hash(platform) % 5000),  # Simulated clicks
            'conversions': 5 + (hash(title) % 500),  # Simulated conversions
            'status': 'active',
            'start_date': start_date,
            'metadata': {
                'source_url': article.get('url'),
                'author': article.get('author'),
                'source': source_name,
                'query_used': query
            }
        }
        
    except Exception as e:
        logger.error(f"Error transforming article to campaign: {e}")
        return None

async def store_campaign_in_db(campaign: Dict) -> Optional[int]:
    """Store campaign in PostgreSQL database"""
    try:
        async with db_pool.acquire() as connection:
            # Calculate CTR
            if campaign.get('impressions') and campaign['impressions'] > 0:
                campaign['ctr'] = round((campaign.get('clicks', 0) / campaign['impressions']) * 100, 2)
            
            query = """
            INSERT INTO campaigns (
                external_id, name, company, platform, content, sentiment_score,
                budget, impressions, clicks, conversions, ctr, status, start_date, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (external_id) DO UPDATE SET
                name = EXCLUDED.name,
                sentiment_score = EXCLUDED.sentiment_score,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """
            
            campaign_id = await connection.fetchval(
                query,
                campaign['external_id'],
                campaign['name'],
                campaign['company'],
                campaign['platform'],
                campaign.get('content'),
                campaign['sentiment_score'],
                campaign.get('budget'),
                campaign.get('impressions'),
                campaign.get('clicks'),
                campaign.get('conversions'),
                campaign.get('ctr'),
                campaign['status'],
                campaign.get('start_date'),
                json.dumps(campaign.get('metadata', {}))
            )
            
            # Update company stats
            await update_company_stats(connection, campaign['company'])
            
            return campaign_id
            
    except Exception as e:
        logger.error(f"Error storing campaign in database: {e}")
        return None

async def update_company_stats(connection, company_name: str):
    """Update company statistics"""
    try:
        query = """
        INSERT INTO companies (name, industry, total_campaigns, total_spend, avg_sentiment)
        SELECT 
            $1,
            CASE 
                WHEN $1 LIKE '%Tech%' OR $1 IN ('Microsoft', 'Apple Inc.', 'Google') THEN 'Technology'
                WHEN $1 LIKE '%Bank%' OR $1 LIKE '%Financial%' OR $1 IN ('Wells Fargo', 'Chase') THEN 'Financial Services'
                WHEN $1 IN ('Forbes', 'Reuters', 'CNN', 'Bloomberg') THEN 'Media'
                ELSE 'Other'
            END,
            COALESCE(stats.campaign_count, 0),
            COALESCE(stats.total_spend, 0),
            COALESCE(stats.avg_sentiment, 0.5)
        FROM (
            SELECT 
                COUNT(*) as campaign_count,
                SUM(budget) as total_spend,
                AVG(sentiment_score) as avg_sentiment
            FROM campaigns 
            WHERE company = $1
        ) stats
        ON CONFLICT (name) DO UPDATE SET
            total_campaigns = EXCLUDED.total_campaigns,
            total_spend = EXCLUDED.total_spend,
            avg_sentiment = EXCLUDED.avg_sentiment,
            updated_at = CURRENT_TIMESTAMP
        """
        
        await connection.execute(query, company_name)
        
    except Exception as e:
        logger.error(f"Error updating company stats: {e}")

async def publish_to_kafka(topic: str, message: Dict):
    """Publish message to Kafka topic"""
    try:
        kafka_message = KafkaMessage(
            topic=topic,
            event_type="campaign_ingested" if topic == "campaigns" else "analytics_updated",
            data=message
        )
        
        await kafka_producer.send_and_wait(
            topic,
            value=kafka_message.dict()
        )
        
        logger.info(f"📡 Published message to Kafka topic: {topic}")
        
        # Store event in database for tracking
        async with db_pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO kafka_events (topic, event_type, payload)
                VALUES ($1, $2, $3)
                """,
                topic,
                kafka_message.event_type,
                json.dumps(kafka_message.data, default=str)
            )
        
    except Exception as e:
        logger.error(f"Error publishing to Kafka: {e}")

async def cache_in_redis(key: str, data: Dict, expire_seconds: int = 300):
    """Cache data in Redis with expiration"""
    try:
        await redis_client.setex(
            key,
            expire_seconds,
            json.dumps(data, default=str)
        )
        logger.info(f"💾 Cached data in Redis: {key}")
        
    except Exception as e:
        logger.error(f"Error caching in Redis: {e}")

async def continuous_data_ingestion():
    """Continuous background task for data ingestion"""
    logger.info("🔄 Starting continuous data ingestion...")
    
    while True:
        try:
            # Fetch new campaign data
            campaigns = await fetch_news_campaigns()
            
            ingested_count = 0
            
            for campaign_data in campaigns:
                # Store in PostgreSQL
                campaign_id = await store_campaign_in_db(campaign_data)
                
                if campaign_id:
                    # Add database ID to the campaign data
                    campaign_data['id'] = campaign_id
                    
                    # Publish to Kafka
                    await publish_to_kafka("campaigns", campaign_data)
                    
                    # Cache recent campaigns in Redis
                    cache_key = f"campaign:{campaign_id}"
                    await cache_in_redis(cache_key, campaign_data, 3600)  # 1 hour
                    
                    ingested_count += 1
            
            if ingested_count > 0:
                logger.info(f"✅ Successfully ingested {ingested_count} campaigns")
                
                # Trigger analytics update
                await publish_to_kafka("analytics", {
                    "action": "recalculate",
                    "reason": f"new_campaigns_ingested_{ingested_count}",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Wait 5 minutes before next ingestion
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"❌ Error in continuous ingestion: {e}")
            # Wait 1 minute before retrying on error
            await asyncio.sleep(60)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "data-ingestion",
        "timestamp": datetime.utcnow().isoformat(),
        "connections": {
            "postgres": db_pool is not None,
            "redis": redis_client is not None,
            "kafka": kafka_producer is not None
        }
    }

@app.post("/ingest/manual")
async def manual_ingestion(background_tasks: BackgroundTasks):
    """Manual trigger for data ingestion"""
    try:
        campaigns = await fetch_news_campaigns()
        
        if not campaigns:
            raise HTTPException(status_code=404, detail="No campaigns found")
        
        ingested_count = 0
        
        for campaign_data in campaigns:
            campaign_id = await store_campaign_in_db(campaign_data)
            if campaign_id:
                campaign_data['id'] = campaign_id
                await publish_to_kafka("campaigns", campaign_data)
                ingested_count += 1
        
        return {
            "status": "success",
            "campaigns_ingested": ingested_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in manual ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_ingestion_stats():
    """Get ingestion statistics"""
    try:
        async with db_pool.acquire() as connection:
            # Get campaign counts by day
            daily_stats = await connection.fetch("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as campaigns_count,
                    COUNT(DISTINCT company) as companies_count
                FROM campaigns 
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            
            # Get Kafka event stats
            kafka_stats = await connection.fetch("""
                SELECT 
                    topic,
                    COUNT(*) as event_count,
                    COUNT(*) FILTER (WHERE processed = true) as processed_count
                FROM kafka_events 
                WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
                GROUP BY topic
            """)
            
            return {
                "daily_ingestion": [dict(row) for row in daily_stats],
                "kafka_events": [dict(row) for row in kafka_stats],
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )