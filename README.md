

# Competiscan Real-Time Marketing Intelligence Platform

## 🎯 Overview
**Competiscan** is a live competitive marketing intelligence platform that automatically ingests real marketing campaign data from News API, social media advertising APIs, and multiple data sources. It provides real-time analytics, trend detection, and competitive insights through a modern React dashboard.

## 🚀 Core Features

### **Live Data Ingestion Pipeline**
- **News API Integration**: Automatically fetches real marketing and advertising news using configurable search queries
- **Multi-Source Data Pipeline**: Integrates Facebook Ad Library, Google Ads API, Twitter Ads, and LinkedIn Ads APIs
- **Real-Time Processing**: Continuous data ingestion every 15 minutes with automatic deduplication
- **Smart Content Detection**: AI-powered campaign detection from news articles and press releases

### **Advanced Analytics Engine**
- **Live Campaign Tracking**: Real-time monitoring of competitor marketing activities
- **Trend Analysis**: Time-series analysis of campaign launch patterns and marketing spend
- **Sentiment Analysis**: Automatic sentiment scoring of campaign coverage and reception
- **Platform Detection**: Intelligent detection of marketing channels from content analysis

### **Real-Time Dashboard**
- **Live Updates**: WebSocket-powered real-time dashboard updates as new campaigns are detected
- **Interactive Analytics**: Campaign trends, top performers, channel distribution charts
- **Advanced Search**: Full-text search across campaign content, company names, and platforms
- **Smart Filtering**: Filter by date ranges, sentiment scores, platforms, and campaign types

## 🏗️ Technical Architecture

### **Data Ingestion Services**
```python
# Real News API Integration
news_ingestion.py    # Fetches live marketing news from NewsAPI.org
data_ingestion.py    # Multi-platform ad API integration (Facebook, Google, Twitter)
```

### **Backend Microservices** 
- **FastAPI Gateway**: Central API routing with health checks and monitoring
- **Analytics Service**: Real-time campaign analytics and competitor analysis 
- **WebSocket Service**: Live dashboard updates and real-time notifications
- **Data Pipeline**: Kafka-powered ETL with PostgreSQL, Elasticsearch, Redis

### **Frontend Stack**
- **React 18**: Modern component architecture with hooks and state management
- **Real-Time UI**: WebSocket integration for live data updates
- **Recharts**: Interactive campaign trend visualizations
- **Tailwind CSS**: Responsive, modern UI design

## 🔧 Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Data Sources** | News API, Facebook Ad Library, Google Ads API, Twitter Ads |
| **Data Pipeline** | Kafka Streams, Redis Caching, PostgreSQL, Elasticsearch |
| **Backend** | FastAPI, SQLAlchemy, WebSockets, async/await |
| **Frontend** | React 18, Recharts, React Query, Tailwind CSS |
| **Infrastructure** | Docker Compose, Health Monitoring, Auto-scaling |## 🎯 **Features**

### **🚀 Real-Time Event Processing**
- **Redis Streams**: Event-driven data pipeline
- **Multi-Consumer Architecture**: Parser, Indexer, and Notifier services
- **WebSocket Integration**: Real-time dashboard updates
- **AI-Powered Analytics**: OpenAI GPT-3.5 sentiment analysis

### **📊 Advanced Analytics Dashboard**
- **Interactive Visualizations**: Recharts integration
- **Real-Time Filtering**: Advanced search capabilities
- **Multi-Format Support**: CSV, JSON data processing
- **Industry Insights**: Campaign performance analytics

### **🤖 AI-Enhanced Processing**
- **Sentiment Analysis**: Campaign content evaluation
- **Automated Classification**: Campaign type detection
- **Predictive Insights**: Performance trend analysis
- **Smart Recommendations**: Optimization suggestions

### **⚡ Enhanced ETL Pipeline**
- **Synthetic Data Generation**: 6 industries, 50+ companies
- **Campaign Templates**: Promotional, educational, retention types
- **Data Validation**: Quality checks and error reporting
- **Multi-Channel Support**: Email, social, display, search, video, SMS
- **Analytics & Trends**: Visualize competitor activity and trends
- **AI-Powered Insights**: Automatic sentiment analysis and campaign classification

### ✨ AI Features
- **Sentiment Analysis**: Classify campaign tone as positive/negative/neutral
- **Campaign Classification**: Auto-categorize as promotional/educational/retention
- **Competitive Intelligence**: Identify trends and competitor strategies

## 🏗️ Architecture

### Frontend (React + Tailwind CSS)
- Clean dashboard with search, filters, and charts
- Responsive design with modern UI components
- Real-time data visualization with Recharts

### Backend (FastAPI + Python)
- RESTful APIs for data ingestion and querying
- Integration with OpenAI for AI analysis
- Structured data storage and full-text search

### Database Stack
- **PostgreSQL**: Structured campaign and company data
- **Elasticsearch**: Full-text search and indexing
- **Docker Compose**: Orchestrated database services

### Data Pipeline
- ETL scripts for data processing and validation
- Sample data generation and format conversion
- Automated data ingestion workflows

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | React 18, Tailwind CSS, React Query, Recharts |
| **Backend** | FastAPI, SQLAlchemy, Pydantic |
| **Database** | PostgreSQL, Elasticsearch |
| **AI/ML** | OpenAI GPT-3.5-turbo |
| **DevOps** | Docker, Docker Compose |
| **Data Processing** | Pandas, NumPy |

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd competiscan
cp .env.example .env
# Edit .env file with your OpenAI API key (optional)
```

### 2. Start Services with Docker
```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Elasticsearch (port 9200)
- FastAPI backend (port 8000)
- React frontend (port 3000)

### 3. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 4. Load Sample Data
```bash
# Upload sample data through the UI at http://localhost:3000/upload
# Or use the sample CSV file in data/sample_data/credit_card_campaigns.csv
```

## 📊 Usage Examples

### Demo Scenario
1. **Upload Data**: Upload marketing campaign data (CSV/JSON)
2. **Search Campaigns**: Search for "credit card ads" or "0% APR"
3. **Filter Results**: Filter by company, date range, or channel
4. **View Analytics**: Explore trends, sentiment analysis, and competitor insights
5. **AI Insights**: Get automatic campaign classification and sentiment scoring

### Sample Search Queries
- `"0% APR"` - Find promotional offers
- `"cash back"` - Discover reward campaigns
- `"travel rewards"` - Search travel-focused campaigns
- `"bonus points"` - Find sign-up bonus campaigns

## 🔧 Development

### Local Development Setup

#### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

#### Frontend Development
```bash
cd frontend
npm install
npm start
```

#### Data Processing
```bash
cd data/etl
pip install -r requirements.txt

# Validate data format
python etl.py validate ../sample_data/credit_card_campaigns.csv

# Convert CSV to JSON
python etl.py convert input.csv output.json

# Generate sample data
python etl.py generate sample_data.csv 100
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API status |
| GET | `/health` | Health check |
| GET | `/campaigns` | List campaigns |
| POST | `/campaigns` | Create campaign |
| POST | `/search` | Search campaigns |
| POST | `/upload` | Upload data file |
| GET | `/analytics/companies` | Company analytics |
| GET | `/analytics/trends` | Trend analytics |

## 📁 Project Structure

```
competiscan/
├── frontend/                 # React frontend application
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Page components (Dashboard, Search, etc.)
│   │   └── services/        # API integration
│   └── package.json
├── backend/                  # FastAPI backend application
│   ├── main.py             # Main application file
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile
├── data/                    # Data processing and samples
│   ├── sample_data/        # Sample campaign data
│   └── etl/                # ETL scripts and utilities
├── docker/                  # Docker configuration
│   └── init-db.sql         # Database initialization
├── docker-compose.yml      # Multi-service orchestration
└── README.md
```

## 🎯 Roadmap

### Phase 1: Core Platform ✅
- [x] Database setup (PostgreSQL + Elasticsearch)
- [x] FastAPI backend with CRUD operations
- [x] React frontend with search and dashboard
- [x] Data upload and processing

### Phase 2: Enhanced Features ✅
- [x] AI-powered sentiment analysis
- [x] Campaign classification
- [x] Data visualization and analytics
- [x] Advanced search and filtering

### Phase 3: Advanced Intelligence (Future)
- [ ] Competitor comparison dashboard
- [ ] Alert system for new campaigns
- [ ] Trend prediction using ML
- [ ] Export and reporting features
- [ ] User authentication and multi-tenancy
- [ ] Advanced data connectors (email, social media APIs)


## 🙏 Acknowledgments

- FastAPI for the excellent Python framework
- React and Tailwind CSS communities
- Elasticsearch for powerful search capabilities



