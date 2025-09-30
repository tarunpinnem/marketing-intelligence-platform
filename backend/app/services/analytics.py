"""
Analytics service for generating insights and trends from campaign data
"""
import asyncio
from typing import List, Dict, Any
from app.db import get_database
from collections import defaultdict, Counter
import statistics
from datetime import datetime, timedelta

async def get_company_trends() -> List[Dict[str, Any]]:
    """Get trends analysis by company"""
    try:
        db = await get_database()
        
        # Get all campaigns from the last 30 days
        query = """
        SELECT company, platform, sentiment_score, impressions, clicks, conversions, 
               budget, ctr, created_at, start_date
        FROM campaigns 
        WHERE created_at >= NOW() - INTERVAL '30 days'
        ORDER BY created_at DESC
        """
        
        result = await db.fetch(query)
        
        if not result:
            return []
        
        # Group by company
        company_data = defaultdict(list)
        for row in result:
            company_data[row['company']].append(dict(row))
        
        trends = []
        for company, campaigns in company_data.items():
            if not campaigns:
                continue
                
            # Calculate metrics
            total_campaigns = len(campaigns)
            avg_sentiment = statistics.mean([c['sentiment_score'] or 0.5 for c in campaigns])
            total_impressions = sum([c['impressions'] or 0 for c in campaigns])
            total_budget = sum([c['budget'] or 0 for c in campaigns])
            avg_ctr = statistics.mean([c['ctr'] or 0 for c in campaigns])
            
            # Platform distribution
            platforms = Counter([c['platform'] for c in campaigns])
            most_used_platform = platforms.most_common(1)[0][0] if platforms else 'Unknown'
            
            trends.append({
                'company': company,
                'total_campaigns': total_campaigns,
                'avg_sentiment': round(avg_sentiment, 3),
                'total_impressions': total_impressions,
                'total_budget': round(total_budget, 2),
                'avg_ctr': round(avg_ctr, 2),
                'platforms': dict(platforms),
                'primary_platform': most_used_platform,
                'trend_direction': 'up' if avg_sentiment > 0.6 else 'down' if avg_sentiment < 0.4 else 'stable'
            })
        
        # Sort by total impressions (engagement)
        trends.sort(key=lambda x: x['total_impressions'], reverse=True)
        
        return trends[:20]  # Return top 20 companies
        
    except Exception as e:
        print(f"Error in get_company_trends: {str(e)}")
        return []

async def get_market_insights() -> Dict[str, Any]:
    """Get overall market insights"""
    try:
        db = await get_database()
        
        # Get recent campaign data
        query = """
        SELECT platform, sentiment_score, impressions, clicks, budget, ctr, 
               created_at, start_date, company
        FROM campaigns 
        WHERE created_at >= NOW() - INTERVAL '7 days'
        ORDER BY created_at DESC
        """
        
        result = await db.fetch(query)
        
        if not result:
            return {
                'total_campaigns': 0,
                'platform_performance': {},
                'sentiment_trends': {},
                'top_performing_companies': []
            }
        
        campaigns = [dict(row) for row in result]
        
        # Platform performance analysis
        platform_stats = defaultdict(lambda: {
            'campaigns': 0, 
            'total_impressions': 0, 
            'avg_ctr': 0, 
            'avg_sentiment': 0,
            'total_budget': 0
        })
        
        for campaign in campaigns:
            platform = campaign['platform']
            platform_stats[platform]['campaigns'] += 1
            platform_stats[platform]['total_impressions'] += campaign['impressions'] or 0
            platform_stats[platform]['avg_sentiment'] += campaign['sentiment_score'] or 0.5
            platform_stats[platform]['avg_ctr'] += campaign['ctr'] or 0
            platform_stats[platform]['total_budget'] += campaign['budget'] or 0
        
        # Calculate averages
        for platform, stats in platform_stats.items():
            if stats['campaigns'] > 0:
                stats['avg_sentiment'] = round(stats['avg_sentiment'] / stats['campaigns'], 3)
                stats['avg_ctr'] = round(stats['avg_ctr'] / stats['campaigns'], 2)
                stats['total_budget'] = round(stats['total_budget'], 2)
        
        # Top performing companies (by impressions)
        company_performance = defaultdict(int)
        for campaign in campaigns:
            company_performance[campaign['company']] += campaign['impressions'] or 0
        
        top_companies = sorted(
            company_performance.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        # Overall sentiment trend
        overall_sentiment = statistics.mean([c['sentiment_score'] or 0.5 for c in campaigns])
        
        return {
            'total_campaigns': len(campaigns),
            'platform_performance': dict(platform_stats),
            'sentiment_trends': {
                'overall_sentiment': round(overall_sentiment, 3),
                'trend': 'positive' if overall_sentiment > 0.6 else 'negative' if overall_sentiment < 0.4 else 'neutral'
            },
            'top_performing_companies': [
                {'company': company, 'total_impressions': impressions}
                for company, impressions in top_companies
            ],
            'analysis_period': '7_days'
        }
        
    except Exception as e:
        print(f"Error in get_market_insights: {str(e)}")
        return {
            'total_campaigns': 0,
            'platform_performance': {},
            'sentiment_trends': {},
            'top_performing_companies': []
        }

async def get_realtime_stats() -> Dict[str, Any]:
    """Get real-time statistics for the dashboard"""
    try:
        db = await get_database()
        
        # Get current statistics
        query = """
        SELECT 
            COUNT(*) as total_campaigns,
            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_campaigns,
            AVG(sentiment_score) as avg_sentiment,
            COUNT(DISTINCT company) as unique_companies,
            SUM(impressions) as total_impressions,
            SUM(budget) as total_budget
        FROM campaigns
        """
        
        result = await db.fetchrow(query)
        
        if not result:
            return {
                'summary': {
                    'total_campaigns': 0,
                    'active_campaigns': 0,
                    'avg_sentiment': 0.5,
                    'unique_companies': 0,
                    'total_impressions': 0,
                    'total_budget': 0
                }
            }
        
        return {
            'summary': {
                'total_campaigns': result['total_campaigns'] or 0,
                'active_campaigns': result['active_campaigns'] or 0,
                'avg_sentiment': round(float(result['avg_sentiment'] or 0.5), 3),
                'unique_companies': result['unique_companies'] or 0,
                'total_impressions': result['total_impressions'] or 0,
                'total_budget': round(float(result['total_budget'] or 0), 2)
            },
            'last_updated': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error in get_realtime_stats: {str(e)}")
        return {
            'summary': {
                'total_campaigns': 0,
                'active_campaigns': 0,
                'avg_sentiment': 0.5,
                'unique_companies': 0,
                'total_impressions': 0,
                'total_budget': 0
            }
        }