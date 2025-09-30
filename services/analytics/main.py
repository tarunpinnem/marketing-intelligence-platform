"""
Analytics Microservice
Processes campaign data and provides advanced analytics with Elasticsearch integration
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid

import asyncpg
import redis.asyncio as redis
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import numpy as np
from collections import defaultdict, Counter
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Analytics Service", version="1.0.0")

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
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")

# Global connections
kafka_consumer = None
kafka_producer = None
db_pool = None
redis_client = None
es_client = None

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    global kafka_consumer, kafka_producer, db_pool, redis_client, es_client
    
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
        
        # Initialize Elasticsearch client
        es_client = AsyncElasticsearch(
            [ELASTICSEARCH_URL],
            verify_certs=False,
            ssl_show_warn=False,
            request_timeout=30
        )
        # Create index if it doesn't exist
        await setup_elasticsearch_index()
        logger.info("✅ Elasticsearch connection established")
        
        # Initialize Kafka producer
        kafka_producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            compression_type="gzip"
        )
        await kafka_producer.start()
        logger.info("✅ Kafka producer started")
        
        # Initialize Kafka consumer
        kafka_consumer = AIOKafkaConsumer(
            'campaigns',
            'analytics',
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id='analytics_service',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest'
        )
        await kafka_consumer.start()
        logger.info("✅ Kafka consumer started")
        
        # Start background tasks
        asyncio.create_task(kafka_message_processor())
        asyncio.create_task(periodic_analytics_calculation())
        logger.info("✅ Background analytics tasks started")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global kafka_consumer, kafka_producer, db_pool, redis_client, es_client
    
    if kafka_consumer:
        await kafka_consumer.stop()
        logger.info("Kafka consumer stopped")
    
    if kafka_producer:
        await kafka_producer.stop()
        logger.info("Kafka producer stopped")
    
    if db_pool:
        await db_pool.close()
        logger.info("PostgreSQL pool closed")
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")
    
    if es_client:
        await es_client.close()
        logger.info("Elasticsearch connection closed")

async def setup_elasticsearch_index():
    """Setup Elasticsearch index for campaign search"""
    index_name = "campaigns"
    
    mapping = {
        "mappings": {
            "properties": {
                "id": {"type": "long"},
                "external_id": {"type": "keyword"},
                "name": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "company": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "platform": {"type": "keyword"},
                "content": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "sentiment_score": {"type": "float"},
                "budget": {"type": "float"},
                "impressions": {"type": "long"},
                "clicks": {"type": "long"},
                "conversions": {"type": "long"},
                "ctr": {"type": "float"},
                "status": {"type": "keyword"},
                "start_date": {"type": "date"},
                "created_at": {"type": "date"},
                "keywords": {"type": "keyword"},
                "category": {"type": "keyword"}
            }
        }
    }
    
    # Check if index exists
    if not await es_client.indices.exists(index=index_name):
        await es_client.indices.create(index=index_name, body=mapping)
        logger.info(f"Created Elasticsearch index: {index_name}")

async def index_campaign_to_elasticsearch(campaign_data: Dict):
    """Index campaign data to Elasticsearch for search"""
    try:
        # Extract keywords from name and content
        text_content = f"{campaign_data.get('name', '')} {campaign_data.get('content', '')}"
        keywords = extract_keywords(text_content)
        
        # Categorize campaign
        category = categorize_campaign(campaign_data)
        
        # Prepare document for indexing with proper date formatting
        doc = {
            **campaign_data,
            "keywords": keywords,
            "category": category,
            "indexed_at": datetime.utcnow().isoformat()
        }
        
        # Fix date formats for Elasticsearch
        for date_field in ['start_date', 'created_at', 'updated_at']:
            if date_field in doc and doc[date_field]:
                # Convert string dates to ISO format
                if isinstance(doc[date_field], str):
                    try:
                        # Parse the date and convert to ISO format
                        dt = datetime.fromisoformat(doc[date_field].replace('Z', '+00:00'))
                        doc[date_field] = dt.isoformat()
                    except (ValueError, AttributeError):
                        # If parsing fails, remove the field to avoid Elasticsearch errors
                        logger.warning(f"Invalid date format for {date_field}: {doc[date_field]}")
                        del doc[date_field]
                elif isinstance(doc[date_field], datetime):
                    doc[date_field] = doc[date_field].isoformat()
        
        # Index to Elasticsearch
        await es_client.index(
            index="campaigns",
            id=campaign_data.get('id') or campaign_data.get('external_id'),
            body=doc
        )
        
        logger.info(f"📊 Indexed campaign to Elasticsearch: {campaign_data.get('name', 'Unknown')}")
        
    except Exception as e:
        logger.error(f"Error indexing to Elasticsearch: {e}")

def extract_keywords(text: str) -> List[str]:
    """Extract keywords from campaign text"""
    if not text:
        return []
    
    # Remove special characters and convert to lowercase
    clean_text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
    
    # Common marketing/business keywords
    marketing_keywords = {
        'marketing', 'campaign', 'advertising', 'promotion', 'brand',
        'digital', 'social', 'content', 'strategy', 'launch', 'product',
        'sales', 'growth', 'engagement', 'awareness', 'conversion',
        'analytics', 'performance', 'roi', 'kpi', 'target', 'audience'
    }
    
    # Extract words from text
    words = set(clean_text.split())
    
    # Filter relevant keywords
    keywords = []
    for word in words:
        if len(word) > 3 and word in marketing_keywords:
            keywords.append(word)
    
    # Add some context-based keywords
    if 'tech' in clean_text or 'software' in clean_text:
        keywords.append('technology')
    if 'finance' in clean_text or 'bank' in clean_text:
        keywords.append('financial')
    if 'health' in clean_text or 'medical' in clean_text:
        keywords.append('healthcare')
    
    return list(set(keywords))[:10]  # Limit to 10 keywords

def categorize_campaign(campaign_data: Dict) -> str:
    """Categorize campaign based on content and metadata"""
    platform = campaign_data.get('platform', '').lower()
    company = campaign_data.get('company', '').lower()
    content = (campaign_data.get('content', '') + ' ' + campaign_data.get('name', '')).lower()
    
    # Platform-based categorization
    if 'facebook' in platform or 'instagram' in platform:
        return 'Social Media'
    elif 'google' in platform or 'search' in platform:
        return 'Search Marketing'
    elif 'linkedin' in platform:
        return 'Professional Marketing'
    elif 'youtube' in platform:
        return 'Video Marketing'
    elif 'news' in platform or 'media' in platform:
        return 'PR & Media'
    
    # Content-based categorization
    if any(word in content for word in ['product', 'launch', 'new']):
        return 'Product Launch'
    elif any(word in content for word in ['brand', 'awareness', 'identity']):
        return 'Brand Awareness'
    elif any(word in content for word in ['sale', 'discount', 'offer', 'deal']):
        return 'Promotional'
    elif any(word in content for word in ['b2b', 'enterprise', 'business']):
        return 'B2B Marketing'
    else:
        return 'General Marketing'

async def kafka_message_processor():
    """Process incoming Kafka messages"""
    logger.info("🔄 Starting Kafka message processor...")
    
    async for message in kafka_consumer:
        try:
            topic = message.topic
            data = message.value
            
            if topic == "campaigns":
                # Process new campaign data
                campaign_data = data.get('data', {})
                if campaign_data:
                    # Index to Elasticsearch
                    await index_campaign_to_elasticsearch(campaign_data)
                    
                    # Trigger analytics recalculation
                    await recalculate_analytics()
                    
            elif topic == "analytics":
                # Process analytics requests
                action = data.get('data', {}).get('action')
                if action == "recalculate":
                    await recalculate_analytics()
            
            logger.info(f"📡 Processed Kafka message from topic: {topic}")
            
        except Exception as e:
            logger.error(f"Error processing Kafka message: {e}")

async def recalculate_analytics():
    """Recalculate and cache analytics data"""
    try:
        async with db_pool.acquire() as connection:
            # Get campaign trends (last 30 days)
            campaign_trends = await get_campaign_trends(connection)
            
            # Get channel distribution
            channel_distribution = await get_channel_distribution(connection)
            
            # Get keyword analysis
            keyword_analysis = await get_keyword_analysis()
            
            # Get competitor analysis
            competitor_analysis = await get_competitor_analysis(connection)
            
            # Get sentiment analysis
            sentiment_analysis = await get_sentiment_analysis(connection)
            
            # Get performance metrics
            performance_metrics = await get_performance_metrics(connection)
            
            # Compile analytics data
            analytics_data = {
                "campaign_trends": campaign_trends,
                "channel_distribution": channel_distribution,
                "keyword_analysis": keyword_analysis,
                "competitor_analysis": competitor_analysis,
                "sentiment_analysis": sentiment_analysis,
                "performance_metrics": performance_metrics,
                "last_updated": datetime.utcnow().isoformat(),
                "data_points": await get_total_campaigns(connection)
            }
            
            # Cache in Redis
            await redis_client.setex(
                "analytics:dashboard",
                300,  # 5 minutes
                json.dumps(analytics_data, default=str)
            )
            
            # Store in PostgreSQL analytics_cache
            await connection.execute(
                """
                INSERT INTO analytics_cache (cache_key, data, expires_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (cache_key) DO UPDATE SET
                    data = EXCLUDED.data,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                "dashboard_analytics",
                json.dumps(analytics_data, default=str),
                datetime.utcnow() + timedelta(minutes=10)
            )
            
            # Publish update to WebSocket service
            await kafka_producer.send_and_wait(
                "websocket_updates",
                value={
                    "type": "analytics_update",
                    "data": analytics_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info("✅ Analytics recalculated and cached")
            
    except Exception as e:
        logger.error(f"Error recalculating analytics: {e}")

async def get_campaign_trends(connection) -> List[Dict]:
    """Get campaign trends over time"""
    query = """
    SELECT 
        DATE(created_at) as date,
        COUNT(*) as campaigns,
        COALESCE(SUM(budget), 0) as total_budget,
        COALESCE(SUM(impressions), 0) as total_impressions,
        COALESCE(SUM(clicks), 0) as total_clicks,
        COALESCE(AVG(ctr), 0) as avg_ctr
    FROM campaigns 
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY DATE(created_at)
    ORDER BY date
    """
    
    results = await connection.fetch(query)
    return [dict(row) for row in results]

async def get_channel_distribution(connection) -> List[Dict]:
    """Get distribution of campaigns by channel/platform"""
    query = """
    SELECT 
        platform,
        COUNT(*) as count,
        COALESCE(SUM(budget), 0) as total_budget,
        COALESCE(AVG(sentiment_score), 0.5) as avg_sentiment
    FROM campaigns 
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY platform
    ORDER BY count DESC
    """
    
    results = await connection.fetch(query)
    return [dict(row) for row in results]

async def get_keyword_analysis() -> List[Dict]:
    """Get keyword analysis from Elasticsearch"""
    try:
        # Aggregate keywords from recent campaigns
        query = {
            "size": 0,
            "query": {
                "range": {
                    "created_at": {
                        "gte": "now-30d"
                    }
                }
            },
            "aggs": {
                "keywords": {
                    "terms": {
                        "field": "keywords",
                        "size": 20
                    }
                }
            }
        }
        
        response = await es_client.search(index="campaigns", body=query)
        keywords = response["aggregations"]["keywords"]["buckets"]
        
        return [
            {
                "keyword": bucket["key"],
                "count": bucket["doc_count"],
                "percentage": round((bucket["doc_count"] / max(1, sum(b["doc_count"] for b in keywords))) * 100, 1)
            }
            for bucket in keywords
        ]
        
    except Exception as e:
        logger.error(f"Error in keyword analysis: {e}")
        return []

async def get_competitor_analysis(connection) -> List[Dict]:
    """Get competitor analysis"""
    query = """
    SELECT 
        company,
        COUNT(*) as campaign_count,
        COALESCE(AVG(budget), 0) as avg_budget,
        COALESCE(AVG(sentiment_score), 0.5) as avg_sentiment,
        COALESCE(AVG(ctr), 0) as avg_ctr,
        COALESCE(SUM(impressions), 0) as total_impressions
    FROM campaigns 
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY company
    ORDER BY campaign_count DESC
    LIMIT 10
    """
    
    results = await connection.fetch(query)
    return [dict(row) for row in results]

async def get_sentiment_analysis(connection) -> Dict:
    """Get sentiment analysis overview"""
    query = """
    SELECT 
        CASE 
            WHEN sentiment_score >= 0.7 THEN 'positive'
            WHEN sentiment_score >= 0.4 THEN 'neutral'
            ELSE 'negative'
        END as sentiment,
        COUNT(*) as count,
        COALESCE(AVG(budget), 0) as avg_budget
    FROM campaigns 
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY 
        CASE 
            WHEN sentiment_score >= 0.7 THEN 'positive'
            WHEN sentiment_score >= 0.4 THEN 'neutral'
            ELSE 'negative'
        END
    """
    
    results = await connection.fetch(query)
    sentiment_data = {row['sentiment']: dict(row) for row in results}
    
    return {
        "distribution": sentiment_data,
        "overall_score": await connection.fetchval(
            "SELECT AVG(sentiment_score) FROM campaigns WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'"
        ) or 0.5
    }

async def get_performance_metrics(connection) -> Dict:
    """Get overall performance metrics"""
    metrics = await connection.fetchrow("""
    SELECT 
        COUNT(*) as total_campaigns,
        COUNT(DISTINCT company) as unique_companies,
        COUNT(DISTINCT platform) as unique_platforms,
        COALESCE(SUM(budget), 0) as total_budget,
        COALESCE(SUM(impressions), 0) as total_impressions,
        COALESCE(SUM(clicks), 0) as total_clicks,
        COALESCE(SUM(conversions), 0) as total_conversions,
        COALESCE(AVG(ctr), 0) as avg_ctr,
        COALESCE(AVG(sentiment_score), 0.5) as avg_sentiment
    FROM campaigns 
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    """)
    
    return dict(metrics) if metrics else {}

async def get_total_campaigns(connection) -> int:
    """Get total number of campaigns"""
    return await connection.fetchval("SELECT COUNT(*) FROM campaigns") or 0

async def periodic_analytics_calculation():
    """Periodic task to recalculate analytics"""
    logger.info("⏰ Starting periodic analytics calculation...")
    
    while True:
        try:
            await recalculate_analytics()
            logger.info("🔄 Periodic analytics calculation completed")
            
            # Wait 1 minute before next calculation
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in periodic analytics: {e}")
            # Wait 30 seconds before retrying on error
            await asyncio.sleep(30)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "analytics",
        "timestamp": datetime.utcnow().isoformat(),
        "connections": {
            "postgres": db_pool is not None,
            "redis": redis_client is not None,
            "elasticsearch": es_client is not None,
            "kafka": kafka_consumer is not None and kafka_producer is not None
        }
    }

@app.get("/analytics")
async def get_analytics():
    """Get cached analytics data"""
    try:
        # Try Redis first
        cached_data = await redis_client.get("analytics:dashboard")
        if cached_data:
            return json.loads(cached_data)
        
        # Fallback to database
        async with db_pool.acquire() as connection:
            result = await connection.fetchrow(
                "SELECT data FROM analytics_cache WHERE cache_key = $1 AND expires_at > $2",
                "dashboard_analytics",
                datetime.utcnow()
            )
            
            if result:
                return json.loads(result['data'])
        
        # If no cache, trigger recalculation
        await recalculate_analytics()
        
        # Return basic response
        return {
            "message": "Analytics calculation in progress",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_campaigns(query: str = "", filters: Dict = None):
    """Search campaigns using Elasticsearch"""
    try:
        # Build Elasticsearch query
        es_query = {
            "query": {
                "bool": {
                    "must": [],
                    "filter": []
                }
            },
            "size": 100,
            "sort": [
                {"created_at": {"order": "desc"}}
            ]
        }
        
        # Add text search if query provided
        if query:
            es_query["query"]["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": ["name^3", "content^2", "company", "keywords"],
                    "type": "best_fields"
                }
            })
        
        # Add filters
        if filters:
            if filters.get("company"):
                es_query["query"]["bool"]["filter"].append({
                    "term": {"company.keyword": filters["company"]}
                })
            
            if filters.get("platform"):
                es_query["query"]["bool"]["filter"].append({
                    "term": {"platform": filters["platform"]}
                })
            
            if filters.get("date_range"):
                es_query["query"]["bool"]["filter"].append({
                    "range": {
                        "created_at": {
                            "gte": filters["date_range"]["start"],
                            "lte": filters["date_range"]["end"]
                        }
                    }
                })
        
        # Execute search
        response = await es_client.search(index="campaigns", body=es_query)
        
        # Format results
        campaigns = []
        for hit in response["hits"]["hits"]:
            campaign = hit["_source"]
            campaign["relevance_score"] = hit["_score"]
            campaigns.append(campaign)
        
        return {
            "campaigns": campaigns,
            "total": response["hits"]["total"]["value"],
            "query": query,
            "filters": filters or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error searching campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analytics/recalculate")
async def trigger_analytics_recalculation(background_tasks: BackgroundTasks):
    """Manually trigger analytics recalculation"""
    background_tasks.add_task(recalculate_analytics)
    return {
        "status": "Analytics recalculation triggered",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )