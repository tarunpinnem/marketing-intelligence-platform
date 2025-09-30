#!/usr/bin/env python3
"""
Competiscan-Lite Standalone Backend with Real-time Streaming
Enhanced with WebSocket support and Kafka-style event streaming
"""

import asyncio
import json
import logging
import os
import random
import time
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket connection manager for real-time streaming
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_count: int = 0

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_count += 1
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if self.active_connections:
            for connection in self.active_connections:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error broadcasting to connection: {e}")

# Global connection manager
manager = ConnectionManager()

# Create FastAPI app
app = FastAPI(
    title="Competiscan-Lite API",
    description="Competitive Marketing Insights Dashboard - Standalone Mode with Real-time Streaming",
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

# In-memory storage for demo
campaigns_data = []
analytics_data = {
    "total_campaigns": 0,
    "companies": 0,
    "channels": {},
    "industries": {},
    "recent_activity": []
}

def load_demo_data():
    """Load demo data from ETL generated files"""
    global campaigns_data, analytics_data
    
    try:
        # Try to load from demo files
        demo_file = Path("/Users/tarunpinnem/Desktop/competiscan/data/etl/demo_campaigns.json")
        if demo_file.exists():
            with open(demo_file, 'r') as f:
                campaigns_data = json.load(f)
            logger.info(f"Loaded {len(campaigns_data)} demo campaigns")
        else:
            # Generate some basic demo data
            campaigns_data = generate_sample_campaigns(10)
            logger.info("Generated sample campaigns")
        
        update_analytics()
        
    except Exception as e:
        logger.error(f"Error loading demo data: {e}")
        campaigns_data = generate_sample_campaigns(5)
        update_analytics()

def generate_sample_campaigns(count: int):
    """Generate sample campaign data"""
    companies = ["Apple", "Google", "Microsoft", "Amazon", "Meta", "Netflix", "Adobe", "Salesforce"]
    industries = ["Technology", "E-commerce", "Financial Services", "Entertainment"]
    channels = ["Email", "Social Media", "Display Ads", "Search Ads", "Video Ads"]
    campaign_types = ["promotional", "educational", "retention"]
    
    campaigns = []
    for i in range(count):
        campaign = {
            "id": i + 1,
            "event_type": "new_campaign",
            "company": random.choice(companies),
            "company_name": random.choice(companies),  # Add both for compatibility
            "industry": random.choice(industries),
            "channel": random.choice(channels),
            "title": f"Campaign {i+1}",
            "subject": f"Amazing offer from {random.choice(companies)}",
            "content": f"This is a sample {random.choice(campaign_types)} campaign with great benefits!",
            "keywords": random.sample(["promotion", "discount", "exclusive", "limited", "offer"], 3),
            "date": (datetime.now() - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d'),
            "launch_date": (datetime.now() - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d'),
            "sentiment_score": round(random.uniform(-1.0, 1.0), 2),
            "source": "sample_data"
        }
        campaigns.append(campaign)
    
    return campaigns

def update_analytics():
    """Update analytics data"""
    global analytics_data
    
    analytics_data["total_campaigns"] = len(campaigns_data)
    analytics_data["companies"] = len(set(c.get("company", "") for c in campaigns_data))
    
    # Channel distribution
    channels = {}
    industries = {}
    for campaign in campaigns_data:
        channel = campaign.get("channel", "Unknown")
        industry = campaign.get("industry", "Unknown")
        channels[channel] = channels.get(channel, 0) + 1
        industries[industry] = industries.get(industry, 0) + 1
    
    analytics_data["channels"] = channels
    analytics_data["industries"] = industries
    analytics_data["recent_activity"] = campaigns_data[-10:] if campaigns_data else []

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    logger.info("🚀 Starting Competiscan-Lite Standalone Backend")
    load_demo_data()
    logger.info(f"📊 Loaded {len(campaigns_data)} campaigns")

@app.get("/")
async def root():
    """Root endpoint with welcome message"""
    return HTMLResponse(content="""
    <html>
        <head><title>Competiscan-Lite API</title></head>
        <body>
            <h1>🏗️ Competiscan-Lite API</h1>
            <p>Event-Driven Competitive Marketing Insights Platform - Standalone Mode</p>
            <h2>Available Endpoints:</h2>
            <ul>
                <li><a href="/docs">📚 API Documentation</a></li>
                <li><a href="/api/campaigns">📋 Campaigns</a></li>
                <li><a href="/api/analytics">📊 Analytics</a></li>
                <li><a href="/api/search?q=campaign">🔍 Search</a></li>
                <li><a href="/api/health">💚 Health Check</a></li>
            </ul>
            <p>Status: ✅ Running in standalone mode</p>
        </body>
    </html>
    """)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mode": "standalone",
        "campaigns_loaded": len(campaigns_data),
        "version": "2.0.0"
    }

@app.get("/api/campaigns")
async def get_campaigns(skip: int = 0, limit: int = 50):
    """Get campaigns with pagination"""
    total = len(campaigns_data)
    campaigns = campaigns_data[skip:skip + limit]
    
    return {
        "campaigns": campaigns,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + limit < total
    }

@app.get("/api/search")
async def search_campaigns(
    q: Optional[str] = None,
    company: Optional[str] = None,
    industry: Optional[str] = None,
    channel: Optional[str] = None
):
    """Search campaigns with filters"""
    results = campaigns_data.copy()
    
    if q:
        q_lower = q.lower()
        results = [
            c for c in results
            if q_lower in c.get("title", "").lower() or
               q_lower in c.get("content", "").lower() or
               q_lower in c.get("company", "").lower()
        ]
    
    if company:
        results = [c for c in results if c.get("company", "").lower() == company.lower()]
    
    if industry:
        results = [c for c in results if c.get("industry", "").lower() == industry.lower()]
    
    if channel:
        results = [c for c in results if c.get("channel", "").lower() == channel.lower()]
    
    return {
        "results": results,
        "total": len(results),
        "query": {
            "text": q,
            "company": company,
            "industry": industry,
            "channel": channel
        }
    }

@app.get("/api/analytics")
async def get_analytics():
    """Get analytics data"""
    companies_list = []
    company_counts = {}
    
    # Count campaigns per company
    for campaign in campaigns_data:
        company = campaign.get("company", "Unknown")
        company_counts[company] = company_counts.get(company, 0) + 1
    
    # Convert to list format expected by frontend
    for company, count in sorted(company_counts.items(), key=lambda x: x[1], reverse=True):
        companies_list.append({
            "name": company,
            "campaign_count": count
        })
    
    return {
        **analytics_data,
        "companies": companies_list
    }

@app.get("/api/insights")
async def get_insights():
    """Get AI-powered insights"""
    # Mock insights since we don't have OpenAI API key
    insights = [
        {
            "type": "trend",
            "title": "Email Campaigns Increasing",
            "description": "Email campaigns have increased by 25% this month",
            "confidence": 0.85
        },
        {
            "type": "opportunity",
            "title": "Technology Sector Active",
            "description": "Technology companies are launching more retention campaigns",
            "confidence": 0.78
        },
        {
            "type": "pattern",
            "title": "Weekend Launch Pattern",
            "description": "Most successful campaigns launch on weekends",
            "confidence": 0.72
        }
    ]
    
    return {"insights": insights}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload campaign data file"""
    global campaigns_data
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            # Read CSV
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
            new_campaigns = df.to_dict('records')
            
            # Convert to our format
            for campaign in new_campaigns:
                campaign_data = {
                    "event_type": "uploaded_campaign",
                    "company": campaign.get("company_name", "Unknown"),
                    "industry": campaign.get("industry", "Unknown"),
                    "channel": campaign.get("channel", "Email"),
                    "title": campaign.get("title", "Untitled"),
                    "subject": campaign.get("subject_line", ""),
                    "content": campaign.get("content", ""),
                    "keywords": campaign.get("keywords", "").split(",") if campaign.get("keywords") else [],
                    "date": campaign.get("launch_date", datetime.now().strftime('%Y-%m-%d')),
                    "source": "upload"
                }
                campaigns_data.append(campaign_data)
        
        elif file.filename.endswith('.json'):
            # Read JSON
            data = json.loads(contents.decode('utf-8'))
            if isinstance(data, list):
                campaigns_data.extend(data)
            else:
                campaigns_data.append(data)
        
        update_analytics()
        
        return {
            "message": f"Successfully uploaded {file.filename}",
            "campaigns_added": len(new_campaigns) if file.filename.endswith('.csv') else 1,
            "total_campaigns": len(campaigns_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

@app.get("/api/stats/realtime")
async def get_realtime_stats():
    """Get real-time statistics"""
    return {
        "timestamp": datetime.now().isoformat(),
        "active_campaigns": len(campaigns_data),
        "companies_tracked": len(set(c.get("company", "") for c in campaigns_data)),
        "channels_active": len(set(c.get("channel", "") for c in campaigns_data)),
        "recent_uploads": len([c for c in campaigns_data if c.get("source") == "upload"]),
        "system_status": "operational"
    }

# WebSocket endpoints for real-time streaming
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time campaign streaming"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            try:
                data = await websocket.receive_text()
                logger.info(f"Received from client: {data}")
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background task for generating live campaign events
async def generate_campaign_events():
    """Background task to generate and broadcast live campaign events"""
    global campaigns_data  # Declare global variable access
    
    companies = ["Apple", "Google", "Microsoft", "Amazon", "Meta", "Netflix", "Adobe", "Salesforce", "Tesla", "SpaceX"]
    industries = ["Technology", "E-commerce", "Financial Services", "Entertainment", "Automotive", "Healthcare"]
    channels = ["Email", "Social Media", "Display Ads", "Search Ads", "Video Ads", "Influencer"]
    event_types = ["new_campaign", "campaign_update", "performance_alert", "competitor_action"]
    
    while True:
        try:
            # Generate a random campaign event
            event = {
                "event_type": random.choice(event_types),
                "id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "company": random.choice(companies),
                "industry": random.choice(industries),
                "channel": random.choice(channels),
                "title": f"Live Campaign {random.randint(1000, 9999)}",
                "sentiment_score": round(random.uniform(-1.0, 1.0), 2),
                "engagement_rate": round(random.uniform(0.01, 0.25), 3),
                "reach": random.randint(1000, 100000),
                "source": "live_stream"
            }
            
            # Add event to campaigns data for consistency
            campaigns_data.append(event)
            
            # Keep only last 1000 campaigns to prevent memory issues
            if len(campaigns_data) > 1000:
                campaigns_data = campaigns_data[-1000:]
            
            # Update analytics
            update_analytics()
            
            # Broadcast to all connected clients
            await manager.broadcast(event)
            
            # Wait for next event (between 2-8 seconds)
            await asyncio.sleep(random.uniform(2, 8))
            
        except Exception as e:
            logger.error(f"Error generating campaign event: {e}")
            await asyncio.sleep(5)

# Start background task when server starts
@app.on_event("startup")
async def startup_event():
    """Initialize server on startup"""
    load_demo_data()
    logger.info(f"✅ Loaded {len(campaigns_data)} demo campaigns")
    
    # Start the background campaign event generator
    asyncio.create_task(generate_campaign_events())
    logger.info("🎯 Started real-time campaign event generator")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    logger.info("🛑 Server shutdown initiated")

if __name__ == "__main__":
    logger.info("🚀 Starting Competiscan-Lite Standalone Server")
    uvicorn.run(
        "standalone_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )