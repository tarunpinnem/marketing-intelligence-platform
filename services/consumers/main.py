import redis
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass

# Database imports
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DECIMAL, ARRAY, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Search imports
from elasticsearch import Elasticsearch

# AI imports
import openai
from textblob import TextBlob
import nltk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/competiscan')
ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SERVICE_TYPE = os.getenv('SERVICE_TYPE', 'parser')
STREAM_NAME = 'campaign_events'
CONSUMER_GROUP = f'competiscan_consumers_{SERVICE_TYPE}'

# Database setup
Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    industry = Column(String(100))
    website = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer)
    title = Column(String(500))
    subject_line = Column(String(500))
    campaign_type = Column(String(50))
    channel = Column(String(50))
    launch_date = Column(Date)
    content = Column(Text)
    keywords = Column(ARRAY(String))
    sentiment_score = Column(DECIMAL(3, 2))
    classification = Column(String(100))
    source = Column(String(50))
    processed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

@dataclass
class CampaignMessage:
    """Parsed campaign message from Redis stream"""
    event_type: str
    company: str
    industry: str
    channel: str
    title: str
    subject: str
    content: str
    keywords: List[str]
    date: str
    source: str
    published_at: str

class BaseConsumer(ABC):
    """Base consumer class for processing campaign events"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        self.consumer_name = f"{SERVICE_TYPE}_{os.getpid()}"
        
        # Create consumer group if it doesn't exist
        try:
            self.redis_client.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id='0', mkstream=True)
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise e
        
        logger.info(f"Consumer {self.consumer_name} initialized for group {CONSUMER_GROUP}")

    def parse_message(self, message_data: Dict[str, str]) -> CampaignMessage:
        """Parse Redis stream message into CampaignMessage"""
        
        keywords = json.loads(message_data.get('keywords', '[]'))
        
        return CampaignMessage(
            event_type=message_data['event_type'],
            company=message_data['company'],
            industry=message_data['industry'],
            channel=message_data['channel'],
            title=message_data['title'],
            subject=message_data['subject'],
            content=message_data['content'],
            keywords=keywords,
            date=message_data['date'],
            source=message_data['source'],
            published_at=message_data['published_at']
        )

    @abstractmethod
    def process_message(self, message: CampaignMessage) -> bool:
        """Process a campaign message - implemented by subclasses"""
        pass

    def run(self):
        """Main consumer loop"""
        
        logger.info(f"Starting {SERVICE_TYPE} consumer...")
        
        while True:
            try:
                # Read messages from stream
                messages = self.redis_client.xreadgroup(
                    CONSUMER_GROUP, 
                    self.consumer_name, 
                    {STREAM_NAME: '>'}, 
                    count=5, 
                    block=1000
                )
                
                if messages:
                    for stream_name, stream_messages in messages:
                        for message_id, message_data in stream_messages:
                            try:
                                # Parse message
                                campaign_message = self.parse_message(message_data)
                                
                                # Process message
                                success = self.process_message(campaign_message)
                                
                                if success:
                                    # Acknowledge message
                                    self.redis_client.xack(STREAM_NAME, CONSUMER_GROUP, message_id)
                                    logger.info(f"Processed message {message_id}")
                                else:
                                    logger.warning(f"Failed to process message {message_id}")
                                    
                            except Exception as e:
                                logger.error(f"Error processing message {message_id}: {e}")
                
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                time.sleep(5)

class ParserConsumer(BaseConsumer):
    """Consumer for parsing and enriching campaign data with AI"""
    
    def __init__(self):
        super().__init__()
        
        # Database setup
        self.engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = SessionLocal()
        
        # AI setup
        if OPENAI_API_KEY:
            openai.api_key = OPENAI_API_KEY
        
        # Download NLTK data if needed
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
            
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')

    def analyze_sentiment(self, content: str) -> float:
        """Analyze sentiment using TextBlob and OpenAI"""
        
        try:
            # Primary: TextBlob analysis (fast, offline)
            blob = TextBlob(content)
            textblob_sentiment = blob.sentiment.polarity
            
            # Secondary: OpenAI analysis (if API key available)
            if OPENAI_API_KEY and len(content) > 50:
                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{
                            "role": "user",
                            "content": f"Rate the sentiment of this marketing content on a scale from -1 (very negative) to 1 (very positive). Return only the numeric score: {content[:300]}"
                        }],
                        max_tokens=10,
                        temperature=0
                    )
                    
                    ai_sentiment = float(response.choices[0].message.content.strip())
                    # Blend TextBlob and AI scores
                    final_sentiment = (textblob_sentiment * 0.4) + (ai_sentiment * 0.6)
                    return max(-1.0, min(1.0, final_sentiment))
                    
                except Exception as e:
                    logger.warning(f"OpenAI sentiment analysis failed: {e}")
            
            return textblob_sentiment
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return 0.0

    def classify_campaign(self, content: str, keywords: List[str]) -> str:
        """Classify campaign type using content analysis"""
        
        content_lower = content.lower()
        keywords_lower = [k.lower() for k in keywords]
        
        # Rule-based classification
        promotional_indicators = ['offer', 'discount', 'sale', 'deal', 'limited time', 'exclusive', 'bonus', 'free', 'save', '%', 'off']
        educational_indicators = ['learn', 'guide', 'tips', 'how to', 'understand', 'benefits', 'help', 'discover', 'knowledge']
        retention_indicators = ['thank you', 'loyal', 'member', 'exclusive', 'valued customer', 'special', 'comeback', 'miss you']
        
        promo_score = sum(1 for indicator in promotional_indicators if indicator in content_lower)
        edu_score = sum(1 for indicator in educational_indicators if indicator in content_lower)
        retention_score = sum(1 for indicator in retention_indicators if indicator in content_lower)
        
        # Also check keywords
        promo_score += sum(1 for kw in keywords_lower if any(pi in kw for pi in promotional_indicators))
        edu_score += sum(1 for kw in keywords_lower if any(ei in kw for ei in educational_indicators))
        retention_score += sum(1 for kw in keywords_lower if any(ri in kw for ri in retention_indicators))
        
        if promo_score >= max(edu_score, retention_score):
            return "promotional"
        elif edu_score >= retention_score:
            return "educational"
        elif retention_score > 0:
            return "retention"
        else:
            return "informational"

    def extract_enhanced_keywords(self, content: str, existing_keywords: List[str]) -> List[str]:
        """Extract additional keywords from content"""
        
        try:
            # Use TextBlob for noun phrase extraction
            blob = TextBlob(content)
            noun_phrases = [str(phrase).lower() for phrase in blob.noun_phrases]
            
            # Filter relevant phrases
            enhanced_keywords = existing_keywords.copy()
            
            for phrase in noun_phrases:
                if (len(phrase.split()) <= 3 and 
                    len(phrase) > 3 and 
                    phrase not in [kw.lower() for kw in enhanced_keywords] and
                    any(char.isalpha() for char in phrase)):
                    enhanced_keywords.append(phrase.title())
            
            return enhanced_keywords[:10]  # Limit to 10 keywords
            
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            return existing_keywords

    def process_message(self, message: CampaignMessage) -> bool:
        """Process campaign message with AI parsing and enrichment"""
        
        try:
            logger.info(f"Processing campaign from {message.company}")
            
            # Get or create company
            company = self.db.query(Company).filter(Company.name == message.company).first()
            if not company:
                company = Company(
                    name=message.company,
                    industry=message.industry
                )
                self.db.add(company)
                self.db.commit()
                self.db.refresh(company)
            
            # Analyze content
            sentiment_score = self.analyze_sentiment(message.content)
            classification = self.classify_campaign(message.content, message.keywords)
            enhanced_keywords = self.extract_enhanced_keywords(message.content, message.keywords)
            
            # Parse launch date
            try:
                launch_date = datetime.fromisoformat(message.date.replace('Z', '+00:00')).date()
            except:
                launch_date = datetime.now().date()
            
            # Create campaign record
            campaign = Campaign(
                company_id=company.id,
                title=message.title,
                subject_line=message.subject,
                channel=message.channel,
                launch_date=launch_date,
                content=message.content,
                keywords=enhanced_keywords,
                sentiment_score=sentiment_score,
                classification=classification,
                source=message.source
            )
            
            self.db.add(campaign)
            self.db.commit()
            
            logger.info(f"Saved campaign {campaign.id} - Sentiment: {sentiment_score:.2f}, Type: {classification}")
            
            return True
            
        except Exception as e:
            logger.error(f"Parser processing failed: {e}")
            self.db.rollback()
            return False

class IndexerConsumer(BaseConsumer):
    """Consumer for indexing campaigns in Elasticsearch"""
    
    def __init__(self):
        super().__init__()
        self.es = Elasticsearch([ELASTICSEARCH_URL])
        
        # Create index if it doesn't exist
        self.create_index()

    def create_index(self):
        """Create Elasticsearch index with proper mapping"""
        
        mapping = {
            "mappings": {
                "properties": {
                    "company": {"type": "keyword"},
                    "industry": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "english",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "subject": {
                        "type": "text",
                        "analyzer": "english"
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "english"
                    },
                    "keywords": {
                        "type": "text",
                        "analyzer": "keyword"
                    },
                    "channel": {"type": "keyword"},
                    "date": {"type": "date"},
                    "source": {"type": "keyword"},
                    "indexed_at": {"type": "date"}
                }
            }
        }
        
        try:
            if not self.es.indices.exists(index="campaigns"):
                self.es.indices.create(index="campaigns", body=mapping)
                logger.info("Created Elasticsearch index 'campaigns'")
        except Exception as e:
            logger.warning(f"Failed to create ES index: {e}")

    def process_message(self, message: CampaignMessage) -> bool:
        """Index campaign in Elasticsearch"""
        
        try:
            doc = {
                "company": message.company,
                "industry": message.industry,
                "title": message.title,
                "subject": message.subject,
                "content": message.content,
                "keywords": " ".join(message.keywords),
                "channel": message.channel,
                "date": message.date,
                "source": message.source,
                "indexed_at": datetime.now().isoformat()
            }
            
            # Generate document ID from content hash for deduplication
            import hashlib
            doc_id = hashlib.md5(f"{message.company}_{message.title}_{message.date}".encode()).hexdigest()
            
            self.es.index(index="campaigns", id=doc_id, body=doc)
            logger.info(f"Indexed campaign {doc_id} for {message.company}")
            
            return True
            
        except Exception as e:
            logger.error(f"Indexer processing failed: {e}")
            return False

class NotifierConsumer(BaseConsumer):
    """Consumer for sending notifications about new campaigns"""
    
    def __init__(self):
        super().__init__()
        self.notification_rules = [
            {"company": "Chase Bank", "keywords": ["credit card", "bonus"], "action": "high_priority"},
            {"industry": "Finance", "keywords": ["APR", "0%"], "action": "track_offer"},
            {"channel": "Email", "sentiment_threshold": 0.8, "action": "positive_campaign"}
        ]

    def check_notification_rules(self, message: CampaignMessage) -> List[str]:
        """Check if message matches notification rules"""
        
        triggered_notifications = []
        
        for rule in self.notification_rules:
            match = True
            
            # Check company filter
            if "company" in rule and rule["company"] != message.company:
                match = False
            
            # Check industry filter
            if "industry" in rule and rule["industry"] != message.industry:
                match = False
            
            # Check keyword filter
            if "keywords" in rule:
                if not any(kw.lower() in [mk.lower() for mk in message.keywords] for kw in rule["keywords"]):
                    match = False
            
            # Check channel filter
            if "channel" in rule and rule["channel"] != message.channel:
                match = False
            
            if match:
                triggered_notifications.append(rule["action"])
        
        return triggered_notifications

    def send_notification(self, message: CampaignMessage, notifications: List[str]):
        """Send notification (simulate with logging)"""
        
        for notification_type in notifications:
            logger.info(f"🚨 NOTIFICATION [{notification_type}]: {message.company} launched '{message.title}' via {message.channel}")
            
            # In production, this would send:
            # - Email alerts
            # - Slack/Teams messages
            # - Webhook calls
            # - Database notifications

    def process_message(self, message: CampaignMessage) -> bool:
        """Process campaign for notifications"""
        
        try:
            triggered_notifications = self.check_notification_rules(message)
            
            if triggered_notifications:
                self.send_notification(message, triggered_notifications)
            
            return True
            
        except Exception as e:
            logger.error(f"Notifier processing failed: {e}")
            return False

def create_consumer(service_type: str) -> BaseConsumer:
    """Factory function to create appropriate consumer"""
    
    if service_type == "parser":
        return ParserConsumer()
    elif service_type == "indexer":
        return IndexerConsumer()
    elif service_type == "notifier":
        return NotifierConsumer()
    else:
        raise ValueError(f"Unknown service type: {service_type}")

def main():
    """Main consumer entry point"""
    
    logger.info(f"Starting {SERVICE_TYPE} consumer...")
    
    try:
        consumer = create_consumer(SERVICE_TYPE)
        consumer.run()
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error(f"Consumer failed: {e}")

if __name__ == "__main__":
    main()