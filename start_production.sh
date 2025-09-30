#!/bin/bash

# Production Competiscan Launch Script
echo "🚀 Starting Production Competiscan System..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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
    print_status "🛑 Shutting down production services..."
    
    # Kill background processes
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    
    print_success "Production services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

print_status "📋 Production pre-flight checks..."

# Check Python
if ! command -v python3 > /dev/null 2>&1; then
    print_error "Python 3 is required"
    exit 1
fi

# Check Node.js
if ! command -v npm > /dev/null 2>&1; then
    print_error "Node.js and npm are required"
    exit 1
fi

print_success "Dependencies verified"

# Install Python dependencies
print_status "📦 Installing Python dependencies..."
pip3 install fastapi uvicorn websockets redis psycopg2-binary || {
    print_warning "Some Python dependencies may not be available, continuing..."
}

# Start production backend
print_status "🔧 Starting production backend..."
python3 production_backend.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

# Test backend health
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    print_success "Backend is healthy"
else
    print_error "Backend failed to start"
    cleanup
fi

# Start frontend in production mode
print_status "🎨 Starting frontend..."
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    print_status "📦 Installing frontend dependencies..."
    npm install
fi

# Start frontend
npm start &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 10

print_success "🎉 Production Competiscan is running!"

echo ""
echo "📍 Production Services:"
echo "   🎨 Frontend Dashboard: http://localhost:3000"
echo "   🔗 Backend API: http://localhost:8000"
echo "   📊 API Documentation: http://localhost:8000/docs"
echo "   ⚡ WebSocket: ws://localhost:8000/ws"
echo ""
echo "🌟 Production Features:"
echo "   ✅ Real-time campaign streaming"
echo "   ✅ WebSocket live updates"
echo "   ✅ Production error handling"
echo "   ✅ Background data generation"
echo "   ✅ Unified dashboard interface"
echo "   ✅ Analytics and insights"
echo ""
echo "🎛️ Management:"
echo "   📊 Health Check: curl http://localhost:8000/api/health"
echo "   ⏹️  Stop Services: Ctrl+C"
echo ""

# Keep script running and monitor services
while true; do
    # Check if backend is still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_error "Backend process died, restarting..."
        python3 production_backend.py &
        BACKEND_PID=$!
        sleep 5
    fi
    
    # Check if frontend is still running
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_error "Frontend process died, restarting..."
        cd frontend
        npm start &
        FRONTEND_PID=$!
        cd ..
        sleep 10
    fi
    
    sleep 30  # Check every 30 seconds
done