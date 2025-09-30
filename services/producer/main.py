import redis
import json
import time
import logging
import schedule
import random
from datetime import datetime, timedelta
from faker import Faker
from typing import Dict, List
import os
from dataclasses import dataclass
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
STREAM_NAME = 'campaign_events'

@dataclass
class CampaignEvent:
    """Campaign event data structure"""
    event_type: str
    company: str
    industry: str
    channel: str
    title: str
    subject: str
    content: str
    keywords: List[str]
    date: str
    source: str = "synthetic"

class SyntheticDataGenerator:
    """Generates realistic marketing campaign data"""
    
    def __init__(self):
        self.fake = Faker()
        
        # Industry-specific companies and keywords
        self.companies_data = {
            "Finance": {
                "companies": ["Chase Bank", "Capital One", "American Express", "Wells Fargo", "Discover", "Bank of America", "Citibank"],
                "keywords": ["credit card", "cash back", "rewards", "APR", "balance transfer", "bonus points", "no annual fee", "travel rewards", "cashback", "0% interest"]
            },
            "E-commerce": {
                "companies": ["Amazon", "eBay", "Shopify", "Target", "Walmart", "Best Buy", "Costco"],
                "keywords": ["free shipping", "discount", "sale", "clearance", "exclusive deal", "limited time", "buy now", "save money", "special offer", "flash sale"]
            },
            "Technology": {
                "companies": ["Apple", "Google", "Microsoft", "Samsung", "Netflix", "Spotify", "Adobe"],
                "keywords": ["cloud storage", "subscription", "premium features", "upgrade", "security", "innovation", "AI-powered", "smart technology", "connectivity", "productivity"]
            },
            "Travel": {
                "companies": ["Expedia", "Booking.com", "Airbnb", "Delta Airlines", "Southwest", "Marriott", "Hilton"],
                "keywords": ["vacation deals", "flight discounts", "hotel rewards", "travel insurance", "destination", "adventure", "getaway", "booking bonus", "loyalty program", "explore"]
            },
            "Food & Beverage": {
                "companies": ["McDonald's", "Starbucks", "DoorDash", "Uber Eats", "Domino's", "Chipotle", "KFC"],
                "keywords": ["food delivery", "mobile order", "loyalty rewards", "new menu", "limited time offer", "combo deal", "fresh ingredients", "convenience", "satisfaction guarantee", "taste"]
            }
        }
        
        self.channels = ["Email", "Social Media", "Display Ads", "Search Ads", "Push Notification", "SMS"]
        
        self.campaign_templates = {
            "promotional": [
                "Limited Time: {offer} - Act Now!",
                "Exclusive {offer} for You!",
                "Don't Miss Out: {offer} Ends Soon",
                "Special {offer} - Today Only!",
                "Get {offer} Before It's Gone"
            ],
            "educational": [
                "Learn About {topic} Benefits",
                "5 Tips for Better {topic}",
                "Understanding {topic}: A Guide",
                "How {topic} Can Help You",
                "The Ultimate {topic} Resource"
            ],
            "retention": [
                "We Miss You - Come Back for {offer}",
                "Your {benefit} is Waiting",
                "Exclusive Member {offer}",
                "Thank You for Being Loyal",
                "Special Offer Just for You"
            ]
        }

    def generate_campaign(self) -> CampaignEvent:
        """Generate a single realistic campaign event"""
        
        # Select random industry and company
        industry = random.choice(list(self.companies_data.keys()))
        company_info = self.companies_data[industry]
        company = random.choice(company_info["companies"])
        
        # Select campaign type and template
        campaign_type = random.choice(["promotional", "educational", "retention"])
        template = random.choice(self.campaign_templates[campaign_type])
        
        # Generate context-specific content
        keywords = random.sample(company_info["keywords"], random.randint(3, 6))
        primary_keyword = keywords[0]
        
        if campaign_type == "promotional":
            offers = ["50% Off", "Buy One Get One Free", "Free Trial", "Cashback Bonus", "No Fees for 12 Months"]
            subject = template.format(offer=random.choice(offers))
            content_focus = f"Take advantage of our {random.choice(offers).lower()} promotion"
        elif campaign_type == "educational":
            subject = template.format(topic=primary_keyword.title())
            content_focus = f"Learn how {primary_keyword} can benefit you"
        else:  # retention
            benefits = ["exclusive rewards", "premium benefits", "loyalty points", "special privileges"]
            subject = template.format(offer=random.choice(offers) if 'offer' in template else '', 
                                    benefit=random.choice(benefits))
            content_focus = f"We value your loyalty and want to offer you {random.choice(benefits)}"
        
        # Generate realistic content
        content = self._generate_content(company, primary_keyword, content_focus, campaign_type)
        
        # Create event
        event = CampaignEvent(
            event_type="new_campaign",
            company=company,
            industry=industry,
            channel=random.choice(self.channels),
            title=f"{company} - {campaign_type.title()} Campaign",
            subject=subject,
            content=content,
            keywords=keywords,
            date=self._random_recent_date().isoformat(),
            source="synthetic_generator"
        )
        
        return event

    def _generate_content(self, company: str, keyword: str, focus: str, campaign_type: str) -> str:
        """Generate realistic campaign content"""
        
        intro_templates = [
            f"Dear Valued Customer,",
            f"Hi there!",
            f"Exclusive for {company} members:",
            f"Important update from {company}:",
            f"You're invited to discover:"
        ]
        
        cta_templates = [
            "Click here to learn more",
            "Apply now - it only takes minutes",
            "Don't wait - this offer expires soon",
            "Get started today",
            "Claim your offer now"
        ]
        
        intro = random.choice(intro_templates)
        cta = random.choice(cta_templates)
        
        content = f"{intro}\n\n{focus}. Our {keyword} solution is designed to provide you with exceptional value and convenience.\n\n"
        
        if campaign_type == "promotional":
            content += f"This limited-time offer includes premium features and exclusive benefits that you won't find anywhere else.\n\n"
        elif campaign_type == "educational":
            content += f"We've compiled expert insights and practical tips to help you make the most of {keyword}.\n\n"
        else:  # retention
            content += f"As a valued customer, you deserve the best. This exclusive offer is our way of saying thank you.\n\n"
        
        content += f"{cta}\n\nBest regards,\nThe {company} Team"
        
        return content

    def _random_recent_date(self) -> datetime:
        """Generate a random date within the last 30 days"""
        start_date = datetime.now() - timedelta(days=30)
        random_days = random.randint(0, 30)
        return start_date + timedelta(days=random_days)

class APIDataFetcher:
    """Fetches real campaign data from APIs"""
    
    def __init__(self):
        self.newsapi_key = os.getenv('NEWSAPI_KEY')
        self.fake = Faker()

    def fetch_news_campaigns(self) -> List[CampaignEvent]:
        """Simulate fetching campaigns from news/marketing APIs"""
        
        # This would be replaced with real API calls
        # For demo purposes, we'll generate realistic-looking data
        campaigns = []
        
        marketing_topics = [
            "credit card promotion",
            "travel deals",
            "technology launch",
            "food delivery discount",
            "streaming service offer"
        ]
        
        for topic in marketing_topics:
            event = CampaignEvent(
                event_type="new_campaign",
                company=f"{self.fake.company()}",
                industry="Mixed",
                channel="API_Source",
                title=f"Market Intelligence: {topic.title()}",
                subject=f"Latest {topic} trends",
                content=f"Market analysis shows increased activity in {topic} campaigns. "
                       f"Companies are focusing on customer acquisition through targeted messaging.",
                keywords=topic.split(),
                date=datetime.now().isoformat(),
                source="api_fetch"
            )
            campaigns.append(event)
            
        return campaigns

class EventProducer:
    """Produces campaign events to Redis stream"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        self.generator = SyntheticDataGenerator()
        self.api_fetcher = APIDataFetcher()
        
        logger.info(f"Connected to Redis at {REDIS_URL}")

    def publish_event(self, event: CampaignEvent):
        """Publish a single campaign event to Redis stream"""
        
        event_data = {
            'event_type': event.event_type,
            'company': event.company,
            'industry': event.industry,
            'channel': event.channel,
            'title': event.title,
            'subject': event.subject,
            'content': event.content,
            'keywords': json.dumps(event.keywords),
            'date': event.date,
            'source': event.source,
            'published_at': datetime.now().isoformat()
        }
        
        try:
            message_id = self.redis_client.xadd(STREAM_NAME, event_data)
            logger.info(f"Published event {message_id} for {event.company} - {event.title}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return None

    def generate_synthetic_campaigns(self, count: int = 5):
        """Generate and publish synthetic campaign events"""
        
        logger.info(f"Generating {count} synthetic campaigns...")
        
        for i in range(count):
            event = self.generator.generate_campaign()
            self.publish_event(event)
            
            # Add small delay to simulate realistic timing
            time.sleep(random.uniform(0.1, 0.5))

    def fetch_and_publish_api_campaigns(self):
        """Fetch campaigns from APIs and publish them"""
        
        logger.info("Fetching campaigns from API sources...")
        
        try:
            campaigns = self.api_fetcher.fetch_news_campaigns()
            
            for campaign in campaigns:
                self.publish_event(campaign)
                time.sleep(0.2)
                
            logger.info(f"Published {len(campaigns)} API-sourced campaigns")
            
        except Exception as e:
            logger.error(f"Failed to fetch API campaigns: {e}")

    def run_continuous_generation(self):
        """Run continuous campaign generation"""
        
        logger.info("Starting continuous campaign generation...")
        
        # Schedule different types of data generation
        schedule.every(2).minutes.do(lambda: self.generate_synthetic_campaigns(3))
        schedule.every(10).minutes.do(self.fetch_and_publish_api_campaigns)
        schedule.every(1).hours.do(lambda: self.generate_synthetic_campaigns(10))
        
        # Initial batch
        self.generate_synthetic_campaigns(5)
        self.fetch_and_publish_api_campaigns()
        
        while True:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds

def main():
    """Main producer entry point"""
    
    logger.info("Starting Competiscan Event Producer...")
    
    producer = EventProducer()
    
    # Test Redis connection
    try:
        producer.redis_client.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return
    
    # Check if running in continuous mode
    mode = os.getenv('PRODUCER_MODE', 'continuous')
    
    if mode == 'batch':
        # Run once and exit
        logger.info("Running in batch mode...")
        producer.generate_synthetic_campaigns(20)
        producer.fetch_and_publish_api_campaigns()
        logger.info("Batch processing completed")
    else:
        # Run continuously
        logger.info("Running in continuous mode...")
        producer.run_continuous_generation()

if __name__ == "__main__":
    main()