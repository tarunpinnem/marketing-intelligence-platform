"""
Enhanced FastAPI Backend with Kafka Integration
Real-time campaign data processing with event-driven architecture
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

import httpx
import psycopg2
import redis
from elasticsearch import Elasticsearch
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaProducer
from kafka.errors import KafkaError
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic Models
class Campaign(BaseModel):
    id: Optional[str] = None
    company: str
    name: str
    platform: str
    status: str = "draft"
    budget: float
    start_date: str
    end_date: str
    metrics: Optional[Dict[str, float]] = {}
    content: Optional[Dict[str, str]] = {}

class AnalyticsEvent(BaseModel):
    company: str
    metric_type: str
    value: float
    trend: str = "stable"
    confidence: float = 0.8

# FastAPI app with Kafka integration
app = FastAPI(
    title="Competiscan-Lite API with Kafka",
    description="Event-driven competitive marketing intelligence platform",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class KafkaService:
    """Kafka service for event streaming"""
    
    def __init__(self):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.producer = None
        self.connected = False

    async def initialize(self):
        """Initialize Kafka producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retries=3,
                batch_size=16384,
                linger_ms=10
            )
            
            # Test connection
            future = self.producer.send('test-connection', {'status': 'connected'})
            future.get(timeout=5)
            
            self.connected = True
            logger.info("✅ Kafka producer initialized")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Kafka not available: {e}")
            self.connected = False
            return False

    async def send_campaign_event(self, campaign: Dict[str, Any], event_type: str):
        """Send campaign event to Kafka"""
        if not self.connected:
            return False
            
        try:
            event = {
                'event_id': str(uuid4()),
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'campaign': campaign
            }
            
            future = self.producer.send(
                'campaign-events',
                key=campaign.get('id', ''),
                value=event
            )
            
            future.get(timeout=5)
            logger.info(f"📧 Campaign event sent: {event_type} - {campaign.get('company')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send campaign event: {e}")
            return False

    async def send_analytics_event(self, analytics: Dict[str, Any], event_type: str):
        """Send analytics event to Kafka"""
        if not self.connected:
            return False
            
        try:
            event = {
                'event_id': str(uuid4()),
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'data': analytics
            }
            
            future = self.producer.send(
                'analytics-events',
                key=analytics.get('company', ''),
                value=event
            )
            
            future.get(timeout=5)
            logger.info(f"📊 Analytics event sent: {event_type} - {analytics.get('company')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send analytics event: {e}")
            return False

# Global instances
kafka_service = KafkaService()
redis_client = None
es_client = None

# WebSocket connections for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"📱 WebSocket connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"📱 WebSocket disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
            
        message_str = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.active_connections.remove(conn)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global redis_client, es_client
    
    # Initialize Kafka
    await kafka_service.initialize()
    
    # Initialize Redis
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis not available: {e}")
    
    # Initialize Elasticsearch
    try:
        es_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
        es_client = Elasticsearch([es_url])
        es_client.info()
        logger.info("✅ Elasticsearch connected")
    except Exception as e:
        logger.warning(f"⚠️ Elasticsearch not available: {e}")

# API Endpoints

@app.get("/api/health")
async def health_check():
    """Enhanced health check with service status"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "kafka": kafka_service.connected,
            "redis": redis_client is not None,
            "elasticsearch": es_client is not None
        },
        "active_websockets": len(manager.active_connections)
    }

@app.post("/api/campaigns")
async def create_campaign(campaign: Campaign, background_tasks: BackgroundTasks):
    """Create new campaign with Kafka event streaming"""
    try:
        # Generate ID if not provided
        if not campaign.id:
            campaign.id = str(uuid4())
        
        campaign_dict = campaign.dict()
        
        # Add creation metadata
        campaign_dict.update({
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        })
        
        # Send to Kafka in background
        if kafka_service.connected:
            background_tasks.add_task(
                kafka_service.send_campaign_event,
                campaign_dict,
                "created"
            )
        
        # Cache in Redis
        if redis_client:
            try:
                redis_client.setex(
                    f"campaign:{campaign.id}",
                    3600,  # 1 hour
                    json.dumps(campaign_dict)
                )
            except Exception as e:
                logger.warning(f"Redis cache failed: {e}")
        
        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "campaign_created",
            "data": campaign_dict
        })
        
        return {
            "message": "Campaign created successfully",
            "campaign": campaign_dict,
            "streaming": kafka_service.connected
        }
        
    except Exception as e:
        logger.error(f"❌ Campaign creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/campaigns")
async def get_campaigns(limit: int = 20, offset: int = 0):
    """Get campaigns with real-time data"""
    try:
        # Try to get from Redis cache first
        if redis_client:
            try:
                cached_campaigns = redis_client.get("campaigns:list")
                if cached_campaigns:
                    campaigns = json.loads(cached_campaigns)
                    return {
                        "campaigns": campaigns[offset:offset+limit],
                        "total": len(campaigns),
                        "cached": True
                    }
            except Exception as e:
                logger.warning(f"Redis read failed: {e}")
        
        # Generate sample data if no cache
        campaigns = generate_realtime_campaigns(limit)
        
        # Cache the result
        if redis_client:
            try:
                redis_client.setex(
                    "campaigns:list",
                    300,  # 5 minutes
                    json.dumps(campaigns)
                )
            except Exception:
                pass
        
        return {
            "campaigns": campaigns,
            "total": len(campaigns),
            "cached": False,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/campaigns/{campaign_id}")
async def update_campaign(campaign_id: str, campaign: Campaign, background_tasks: BackgroundTasks):
    """Update campaign with event streaming"""
    try:
        campaign_dict = campaign.dict()
        campaign_dict.update({
            "id": campaign_id,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        # Send update event to Kafka
        if kafka_service.connected:
            background_tasks.add_task(
                kafka_service.send_campaign_event,
                campaign_dict,
                "updated"
            )
        
        # Update cache
        if redis_client:
            try:
                redis_client.setex(
                    f"campaign:{campaign_id}",
                    3600,
                    json.dumps(campaign_dict)
                )
            except Exception:
                pass
        
        # Broadcast update
        await manager.broadcast({
            "type": "campaign_updated",
            "data": campaign_dict
        })
        
        return {
            "message": "Campaign updated successfully",
            "campaign": campaign_dict
        }
        
    except Exception as e:
        logger.error(f"❌ Campaign update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analytics/event")
async def track_analytics_event(event: AnalyticsEvent, background_tasks: BackgroundTasks):
    """Track analytics event with streaming"""
    try:
        event_dict = event.dict()
        event_dict.update({
            "timestamp": datetime.utcnow().isoformat(),
            "source": "api"
        })
        
        # Send to Kafka
        if kafka_service.connected:
            background_tasks.add_task(
                kafka_service.send_analytics_event,
                event_dict,
                "tracked"
            )
        
        # Broadcast to clients
        await manager.broadcast({
            "type": "analytics_update",
            "data": event_dict
        })
        
        return {
            "message": "Analytics event tracked",
            "event": event_dict,
            "streaming": kafka_service.connected
        }
        
    except Exception as e:
        logger.error(f"❌ Analytics tracking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/realtime")
async def get_realtime_analytics():
    """Get real-time analytics summary"""
    try:
        # Get from Redis cache
        if redis_client:
            try:
                cached_analytics = redis_client.get("analytics:realtime")
                if cached_analytics:
                    return json.loads(cached_analytics)
            except Exception:
                pass
        
        # Generate real-time analytics
        analytics = generate_realtime_analytics()
        
        # Cache result
        if redis_client:
            try:
                redis_client.setex(
                    "analytics:realtime",
                    60,  # 1 minute
                    json.dumps(analytics)
                )
            except Exception:
                pass
        
        return analytics
        
    except Exception as e:
        logger.error(f"❌ Real-time analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid WebSocket message: {data}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Helper functions

def generate_realtime_campaigns(limit: int = 20) -> List[Dict[str, Any]]:
    """Generate realistic campaign data with live metrics"""
    import random
    
    companies = [
        "Apple Inc.", "Microsoft", "Google", "Amazon", "Meta", "Tesla",
        "Nike", "Coca-Cola", "McDonald's", "Disney", "Netflix", "Spotify"
    ]
    
    platforms = ["Facebook", "Instagram", "Twitter", "LinkedIn", "YouTube", "Google Ads"]
    
    campaigns = []
    
    for i in range(limit):
        campaign_id = str(uuid4())
        company = random.choice(companies)
        
        # Generate realistic metrics with some randomness
        impressions = random.randint(5000, 500000)
        clicks = int(impressions * random.uniform(0.01, 0.08))  # 1-8% CTR
        conversions = int(clicks * random.uniform(0.02, 0.15))  # 2-15% conversion
        
        campaign = {
            "id": campaign_id,
            "company": company,
            "name": f"{company} - {random.choice(['Brand Awareness', 'Product Launch', 'Lead Generation'])}",
            "platform": random.choice(platforms),
            "status": random.choice(["active", "paused", "completed"]),
            "budget": random.randint(5000, 100000),
            "start_date": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            "end_date": (datetime.now() + timedelta(days=random.randint(1, 60))).isoformat(),
            "metrics": {
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "spend": round(random.uniform(100, 50000), 2),
                "ctr": round((clicks / impressions) * 100, 2),
                "cpc": round(random.uniform(0.5, 5.0), 2),
                "sentiment_score": round(random.uniform(0.3, 0.95), 2)
            },
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        campaigns.append(campaign)
    
    return campaigns

def generate_realtime_analytics() -> Dict[str, Any]:
    """Generate real-time analytics summary"""
    import random
    
    return {
        "summary": {
            "total_campaigns": random.randint(50, 200),
            "active_campaigns": random.randint(20, 80),
            "total_companies": random.randint(15, 50),
            "avg_sentiment": round(random.uniform(0.6, 0.8), 2),
            "total_spend": round(random.uniform(100000, 1000000), 2)
        },
        "trends": {
            "campaign_growth": round(random.uniform(-5, 15), 1),
            "engagement_trend": round(random.uniform(-2, 12), 1),
            "spend_trend": round(random.uniform(-8, 20), 1)
        },
        "top_companies": [
            {
                "company": company,
                "campaigns": random.randint(3, 15),
                "sentiment": round(random.uniform(0.4, 0.9), 2)
            }
            for company in ["Apple Inc.", "Microsoft", "Google", "Amazon", "Meta"]
        ],
        "real_time": True,
        "updated_at": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "kafka_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )