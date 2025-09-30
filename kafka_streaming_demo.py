#!/usr/bin/env python3
"""
Competiscan-Lite Standalone Event Streaming Demo
Demonstrates Kafka-style event streaming using in-memory queues
"""

import asyncio
import json
import logging
import random
import time
import websockets
import websockets.exceptions
from datetime import datetime, timedelta
from typing import Dict, List, Any
from uuid import uuid4
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

@dataclass
class CampaignEvent:
    """Campaign event data structure"""
    event_id: str
    event_type: str
    timestamp: str
    campaign: Dict[str, Any]

@dataclass
class AnalyticsEvent:
    """Analytics event data structure"""
    event_id: str
    event_type: str
    timestamp: str
    data: Dict[str, Any]

class EventBus:
    """In-memory event streaming bus (simulates Kafka)"""
    
    def __init__(self):
        self.campaign_queue = Queue()
        self.analytics_queue = Queue()
        self.subscribers = {}
        self.running = True
        self.stats = {
            'campaign_events': 0,
            'analytics_events': 0,
            'processed_events': 0
        }

    def publish_campaign_event(self, event: CampaignEvent):
        """Publish campaign event to bus"""
        self.campaign_queue.put(event)
        self.stats['campaign_events'] += 1
        logger.info(f"📧 Published: {event.event_type} - {event.campaign['company']}")

    def publish_analytics_event(self, event: AnalyticsEvent):
        """Publish analytics event to bus"""
        self.analytics_queue.put(event)
        self.stats['analytics_events'] += 1
        logger.info(f"📊 Published: {event.event_type} - {event.data['company']}")

    def subscribe(self, topic: str, callback):
        """Subscribe to event topic"""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)
        logger.info(f"📝 Subscribed to {topic}")

    async def start_processing(self):
        """Start event processing loop"""
        logger.info("🚀 Event bus processing started")
        
        while self.running:
            # Process campaign events
            while not self.campaign_queue.empty():
                event = self.campaign_queue.get()
                for callback in self.subscribers.get('campaigns', []):
                    try:
                        await callback(event)
                        self.stats['processed_events'] += 1
                    except Exception as e:
                        logger.error(f"❌ Event processing error: {e}")

            # Process analytics events
            while not self.analytics_queue.empty():
                event = self.analytics_queue.get()
                for callback in self.subscribers.get('analytics', []):
                    try:
                        await callback(event)
                        self.stats['processed_events'] += 1
                    except Exception as e:
                        logger.error(f"❌ Event processing error: {e}")

            await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

    def stop(self):
        """Stop event processing"""
        self.running = False
        logger.info("⏹️ Event bus stopped")

class DataStreamer:
    """Simulates real-time data streaming"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.running = True
        
        # Sample data
        self.companies = [
            "Apple Inc.", "Microsoft", "Google", "Amazon", "Meta", "Tesla",
            "Nike", "Coca-Cola", "McDonald's", "Disney", "Netflix", "Spotify"
        ]
        
        self.platforms = ["Facebook", "Instagram", "Twitter", "LinkedIn", "YouTube", "TikTok"]
        
        self.campaign_types = [
            "Brand Awareness", "Product Launch", "Lead Generation", "Retargeting",
            "Influencer Campaign", "Content Marketing", "Holiday Promotion"
        ]

    def generate_campaign_event(self, event_type: str = None) -> CampaignEvent:
        """Generate realistic campaign event"""
        if not event_type:
            event_type = random.choice(['created', 'updated', 'launched', 'paused', 'completed'])
        
        company = random.choice(self.companies)
        
        # Generate realistic metrics
        impressions = random.randint(5000, 500000)
        clicks = int(impressions * random.uniform(0.01, 0.08))
        conversions = int(clicks * random.uniform(0.02, 0.15))
        
        campaign = {
            'id': str(uuid4()),
            'company': company,
            'name': f"{company} - {random.choice(self.campaign_types)}",
            'platform': random.choice(self.platforms),
            'status': random.choice(['active', 'paused', 'draft']),
            'budget': random.randint(5000, 100000),
            'start_date': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            'end_date': (datetime.now() + timedelta(days=random.randint(1, 60))).isoformat(),
            'metrics': {
                'impressions': impressions,
                'clicks': clicks,
                'conversions': conversions,
                'spend': round(random.uniform(100, 50000), 2),
                'ctr': round((clicks / impressions) * 100, 2),
                'cpc': round(random.uniform(0.5, 5.0), 2),
                'sentiment_score': round(random.uniform(0.3, 0.95), 2)
            }
        }
        
        return CampaignEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            campaign=campaign
        )

    def generate_analytics_event(self, event_type: str = None) -> AnalyticsEvent:
        """Generate analytics event"""
        if not event_type:
            event_type = random.choice(['engagement_update', 'conversion_tracked', 'sentiment_change'])
        
        data = {
            'company': random.choice(self.companies),
            'metric_type': random.choice(['engagement', 'conversion', 'sentiment', 'reach']),
            'value': round(random.uniform(0.1, 100.0), 2),
            'trend': random.choice(['increasing', 'decreasing', 'stable']),
            'confidence': round(random.uniform(0.7, 0.99), 2),
            'source': random.choice(['social_media', 'web_analytics', 'survey'])
        }
        
        return AnalyticsEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            data=data
        )

    async def start_streaming(self):
        """Start data streaming"""
        logger.info("🌊 Data streaming started")
        
        while self.running:
            try:
                # Generate campaign event every 3-6 seconds
                if random.random() < 0.7:  # 70% chance
                    event = self.generate_campaign_event()
                    self.event_bus.publish_campaign_event(event)
                
                # Generate analytics event every 2-4 seconds
                if random.random() < 0.8:  # 80% chance
                    event = self.generate_analytics_event()
                    self.event_bus.publish_analytics_event(event)
                
                await asyncio.sleep(random.uniform(2, 6))
                
            except Exception as e:
                logger.error(f"❌ Streaming error: {e}")
                await asyncio.sleep(1)

    def stop(self):
        """Stop data streaming"""
        self.running = False
        logger.info("⏹️ Data streaming stopped")

class RealTimeDashboard:
    """Real-time dashboard with WebSocket support"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.connected_clients = set()
        self.campaigns = []
        self.analytics_summary = {
            'total_campaigns': 0,
            'active_campaigns': 0,
            'total_companies': len(set()),
            'avg_sentiment': 0.5
        }
        
        # Subscribe to events
        self.event_bus.subscribe('campaigns', self.handle_campaign_event)
        self.event_bus.subscribe('analytics', self.handle_analytics_event)

    async def handle_campaign_event(self, event: CampaignEvent):
        """Process campaign events"""
        campaign = event.campaign
        
        # Update campaigns list
        existing_idx = next((i for i, c in enumerate(self.campaigns) if c['id'] == campaign['id']), None)
        
        if existing_idx is not None:
            self.campaigns[existing_idx] = campaign
        else:
            self.campaigns.insert(0, campaign)
            self.campaigns = self.campaigns[:50]  # Keep latest 50
            
            if event.event_type == 'created':
                self.analytics_summary['total_campaigns'] += 1
                if campaign.get('status') == 'active':
                    self.analytics_summary['active_campaigns'] += 1

        # Broadcast to WebSocket clients
        await self.broadcast_update({
            'type': 'campaign_update',
            'event_type': event.event_type,
            'data': campaign,
            'timestamp': event.timestamp
        })

    async def handle_analytics_event(self, event: AnalyticsEvent):
        """Process analytics events"""
        # Broadcast analytics update
        await self.broadcast_update({
            'type': 'analytics_update',
            'event_type': event.event_type,
            'data': event.data,
            'timestamp': event.timestamp
        })

    async def broadcast_update(self, message: Dict[str, Any]):
        """Broadcast update to all connected WebSocket clients"""
        if not self.connected_clients:
            return
        
        message_str = json.dumps(message)
        disconnected = set()
        
        for client in self.connected_clients.copy():
            try:
                await client.send(message_str)
            except Exception:
                disconnected.add(client)
        
        # Remove disconnected clients
        self.connected_clients -= disconnected

    async def websocket_handler(self, websocket):
        """Handle WebSocket connections"""
        self.connected_clients.add(websocket)
        logger.info(f"📱 WebSocket connected. Active: {len(self.connected_clients)}")
        
        try:
            # Send initial data
            await websocket.send(json.dumps({
                'type': 'initial_data',
                'campaigns': self.campaigns[:10],
                'summary': self.analytics_summary,
                'timestamp': datetime.now().isoformat()
            }))
            
            # Keep connection alive
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get('type') == 'ping':
                        await websocket.send(json.dumps({'type': 'pong'}))
                except json.JSONDecodeError:
                    pass
                    
        except websockets.exceptions.ConnectionClosedError:
            pass
        except Exception as e:
            logger.error(f"❌ WebSocket error: {e}")
        finally:
            self.connected_clients.discard(websocket)
            logger.info(f"📱 WebSocket disconnected. Active: {len(self.connected_clients)}")

class CompetiscanStreaming:
    """Main application orchestrator"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self.data_streamer = DataStreamer(self.event_bus)
        self.dashboard = RealTimeDashboard(self.event_bus)
        self.websocket_server = None
        self.running = True

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("🛑 Shutdown signal received...")
        self.running = False
        self.event_bus.stop()
        self.data_streamer.stop()
        
        if self.websocket_server:
            self.websocket_server.close()
        
        logger.info("✅ Competiscan streaming stopped")
        sys.exit(0)

    async def start_services(self):
        """Start all services"""
        logger.info("🚀 Starting Competiscan Event Streaming System...")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Start WebSocket server
        self.websocket_server = await websockets.serve(
            self.dashboard.websocket_handler,
            "localhost",
            8765
        )
        logger.info("🔗 WebSocket server started on ws://localhost:8765")
        
        # Start all services concurrently
        await asyncio.gather(
            self.event_bus.start_processing(),
            self.data_streamer.start_streaming(),
            self.monitor_stats()
        )

    async def monitor_stats(self):
        """Monitor and display system statistics"""
        while self.running:
            await asyncio.sleep(30)  # Every 30 seconds
            
            stats = self.event_bus.stats
            logger.info(
                f"📊 Stats: Campaign Events: {stats['campaign_events']}, "
                f"Analytics Events: {stats['analytics_events']}, "
                f"Processed: {stats['processed_events']}, "
                f"WebSocket Clients: {len(self.dashboard.connected_clients)}"
            )

def main():
    """Main entry point"""
    print("🌊 Competiscan-Lite Event Streaming Demo")
    print("=" * 50)
    print("🔗 WebSocket Dashboard: ws://localhost:8765")
    print("📊 Real-time campaign and analytics streaming")
    print("⏹️  Press Ctrl+C to stop")
    print("=" * 50)
    
    app = CompetiscanStreaming()
    
    try:
        asyncio.run(app.start_services())
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")
    except Exception as e:
        logger.error(f"❌ Application error: {e}")

if __name__ == "__main__":
    main()