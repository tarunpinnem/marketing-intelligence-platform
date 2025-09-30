#!/usr/bin/env python3
"""
Competiscan-Lite Project Tester
Tests all API endpoints and displays results
"""

import requests
import json
from datetime import datetime

def test_api():
    """Test all API endpoints"""
    base_url = "http://localhost:8001"
    
    print("🧪 Testing Competiscan-Lite API")
    print("=" * 50)
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            health = response.json()
            print("✅ Backend Health Check:")
            print(f"   Status: {health['status']}")
            print(f"   Mode: {health['mode']}")
            print(f"   Campaigns Loaded: {health['campaigns_loaded']}")
            print(f"   Version: {health['version']}")
        else:
            print("❌ Backend Health Check Failed")
            return False
    except Exception as e:
        print(f"❌ Backend not accessible: {e}")
        return False
    
    print()
    
    # Test campaigns endpoint
    try:
        response = requests.get(f"{base_url}/api/campaigns?limit=5")
        if response.status_code == 200:
            data = response.json()
            print("📋 Campaign Data:")
            print(f"   Total Campaigns: {data['total']}")
            print(f"   Showing: {len(data['campaigns'])} campaigns")
            
            if data['campaigns']:
                sample = data['campaigns'][0]
                print(f"   Sample Campaign:")
                print(f"     • Company: {sample.get('company', 'N/A')}")
                print(f"     • Industry: {sample.get('industry', 'N/A')}")
                print(f"     • Channel: {sample.get('channel', 'N/A')}")
                print(f"     • Title: {sample.get('title', 'N/A')}")
        else:
            print("❌ Campaigns endpoint failed")
    except Exception as e:
        print(f"❌ Campaigns test failed: {e}")
    
    print()
    
    # Test analytics endpoint
    try:
        response = requests.get(f"{base_url}/api/analytics")
        if response.status_code == 200:
            analytics = response.json()
            print("📊 Analytics Data:")
            print(f"   Total Campaigns: {analytics['total_campaigns']}")
            print(f"   Companies Tracked: {analytics['companies']}")
            print(f"   Channel Distribution:")
            for channel, count in analytics.get('channels', {}).items():
                print(f"     • {channel}: {count}")
        else:
            print("❌ Analytics endpoint failed")
    except Exception as e:
        print(f"❌ Analytics test failed: {e}")
    
    print()
    
    # Test search endpoint
    try:
        response = requests.get(f"{base_url}/api/search?q=campaign")
        if response.status_code == 200:
            search = response.json()
            print("🔍 Search Test:")
            print(f"   Search Results: {search['total']} campaigns found")
            print(f"   Query: '{search['query']['text']}'")
        else:
            print("❌ Search endpoint failed")
    except Exception as e:
        print(f"❌ Search test failed: {e}")
    
    print()
    
    # Test insights endpoint
    try:
        response = requests.get(f"{base_url}/api/insights")
        if response.status_code == 200:
            insights = response.json()
            print("🤖 AI Insights:")
            for insight in insights.get('insights', []):
                print(f"   • {insight['title']} (Confidence: {insight['confidence']:.0%})")
                print(f"     {insight['description']}")
        else:
            print("❌ Insights endpoint failed")
    except Exception as e:
        print(f"❌ Insights test failed: {e}")
    
    print()
    print("🎯 API Testing Complete!")
    print("=" * 50)
    print("📊 Backend URL: http://localhost:8001")
    print("📚 API Docs: http://localhost:8001/docs")
    print("🖥️  Frontend: http://localhost:3000 (if running)")
    
    return True

if __name__ == "__main__":
    test_api()