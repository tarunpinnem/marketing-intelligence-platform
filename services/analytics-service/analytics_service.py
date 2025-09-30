"""
Real-time Analytics Service for Competiscan-Lite
Provides WebSocket connections for live dashboard updates
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Set

import redis
import websockets
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from websockets.exceptions import ConnectionClosedError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealTimeAnalyticsService:
    def __init__(self):
        self.kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.websocket_port = int(os.getenv('WEBSOCKET_PORT', 8002))
        
        # Connected clients
        self.connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Redis for caching real-time data
        self.redis_client = None
        self.kafka_consumer = None
        
        # Statistics
        self.messages_sent = 0
        self.active_connections = 0

    async def initialize_services(self):
        """Initialize Redis and Kafka connections"""
        try:
            # Redis connection
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await asyncio.to_thread(self.redis_client.ping)
            
            # Kafka consumer for real-time events
            self.kafka_consumer = KafkaConsumer(
                'campaign-events',
                'analytics-events', 
                bootstrap_servers=self.kafka_servers.split(','),
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='realtime-analytics',
                auto_offset_reset='latest'
            )
            
            logger.info("✅ Analytics service initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            return False

    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new WebSocket client"""
        self.connected_clients.add(websocket)
        self.active_connections += 1
        
        logger.info(f"📱 Client connected. Active connections: {self.active_connections}")
        
        # Send initial data to new client
        await self.send_initial_data(websocket)

    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister a WebSocket client"""
        self.connected_clients.discard(websocket)
        self.active_connections -= 1
        
        logger.info(f"📱 Client disconnected. Active connections: {self.active_connections}")

    async def send_initial_data(self, websocket: websockets.WebSocketServerProtocol):
        """Send initial dashboard data to newly connected client"""
        try:
            # Get cached summary data from Redis
            summary_data = await asyncio.to_thread(
                self.redis_client.get, 'dashboard:summary'
            )
            
            if summary_data:
                initial_message = {
                    'type': 'initial_data',
                    'data': json.loads(summary_data),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                await websocket.send(json.dumps(initial_message))
            else:
                # Send placeholder data
                placeholder_data = {
                    'type': 'initial_data',
                    'data': {
                        'total_campaigns': 0,
                        'active_campaigns': 0,
                        'total_companies': 0,
                        'avg_sentiment': 0.5,
                        'recent_events': []
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                await websocket.send(json.dumps(placeholder_data))
                
        except Exception as e:
            logger.error(f"❌ Error sending initial data: {e}")

    async def broadcast_to_clients(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients"""
        if not self.connected_clients:
            return
        
        message_str = json.dumps(message)
        disconnected_clients = set()
        
        for client in self.connected_clients.copy():
            try:
                await client.send(message_str)
                self.messages_sent += 1
                
            except ConnectionClosedError:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"❌ Error broadcasting to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            await self.unregister_client(client)

    async def process_campaign_update(self, event: Dict[str, Any]):
        """Process campaign events for real-time updates"""
        try:
            campaign = event.get('campaign', {})
            event_type = event.get('event_type')
            
            # Create real-time update message
            update_message = {
                'type': 'campaign_update',
                'event_type': event_type,
                'data': {
                    'id': campaign.get('id'),
                    'company': campaign.get('company'),
                    'name': campaign.get('name'),
                    'platform': campaign.get('platform'),
                    'status': campaign.get('status'),
                    'metrics': campaign.get('metrics', {}),
                    'sentiment_score': campaign.get('metrics', {}).get('sentiment_score', 0.5)
                },
                'timestamp': event.get('timestamp')
            }
            
            # Broadcast to clients
            await self.broadcast_to_clients(update_message)
            
            # Update Redis cache
            await self.update_dashboard_cache(campaign, event_type)
            
            logger.info(f"📊 Campaign update broadcasted: {campaign.get('company')} - {event_type}")
            
        except Exception as e:
            logger.error(f"❌ Error processing campaign update: {e}")

    async def process_analytics_update(self, event: Dict[str, Any]):
        """Process analytics events for real-time updates"""
        try:
            data = event.get('data', {})
            event_type = event.get('event_type')
            
            # Create analytics update message
            update_message = {
                'type': 'analytics_update',
                'event_type': event_type,
                'data': {
                    'company': data.get('company'),
                    'metric_type': data.get('metric_type'),
                    'value': data.get('value'),
                    'trend': data.get('trend'),
                    'confidence': data.get('confidence')
                },
                'timestamp': event.get('timestamp')
            }
            
            # Broadcast to clients
            await self.broadcast_to_clients(update_message)
            
            # Update analytics cache
            await self.update_analytics_cache(data)
            
            logger.info(f"📈 Analytics update broadcasted: {data.get('company')} - {data.get('metric_type')}")
            
        except Exception as e:
            logger.error(f"❌ Error processing analytics update: {e}")

    async def update_dashboard_cache(self, campaign: Dict[str, Any], event_type: str):
        """Update dashboard summary cache in Redis"""
        try:
            # Get current summary
            current_summary = await asyncio.to_thread(
                self.redis_client.get, 'dashboard:summary'
            )
            
            if current_summary:
                summary = json.loads(current_summary)
            else:
                summary = {
                    'total_campaigns': 0,
                    'active_campaigns': 0,
                    'total_companies': 0,
                    'avg_sentiment': 0.5,
                    'recent_events': []
                }
            
            # Update based on event type
            if event_type == 'created':
                summary['total_campaigns'] += 1
                if campaign.get('status') == 'active':
                    summary['active_campaigns'] += 1
            
            # Update recent events
            recent_event = {
                'company': campaign.get('company'),
                'event': event_type,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            summary['recent_events'].insert(0, recent_event)
            summary['recent_events'] = summary['recent_events'][:10]  # Keep last 10
            
            # Cache updated summary
            await asyncio.to_thread(
                self.redis_client.setex,
                'dashboard:summary',
                3600,  # 1 hour expiry
                json.dumps(summary)
            )
            
        except Exception as e:
            logger.error(f"❌ Error updating dashboard cache: {e}")

    async def update_analytics_cache(self, data: Dict[str, Any]):
        """Update analytics cache in Redis"""
        try:
            company = data.get('company')
            metric_type = data.get('metric_type')
            
            # Cache company-specific metrics
            cache_key = f"analytics:{company}:{metric_type}"
            
            analytics_data = {
                'value': data.get('value'),
                'trend': data.get('trend'),
                'confidence': data.get('confidence'),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            await asyncio.to_thread(
                self.redis_client.setex,
                cache_key,
                1800,  # 30 minutes expiry
                json.dumps(analytics_data)
            )
            
        except Exception as e:
            logger.error(f"❌ Error updating analytics cache: {e}")

    async def kafka_consumer_loop(self):
        """Main Kafka consumer loop"""
        logger.info("🔄 Starting Kafka consumer loop...")
        
        try:
            while True:
                try:
                    message_pack = self.kafka_consumer.poll(timeout_ms=1000)
                    
                    for topic_partition, messages in message_pack.items():
                        for message in messages:
                            topic = topic_partition.topic
                            event_data = message.value
                            
                            if topic == 'campaign-events':
                                await self.process_campaign_update(event_data)
                            elif topic == 'analytics-events':
                                await self.process_analytics_update(event_data)
                                
                except Exception as e:
                    logger.error(f"❌ Kafka consumer error: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"❌ Kafka consumer loop failed: {e}")

    async def websocket_handler(self, websocket, path):
        """Handle WebSocket connections"""
        await self.register_client(websocket)
        
        try:
            # Keep connection alive and handle client messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"📱 Invalid JSON from client: {message}")
                    
        except ConnectionClosedError:
            logger.info("📱 Client connection closed")
        finally:
            await self.unregister_client(websocket)

    async def handle_client_message(self, websocket: websockets.WebSocketServerProtocol, message: Dict[str, Any]):
        """Handle messages from WebSocket clients"""
        try:
            message_type = message.get('type')
            
            if message_type == 'ping':
                # Respond to ping with pong
                pong_response = {
                    'type': 'pong',
                    'timestamp': datetime.utcnow().isoformat()
                }
                await websocket.send(json.dumps(pong_response))
                
            elif message_type == 'get_summary':
                # Send current summary data
                await self.send_initial_data(websocket)
                
            else:
                logger.info(f"📱 Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"❌ Error handling client message: {e}")

    async def start_server(self):
        """Start the WebSocket server and Kafka consumer"""
        if not await self.initialize_services():
            return
        
        logger.info(f"🚀 Starting WebSocket server on port {self.websocket_port}")
        
        # Start WebSocket server
        websocket_server = websockets.serve(
            self.websocket_handler,
            "0.0.0.0",
            self.websocket_port
        )
        
        # Start both WebSocket server and Kafka consumer
        await asyncio.gather(
            websocket_server,
            self.kafka_consumer_loop()
        )

async def main():
    """Main entry point"""
    service = RealTimeAnalyticsService()
    
    try:
        await service.start_server()
    except KeyboardInterrupt:
        logger.info("⏹️  Shutting down analytics service...")
    except Exception as e:
        logger.error(f"❌ Service failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())