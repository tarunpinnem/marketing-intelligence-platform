-- Competiscan Database Schema
-- PostgreSQL database initialization

-- Create campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE,
    name VARCHAR(500) NOT NULL,
    company VARCHAR(255) NOT NULL,
    platform VARCHAR(100) NOT NULL,
    content TEXT,
    sentiment_score DECIMAL(3,3) DEFAULT 0.500,
    budget DECIMAL(12,2),
    impressions INTEGER,
    clicks INTEGER,
    conversions INTEGER,
    ctr DECIMAL(5,2),
    status VARCHAR(50) DEFAULT 'active',
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Create companies table
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    industry VARCHAR(100),
    total_campaigns INTEGER DEFAULT 0,
    total_spend DECIMAL(15,2) DEFAULT 0.00,
    avg_sentiment DECIMAL(3,3) DEFAULT 0.500,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create analytics_cache table for performance
CREATE TABLE IF NOT EXISTS analytics_cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    data JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create kafka_events table for event tracking
CREATE TABLE IF NOT EXISTS kafka_events (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Create search_queries table for search analytics
CREATE TABLE IF NOT EXISTS search_queries (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    filters JSONB,
    results_count INTEGER,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_campaigns_company ON campaigns(company);
CREATE INDEX IF NOT EXISTS idx_campaigns_platform ON campaigns(platform);
CREATE INDEX IF NOT EXISTS idx_campaigns_created_at ON campaigns(created_at);
CREATE INDEX IF NOT EXISTS idx_campaigns_sentiment ON campaigns(sentiment_score);
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name);
CREATE INDEX IF NOT EXISTS idx_analytics_cache_expires ON analytics_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_kafka_events_processed ON kafka_events(processed, created_at);
CREATE INDEX IF NOT EXISTS idx_search_queries_created ON search_queries(created_at);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_campaigns_updated_at 
    BEFORE UPDATE ON campaigns 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_companies_updated_at 
    BEFORE UPDATE ON companies 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial sample data
INSERT INTO companies (name, industry, total_campaigns, total_spend, avg_sentiment) VALUES
    ('Microsoft', 'Technology', 0, 0.00, 0.650),
    ('Apple Inc.', 'Technology', 0, 0.00, 0.720),
    ('Forbes', 'Media', 0, 0.00, 0.580),
    ('Wells Fargo', 'Financial Services', 0, 0.00, 0.620),
    ('Netflix', 'Entertainment', 0, 0.00, 0.680)
ON CONFLICT (name) DO NOTHING;

-- Create materialized view for analytics performance
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics_summary AS
SELECT 
    COUNT(*) as total_campaigns,
    COUNT(DISTINCT company) as total_companies,
    AVG(sentiment_score) as avg_sentiment,
    SUM(budget) as total_spend,
    AVG(ctr) as avg_ctr,
    COUNT(DISTINCT platform) as total_platforms,
    DATE_TRUNC('day', created_at) as date
FROM campaigns 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_summary_date ON analytics_summary(date);

-- Refresh the materialized view
REFRESH MATERIALIZED VIEW analytics_summary;