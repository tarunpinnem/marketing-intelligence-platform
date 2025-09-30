import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from app.config import KAFKA_BOOTSTRAP_SERVERS, NEWS_API_KEY
import aiohttp

logger = logging.getLogger(__name__)

class KafkaStreaming:
    def __init__(self):
        self.producer = None
        self.consumer = None
        self.running = False
        
    async def start_producer(self):
        """Initialize Kafka producer"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        await self.producer.start()
        logger.info("✅ Kafka producer started")

    async def start_consumer(self):
        """Initialize Kafka consumer"""
        self.consumer = AIOKafkaConsumer(
            'campaign-updates',
            'news-feed',
            'analytics-updates',
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id='competiscan-backend',
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await self.consumer.start()
        logger.info("✅ Kafka consumer started")

    async def stop(self):
        """Stop Kafka producer and consumer"""
        self.running = False
        if self.producer:
            await self.producer.stop()
        if self.consumer:
            await self.consumer.stop()
        logger.info("🛑 Kafka streaming stopped")

    async def produce_news_data(self):
        """Fetch real news data and stream to Kafka"""
        if not self.producer:
            return
            
        try:
            # Fetch real news data from News API
            async with aiohttp.ClientSession() as session:
                # Business/marketing related news
                url = f"https://newsapi.org/v2/everything"
                params = {
                    'apiKey': NEWS_API_KEY,
                    'q': 'marketing OR advertising OR campaign OR "digital marketing" OR "social media marketing"',
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'pageSize': 10
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for article in data.get('articles', []):
                            # Transform news article into campaign-like data
                            campaign_data = {
                                'id': f"news_{hash(article['url'])}",
                                'title': article['title'],
                                'company': article['source']['name'],
                                'company_name': article['source']['name'],
                                'content': article['description'] or article['content'],
                                'subject_line': article['title'],
                                'channel': 'news',
                                'platform': 'digital',
                                'classification': 'media_coverage',
                                'launch_date': article['publishedAt'],
                                'url': article['url'],
                                'image_url': article.get('urlToImage'),
                                'status': 'active',
                                'timestamp': datetime.utcnow().isoformat(),
                                'metrics': {
                                    'impressions': hash(article['url']) % 50000 + 10000,  # Simulated based on source
                                    'clicks': hash(article['url']) % 5000 + 100,
                                    'ctr': (hash(article['url']) % 500) / 100 + 1.0,
                                    'sentiment_score': self._analyze_sentiment(article['title'] + ' ' + (article['description'] or '')),
                                    'conversions': hash(article['url']) % 500 + 10
                                },
                                'keywords': self._extract_keywords(article['title'] + ' ' + (article['description'] or ''))
                            }
                            
                            # Send to Kafka
                            await self.producer.send('campaign-updates', campaign_data)
                            logger.info(f"📰 Streamed news campaign: {campaign_data['title'][:50]}...")
                            
                            # Add delay to simulate real-time streaming
                            await asyncio.sleep(2)
                            
        except Exception as e:
            logger.error(f"❌ Error producing news data: {str(e)}")

    async def produce_social_media_data(self):
        """Simulate social media campaign data streaming"""
        if not self.producer:
            return
            
        try:
            # Simulate real social media campaigns
            social_platforms = ['Facebook', 'Instagram', 'Twitter', 'LinkedIn', 'TikTok']
            companies = ['Meta', 'Google', 'Microsoft', 'Apple', 'Amazon', 'Tesla', 'Netflix', 'Spotify', 'Nike', 'Coca-Cola']
            campaign_types = ['Brand Awareness', 'Lead Generation', 'Sales', 'Engagement', 'App Install', 'Video Views']
            
            while self.running:
                import random
                
                company = random.choice(companies)
                platform = random.choice(social_platforms)
                campaign_type = random.choice(campaign_types)
                
                campaign_data = {
                    'id': f"social_{datetime.utcnow().timestamp()}_{random.randint(1000, 9999)}",
                    'title': f"{company} {campaign_type} Campaign",
                    'company': company,
                    'company_name': company,
                    'content': f"Latest {campaign_type.lower()} campaign from {company} targeting key demographics with innovative {platform} strategy.",
                    'subject_line': f"New {campaign_type} Initiative",
                    'channel': 'social',
                    'platform': platform,
                    'classification': campaign_type.lower().replace(' ', '_'),
                    'launch_date': datetime.utcnow().isoformat(),
                    'status': random.choice(['active', 'paused', 'completed']),
                    'timestamp': datetime.utcnow().isoformat(),
                    'metrics': {
                        'impressions': random.randint(10000, 500000),
                        'clicks': random.randint(500, 25000),
                        'ctr': random.uniform(1.0, 8.0),
                        'sentiment_score': random.uniform(0.3, 0.9),
                        'conversions': random.randint(50, 2000),
                        'spend': random.uniform(1000, 50000)
                    },
                    'keywords': [f"{company.lower()}", f"{platform.lower()}", campaign_type.lower().split()[0]]
                }
                
                # Send to Kafka
                await self.producer.send('campaign-updates', campaign_data)
                logger.info(f"📱 Streamed social campaign: {company} on {platform}")
                
                # Random delay between 5-15 seconds
                await asyncio.sleep(random.uniform(5, 15))
                
        except Exception as e:
            logger.error(f"❌ Error producing social media data: {str(e)}")

    async def produce_analytics_data(self):
        """Stream real-time analytics updates"""
        if not self.producer:
            return
            
        try:
            companies = ['Meta', 'Google', 'Microsoft', 'Apple', 'Amazon']
            
            while self.running:
                import random
                
                company = random.choice(companies)
                metric_types = ['engagement_rate', 'conversion_rate', 'ctr', 'cpm', 'roas']
                
                for metric_type in metric_types:
                    analytics_data = {
                        'company': company,
                        'metric_type': metric_type,
                        'value': round(random.uniform(0.5, 15.0), 2),
                        'timestamp': datetime.utcnow().isoformat(),
                        'period': '1h',
                        'trend': random.choice(['up', 'down', 'stable'])
                    }
                    
                    await self.producer.send('analytics-updates', analytics_data)
                
                logger.info(f"📊 Streamed analytics for: {company}")
                await asyncio.sleep(30)  # Analytics every 30 seconds
                
        except Exception as e:
            logger.error(f"❌ Error producing analytics data: {str(e)}")

    def _analyze_sentiment(self, text: str) -> float:
        """Simple sentiment analysis - replace with proper NLP in production"""
        positive_words = ['good', 'great', 'excellent', 'amazing', 'success', 'win', 'best', 'top', 'innovative', 'growth']
        negative_words = ['bad', 'worst', 'fail', 'decline', 'loss', 'poor', 'terrible', 'crisis', 'drop', 'down']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return min(0.9, 0.6 + (positive_count - negative_count) * 0.1)
        elif negative_count > positive_count:
            return max(0.1, 0.4 - (negative_count - positive_count) * 0.1)
        else:
            return 0.5

    def _extract_keywords(self, text: str) -> list:
        """Extract keywords from text - replace with proper NLP in production"""
        import re
        
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        
        keywords = [word for word in words if len(word) > 3 and word not in common_words]
        return list(set(keywords[:5]))  # Return top 5 unique keywords

# Global instance
kafka_streaming = KafkaStreaming()