import React, { useState, useEffect } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { fetchMetaAds } from '../services/metaAdLibrary';
import AdvancedAnalytics from './AdvancedAnalytics';
import AIInsights from './AIInsights';
import AdvancedSearch from './AdvancedSearch';
import CampaignPreviewModal from './CampaignPreviewModal';
import { saveAs } from 'file-saver';

const RealTimeDashboard = () => {
  const [campaigns, setCampaigns] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('Connecting...');
  const [realTimeEvents, setRealTimeEvents] = useState([]);
  const [lastUpdateTime, setLastUpdateTime] = useState(null);
  const [metaAds, setMetaAds] = useState([]);
  const [trendingKeywords, setTrendingKeywords] = useState([]);
  const [crossChannelMetrics, setCrossChannelMetrics] = useState({});
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [filters, setFilters] = useState({
    company: '',
    dateRange: { start: '', end: '' },
    keywords: '',
    platforms: []
  });

  const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8002/ws';

  const { sendMessage, lastMessage, readyState } = useWebSocket(WS_URL, {
    onOpen: () => {
      console.log('🔗 WebSocket connected');
      setConnectionStatus('Connected');
    },
    onClose: () => {
      console.log('❌ WebSocket disconnected');
      setConnectionStatus('Disconnected');
    },
    onError: (error) => {
      console.error('❌ WebSocket error:', error);
      setConnectionStatus('Error');
    },
    shouldReconnect: (closeEvent) => true,
    reconnectAttempts: 10,
    reconnectInterval: 3000,
  });

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (lastMessage !== null) {
      try {
        const message = JSON.parse(lastMessage.data);
        
        switch (message.type) {
          case 'campaign_created':
          case 'campaign_updated':
            // Update campaigns list
            setCampaigns(prev => {
              const existing = prev.findIndex(c => c.id === message.data.id);
              if (existing >= 0) {
                const updated = [...prev];
                updated[existing] = message.data;
                return updated;
              } else {
                return [message.data, ...prev.slice(0, 19)]; // Keep latest 20
              }
            });
            
            // Add to real-time events
            setRealTimeEvents(prev => [
              {
                id: Date.now(),
                type: message.type,
                company: message.data.company,
                timestamp: new Date().toLocaleTimeString()
              },
              ...prev.slice(0, 9) // Keep latest 10
            ]);
            break;
            
          case 'analytics_update':
            // Update analytics
            setAnalytics(prev => ({
              ...prev,
              lastUpdate: message.data,
              updatedAt: new Date().toISOString()
            }));
            
            // Add to events
            setRealTimeEvents(prev => [
              {
                id: Date.now(),
                type: 'analytics_update',
                company: message.data.company,
                metric: `${message.data.metric_type}: ${message.data.value}`,
                timestamp: new Date().toLocaleTimeString()
              },
              ...prev.slice(0, 9)
            ]);
            break;
            
          case 'pong':
            // Handle ping/pong for connection health
            console.log('🏓 WebSocket pong received');
            break;
            
          default:
            console.log('📨 Unknown message type:', message.type);
        }
      } catch (error) {
        console.error('❌ Error parsing WebSocket message:', error);
      }
    }
  }, [lastMessage]);

  // Send periodic ping to keep connection alive
  useEffect(() => {
    const interval = setInterval(() => {
      if (readyState === ReadyState.OPEN) {
        sendMessage(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Every 30 seconds

    return () => clearInterval(interval);
  }, [readyState, sendMessage]);

  // Fetch initial data and set up polling
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        // Fetch campaigns
        const campaignResponse = await fetch('/api/campaigns?limit=20');
        const campaignData = await campaignResponse.json();
        setCampaigns(campaignData.campaigns || []);

        // Fetch analytics (using realtime stats endpoint)
        const analyticsResponse = await fetch('/api/realtime/stats');
        const analyticsData = await analyticsResponse.json();
        setAnalytics(analyticsData);

        // Fetch Meta Ads
        const metaAdsData = await fetchMetaAds(process.env.REACT_APP_META_ACCESS_TOKEN, ['marketing', 'promotion']);
        setMetaAds(metaAdsData);

        // Set last update time
        setLastUpdateTime(new Date().toISOString());

        // Calculate trending keywords
        const keywords = analyzeKeywords(campaignData.campaigns || []);
        setTrendingKeywords(keywords);

        // Calculate cross-channel metrics
        const metrics = analyzeCrossChannel(campaignData.campaigns || []);
        setCrossChannelMetrics(metrics);

      } catch (error) {
        console.error('Error fetching initial data:', error);
      }
    };

    fetchInitialData();

    // Set up polling every 30 seconds
    const pollInterval = setInterval(fetchInitialData, 30000);

    return () => clearInterval(pollInterval);
  }, []);

  // Analyze keywords from campaign content
  const analyzeKeywords = (campaigns) => {
    const keywordMap = new Map();
    
    campaigns.forEach(campaign => {
      const words = campaign.name.toLowerCase().split(/\W+/);
      words.forEach(word => {
        if (word.length > 3) {
          keywordMap.set(word, (keywordMap.get(word) || 0) + 1);
        }
      });
    });

    return Array.from(keywordMap.entries())
      .map(([text, count]) => ({
        text,
        weight: Math.min(2, 0.8 + (count / campaigns.length))
      }))
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 15);
  };

  // Analyze cross-channel metrics
  const analyzeCrossChannel = (campaigns) => {
    const metrics = {};
    
    campaigns.forEach(campaign => {
      const platform = campaign.platform;
      if (!metrics[platform]) {
        metrics[platform] = {
          count: 0,
          totalSpend: 0,
          avgEngagement: 0
        };
      }
      
      metrics[platform].count++;
      metrics[platform].totalSpend += campaign.metrics?.spend || 0;
      metrics[platform].avgEngagement += campaign.metrics?.impressions || 0;
    });

    Object.keys(metrics).forEach(platform => {
      metrics[platform].avgEngagement /= metrics[platform].count;
    });

    return metrics;
  };

  // Export data to CSV
  const exportToCSV = () => {
    const headers = ['Company', 'Campaign', 'Platform', 'Status', 'Start Date', 'Impressions', 'CTR', 'Sentiment'];
    const csvData = campaigns.map(campaign => [
      campaign.company,
      campaign.name,
      campaign.platform,
      campaign.status,
      campaign.start_date,
      campaign.metrics?.impressions || 0,
      campaign.metrics?.ctr || 0,
      campaign.metrics?.sentiment_score || 0
    ]);

    const csvContent = [
      headers.join(','),
      ...csvData.map(row => row.join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    saveAs(blob, `campaign_report_${new Date().toISOString().slice(0,10)}.csv`);
  };

  const getConnectionStatusColor = () => {
    switch (readyState) {
      case ReadyState.OPEN: return 'text-green-500';
      case ReadyState.CONNECTING: return 'text-yellow-500';
      case ReadyState.CLOSING:
      case ReadyState.CLOSED: return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const createTestCampaign = async () => {
    try {
      const testCampaign = {
        company: 'Test Company',
        name: 'Live Test Campaign',
        platform: 'Facebook',
        status: 'active',
        budget: 5000,
        start_date: new Date().toISOString(),
        end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        metrics: {
          impressions: Math.floor(Math.random() * 10000),
          clicks: Math.floor(Math.random() * 500),
          conversions: Math.floor(Math.random() * 50),
          spend: Math.random() * 1000,
          ctr: Math.random() * 5,
          sentiment_score: Math.random()
        }
      };

      const response = await fetch('/api/campaigns', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(testCampaign),
      });

      if (response.ok) {
        console.log('✅ Test campaign created');
      }
    } catch (error) {
      console.error('❌ Error creating test campaign:', error);
    }
  };

  const sendTestAnalytics = async () => {
    try {
      const testEvent = {
        company: 'Test Company',
        metric_type: 'engagement',
        value: Math.random() * 100,
        trend: Math.random() > 0.5 ? 'increasing' : 'decreasing',
        confidence: 0.8 + Math.random() * 0.2
      };

      const response = await fetch('/api/events/trigger', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(testEvent),
      });

      if (response.ok) {
        console.log('✅ Test analytics sent');
      }
    } catch (error) {
      console.error('❌ Error sending test analytics:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-gray-900">
              Real-Time Marketing Intelligence Dashboard
            </h1>
            
            <div className="flex items-center space-x-4">
              <div className={`flex items-center space-x-2`}>
                <div className={`w-3 h-3 rounded-full ${
                  readyState === ReadyState.OPEN ? 'bg-green-500' : 
                  readyState === ReadyState.CONNECTING ? 'bg-yellow-500' : 
                  'bg-red-500'
                }`}></div>
                <span className={`font-medium ${getConnectionStatusColor()}`}>
                  {connectionStatus}
                </span>
              </div>
              
              <div className="flex space-x-2">
                <button
                  onClick={createTestCampaign}
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                >
                  New Campaign
                </button>
                <button
                  onClick={sendTestAnalytics}
                  className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
                >
                  Update Analytics
                </button>
              </div>
            </div>
          </div>

          <div className="mt-4">
            <div className="text-sm text-gray-600">
              Last update: {lastUpdateTime ? new Date(lastUpdateTime).toLocaleString() : 'Never'}
              {lastUpdateTime && <span className="ml-2">(New data arrives every 30 seconds)</span>}
            </div>
          </div>
        </div>

        {/* Advanced Search */}
        <AdvancedSearch
          onSearch={(filters) => {
            // Implement search logic
          }}
          onSaveSearch={(savedSearch) => {
            // Implement save search logic
          }}
        />

        {/* Main Analytics Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Analytics Summary */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Live Analytics</h2>
            {analytics ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {analytics.summary?.total_campaigns || 0}
                    </div>
                    <div className="text-sm text-gray-600">Total Campaigns</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {analytics.summary?.active_campaigns || 0}
                    </div>
                    <div className="text-sm text-gray-600">Active Now</div>
                  </div>
                </div>
                
                <div className="text-center">
                  <div className="text-lg font-semibold text-purple-600">
                    {analytics.summary?.avg_sentiment?.toFixed(2) || '0.00'}
                  </div>
                  <div className="text-sm text-gray-600">Avg Sentiment</div>
                </div>

                <button
                  onClick={exportToCSV}
                  className="w-full mt-4 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition-colors"
                >
                  Export Report
                </button>
              </div>
            ) : (
              <div className="text-gray-500">Loading analytics...</div>
            )}
          </div>

          {/* Real-time Events */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Live Events</h2>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {realTimeEvents.length > 0 ? realTimeEvents.map((event) => (
                <div key={event.id} className="border-l-4 border-blue-500 pl-3 py-2 bg-blue-50">
                  <div className="font-medium text-sm">
                    {event.type.replace('_', ' ').toUpperCase()}
                  </div>
                  <div className="text-sm text-gray-600">
                    {event.company} {event.metric && `- ${event.metric}`}
                  </div>
                  <div className="text-xs text-gray-500">{event.timestamp}</div>
                </div>
              )) : (
                <div className="text-gray-500 text-sm">No live events yet...</div>
              )}
            </div>
          </div>

          {/* Meta Ads Integration */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Meta Ad Library</h2>
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {metaAds.length > 0 ? metaAds.slice(0, 5).map((ad) => (
                <div key={ad.id} className="border rounded p-3 bg-gray-50">
                  <div className="font-medium text-sm">{ad.company}</div>
                  <div className="text-sm text-gray-600 truncate">{ad.name}</div>
                  <div className="flex justify-between items-center mt-2">
                    <span className="px-2 py-1 rounded text-xs bg-blue-100 text-blue-800">
                      {ad.platform}
                    </span>
                    <a
                      href={ad.preview_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-indigo-600 hover:text-indigo-800"
                    >
                      View Ad
                    </a>
                  </div>
                </div>
              )) : (
                <div className="text-gray-500 text-sm">Loading Meta ads...</div>
              )}
            </div>
          </div>
        </div>

        {/* Advanced Analytics */}
        <AdvancedAnalytics
          campaigns={campaigns}
          crossChannelMetrics={crossChannelMetrics}
          trendingKeywords={trendingKeywords}
        />

        {/* Full Campaigns Table */}
        <div className="bg-white rounded-lg shadow-md p-6 mt-6">
          <h2 className="text-xl font-semibold mb-4">Campaign Intelligence Center</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full table-auto">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-2 text-left">Company</th>
                  <th className="px-4 py-2 text-left">Campaign</th>
                  <th className="px-4 py-2 text-left">Platform</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left">Performance</th>
                  <th className="px-4 py-2 text-left">AI Analysis</th>
                  <th className="px-4 py-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((campaign) => (
                  <tr key={campaign.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <div className="font-medium">{campaign.company}</div>
                      <div className="text-xs text-gray-500">ID: {campaign.id}</div>
                    </td>
                    <td className="px-4 py-2">
                      <div className="truncate max-w-xs font-medium">{campaign.name}</div>
                      <div className="text-xs text-gray-500">
                        Started: {new Date(campaign.start_date).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        campaign.platform === 'Facebook' ? 'bg-blue-100 text-blue-800' :
                        campaign.platform === 'Instagram' ? 'bg-purple-100 text-purple-800' :
                        campaign.platform === 'LinkedIn' ? 'bg-indigo-100 text-indigo-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {campaign.platform}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        campaign.status === 'active' ? 'bg-green-100 text-green-800' :
                        campaign.status === 'paused' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {campaign.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-500">Impressions</span>
                          <span className="text-sm font-medium">
                            {campaign.metrics?.impressions?.toLocaleString() || '0'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-500">CTR</span>
                          <span className="text-sm font-medium">
                            {campaign.metrics?.ctr?.toFixed(2) || '0.00'}%
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-500">Spend</span>
                          <span className="text-sm font-medium">
                            ${campaign.metrics?.spend?.toFixed(2) || '0.00'}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      <AIInsights campaign={campaign} />
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => {/* Implement preview modal */}}
                          className="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 transition-colors"
                        >
                          Preview
                        </button>
                        <button
                          onClick={() => {/* Implement export */}}
                          className="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
                        >
                          Export
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      
      {/* Campaign Preview Modal */}
      {selectedCampaign && (
        <CampaignPreviewModal
          campaign={selectedCampaign}
          onClose={() => setSelectedCampaign(null)}
        />
      )}
    </div>
  );
};

export default RealTimeDashboard;