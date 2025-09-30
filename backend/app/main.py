from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.routes import search, campaigns, analytics
from app.db import init_db
from app.services.websocket_manager import websocket_manager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CompetiscanLite API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - update in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("🚀 CompetiscanLite API started")

@app.on_event("shutdown")
async def shutdown():
    await websocket_manager.stop_kafka_streaming()
    logger.info("🛑 CompetiscanLite API stopped")

# Include routers
app.include_router(search.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

# WebSocket endpoint for real-time streaming
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    
    try:
        # Send initial data
        await websocket_manager.send_initial_data(websocket)
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            message = eval(data)  # In production, use json.loads and validate
            
            if message.get('type') == 'request_initial_data':
                await websocket_manager.send_initial_data(websocket)
                
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"❌ WebSocket error: {str(e)}")
        await websocket_manager.disconnect(websocket)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "streaming": websocket_manager.running,
        "active_connections": len(websocket_manager.active_connections)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)