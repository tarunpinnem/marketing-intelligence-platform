-- Initialize Competiscan Database

-- Create companies table
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    industry VARCHAR(100),
    website VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    title VARCHAR(500),
    subject_line VARCHAR(500),
    campaign_type VARCHAR(50),
    channel VARCHAR(50),
    launch_date DATE,
    content TEXT,
    keywords TEXT[],
    sentiment_score DECIMAL(3,2),
    classification VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_campaigns_company_id ON campaigns(company_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_launch_date ON campaigns(launch_date);
CREATE INDEX IF NOT EXISTS idx_campaigns_channel ON campaigns(channel);
CREATE INDEX IF NOT EXISTS idx_campaigns_keywords ON campaigns USING GIN(keywords);

-- Insert sample companies
INSERT INTO companies (name, industry, website) VALUES
('Chase Bank', 'Financial Services', 'https://chase.com'),
('Capital One', 'Financial Services', 'https://capitalone.com'),
('American Express', 'Financial Services', 'https://americanexpress.com'),
('Discover', 'Financial Services', 'https://discover.com'),
('Wells Fargo', 'Financial Services', 'https://wellsfargo.com')
ON CONFLICT (name) DO NOTHING;