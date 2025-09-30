from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DECIMAL, ARRAY, DateTime, func, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from elasticsearch import Elasticsearch
import os
import json
import pandas as pd
import io
from datetime import datetime, timedelta
from typing import List, Optional
import openai
from pydantic import BaseModel
import redis
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/competiscan")
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Elasticsearch setup
es = Elasticsearch([ELASTICSEARCH_URL])

# Redis setup
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# OpenAI setup
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

app = FastAPI(title="Competiscan API", version="2.0.0", description="Event-driven competitive marketing insights")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Models
class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    industry = Column(String(100))
    website = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer)
    title = Column(String(500))
    subject_line = Column(String(500))
    campaign_type = Column(String(50))
    channel = Column(String(50))
    launch_date = Column(Date)
    content = Column(Text)
    keywords = Column(ARRAY(String))
    sentiment_score = Column(DECIMAL(3, 2))
    classification = Column(String(100))
    source = Column(String(50))
    processed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic Models
class CampaignCreate(BaseModel):
    company_name: str
    title: str
    subject_line: Optional[str] = None
    campaign_type: Optional[str] = None
    channel: Optional[str] = None
    launch_date: Optional[str] = None
    content: str
    keywords: Optional[List[str]] = []

class CampaignResponse(BaseModel):
    id: int
    company_name: str
    title: str
    subject_line: Optional[str]
    campaign_type: Optional[str]
    channel: Optional[str]
    launch_date: Optional[str]
    content: str
    keywords: Optional[List[str]]
    sentiment_score: Optional[float]
    classification: Optional[str]
    source: Optional[str] = "manual"

class EventTrigger(BaseModel):
    event_type: str
    company: str
    industry: str
    channel: str
    title: str
    subject: str
    content: str
    keywords: List[str]

class SearchRequest(BaseModel):
    query: str
    company: Optional[str] = None
    channel: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

class RealTimeStats(BaseModel):
    total_campaigns: int
    campaigns_today: int
    active_companies: int
    trending_keywords: List[str]
    recent_campaigns: List[dict]

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Connection closed, remove it
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Event Publishing Functions
async def publish_campaign_event(campaign_data: dict):
    """Publish campaign event to Redis stream"""
    
    try:
        event_data = {
            'event_type': 'new_campaign',
            'company': campaign_data['company_name'],
            'industry': campaign_data.get('industry', 'Unknown'),
            'channel': campaign_data.get('channel', 'Manual'),
            'title': campaign_data['title'],
            'subject': campaign_data.get('subject_line', ''),
            'content': campaign_data['content'],
            'keywords': json.dumps(campaign_data.get('keywords', [])),
            'date': campaign_data.get('launch_date', datetime.now().isoformat()),
            'source': 'api_manual',
            'published_at': datetime.now().isoformat()
        }
        
        message_id = redis_client.xadd('campaign_events', event_data)
        logger.info(f"Published campaign event {message_id}")
        
        # Broadcast to WebSocket clients
        await manager.broadcast(json.dumps({
            'type': 'new_campaign',
            'data': campaign_data
        }))
        
        return message_id
    
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        return None

# AI Analysis Functions (Enhanced)
async def analyze_sentiment(content: str) -> float:
    """Analyze sentiment using OpenAI API"""
    if not OPENAI_API_KEY:
        return 0.0
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Analyze the sentiment of this marketing content and return a score between -1 (very negative) and 1 (very positive). Return only the numeric score: {content[:500]}"
            }],
            max_tokens=10
        )
        score = float(response.choices[0].message.content.strip())
        return max(-1.0, min(1.0, score))
    except:
        return 0.0

async def classify_campaign(content: str) -> str:
    """Classify campaign type using OpenAI API"""
    if not OPENAI_API_KEY:
        return "unknown"
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Classify this marketing campaign into one of these categories: promotional, educational, retention, acquisition, brand_awareness. Content: {content[:500]}"
            }],
            max_tokens=10
        )
        return response.choices[0].message.content.strip().lower()
    except:
        return "unknown"

# API Routes
@app.get("/")
async def root():
    return {"message": "Competiscan API v2.0.0 - Event-Driven Architecture"}

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint"""
    try:
        # Check database
        db = next(get_db())
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        
        # Check Elasticsearch (optional)
        try:
            es.ping()
            es_status = "connected"
        except:
            es_status = "not available"
        
        # Check Redis
        try:
            redis_client.ping()
            redis_status = "connected"
        except:
            redis_status = "not available"
        
        return {
            "status": "healthy", 
            "database": "connected", 
            "elasticsearch": es_status,
            "redis": redis_status,
            "version": "2.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/realtime/stats", response_model=RealTimeStats)
async def get_realtime_stats(db: Session = Depends(get_db)):
    """Get real-time dashboard statistics"""
    try:
        # Get basic counts
        total_campaigns = db.query(Campaign).count()
        today = datetime.now().date()
        campaigns_today = db.query(Campaign).filter(Campaign.launch_date == today).count()
        active_companies = db.query(Company).count()
        
        # Get trending keywords from recent campaigns
        recent_campaigns = db.query(Campaign).filter(
            Campaign.launch_date >= (today - timedelta(days=7))
        ).limit(50).all()
        
        all_keywords = []
        for campaign in recent_campaigns:
            if campaign.keywords:
                all_keywords.extend(campaign.keywords)
        
        # Count keyword frequency
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        trending_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        trending_keywords = [kw[0] for kw in trending_keywords]
        
        # Get recent campaigns with company names
        recent_campaigns_data = []
        for campaign in db.query(Campaign).order_by(desc(Campaign.created_at)).limit(5).all():
            company = db.query(Company).filter(Company.id == campaign.company_id).first()
            recent_campaigns_data.append({
                "id": campaign.id,
                "title": campaign.title,
                "company_name": company.name if company else "Unknown",
                "channel": campaign.channel,
                "sentiment_score": float(campaign.sentiment_score) if campaign.sentiment_score else None,
                "created_at": campaign.created_at.isoformat() if campaign.created_at else None
            })
        
        return RealTimeStats(
            total_campaigns=total_campaigns,
            campaigns_today=campaigns_today,
            active_companies=active_companies,
            trending_keywords=trending_keywords,
            recent_campaigns=recent_campaigns_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/events/trigger")
async def trigger_campaign_event(event: EventTrigger):
    """Manually trigger a campaign event for testing"""
    try:
        event_data = {
            'event_type': event.event_type,
            'company': event.company,
            'industry': event.industry,
            'channel': event.channel,
            'title': event.title,
            'subject': event.subject,
            'content': event.content,
            'keywords': json.dumps(event.keywords),
            'date': datetime.now().isoformat(),
            'source': 'api_trigger',
            'published_at': datetime.now().isoformat()
        }
        
        message_id = redis_client.xadd('campaign_events', event_data)
        
        return {
            "message": "Event triggered successfully",
            "message_id": message_id,
            "event_data": event_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream/info")
async def get_stream_info():
    """Get Redis stream information"""
    try:
        stream_info = redis_client.xinfo_stream('campaign_events')
        groups_info = redis_client.xinfo_groups('campaign_events')
        
        return {
            "stream_length": stream_info.get('length', 0),
            "consumer_groups": len(groups_info),
            "groups": [
                {
                    "name": group['name'],
                    "consumers": group['consumers'],
                    "pending": group['pending']
                }
                for group in groups_info
            ]
        }
        
    except Exception as e:
        return {"error": str(e), "stream_length": 0, "consumer_groups": 0}

@app.post("/campaigns", response_model=CampaignResponse)
async def create_campaign(campaign: CampaignCreate, db: Session = Depends(get_db)):
    """Create a new campaign and trigger event processing"""
    try:
        # Publish event first (for real-time processing)
        await publish_campaign_event(campaign.dict())
        
        # Then handle manual creation for immediate response
        company = db.query(Company).filter(Company.name == campaign.company_name).first()
        if not company:
            company = Company(name=campaign.company_name)
            db.add(company)
            db.commit()
            db.refresh(company)
        
        # AI Analysis for immediate response
        sentiment_score = await analyze_sentiment(campaign.content)
        classification = await classify_campaign(campaign.content)
        
        # Create campaign
        db_campaign = Campaign(
            company_id=company.id,
            title=campaign.title,
            subject_line=campaign.subject_line,
            campaign_type=campaign.campaign_type,
            channel=campaign.channel,
            launch_date=datetime.strptime(campaign.launch_date, "%Y-%m-%d").date() if campaign.launch_date else None,
            content=campaign.content,
            keywords=campaign.keywords,
            sentiment_score=sentiment_score,
            classification=classification,
            source="api_manual"
        )
        
        db.add(db_campaign)
        db.commit()
        db.refresh(db_campaign)
        
        # Index in Elasticsearch
        doc = {
            "id": db_campaign.id,
            "company_name": campaign.company_name,
            "title": campaign.title,
            "subject_line": campaign.subject_line,
            "content": campaign.content,
            "keywords": campaign.keywords,
            "channel": campaign.channel,
            "launch_date": campaign.launch_date,
            "sentiment_score": sentiment_score,
            "classification": classification
        }
        
        try:
            es.index(index="campaigns", id=db_campaign.id, body=doc)
        except:
            logger.warning("Failed to index in Elasticsearch")
        
        return CampaignResponse(
            id=db_campaign.id,
            company_name=company.name,
            title=db_campaign.title,
            subject_line=db_campaign.subject_line,
            campaign_type=db_campaign.campaign_type,
            channel=db_campaign.channel,
            launch_date=str(db_campaign.launch_date) if db_campaign.launch_date else None,
            content=db_campaign.content,
            keywords=db_campaign.keywords,
            sentiment_score=float(db_campaign.sentiment_score) if db_campaign.sentiment_score else None,
            classification=db_campaign.classification,
            source=db_campaign.source
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    try:
        # Check database
        db = next(get_db())
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        
        # Check Elasticsearch (optional)
        try:
            es.ping()
            es_status = "connected"
        except:
            es_status = "not available"
        
        return {"status": "healthy", "database": "connected", "elasticsearch": es_status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/campaigns", response_model=CampaignResponse)
async def create_campaign(campaign: CampaignCreate, db: Session = Depends(get_db)):
    """Create a new campaign"""
    try:
        # Get or create company
        company = db.query(Company).filter(Company.name == campaign.company_name).first()
        if not company:
            company = Company(name=campaign.company_name)
            db.add(company)
            db.commit()
            db.refresh(company)
        
        # Analyze content with AI
        sentiment_score = await analyze_sentiment(campaign.content)
        classification = await classify_campaign(campaign.content)
        
        # Create campaign
        db_campaign = Campaign(
            company_id=company.id,
            title=campaign.title,
            subject_line=campaign.subject_line,
            campaign_type=campaign.campaign_type,
            channel=campaign.channel,
            launch_date=datetime.strptime(campaign.launch_date, "%Y-%m-%d").date() if campaign.launch_date else None,
            content=campaign.content,
            keywords=campaign.keywords,
            sentiment_score=sentiment_score,
            classification=classification
        )
        
        db.add(db_campaign)
        db.commit()
        db.refresh(db_campaign)
        
        # Index in Elasticsearch
        doc = {
            "id": db_campaign.id,
            "company_name": campaign.company_name,
            "title": campaign.title,
            "subject_line": campaign.subject_line,
            "content": campaign.content,
            "keywords": campaign.keywords,
            "channel": campaign.channel,
            "launch_date": campaign.launch_date,
            "sentiment_score": sentiment_score,
            "classification": classification
        }
        
        es.index(index="campaigns", id=db_campaign.id, body=doc)
        
        return CampaignResponse(
            id=db_campaign.id,
            company_name=company.name,
            title=db_campaign.title,
            subject_line=db_campaign.subject_line,
            campaign_type=db_campaign.campaign_type,
            channel=db_campaign.channel,
            launch_date=str(db_campaign.launch_date) if db_campaign.launch_date else None,
            content=db_campaign.content,
            keywords=db_campaign.keywords,
            sentiment_score=float(db_campaign.sentiment_score) if db_campaign.sentiment_score else None,
            classification=db_campaign.classification
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_campaigns(request: SearchRequest, db: Session = Depends(get_db)):
    """Search campaigns using Elasticsearch"""
    try:
        # Build Elasticsearch query
        query = {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": request.query,
                            "fields": ["title", "subject_line", "content", "keywords"]
                        }
                    }
                ]
            }
        }
        
        # Add filters
        if request.company:
            query["bool"]["must"].append({"match": {"company_name": request.company}})
        
        if request.channel:
            query["bool"]["must"].append({"match": {"channel": request.channel}})
        
        if request.date_from or request.date_to:
            date_range = {}
            if request.date_from:
                date_range["gte"] = request.date_from
            if request.date_to:
                date_range["lte"] = request.date_to
            
            query["bool"]["must"].append({
                "range": {"launch_date": date_range}
            })
        
        # Execute search
        response = es.search(
            index="campaigns",
            body={"query": query, "size": 100}
        )
        
        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            results.append({
                "id": source["id"],
                "company_name": source["company_name"],
                "title": source["title"],
                "subject_line": source.get("subject_line"),
                "channel": source.get("channel"),
                "launch_date": source.get("launch_date"),
                "content": source["content"],
                "keywords": source.get("keywords", []),
                "sentiment_score": source.get("sentiment_score"),
                "classification": source.get("classification"),
                "score": hit["_score"]
            })
        
        return {
            "results": results,
            "total": response["hits"]["total"]["value"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/campaigns")
async def list_campaigns(
    limit: int = 50,
    offset: int = 0,
    company: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List campaigns with pagination"""
    try:
        query = db.query(Campaign).join(Company)
        
        if company:
            query = query.filter(Company.name.ilike(f"%{company}%"))
        
        campaigns = query.offset(offset).limit(limit).all()
        
        results = []
        for campaign in campaigns:
            company_obj = db.query(Company).filter(Company.id == campaign.company_id).first()
            results.append({
                "id": campaign.id,
                "company_name": company_obj.name if company_obj else "Unknown",
                "title": campaign.title,
                "subject_line": campaign.subject_line,
                "campaign_type": campaign.campaign_type,
                "channel": campaign.channel,
                "launch_date": str(campaign.launch_date) if campaign.launch_date else None,
                "content": campaign.content,
                "keywords": campaign.keywords,
                "sentiment_score": float(campaign.sentiment_score) if campaign.sentiment_score else None,
                "classification": campaign.classification
            })
        
        return {"campaigns": results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/companies")
async def get_company_analytics(db: Session = Depends(get_db)):
    """Get analytics by company"""
    try:
        # Get campaign counts by company
        result = db.execute("""
            SELECT c.name, COUNT(ca.id) as campaign_count
            FROM companies c
            LEFT JOIN campaigns ca ON c.id = ca.company_id
            GROUP BY c.name
            ORDER BY campaign_count DESC
        """)
        
        companies = [{"name": row[0], "campaign_count": row[1]} for row in result]
        
        return {"companies": companies}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/trends")
async def get_trends(db: Session = Depends(get_db)):
    """Get campaign trends over time"""
    try:
        result = db.execute("""
            SELECT 
                DATE_TRUNC('month', launch_date) as month,
                COUNT(*) as campaign_count
            FROM campaigns
            WHERE launch_date IS NOT NULL
            GROUP BY month
            ORDER BY month
        """)
        
        trends = [{"month": str(row[0]), "campaign_count": row[1]} for row in result]
        
        return {"trends": trends}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload campaign data from CSV/JSON file"""
    try:
        content = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        elif file.filename.endswith('.json'):
            data = json.loads(content)
            df = pd.DataFrame(data)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        # Process each row
        created_count = 0
        for _, row in df.iterrows():
            campaign_data = CampaignCreate(
                company_name=row.get('company_name', ''),
                title=row.get('title', ''),
                subject_line=row.get('subject_line'),
                campaign_type=row.get('campaign_type'),
                channel=row.get('channel'),
                launch_date=row.get('launch_date'),
                content=row.get('content', ''),
                keywords=row.get('keywords', '').split(',') if row.get('keywords') else []
            )
            
            await create_campaign(campaign_data, db)
            created_count += 1
        
        return {"message": f"Successfully uploaded {created_count} campaigns"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)