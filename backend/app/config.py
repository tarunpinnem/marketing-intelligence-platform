import os
from elasticsearch import AsyncElasticsearch

# Database connection strings
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elasticsearch:9200")

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# News API configuration
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "13eed0028f36481e9cb158bc85df0875")

# Initialize database connections
es = AsyncElasticsearch([ELASTIC_URL])

async def init_db():
    try:
        # Create campaigns index if it doesn't exist
        if not await es.indices.exists(index="campaigns"):
            await es.indices.create(
                index="campaigns",
                body={
                    "mappings": {
                        "properties": {
                            "title": {"type": "text"},
                            "company_name": {"type": "keyword"},
                            "subject_line": {"type": "text"},
                            "content": {"type": "text"},
                            "channel": {"type": "keyword"},
                            "classification": {"type": "keyword"},
                            "launch_date": {"type": "date"},
                            "score": {"type": "float"},
                            "sentiment_score": {"type": "float"},
                            "keywords": {"type": "keyword"}
                        }
                    }
                }
            )
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise e

async def close_db():
    await es.close()