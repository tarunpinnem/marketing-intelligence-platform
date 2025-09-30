"""
API Gateway Service
Routes requests to appropriate microservices with load balancing and authentication
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional
import time
from datetime import datetime

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React apps
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))

# Service endpoints
SERVICE_REGISTRY = {
    "data-ingestion": {
        "urls": ["http://data-ingestion:8000"],
        "health_endpoint": "/health",
        "timeout": 30
    },
    "analytics": {
        "urls": ["http://analytics:8001"],
        "health_endpoint": "/health",
        "timeout": 30
    },
    "websocket": {
        "urls": ["http://websocket:8002"],
        "health_endpoint": "/health",
        "timeout": 10
    }
}

# Global connections
redis_client = None
http_client = None

class ServiceStatus(BaseModel):
    service: str
    status: str
    response_time: float
    last_check: datetime

@app.on_event("startup")
async def startup_event():
    """Initialize connections and start health checks"""
    global redis_client, http_client
    
    try:
        # Initialize Redis for rate limiting and caching
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("✅ Redis connection established")
        
        # Initialize HTTP client for service communication
        http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("✅ HTTP client initialized")
        
        # Start health check background task
        asyncio.create_task(periodic_health_checks())
        logger.info("✅ Health checks started")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global redis_client, http_client
    
    if http_client:
        await http_client.aclose()
        logger.info("HTTP client closed")
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

async def rate_limit_check(client_id: str) -> bool:
    """Check rate limiting for client"""
    try:
        key = f"rate_limit:{client_id}:{int(time.time() / 60)}"  # Per minute window
        
        current = await redis_client.get(key)
        if current is None:
            await redis_client.setex(key, 60, 1)
            return True
        elif int(current) < RATE_LIMIT_PER_MINUTE:
            await redis_client.incr(key)
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        return True  # Allow on error

async def get_healthy_service_url(service_name: str) -> Optional[str]:
    """Get URL of a healthy service instance"""
    try:
        service_config = SERVICE_REGISTRY.get(service_name)
        if not service_config:
            return None
        
        # Check cache for healthy services
        cache_key = f"healthy_services:{service_name}"
        cached_urls = await redis_client.lrange(cache_key, 0, -1)
        
        if cached_urls:
            # Return first healthy URL (simple round-robin)
            return cached_urls[0]
        
        # If no cached healthy services, return first URL
        return service_config["urls"][0] if service_config["urls"] else None
        
    except Exception as e:
        logger.error(f"Error getting healthy service URL: {e}")
        return None

async def proxy_request(
    service_name: str,
    endpoint: str,
    method: str = "GET",
    json_data: Dict = None,
    params: Dict = None,
    headers: Dict = None
) -> Dict:
    """Proxy request to microservice"""
    try:
        service_url = await get_healthy_service_url(service_name)
        if not service_url:
            raise HTTPException(
                status_code=503, 
                detail=f"Service {service_name} is unavailable"
            )
        
        url = f"{service_url}{endpoint}"
        
        # Forward request to service
        response = await http_client.request(
            method=method,
            url=url,
            json=json_data,
            params=params,
            headers=headers
        )
        
        # Log request for monitoring
        logger.info(f"🔄 {method} {url} -> {response.status_code}")
        
        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )
        
        return response.json()
        
    except httpx.RequestError as e:
        logger.error(f"Request error to {service_name}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service {service_name} communication error"
        )
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def periodic_health_checks():
    """Periodically check service health"""
    logger.info("🔄 Starting periodic health checks...")
    
    while True:
        try:
            for service_name, config in SERVICE_REGISTRY.items():
                healthy_urls = []
                
                for url in config["urls"]:
                    try:
                        start_time = time.time()
                        health_url = f"{url}{config['health_endpoint']}"
                        
                        response = await http_client.get(
                            health_url,
                            timeout=config.get("timeout", 10)
                        )
                        
                        response_time = time.time() - start_time
                        
                        if response.status_code == 200:
                            healthy_urls.append(url)
                            logger.debug(f"✅ {service_name} at {url} is healthy ({response_time:.2f}s)")
                        else:
                            logger.warning(f"❌ {service_name} at {url} unhealthy: {response.status_code}")
                            
                    except Exception as e:
                        logger.warning(f"❌ {service_name} at {url} failed health check: {e}")
                
                # Update healthy services cache
                cache_key = f"healthy_services:{service_name}"
                await redis_client.delete(cache_key)
                if healthy_urls:
                    await redis_client.lpush(cache_key, *healthy_urls)
                    await redis_client.expire(cache_key, 60)  # 1 minute TTL
            
            # Wait 30 seconds before next health check
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in health checks: {e}")
            await asyncio.sleep(30)

# Middleware for request logging and rate limiting
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Process all requests for logging and rate limiting"""
    start_time = time.time()
    client_ip = request.client.host
    
    # Rate limiting
    if not await rate_limit_check(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"}
        )
    
    # Process request
    response = await call_next(request)
    
    # Log request
    process_time = time.time() - start_time
    logger.info(
        f"📊 {request.method} {request.url.path} "
        f"[{client_ip}] -> {response.status_code} ({process_time:.3f}s)"
    )
    
    # Add response headers
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Gateway"] = "competiscan-api-gateway"
    
    return response

@app.get("/health")
async def gateway_health():
    """Gateway health check"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/health/services")
async def services_health():
    """Check health of all services"""
    service_statuses = {}
    
    for service_name in SERVICE_REGISTRY.keys():
        healthy_urls = await redis_client.lrange(f"healthy_services:{service_name}", 0, -1)
        service_statuses[service_name] = {
            "status": "healthy" if healthy_urls else "unhealthy",
            "healthy_instances": len(healthy_urls),
            "total_instances": len(SERVICE_REGISTRY[service_name]["urls"])
        }
    
    return {
        "gateway_status": "healthy",
        "services": service_statuses,
        "timestamp": datetime.utcnow().isoformat()
    }

# Data Ingestion Service Endpoints
@app.get("/api/ingestion/health")
async def ingestion_health():
    """Proxy to data ingestion health"""
    return await proxy_request("data-ingestion", "/health")

@app.post("/api/ingestion/manual")
async def manual_ingestion():
    """Trigger manual data ingestion"""
    return await proxy_request("data-ingestion", "/ingest/manual", "POST")

@app.get("/api/ingestion/stats")
async def ingestion_stats():
    """Get ingestion statistics"""
    return await proxy_request("data-ingestion", "/stats")

# Analytics Service Endpoints
@app.get("/api/analytics")
async def get_analytics():
    """Get analytics data"""
    return await proxy_request("analytics", "/analytics")

@app.post("/api/analytics/recalculate")
async def recalculate_analytics():
    """Trigger analytics recalculation"""
    return await proxy_request("analytics", "/analytics/recalculate", "POST")

@app.post("/api/analytics/search")
async def search_campaigns(request: Request):
    """Search campaigns"""
    body = await request.json()
    query = body.get("query", "")
    filters = body.get("filters", {})
    
    return await proxy_request(
        "analytics", 
        "/search", 
        "POST",
        json_data={"query": query, "filters": filters}
    )

# WebSocket Service Endpoint
@app.get("/api/websocket/health")
async def websocket_health():
    """Proxy to websocket service health"""
    return await proxy_request("websocket", "/health")

# Campaign endpoints - proxy to PostgreSQL data
@app.get("/api/campaigns")
async def get_campaigns(limit: int = 100, offset: int = 0):
    """Get campaigns directly from PostgreSQL"""
    try:
        import asyncpg
        
        # Connect to PostgreSQL directly for campaigns
        conn = await asyncpg.connect("postgresql://postgres:postgres@postgres:5432/competiscan")
        
        campaigns = await conn.fetch("""
            SELECT 
                id, external_id, name, company, platform, content, 
                sentiment_score, budget, impressions, clicks, conversions, 
                ctr, status, start_date, created_at, metadata
            FROM campaigns 
            ORDER BY created_at DESC 
            LIMIT $1 OFFSET $2
        """, limit, offset)
        
        await conn.close()
        
        result = []
        for campaign in campaigns:
            result.append({
                "id": campaign['id'],
                "external_id": campaign['external_id'],
                "name": campaign['name'],
                "company": campaign['company'],
                "platform": campaign['platform'],
                "content": campaign['content'],
                "sentiment_score": float(campaign['sentiment_score']) if campaign['sentiment_score'] else 0.5,
                "budget": float(campaign['budget']) if campaign['budget'] else 0,
                "impressions": campaign['impressions'] or 0,
                "clicks": campaign['clicks'] or 0,
                "conversions": campaign['conversions'] or 0,
                "ctr": float(campaign['ctr']) if campaign['ctr'] else 0,
                "status": campaign['status'],
                "start_date": campaign['start_date'].isoformat() if campaign['start_date'] else None,
                "created_at": campaign['created_at'].isoformat() if campaign['created_at'] else None,
                "metadata": campaign['metadata'] if campaign['metadata'] else {}
            })
        
        return {"campaigns": result, "total": len(result)}
        
    except Exception as e:
        logger.error(f"Error fetching campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def api_health():
    """API health endpoint for frontend compatibility"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Competiscan API Gateway operational"
    }

# Generic proxy endpoint for development
@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def generic_proxy(service: str, path: str, request: Request):
    """Generic proxy for any service endpoint"""
    if service not in SERVICE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Service {service} not found")
    
    # Get request body if present
    json_data = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            json_data = await request.json()
        except:
            pass  # No JSON body
    
    return await proxy_request(
        service,
        f"/{path}",
        request.method,
        json_data=json_data,
        params=dict(request.query_params),
        headers=dict(request.headers)
    )

@app.get("/api/metrics")
async def get_metrics():
    """Get gateway metrics"""
    try:
        # Get rate limiting stats
        rate_limit_keys = await redis_client.keys("rate_limit:*")
        active_clients = len(set(key.split(":")[1] for key in rate_limit_keys))
        
        return {
            "active_clients": active_clients,
            "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
            "services_registered": len(SERVICE_REGISTRY),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )