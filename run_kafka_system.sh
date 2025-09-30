#!/bin/bash

# Competiscan-Lite with Kafka - Full System Launch
echo "🚀 Starting Competiscan-Lite with Kafka Event Streaming..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ❌${NC} $1"
}

# Cleanup function
cleanup() {
    print_status "🛑 Shutting down services..."
    docker-compose -f docker-compose-kafka.yml down
    print_success "All services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    print_error "docker-compose is not installed. Please install it and try again."
    exit 1
fi

print_status "📋 Pre-flight checks..."

# Create necessary directories
mkdir -p data/uploads
mkdir -p logs

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating default configuration..."
    cat > .env << EOF
# Competiscan-Lite Environment Configuration

# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/competiscan
POSTGRES_DB=competiscan
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Elasticsearch
ELASTICSEARCH_URL=http://elasticsearch:9200

# Redis
REDIS_URL=redis://redis:6379

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_TOPIC_CAMPAIGNS=campaign-events
KAFKA_TOPIC_ANALYTICS=analytics-events

# OpenAI (optional - for AI-powered analytics)
# OPENAI_API_KEY=your_openai_api_key_here

# Frontend
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8002
EOF
    print_success "Default .env file created"
fi

print_status "🐳 Starting Kafka infrastructure..."

# Start Kafka infrastructure first
docker-compose -f docker-compose-kafka.yml up -d zookeeper kafka kafka-ui redis

print_status "⏳ Waiting for Kafka to be ready..."
sleep 15

# Check if Kafka is ready
for i in {1..30}; do
    if docker-compose -f docker-compose-kafka.yml exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list > /dev/null 2>&1; then
        print_success "Kafka is ready!"
        break
    fi
    
    if [ $i -eq 30 ]; then
        print_error "Kafka failed to start after 5 minutes"
        exit 1
    fi
    
    print_status "Waiting for Kafka... (attempt $i/30)"
    sleep 10
done

print_status "📊 Starting databases..."

# Start databases
docker-compose -f docker-compose-kafka.yml up -d postgres elasticsearch

print_status "⏳ Waiting for databases..."
sleep 10

print_status "🔧 Starting application services..."

# Start backend services
docker-compose -f docker-compose-kafka.yml up -d backend kafka-producer kafka-processor analytics-service

print_status "⏳ Waiting for backend services..."
sleep 10

print_status "🎨 Starting frontend..."

# Start frontend
docker-compose -f docker-compose-kafka.yml up -d frontend

print_status "🔍 Performing health checks..."

# Wait a bit for services to fully start
sleep 15

# Health check function
check_service() {
    local service_name=$1
    local url=$2
    local timeout=${3:-10}
    
    if curl -s --max-time $timeout "$url" > /dev/null 2>&1; then
        print_success "$service_name is healthy"
        return 0
    else
        print_error "$service_name is not responding"
        return 1
    fi
}

# Perform health checks
print_status "🏥 Running health checks..."

check_service "Backend API" "http://localhost:8000/api/health"
check_service "Analytics Service" "http://localhost:8002" 5
check_service "Frontend" "http://localhost:3000" 5
check_service "Kafka UI" "http://localhost:8080" 5

print_status "📈 Checking Kafka topics..."

# Create Kafka topics if they don't exist
docker-compose -f docker-compose-kafka.yml exec -T kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic campaign-events --partitions 3 --replication-factor 1
docker-compose -f docker-compose-kafka.yml exec -T kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic analytics-events --partitions 3 --replication-factor 1

print_success "Kafka topics configured"

print_status "🎯 Testing data streaming..."

# Test campaign creation via API
sleep 5
test_campaign=$(curl -s -X POST "http://localhost:8000/api/campaigns" \
    -H "Content-Type: application/json" \
    -d '{
        "company": "Test Streaming Co",
        "name": "Live Data Test Campaign",
        "platform": "Facebook",
        "status": "active",
        "budget": 10000,
        "start_date": "'$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'",
        "end_date": "'$(date -u -d '+30 days' +%Y-%m-%dT%H:%M:%S.000Z)'",
        "metrics": {
            "impressions": 15000,
            "clicks": 750,
            "conversions": 45,
            "spend": 2500,
            "ctr": 5.0,
            "sentiment_score": 0.85
        }
    }' 2>/dev/null)

if [[ "$test_campaign" == *"successfully"* ]]; then
    print_success "Test campaign created - data streaming active!"
else
    print_warning "Campaign creation test had issues"
fi

print_success "🎉 Competiscan-Lite with Kafka is fully operational!"

echo ""
echo "📍 Service URLs:"
echo "   🎨 Frontend Dashboard: http://localhost:3000"
echo "   🔗 Backend API: http://localhost:8000"
echo "   📊 API Documentation: http://localhost:8000/docs"
echo "   ⚡ Real-time Analytics: http://localhost:8002"
echo "   🔍 Kafka UI: http://localhost:8080"
echo ""
echo "🌊 Data Streaming:"
echo "   📧 Campaign Events: campaign-events topic"
echo "   📈 Analytics Events: analytics-events topic"
echo "   🔴 WebSocket: ws://localhost:8002 (Real-time updates)"
echo ""
echo "💾 Databases:"
echo "   🐘 PostgreSQL: localhost:5432"
echo "   🔍 Elasticsearch: http://localhost:9200"
echo "   🗄️ Redis: localhost:6379"
echo ""
echo "🎛️ Control:"
echo "   📊 View logs: docker-compose -f docker-compose-kafka.yml logs [service]"
echo "   ⏹️ Stop all: Ctrl+C or docker-compose -f docker-compose-kafka.yml down"
echo ""

# Monitor logs in real-time
print_status "📊 Streaming live logs (Ctrl+C to stop monitoring)..."
echo ""

# Follow logs for key services
docker-compose -f docker-compose-kafka.yml logs -f --tail=10 backend kafka-producer kafka-processor analytics-service