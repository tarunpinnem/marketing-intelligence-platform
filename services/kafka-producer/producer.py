"""
Kafka Data Producer for Competiscan-Lite
Simulates real-time campaign data streaming from various sources
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
from uuid import uuid4

import aiohttp
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompetiscanKafkaProducer:
    def __init__(self):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.topic_campaigns = os.getenv('KAFKA_TOPIC_CAMPAIGNS', 'campaign-events')
        self.topic_analytics = os.getenv('KAFKA_TOPIC_ANALYTICS', 'analytics-events')
        
        self.producer = None
        self.running = False
        
        # Sample data templates for realistic streaming
        self.companies = [
            "Apple Inc.", "Microsoft", "Google", "Amazon", "Meta", "Tesla", 
            "Nike", "Coca-Cola", "McDonald's", "Disney", "Netflix", "Spotify",
            "Uber", "Airbnb", "Shopify", "Zoom", "Slack", "Adobe", "Salesforce",
            "Chase Bank", "Wells Fargo", "American Express", "Visa", "Mastercard"
        ]
        
        self.campaign_types = [
            "Social Media Campaign", "Email Marketing", "PPC Advertising", 
            "Content Marketing", "Influencer Partnership", "TV Commercial",
            "Radio Advertisement", "Billboard Campaign", "Sponsored Content",
            "Product Launch", "Brand Awareness", "Retargeting Campaign"
        ]
        
        self.platforms = [
            "Facebook", "Instagram", "Twitter", "LinkedIn", "TikTok", "YouTube",
            "Google Ads", "Amazon Ads", "Spotify", "Pandora", "Hulu", "Netflix"
        ]
        
        self.keywords = [
            "innovation", "quality", "affordable", "premium", "sustainable",
            "digital transformation", "AI-powered", "customer-focused", "breakthrough",
            "revolutionary", "trusted", "reliable", "cutting-edge", "user-friendly"
        ]

    async def initialize_producer(self):
        """Initialize Kafka producer with retry logic"""
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers.split(','),
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    retries=3,
                    batch_size=16384,
                    linger_ms=10,
                    compression_type='gzip'
                )
                
                # Test connection
                future = self.producer.send('test-topic', {'test': 'connection'})
                future.get(timeout=10)
                
                logger.info(f"✅ Kafka producer connected to {self.bootstrap_servers}")
                return True
                
            except Exception as e:
                logger.warning(f"❌ Kafka connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to Kafka after all retries")
                    return False

    def generate_campaign_event(self) -> Dict[str, Any]:
        """Generate realistic campaign event data"""
        event_types = ['created', 'updated', 'launched', 'paused', 'completed', 'metrics_updated']
        
        campaign = {
            'event_id': str(uuid4()),
            'event_type': random.choice(event_types),
            'timestamp': datetime.utcnow().isoformat(),
            'campaign': {
                'id': str(uuid4()),
                'company': random.choice(self.companies),
                'name': f"{random.choice(self.campaign_types)} - {random.choice(self.keywords).title()}",
                'platform': random.choice(self.platforms),
                'status': random.choice(['active', 'paused', 'draft', 'completed']),
                'budget': random.randint(1000, 100000),
                'start_date': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                'end_date': (datetime.now() + timedelta(days=random.randint(1, 90))).isoformat(),
                'target_audience': {
                    'demographics': random.choice(['18-25', '26-35', '36-50', '50+']),
                    'interests': random.sample(self.keywords, k=random.randint(2, 4)),
                    'location': random.choice(['Global', 'US', 'EU', 'APAC'])
                },
                'metrics': {
                    'impressions': random.randint(1000, 1000000),
                    'clicks': random.randint(10, 50000),
                    'conversions': random.randint(1, 5000),
                    'spend': round(random.uniform(100, 50000), 2),
                    'ctr': round(random.uniform(0.5, 15.0), 2),
                    'cpc': round(random.uniform(0.10, 5.0), 2),
                    'sentiment_score': round(random.uniform(0.1, 1.0), 2)
                },
                'content': {
                    'headline': f"Discover {random.choice(self.keywords)} {random.choice(['solutions', 'products', 'services'])}",
                    'description': f"Join thousands who trust our {random.choice(self.keywords)} approach to {random.choice(['innovation', 'quality', 'excellence'])}",
                    'call_to_action': random.choice(['Learn More', 'Shop Now', 'Sign Up', 'Get Started', 'Try Free'])
                }
            }
        }
        
        return campaign

    def generate_analytics_event(self) -> Dict[str, Any]:
        """Generate real-time analytics events"""
        event_types = ['user_engagement', 'conversion_tracked', 'sentiment_updated', 'competitor_detected']
        
        analytics = {
            'event_id': str(uuid4()),
            'event_type': random.choice(event_types),
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'company': random.choice(self.companies),
                'metric_type': random.choice(['engagement', 'conversion', 'sentiment', 'reach']),
                'value': round(random.uniform(0.1, 100.0), 2),
                'trend': random.choice(['increasing', 'decreasing', 'stable']),
                'confidence': round(random.uniform(0.7, 0.99), 2),
                'source': random.choice(['social_media', 'web_scraping', 'api_feed', 'user_generated'])
            }
        }
        
        return analytics

    async def send_campaign_event(self):
        """Send campaign event to Kafka"""
        try:
            event = self.generate_campaign_event()
            
            future = self.producer.send(
                self.topic_campaigns,
                key=event['campaign']['id'],
                value=event
            )
            
            # Wait for send to complete
            record_metadata = future.get(timeout=10)
            
            logger.info(f"📧 Campaign event sent: {event['event_type']} - {event['campaign']['company']}")
            return True
            
        except KafkaError as e:
            logger.error(f"❌ Failed to send campaign event: {e}")
            return False

    async def send_analytics_event(self):
        """Send analytics event to Kafka"""
        try:
            event = self.generate_analytics_event()
            
            future = self.producer.send(
                self.topic_analytics,
                key=event['data']['company'],
                value=event
            )
            
            record_metadata = future.get(timeout=10)
            
            logger.info(f"📊 Analytics event sent: {event['event_type']} - {event['data']['company']}")
            return True
            
        except KafkaError as e:
            logger.error(f"❌ Failed to send analytics event: {e}")
            return False

    async def start_streaming(self):
        """Start the data streaming process"""
        if not await self.initialize_producer():
            return
        
        self.running = True
        logger.info("🚀 Starting Kafka data streaming...")
        
        try:
            while self.running:
                # Send campaign events every 3-8 seconds
                await self.send_campaign_event()
                await asyncio.sleep(random.uniform(3, 8))
                
                # Send analytics events every 2-5 seconds  
                await self.send_analytics_event()
                await asyncio.sleep(random.uniform(2, 5))
                
                # Batch send every 10 events
                if random.randint(1, 10) == 1:
                    logger.info("🔄 Flushing producer buffer...")
                    self.producer.flush()
                    
        except KeyboardInterrupt:
            logger.info("⏹️  Stopping data streaming...")
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        self.running = False
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("✅ Kafka producer closed")

async def main():
    """Main entry point"""
    producer = CompetiscanKafkaProducer()
    
    try:
        await producer.start_streaming()
    except Exception as e:
        logger.error(f"❌ Producer failed: {e}")
    finally:
        await producer.cleanup()

if __name__ == "__main__":
    asyncio.run(main())