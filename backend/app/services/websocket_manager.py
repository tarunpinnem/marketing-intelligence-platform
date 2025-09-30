import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Set
from fastapi import WebSocket
from app.services.kafka_streaming import kafka_streaming

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.kafka_task = None
        self.running = False

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"📡 New WebSocket connection. Total: {len(self.active_connections)}")
        
        # Start Kafka streaming if first connection
        if len(self.active_connections) == 1 and not self.running:
            await self.start_kafka_streaming()

    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        self.active_connections.discard(websocket)
        logger.info(f"📡 WebSocket disconnected. Total: {len(self.active_connections)}")
        
        # Stop Kafka streaming if no connections
        if len(self.active_connections) == 0 and self.running:
            await self.stop_kafka_streaming()

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"❌ Error sending personal message: {str(e)}")
            await self.disconnect(websocket)

    async def broadcast(self, message: Dict[Any, Any]):
        """Broadcast message to all connected WebSockets"""
        if not self.active_connections:
            return
            
        message_str = json.dumps(message)
        disconnected = set()
        
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"❌ Error broadcasting to connection: {str(e)}")
                disconnected.add(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.active_connections.discard(connection)

    async def start_kafka_streaming(self):
        """Start Kafka streaming and consumption"""
        try:
            self.running = True
            
            # Start Kafka producer and consumer
            await kafka_streaming.start_producer()
            await kafka_streaming.start_consumer()
            kafka_streaming.running = True
            
            # Start background tasks
            self.kafka_task = asyncio.create_task(self._kafka_consumer_loop())
            
            # Start data producers
            asyncio.create_task(self._start_data_producers())
            
            logger.info("🚀 Kafka streaming started")
            
        except Exception as e:
            logger.error(f"❌ Error starting Kafka streaming: {str(e)}")

    async def stop_kafka_streaming(self):
        """Stop Kafka streaming"""
        try:
            self.running = False
            
            if self.kafka_task:
                self.kafka_task.cancel()
                
            await kafka_streaming.stop()
            
            logger.info("🛑 Kafka streaming stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping Kafka streaming: {str(e)}")

    async def _kafka_consumer_loop(self):
        """Main Kafka consumer loop"""
        try:
            async for message in kafka_streaming.consumer:
                if not self.running:
                    break
                    
                topic = message.topic
                data = message.value
                
                # Process message based on topic
                if topic == 'campaign-updates':
                    await self._handle_campaign_update(data)
                elif topic == 'analytics-updates':
                    await self._handle_analytics_update(data)
                elif topic == 'news-feed':
                    await self._handle_news_update(data)
                    
        except asyncio.CancelledError:
            logger.info("📡 Kafka consumer loop cancelled")
        except Exception as e:
            logger.error(f"❌ Error in Kafka consumer loop: {str(e)}")

    async def _handle_campaign_update(self, data: Dict[Any, Any]):
        """Handle campaign update from Kafka"""
        try:
            # Store in Elasticsearch
            from app.db import es
            await es.index(
                index="campaigns",
                id=data['id'],
                body=data
            )
            
            # Broadcast to WebSocket clients
            await self.broadcast({
                'type': 'campaign_update',
                'data': data,
                'event_type': 'campaign_update',
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"📢 Campaign update broadcasted: {data.get('company', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"❌ Error handling campaign update: {str(e)}")

    async def _handle_analytics_update(self, data: Dict[Any, Any]):
        """Handle analytics update from Kafka"""
        try:
            # Broadcast to WebSocket clients
            await self.broadcast({
                'type': 'analytics_update',
                'data': data,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"📊 Analytics update broadcasted: {data.get('company', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"❌ Error handling analytics update: {str(e)}")

    async def _handle_news_update(self, data: Dict[Any, Any]):
        """Handle news update from Kafka"""
        try:
            # Store in Elasticsearch
            from app.db import es
            await es.index(
                index="campaigns",
                id=data['id'],
                body=data
            )
            
            # Broadcast to WebSocket clients
            await self.broadcast({
                'type': 'campaign_update',
                'data': data,
                'event_type': 'news_update',
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"📰 News update broadcasted: {data.get('company', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"❌ Error handling news update: {str(e)}")

    async def _start_data_producers(self):
        """Start all Kafka data producers"""
        try:
            # Start news data producer
            asyncio.create_task(kafka_streaming.produce_news_data())
            
            # Start social media data producer
            asyncio.create_task(kafka_streaming.produce_social_media_data())
            
            # Start analytics data producer
            asyncio.create_task(kafka_streaming.produce_analytics_data())
            
            logger.info("🏭 All Kafka data producers started")
            
        except Exception as e:
            logger.error(f"❌ Error starting data producers: {str(e)}")

    async def send_initial_data(self, websocket: WebSocket):
        """Send initial data to new WebSocket connection"""
        try:
            from app.db import es
            
            # Get recent campaigns
            response = await es.search(
                index="campaigns",
                body={
                    "query": {"match_all": {}},
                    "sort": [{"timestamp": {"order": "desc"}}],
                    "size": 20
                }
            )
            
            campaigns = []
            for hit in response['hits']['hits']:
                campaigns.append({
                    'id': hit['_id'],
                    **hit['_source']
                })
            
            # Send initial data
            await self.send_personal_message(json.dumps({
                'type': 'initial_data',
                'campaigns': campaigns,
                'summary': {
                    'totalCampaigns': len(campaigns),
                    'activeCampaigns': len([c for c in campaigns if c.get('status') == 'active']),
                    'companiesCount': len(set(c.get('company', '') for c in campaigns)),
                    'avgSentiment': sum(c.get('metrics', {}).get('sentiment_score', 0.5) for c in campaigns) / len(campaigns) if campaigns else 0.5
                }
            }), websocket)
            
            logger.info("📦 Initial data sent to WebSocket connection")
            
        except Exception as e:
            logger.error(f"❌ Error sending initial data: {str(e)}")

# Global WebSocket manager instance
websocket_manager = WebSocketManager()