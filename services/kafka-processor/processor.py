"""
Kafka Stream Processor for Competiscan-Lite
Processes campaign and analytics events in real-time
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List

import psycopg2
from psycopg2.extras import RealDictCursor
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from elasticsearch import Elasticsearch
import openai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompetiscanStreamProcessor:
    def __init__(self):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.consumer_group = os.getenv('KAFKA_CONSUMER_GROUP', 'campaign-processor')
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/competiscan')
        self.elasticsearch_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
        
        # Initialize clients
        self.consumer = None
        self.db_conn = None
        self.es_client = None
        self.openai_client = None
        
        # Processing statistics
        self.processed_events = 0
        self.processing_errors = 0

    async def initialize_clients(self):
        """Initialize all service clients"""
        try:
            # Kafka Consumer
            self.consumer = KafkaConsumer(
                'campaign-events',
                'analytics-events',
                bootstrap_servers=self.bootstrap_servers.split(','),
                group_id=self.consumer_group,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                consumer_timeout_ms=1000
            )
            
            # PostgreSQL Connection
            self.db_conn = psycopg2.connect(self.database_url)
            self.db_conn.autocommit = True
            
            # Elasticsearch Client
            self.es_client = Elasticsearch([self.elasticsearch_url])
            
            # OpenAI Client (if API key provided)
            if os.getenv('OPENAI_API_KEY'):
                openai.api_key = os.getenv('OPENAI_API_KEY')
                self.openai_client = openai
            
            logger.info("✅ All clients initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize clients: {e}")
            return False

    async def process_campaign_event(self, event: Dict[str, Any]):
        """Process campaign-related events"""
        try:
            event_type = event.get('event_type')
            campaign = event.get('campaign', {})
            
            logger.info(f"🔄 Processing campaign event: {event_type} - {campaign.get('company')}")
            
            # Store in PostgreSQL
            await self.store_campaign_in_db(campaign, event_type)
            
            # Index in Elasticsearch for searching
            await self.index_campaign_in_es(campaign, event)
            
            # AI-powered sentiment analysis (if OpenAI available)
            if self.openai_client and 'content' in campaign:
                await self.analyze_campaign_sentiment(campaign)
            
            # Update real-time metrics
            await self.update_campaign_metrics(campaign)
            
            self.processed_events += 1
            
        except Exception as e:
            logger.error(f"❌ Error processing campaign event: {e}")
            self.processing_errors += 1

    async def process_analytics_event(self, event: Dict[str, Any]):
        """Process analytics-related events"""
        try:
            event_type = event.get('event_type')
            data = event.get('data', {})
            
            logger.info(f"📊 Processing analytics event: {event_type} - {data.get('company')}")
            
            # Store analytics data
            await self.store_analytics_in_db(data, event_type)
            
            # Update real-time dashboards
            await self.update_realtime_metrics(data)
            
            # Trigger alerts if needed
            await self.check_alert_conditions(data)
            
            self.processed_events += 1
            
        except Exception as e:
            logger.error(f"❌ Error processing analytics event: {e}")
            self.processing_errors += 1

    async def store_campaign_in_db(self, campaign: Dict[str, Any], event_type: str):
        """Store campaign data in PostgreSQL"""
        try:
            cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            
            # Upsert campaign data
            upsert_query = """
            INSERT INTO campaigns (
                id, company, name, platform, status, budget, 
                start_date, end_date, created_at, updated_at,
                impressions, clicks, conversions, spend, ctr, cpc, sentiment_score
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO UPDATE SET
                company = EXCLUDED.company,
                name = EXCLUDED.name,
                platform = EXCLUDED.platform,
                status = EXCLUDED.status,
                budget = EXCLUDED.budget,
                updated_at = EXCLUDED.updated_at,
                impressions = EXCLUDED.impressions,
                clicks = EXCLUDED.clicks,
                conversions = EXCLUDED.conversions,
                spend = EXCLUDED.spend,
                ctr = EXCLUDED.ctr,
                cpc = EXCLUDED.cpc,
                sentiment_score = EXCLUDED.sentiment_score
            """
            
            metrics = campaign.get('metrics', {})
            cursor.execute(upsert_query, (
                campaign.get('id'),
                campaign.get('company'),
                campaign.get('name'),
                campaign.get('platform'),
                campaign.get('status'),
                campaign.get('budget'),
                campaign.get('start_date'),
                campaign.get('end_date'),
                datetime.utcnow() if event_type == 'created' else None,
                datetime.utcnow(),
                metrics.get('impressions', 0),
                metrics.get('clicks', 0),
                metrics.get('conversions', 0),
                metrics.get('spend', 0.0),
                metrics.get('ctr', 0.0),
                metrics.get('cpc', 0.0),
                metrics.get('sentiment_score', 0.5)
            ))
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"❌ Database storage error: {e}")

    async def index_campaign_in_es(self, campaign: Dict[str, Any], event: Dict[str, Any]):
        """Index campaign data in Elasticsearch"""
        try:
            doc = {
                'campaign_id': campaign.get('id'),
                'company': campaign.get('company'),
                'name': campaign.get('name'),
                'platform': campaign.get('platform'),
                'status': campaign.get('status'),
                'budget': campaign.get('budget'),
                'content': campaign.get('content', {}),
                'metrics': campaign.get('metrics', {}),
                'target_audience': campaign.get('target_audience', {}),
                'indexed_at': datetime.utcnow().isoformat(),
                'event_type': event.get('event_type')
            }
            
            self.es_client.index(
                index='campaigns',
                id=campaign.get('id'),
                body=doc
            )
            
        except Exception as e:
            logger.error(f"❌ Elasticsearch indexing error: {e}")

    async def analyze_campaign_sentiment(self, campaign: Dict[str, Any]):
        """AI-powered sentiment analysis using OpenAI"""
        try:
            content = campaign.get('content', {})
            text_to_analyze = f"{content.get('headline', '')} {content.get('description', '')}"
            
            if not text_to_analyze.strip():
                return
            
            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "Analyze the sentiment of this marketing campaign content. Return a JSON with sentiment score (0-1) and category (positive/negative/neutral)."
                    },
                    {"role": "user", "content": text_to_analyze}
                ],
                max_tokens=100
            )
            
            # Parse AI response and update campaign
            ai_result = json.loads(response.choices[0].message.content)
            campaign['ai_sentiment'] = ai_result
            
        except Exception as e:
            logger.error(f"❌ AI sentiment analysis error: {e}")

    async def store_analytics_in_db(self, data: Dict[str, Any], event_type: str):
        """Store analytics data in PostgreSQL"""
        try:
            cursor = self.db_conn.cursor()
            
            insert_query = """
            INSERT INTO analytics_events (
                company, metric_type, value, trend, confidence, 
                source, event_type, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                data.get('company'),
                data.get('metric_type'),
                data.get('value'),
                data.get('trend'),
                data.get('confidence'),
                data.get('source'),
                event_type,
                datetime.utcnow()
            ))
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"❌ Analytics storage error: {e}")

    async def update_campaign_metrics(self, campaign: Dict[str, Any]):
        """Update aggregated campaign metrics"""
        try:
            cursor = self.db_conn.cursor()
            
            # Update company-level aggregations
            update_query = """
            INSERT INTO company_metrics (
                company, total_campaigns, total_spend, total_impressions,
                avg_ctr, avg_sentiment, updated_at
            ) VALUES (%s, 1, %s, %s, %s, %s, %s)
            ON CONFLICT (company) DO UPDATE SET
                total_campaigns = company_metrics.total_campaigns + 1,
                total_spend = company_metrics.total_spend + EXCLUDED.total_spend,
                total_impressions = company_metrics.total_impressions + EXCLUDED.total_impressions,
                avg_ctr = (company_metrics.avg_ctr + EXCLUDED.avg_ctr) / 2,
                avg_sentiment = (company_metrics.avg_sentiment + EXCLUDED.avg_sentiment) / 2,
                updated_at = EXCLUDED.updated_at
            """
            
            metrics = campaign.get('metrics', {})
            cursor.execute(update_query, (
                campaign.get('company'),
                metrics.get('spend', 0),
                metrics.get('impressions', 0),
                metrics.get('ctr', 0),
                metrics.get('sentiment_score', 0.5),
                datetime.utcnow()
            ))
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"❌ Metrics update error: {e}")

    async def update_realtime_metrics(self, data: Dict[str, Any]):
        """Update real-time analytics metrics"""
        try:
            # This would typically push to Redis or WebSocket for real-time updates
            logger.info(f"📈 Real-time update: {data.get('company')} - {data.get('metric_type')}: {data.get('value')}")
            
        except Exception as e:
            logger.error(f"❌ Real-time update error: {e}")

    async def check_alert_conditions(self, data: Dict[str, Any]):
        """Check if analytics data triggers any alerts"""
        try:
            # Example alert conditions
            if data.get('metric_type') == 'conversion' and data.get('value', 0) > 95:
                logger.warning(f"🚨 HIGH CONVERSION ALERT: {data.get('company')} - {data.get('value')}%")
            
            if data.get('metric_type') == 'sentiment' and data.get('value', 1) < 0.3:
                logger.warning(f"🚨 LOW SENTIMENT ALERT: {data.get('company')} - {data.get('value')}")
                
        except Exception as e:
            logger.error(f"❌ Alert checking error: {e}")

    async def start_processing(self):
        """Start the stream processing"""
        if not await self.initialize_clients():
            return
        
        logger.info("🚀 Starting Kafka stream processing...")
        
        try:
            while True:
                try:
                    message_pack = self.consumer.poll(timeout_ms=1000)
                    
                    for topic_partition, messages in message_pack.items():
                        for message in messages:
                            topic = topic_partition.topic
                            
                            if topic == 'campaign-events':
                                await self.process_campaign_event(message.value)
                            elif topic == 'analytics-events':
                                await self.process_analytics_event(message.value)
                    
                    # Log processing statistics every 100 events
                    if self.processed_events % 100 == 0 and self.processed_events > 0:
                        logger.info(f"📊 Processed: {self.processed_events} events, Errors: {self.processing_errors}")
                        
                except Exception as e:
                    logger.error(f"❌ Processing error: {e}")
                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("⏹️  Stopping stream processing...")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        if self.consumer:
            self.consumer.close()
        if self.db_conn:
            self.db_conn.close()
        logger.info("✅ Stream processor cleaned up")

async def main():
    """Main entry point"""
    processor = CompetiscanStreamProcessor()
    
    try:
        await processor.start_processing()
    except Exception as e:
        logger.error(f"❌ Processor failed: {e}")
    finally:
        await processor.cleanup()

if __name__ == "__main__":
    asyncio.run(main())