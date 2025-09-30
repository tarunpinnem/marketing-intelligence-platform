"""
WebSocket Service
Handles real-time updates to frontend via WebSocket connections and Kafka consumption
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Set
from datetime import datetime

import redis.asyncio as redis
from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WebSocket Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Global connections and state
kafka_consumer = None
redis_client = None
active_connections: Set[WebSocket] = set()
connection_stats = {
    "total_connections": 0,
    "active_connections": 0,
    "messages_sent": 0,
    "start_time": datetime.utcnow()
}

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Add new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        connection_stats["total_connections"] += 1
        connection_stats["active_connections"] = len(self.active_connections)
        
        logger.info(f"🔌 New WebSocket connection. Active: {len(self.active_connections)}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "welcome",
            "message": "Connected to Competiscan real-time updates",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        connection_stats["active_connections"] = len(self.active_connections)
        logger.info(f"🔌 WebSocket disconnected. Active: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(json.dumps(message, default=str))
            connection_stats["messages_sent"] += 1
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected WebSockets"""
        if not self.active_connections:
            return
        
        disconnected = set()
        
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(json.dumps(message, default=str))
                connection_stats["messages_sent"] += 1
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
        
        if disconnected:
            logger.info(f"📡 Broadcast to {len(self.active_connections)} clients, removed {len(disconnected)} dead connections")
        else:
            logger.info(f"📡 Broadcast to {len(self.active_connections)} clients")

# Initialize connection manager
manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize connections and start Kafka consumer"""
    global kafka_consumer, redis_client
    
    try:
        # Initialize Redis connection
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("✅ Redis connection established")
        
        # Initialize Kafka consumer
        kafka_consumer = AIOKafkaConsumer(
            'websocket_updates',
            'campaigns',
            'analytics',
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id='websocket_service',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest'
        )
        await kafka_consumer.start()
        logger.info("✅ Kafka consumer started")
        
        # Start background Kafka message processor
        asyncio.create_task(kafka_message_processor())
        
        # Start heartbeat task
        asyncio.create_task(heartbeat_task())
        
        logger.info("✅ WebSocket service started")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global kafka_consumer, redis_client
    
    # Notify all connected clients of shutdown
    if manager.active_connections:
        await manager.broadcast({
            "type": "system",
            "message": "Service is shutting down",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    if kafka_consumer:
        await kafka_consumer.stop()
        logger.info("Kafka consumer stopped")
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

async def kafka_message_processor():
    """Process messages from Kafka and broadcast to WebSocket clients"""
    logger.info("🔄 Starting Kafka message processor...")
    
    async for message in kafka_consumer:
        try:
            topic = message.topic
            data = message.value
            
            # Process different message types
            websocket_message = await process_kafka_message(topic, data)
            
            if websocket_message and manager.active_connections:
                await manager.broadcast(websocket_message)
                
                # Cache the message in Redis for new connections
                await cache_recent_message(websocket_message)
            
        except Exception as e:
            logger.error(f"Error processing Kafka message: {e}")

async def process_kafka_message(topic: str, data: Dict) -> Dict:
    """Process and format Kafka message for WebSocket broadcast"""
    try:
        if topic == "websocket_updates":
            # Direct WebSocket updates
            return {
                "type": data.get("type", "update"),
                "data": data.get("data", {}),
                "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
                "source": "websocket_updates"
            }
        
        elif topic == "campaigns":
            # New campaign data
            campaign_data = data.get("data", {})
            return {
                "type": "campaign_update",
                "data": {
                    "campaign": {
                        "name": campaign_data.get("name", ""),
                        "company": campaign_data.get("company", ""),
                        "platform": campaign_data.get("platform", ""),
                        "sentiment_score": campaign_data.get("sentiment_score", 0.5)
                    },
                    "action": "new_campaign"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "source": "campaigns"
            }
        
        elif topic == "analytics":
            # Analytics update trigger
            return {
                "type": "analytics_update",
                "data": {
                    "action": data.get("data", {}).get("action", "update"),
                    "reason": data.get("data", {}).get("reason", "periodic_update")
                },
                "timestamp": datetime.utcnow().isoformat(),
                "source": "analytics"
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error processing message from topic {topic}: {e}")
        return None

async def cache_recent_message(message: Dict):
    """Cache recent messages in Redis for new connections"""
    try:
        # Store in a Redis list with TTL
        await redis_client.lpush("recent_messages", json.dumps(message, default=str))
        await redis_client.ltrim("recent_messages", 0, 99)  # Keep last 100 messages
        await redis_client.expire("recent_messages", 3600)  # 1 hour TTL
        
    except Exception as e:
        logger.error(f"Error caching message: {e}")

async def get_recent_messages() -> List[Dict]:
    """Get recent cached messages for new connections"""
    try:
        messages = await redis_client.lrange("recent_messages", 0, 9)  # Last 10 messages
        return [json.loads(msg) for msg in messages]
    except Exception as e:
        logger.error(f"Error getting recent messages: {e}")
        return []

async def heartbeat_task():
    """Send periodic heartbeat to maintain connections"""
    while True:
        try:
            if manager.active_connections:
                heartbeat_message = {
                    "type": "heartbeat",
                    "data": {
                        "active_connections": len(manager.active_connections),
                        "uptime": str(datetime.utcnow() - connection_stats["start_time"]),
                        "messages_sent": connection_stats["messages_sent"]
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await manager.broadcast(heartbeat_message)
            
            # Wait 30 seconds before next heartbeat
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in heartbeat task: {e}")
            await asyncio.sleep(30)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        # Send recent messages to new connection
        recent_messages = await get_recent_messages()
        for message in reversed(recent_messages):  # Send in chronological order
            await manager.send_personal_message(message, websocket)
        
        # Keep connection alive and handle client messages
        while True:
            # Wait for client messages (ping, preferences, etc.)
            try:
                data = await websocket.receive_text()
                client_message = json.loads(data)
                
                # Handle client message types
                if client_message.get("type") == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)
                
                elif client_message.get("type") == "subscribe":
                    # Handle subscription preferences (future feature)
                    await manager.send_personal_message({
                        "type": "subscription_confirmed",
                        "data": client_message.get("data", {}),
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)
                
            except asyncio.TimeoutError:
                # No message received, continue loop
                continue
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "websocket",
        "timestamp": datetime.utcnow().isoformat(),
        "connections": {
            "active": len(manager.active_connections),
            "total": connection_stats["total_connections"]
        },
        "kafka_consumer": kafka_consumer is not None,
        "redis": redis_client is not None
    }

@app.get("/stats")
async def get_connection_stats():
    """Get WebSocket connection statistics"""
    uptime = datetime.utcnow() - connection_stats["start_time"]
    
    return {
        "active_connections": len(manager.active_connections),
        "total_connections": connection_stats["total_connections"],
        "messages_sent": connection_stats["messages_sent"],
        "uptime_seconds": int(uptime.total_seconds()),
        "uptime_formatted": str(uptime),
        "start_time": connection_stats["start_time"].isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/broadcast")
async def manual_broadcast(message: Dict):
    """Manually broadcast message to all connected clients"""
    try:
        websocket_message = {
            "type": "manual_broadcast",
            "data": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await manager.broadcast(websocket_message)
        
        return {
            "status": "broadcast_sent",
            "recipients": len(manager.active_connections),
            "message": websocket_message
        }
        
    except Exception as e:
        logger.error(f"Error in manual broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recent-messages")
async def get_recent_messages_endpoint():
    """Get recent cached messages"""
    try:
        messages = await get_recent_messages()
        return {
            "messages": messages,
            "count": len(messages),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting recent messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )