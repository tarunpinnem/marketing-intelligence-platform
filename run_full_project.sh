#!/bin/bash

echo "🚀 STARTING COMPETISCAN-LITE - COMPLETE PROJECT"
echo "==============================================="
echo "Event-Driven Competitive Marketing Insights Platform"
echo ""

# Navigate to project directory
cd /Users/tarunpinnem/Desktop/competiscan

# Function to cleanup processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    
    # Kill backend process
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null
    fi
    
    # Kill frontend process  
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null
    fi
    
    # Kill any remaining processes
    pkill -f "standalone_backend" 2>/dev/null
    pkill -f "npm start" 2>/dev/null
    
    echo "✅ All services stopped."
    exit 0
}

# Set trap to cleanup on exit
trap cleanup SIGINT SIGTERM EXIT

echo "📦 Setting up environment..."

# Activate Python virtual environment
echo "🐍 Activating Python virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment. Creating new one..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Install Python dependencies if needed
echo "📥 Checking Python dependencies..."
pip install -q fastapi uvicorn sqlalchemy psycopg2-binary elasticsearch pandas python-multipart openai redis requests

echo ""
echo "🔧 STARTING BACKEND SERVER"
echo "=========================="

# Start the backend server
echo "📡 Starting FastAPI backend on port 8001..."
python -c "
import uvicorn
from standalone_backend import app
print('🚀 Backend Server Starting...')
print('📊 API: http://localhost:8001')
print('📚 Docs: http://localhost:8001/docs')
print('💚 Health: http://localhost:8001/api/health')
print('')
uvicorn.run(app, host='0.0.0.0', port=8001, log_level='info')
" &

BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 5

# Test backend
echo "🧪 Testing backend connection..."
if curl -s http://localhost:8001/api/health > /dev/null; then
    echo "✅ Backend is running successfully!"
    echo "📊 Backend API: http://localhost:8001"
    echo "📚 API Documentation: http://localhost:8001/docs"
else
    echo "❌ Backend failed to start properly"
fi

echo ""
echo "🎨 STARTING FRONTEND SERVER"
echo "==========================="

# Start the frontend server
cd frontend

# Check if node_modules exists, install if needed
if [ ! -d "node_modules" ]; then
    echo "📥 Installing frontend dependencies..."
    npm install
fi

echo "🖥️ Starting React frontend on port 3000..."
npm start &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

cd ..

# Wait for frontend to start
echo "⏳ Waiting for frontend to initialize..."
sleep 10

# Test frontend (it might take longer to start)
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend is running successfully!"
else
    echo "⏳ Frontend is still starting up..."
fi

echo ""
echo "🎯 PROJECT STATUS"
echo "================="
echo "✅ Backend API:      http://localhost:8001"
echo "✅ API Docs:         http://localhost:8001/docs"  
echo "✅ Frontend:         http://localhost:3000"
echo "📊 Campaigns:        $(curl -s http://localhost:8001/api/health 2>/dev/null | grep -o '"campaigns_loaded":[0-9]*' | cut -d: -f2 || echo 'Loading...')"

echo ""
echo "🛠️ AVAILABLE ENDPOINTS"
echo "====================="
echo "💚 Health Check:     curl http://localhost:8001/api/health"
echo "📋 Campaigns:        curl http://localhost:8001/api/campaigns"
echo "📊 Analytics:        curl http://localhost:8001/api/analytics"
echo "🔍 Search:           curl \"http://localhost:8001/api/search?q=campaign\""
echo "🤖 AI Insights:      curl http://localhost:8001/api/insights"

echo ""
echo "🚀 QUICK TESTS"
echo "=============="

# Run some quick tests
echo "🧪 Testing API endpoints..."

# Test health endpoint
health_response=$(curl -s http://localhost:8001/api/health 2>/dev/null)
if [ ! -z "$health_response" ]; then
    echo "✅ Health Check: API is responding"
    campaigns_count=$(echo $health_response | grep -o '"campaigns_loaded":[0-9]*' | cut -d: -f2)
    echo "📊 Campaigns Loaded: $campaigns_count"
else
    echo "❌ Health Check: API not responding"
fi

# Test campaigns endpoint
campaigns_response=$(curl -s "http://localhost:8001/api/campaigns?limit=1" 2>/dev/null)
if [ ! -z "$campaigns_response" ]; then
    echo "✅ Campaigns API: Working"
else
    echo "❌ Campaigns API: Not responding"
fi

echo ""
echo "📖 USAGE EXAMPLES"
echo "================"
echo ""
echo "1. View in Browser:"
echo "   🌐 Open http://localhost:3000 for the dashboard"
echo "   📚 Open http://localhost:8001/docs for API documentation"
echo ""
echo "2. Test ETL Pipeline:"
echo "   cd data/etl"
echo "   python3 etl.py generate new_campaigns.csv --count 20"
echo "   python3 etl.py analyze new_campaigns.csv"
echo ""
echo "3. API Examples:"
echo "   curl http://localhost:8001/api/campaigns | jq"
echo "   curl http://localhost:8001/api/analytics | jq"
echo ""
echo "4. Upload Data:"
echo "   curl -X POST -F \"file=@data.csv\" http://localhost:8001/api/upload"

echo ""
echo "🏆 COMPETISCAN-LITE IS FULLY RUNNING!"
echo "====================================="
echo "🎯 Frontend Dashboard: http://localhost:3000"
echo "📊 Backend API:        http://localhost:8001"
echo "📚 API Documentation:  http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep the script running
while true; do
    sleep 30
    # Check if services are still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "⚠️ Backend process has stopped"
        break
    fi
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "⚠️ Frontend process has stopped"  
        break
    fi
done

echo "🛑 Services have stopped"