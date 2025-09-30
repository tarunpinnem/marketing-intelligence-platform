#!/bin/bash

echo "🚀 Starting Competiscan-Lite Project"
echo "===================================="

# Navigate to project directory
cd /Users/tarunpinnem/Desktop/competiscan

# Start the backend in background
echo "📡 Starting Backend Server..."
source venv/bin/activate && python standalone_backend.py &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait a moment for backend to start
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "✅ Backend is running at http://localhost:8000"
    echo "📚 API Documentation: http://localhost:8000/docs"
else
    echo "❌ Backend failed to start"
fi

# Start the frontend
echo "🎨 Starting Frontend Server..."
cd frontend
npm start &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

echo ""
echo "🎯 Competiscan-Lite is starting up!"
echo "📊 Backend API: http://localhost:8000"
echo "🖥️  Frontend Dashboard: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user to stop
wait