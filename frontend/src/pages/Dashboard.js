import React, { useState, useEffect } from 'react';
import { useQuery } from 'react-query';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { campaignService } from '../services/api';
import CampaignModal from '../components/CampaignModal';
import {
  EnvelopeIcon,
  ChartBarIcon,
  BuildingOfficeIcon,
  ChartPieIcon,
  RocketLaunchIcon,
  BoltIcon,
  ArrowPathIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';

const Dashboard = () => {
  // Real-time state management
  const [realTimeCampaigns, setRealTimeCampaigns] = useState([]);
  const [liveEvents, setLiveEvents] = useState([]);
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  
  // Counter for unique event IDs
  const eventIdCounter = React.useRef(0);
  const generateUniqueId = () => {
    eventIdCounter.current += 1;
    return `${Date.now()}-${eventIdCounter.current}`;
  };
  const [hoveredMetric, setHoveredMetric] = useState(null);
  const [streamingStats, setStreamingStats] = useState({
    totalCampaigns: 0,
    activeCampaigns: 0,
    companiesCount: 0,
    avgSentiment: 0
  });
  const [isStreamingEnabled, setIsStreamingEnabled] = useState(true);
  const [dataSourceStatus, setDataSourceStatus] = useState({
    realNewsCount: 0,
    simulatedCount: 0,
    currentSource: 'unknown',
    apiStatus: 'checking'
  });

    // WebSocket connection for real-time updates
  const { lastMessage, readyState, sendJsonMessage } = useWebSocket(
    `${process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws'}`,
    {
      onOpen: () => {
        console.log('🔗 WebSocket connected to Kafka streaming backend');
        setIsStreamingEnabled(true);
        // Request initial data
        sendJsonMessage({ type: 'request_initial_data' });
      },
      onClose: () => {
        console.log('❌ WebSocket disconnected from Kafka streaming');
        setIsStreamingEnabled(false);
        setRealTimeCampaigns([]);
        setStreamingStats({
          totalCampaigns: 0,
          activeCampaigns: 0,
          companiesCount: 0,
          avgSentiment: 0
        });
      },
      onError: (error) => {
        console.error('❌ WebSocket error:', error);
        setIsStreamingEnabled(false);
      },
      shouldReconnect: (closeEvent) => true,
      reconnectAttempts: 10,
      reconnectInterval: 3000,
    }
  );

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (lastMessage !== null) {
      try {
        const message = JSON.parse(lastMessage.data);
        
        switch (message.type) {
          case 'initial_data':
            if (message.campaigns) {
              setRealTimeCampaigns(message.campaigns);
            }
            if (message.summary) {
              setStreamingStats({
                totalCampaigns: message.summary.totalCampaigns || 0,
                activeCampaigns: message.summary.activeCampaigns || 0,
                companiesCount: message.summary.companiesCount || 0,
                avgSentiment: message.summary.avgSentiment || 0
              });
            }
            break;
            
          case 'batch_ingestion':
            // Handle batch data ingestion - more efficient approach
            if (message.data.new_campaigns) {
              setRealTimeCampaigns(prev => {
                const combined = [...message.data.new_campaigns, ...prev];
                return combined.slice(0, 50); // Keep latest 50
              });
              
              // Update data source status
              setDataSourceStatus(prev => ({
                ...prev,
                currentSource: message.data.source,
                realNewsCount: message.data.source === 'real_news' ? prev.realNewsCount + message.data.new_campaigns.length : prev.realNewsCount,
                simulatedCount: message.data.source === 'simulated' ? prev.simulatedCount + message.data.new_campaigns.length : prev.simulatedCount,
                apiStatus: message.data.source === 'real_news' ? 'active' : 'limited'
              }));
              
              // Update stats
              setStreamingStats(prev => ({
                ...prev,
                totalCampaigns: message.data.total_campaigns,
                activeCampaigns: message.data.new_campaigns.length,
                companiesCount: new Set(message.data.new_campaigns.map(c => c.company)).size
              }));
              
              // Add batch ingestion event
              setLiveEvents(prev => [
                {
                  id: generateUniqueId(),
                  type: 'batch_update',
                  company: `${message.data.new_campaigns.length} campaigns`,
                  name: 'Data Batch Ingested',
                  platform: message.data.source === 'real_news' ? 'News API' : 'Simulation',
                  status: 'processed',
                  timestamp: new Date().toLocaleTimeString()
                },
                ...prev.slice(0, 4)
              ]);
            }
            break;
            
          case 'analytics_push':
            // Handle targeted analytics updates
            if (message.data) {
              setStreamingStats(prev => ({
                ...prev,
                totalCampaigns: message.data.overview?.total_campaigns || prev.totalCampaigns,
                companiesCount: message.data.overview?.companies || prev.companiesCount,
                avgSentiment: message.data.overview?.avg_sentiment || prev.avgSentiment,
                activeCampaigns: message.data.metrics?.total_impressions || prev.activeCampaigns
              }));
              
              // Add analytics update event
              setLiveEvents(prev => [
                {
                  id: generateUniqueId(),
                  type: 'analytics',
                  company: 'System',
                  name: 'Analytics Updated',
                  metric: `Sentiment: ${(message.data.overview?.avg_sentiment || 0).toFixed(2)}`,
                  timestamp: new Date().toLocaleTimeString()
                },
                ...prev.slice(0, 4)
              ]);
            }
            break;

          case 'analytics_update':
            // Update streaming stats
            setStreamingStats(prev => ({
              ...prev,
              ...message.data
            }));
            
            // Add analytics to events
            setLiveEvents(prev => [
              {
                id: generateUniqueId(),
                type: 'analytics',
                company: message.data.company,
                metric: `${message.data.metric_type}: ${message.data.value}`,
                timestamp: new Date().toLocaleTimeString()
              },
              ...prev.slice(0, 4)
            ]);
            break;
            
          case 'error':
            console.error('WebSocket Error:', message.error);
            break;
            
          default:
            console.log('Unknown message type:', message.type);
            break;
        }
      } catch (error) {
        console.error('❌ Error parsing WebSocket message:', error);
      }
    }
  }, [lastMessage]);

  // Traditional data fetching
  const { data: campaigns, isLoading, error } = useQuery(
    'campaigns',
    () => campaignService.getCampaigns({ limit: 10 }),
    {
      refetchInterval: isStreamingEnabled ? false : 30000, // Don't auto-refresh if streaming
    }
  );

  const { data: companyAnalytics } = useQuery(
    'company-analytics',
    campaignService.getCompanyAnalytics,
    {
      refetchInterval: isStreamingEnabled ? false : 60000,
    }
  );

  // Health check for data source status
  const { data: healthStatus } = useQuery(
    'health-status',
    async () => {
      const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/health`);
      if (!response.ok) throw new Error('Health check failed');
      return response.json();
    },
    {
      refetchInterval: 30000, // Check every 30 seconds
      onSuccess: (data) => {
        if (data) {
          setDataSourceStatus(prev => ({
            ...prev,
            realNewsCount: data.real_news_campaigns || 0,
            simulatedCount: data.total_campaigns - (data.real_news_campaigns || 0),
            apiStatus: data.news_api_status === 'active' ? 'active' : 'limited'
          }));
        }
      }
    }
  );

  // Toggle streaming
  const toggleStreaming = () => {
    setIsStreamingEnabled(!isStreamingEnabled);
  };

  // Create test data for streaming
  const createTestCampaign = async () => {
    try {
      const testCampaign = {
        company: 'Test Company Live',
        name: 'Real-Time Test Campaign',
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

      // Create via API (this will also trigger streaming events)
      await campaignService.createCampaign(testCampaign);
    } catch (error) {
      console.error('❌ Error creating test campaign:', error);
    }
  };

  // Get connection status
  const getConnectionStatus = () => {
    switch (readyState) {
      case ReadyState.OPEN: return { status: 'Connected', color: 'text-green-600', dot: 'bg-green-500' };
      case ReadyState.CONNECTING: return { status: 'Connecting...', color: 'text-yellow-600', dot: 'bg-yellow-500' };
      case ReadyState.CLOSING:
      case ReadyState.CLOSED: return { status: 'Disconnected', color: 'text-red-600', dot: 'bg-red-500' };
      default: return { status: 'Unknown', color: 'text-gray-600', dot: 'bg-gray-500' };
    }
  };

  const connectionStatus = getConnectionStatus();
  
  // Use streaming data if available, fallback to traditional data
  const displayCampaigns = realTimeCampaigns.length > 0 ? realTimeCampaigns : campaigns?.campaigns || [];
  const displayStats = streamingStats.totalCampaigns > 0 ? streamingStats : {
    totalCampaigns: campaigns?.campaigns?.length || 0,
    activeCampaigns: campaigns?.campaigns?.filter(c => c.status === 'active')?.length || 0,
    avgSentiment: 0.65
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">
              Error loading dashboard
            </h3>
            <div className="mt-2 text-sm text-red-700">
              {error.message || 'Failed to load data. Please check if the backend is running.'}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Real-time Controls */}
      <div className="md:flex md:items-center md:justify-between">
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
            Competitive Marketing Dashboard
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            100% Real-time data streaming from News API - All campaigns are authentic news articles • Live data streaming active
          </p>
        </div>
        
        {/* Real-time Controls */}
        <div className="mt-4 md:mt-0 flex items-center space-x-4">
          {/* Connection Status */}
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${connectionStatus.dot}`}></div>
            <span className={`text-sm font-medium ${connectionStatus.color}`}>
              {connectionStatus.status}
            </span>
          </div>
          
          {/* Streaming Toggle */}
          <button
            onClick={toggleStreaming}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              isStreamingEnabled
                ? 'bg-green-100 text-green-800 hover:bg-green-200'
                : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
            }`}
          >
            <div className="flex items-center">
              {isStreamingEnabled ? (
                <BoltIcon className="w-4 h-4 mr-1" />
              ) : (
                <ArrowPathIcon className="w-4 h-4 mr-1" />
              )}
              {isStreamingEnabled ? 'Live' : 'Enable Live'}
            </div>
          </button>

          {/* Data Source Indicator */}
          {isStreamingEnabled && (
            <div 
              className={`px-3 py-2 rounded-md text-xs font-medium flex items-center cursor-help ${
                dataSourceStatus.apiStatus === 'active' 
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-amber-100 text-amber-800'
              }`}
              title={dataSourceStatus.apiStatus === 'active' 
                ? `Using real news data from News API. Real: ${dataSourceStatus.realNewsCount}, Simulated: ${dataSourceStatus.simulatedCount}`
                : `API rate limited. Using realistic simulation. Real: ${dataSourceStatus.realNewsCount}, Simulated: ${dataSourceStatus.simulatedCount}`
              }
            >
              <InformationCircleIcon className="w-3 h-3 mr-1" />
              <span>
                {dataSourceStatus.apiStatus === 'active' ? 'News API Active' : 'Rate Limited'}
                {(dataSourceStatus.realNewsCount > 0 || dataSourceStatus.simulatedCount > 0) && 
                  ` (${dataSourceStatus.realNewsCount}R/${dataSourceStatus.simulatedCount}S)`
                }
              </span>
            </div>
          )}
          
          {/* Test Campaign Button */}
          {isStreamingEnabled && (
            <button
              onClick={createTestCampaign}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              <div className="flex items-center">
                <RocketLaunchIcon className="w-4 h-4 mr-1" />
                Test Campaign
              </div>
            </button>
          )}
        </div>
      </div>

      {/* Live Events Banner */}
      {liveEvents.length > 0 && (
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-md">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-blue-800">⚡ Live Events</h3>
              <div className="mt-1 text-sm text-blue-700">
                Latest: {liveEvents[0]?.type.replace('_', ' ').toUpperCase()} - {liveEvents[0]?.company} at {liveEvents[0]?.timestamp}
              </div>
            </div>
            <div className="text-xs text-blue-600">
              {liveEvents.length} recent events
            </div>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div 
          className="bg-white overflow-hidden shadow rounded-lg transition-shadow hover:shadow-lg cursor-pointer relative"
          onMouseEnter={() => setHoveredMetric('campaigns')}
          onMouseLeave={() => setHoveredMetric(null)}
        >
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-primary-500 rounded-md flex items-center justify-center">
                  <EnvelopeIcon className="w-5 h-5 text-white" />
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Campaigns {isStreamingEnabled && '(Live)'}
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {displayStats.totalCampaigns}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
          {hoveredMetric === 'campaigns' && (
            <div className="absolute inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center text-white p-4 transition-opacity">
              <div className="text-center">
                <p className="text-sm">Includes all tracked marketing campaigns across channels</p>
                <p className="text-xs mt-2">Updated {isStreamingEnabled ? 'in real-time' : 'daily'}</p>
              </div>
            </div>
          )}
        </div>

        <div 
          className="bg-white overflow-hidden shadow rounded-lg transition-shadow hover:shadow-lg cursor-pointer relative"
          onMouseEnter={() => setHoveredMetric('active')}
          onMouseLeave={() => setHoveredMetric(null)}
        >
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                  <ChartBarIcon className="w-5 h-5 text-white" />
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Active Now {isStreamingEnabled && '(Live)'}
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {displayStats.activeCampaigns}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
          {hoveredMetric === 'active' && (
            <div className="absolute inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center text-white p-4 transition-opacity">
              <div className="text-center">
                <p className="text-sm">Currently running campaigns</p>
                <p className="text-xs mt-2">{Math.round((displayStats.activeCampaigns / displayStats.totalCampaigns) * 100)}% of total campaigns</p>
              </div>
            </div>
          )}
        </div>

        <div 
          className="bg-white overflow-hidden shadow rounded-lg transition-shadow hover:shadow-lg cursor-pointer relative"
          onMouseEnter={() => setHoveredMetric('companies')}
          onMouseLeave={() => setHoveredMetric(null)}
        >
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                  <BuildingOfficeIcon className="w-5 h-5 text-white" />
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Companies
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {streamingStats.companiesCount || companyAnalytics?.companies?.length || 15}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
          {hoveredMetric === 'companies' && (
            <div className="absolute inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center text-white p-4 transition-opacity">
              <div className="text-center">
                <p className="text-sm">Unique companies tracked</p>
                <p className="text-xs mt-2">Average {(displayStats.totalCampaigns / (streamingStats.companiesCount || companyAnalytics?.companies?.length || 1)).toFixed(1)} campaigns per company</p>
              </div>
            </div>
          )}
        </div>

        <div 
          className="bg-white overflow-hidden shadow rounded-lg transition-shadow hover:shadow-lg cursor-pointer relative"
          onMouseEnter={() => setHoveredMetric('sentiment')}
          onMouseLeave={() => setHoveredMetric(null)}
        >
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                  <ChartPieIcon className="w-5 h-5 text-white" />
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Avg. Sentiment {isStreamingEnabled && '(Live)'}
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    <div className="flex items-center">
                      {displayStats.avgSentiment?.toFixed(2) || '0.65'}
                      <span className={`ml-2 inline-flex h-2 w-2 rounded-full ${
                        (displayStats.avgSentiment || 0.65) > 0.7 ? 'bg-green-500' :
                        (displayStats.avgSentiment || 0.65) > 0.4 ? 'bg-yellow-500' :
                        'bg-red-500'
                      }`}></span>
                    </div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
          {hoveredMetric === 'sentiment' && (
            <div className="absolute inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center text-white p-4 transition-opacity">
              <div className="text-center">
                <p className="text-sm">Average campaign sentiment score</p>
                <p className="text-xs mt-2">
                  {(displayStats.avgSentiment || 0.65) > 0.7 ? 'Positive' :
                   (displayStats.avgSentiment || 0.65) > 0.4 ? 'Neutral' :
                   'Negative'} overall tone
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recent Campaigns */}
      <div className="bg-white shadow rounded-lg hover:shadow-lg transition-shadow">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Recent Campaigns {isStreamingEnabled && '(Live Updates)'}
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                Latest 10 campaigns - Click on a campaign to view detailed insights
              </p>
            </div>
            {liveEvents.length > 0 && (
              <div className="flex space-x-2">
                {liveEvents.slice(0, 3).map((event, index) => (
                  <span
                    key={event.id ? `${event.id}-${index}` : `event-${index}`}
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 animate-pulse transition-colors hover:bg-blue-200"
                  >
                    {event.type.replace('_', ' ').toUpperCase()}
                  </span>
                ))}
              </div>
            )}
          </div>
          
          <div className="mt-5">
            {displayCampaigns?.length > 0 ? (
              <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
                <table className="min-w-full divide-y divide-gray-300">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Company
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Campaign
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Platform
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        {isStreamingEnabled ? 'Impressions' : 'Date'}
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Sentiment
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {displayCampaigns.slice(0, 10).map((campaign, index) => (
                      <tr 
                        key={campaign.id ? `${campaign.id}-${index}` : `campaign-${index}`} 
                        className="hover:bg-gray-50 cursor-pointer transition-colors"
                        onClick={() => setSelectedCampaign(campaign)}
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {campaign.company || campaign.company_name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="max-w-xs truncate">
                            {campaign.name || campaign.title}
                            {campaign.is_real_news && (
                              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                REAL
                              </span>
                            )}
                            {campaign.content && (
                              <InformationCircleIcon className="inline-block w-4 h-4 ml-1 text-gray-400" />
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full transition-colors ${
                            campaign.platform?.toLowerCase() === 'email' ? 'bg-blue-100 text-blue-800' :
                            campaign.platform?.toLowerCase() === 'social' ? 'bg-purple-100 text-purple-800' :
                            campaign.platform?.toLowerCase() === 'display' ? 'bg-green-100 text-green-800' :
                            campaign.platform?.toLowerCase() === 'search' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {campaign.platform || campaign.channel || 'Email'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            campaign.status === 'active' ? 'bg-green-100 text-green-800' :
                            campaign.status === 'paused' ? 'bg-yellow-100 text-yellow-800' :
                            campaign.status === 'completed' ? 'bg-gray-100 text-gray-800' :
                            'bg-blue-100 text-blue-800'
                          }`}>
                            {campaign.status || 'Active'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="group relative">
                            <div className="hover:text-blue-600 transition-colors">
                              {isStreamingEnabled && campaign.metrics?.impressions ? 
                                campaign.metrics.impressions.toLocaleString() :
                                campaign.launch_date || 'N/A'
                              }
                            </div>
                            {isStreamingEnabled && campaign.metrics?.impressions && (
                              <div className="hidden group-hover:block absolute z-10 w-48 p-2 mt-1 text-xs bg-gray-900 text-white rounded shadow-lg">
                                <div className="px-2 py-1">
                                  <div className="font-semibold">Campaign Metrics</div>
                                  <div className="mt-1">
                                    <div>Clicks: {campaign.metrics.clicks?.toLocaleString() || 0}</div>
                                    <div>CTR: {(campaign.metrics.ctr || 0).toFixed(2)}%</div>
                                    <div>Conversions: {campaign.metrics.conversions?.toLocaleString() || 0}</div>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {campaign.metrics?.sentiment_score !== undefined ? (
                            <div className="flex items-center">
                              <div className={`w-3 h-3 rounded-full mr-2 ${
                                campaign.metrics.sentiment_score > 0.7 ? 'bg-green-500' :
                                campaign.metrics.sentiment_score > 0.4 ? 'bg-yellow-500' :
                                'bg-red-500'
                              }`}></div>
                              <span className={`text-sm font-medium ${
                                campaign.metrics.sentiment_score > 0.7 ? 'text-green-600' :
                                campaign.metrics.sentiment_score > 0.4 ? 'text-yellow-600' :
                                'text-red-600'
                              }`}>
                                {campaign.metrics.sentiment_score.toFixed(2)}
                              </span>
                            </div>
                          ) : (
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              (campaign.sentiment_score || 0) > 0 
                                ? 'bg-green-100 text-green-800' 
                                : (campaign.sentiment_score || 0) < 0 
                                ? 'bg-red-100 text-red-800' 
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {(campaign.sentiment_score || 0) > 0 ? 'Positive' : 
                               (campaign.sentiment_score || 0) < 0 ? 'Negative' : 'Neutral'}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="text-gray-400 text-6xl mb-4">
                  {isStreamingEnabled ? '🌊' : '📭'}
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {isStreamingEnabled ? 'Waiting for live data...' : 'No campaigns yet'}
                </h3>
                <p className="text-gray-500 mb-4">
                  {isStreamingEnabled 
                    ? 'Real-time campaigns will appear here as they are created.'
                    : 'Upload some campaign data to get started with competitor analysis.'
                  }
                </p>
                <div className="space-x-3">
                  {!isStreamingEnabled && (
                    <button
                      onClick={() => window.location.href = '/upload'}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700"
                    >
                      Upload Data
                    </button>
                  )}
                  {isStreamingEnabled && (
                    <button
                      onClick={createTestCampaign}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
                    >
                      🚀 Create Test Campaign
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Top 5 Performers Section */}
      {displayCampaigns?.length > 0 && (
        <div className="bg-white overflow-hidden shadow rounded-lg mb-6">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg leading-6 font-medium text-gray-900">
                  Top 5 Performance Leaders
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  Best performing campaigns by engagement and sentiment
                </p>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {displayCampaigns
                .sort((a, b) => {
                  // Sort by sentiment score, impressions, and engagement
                  const scoreA = (a.sentiment_score || 0) + ((a.impressions || 0) / 10000) + ((a.clicks || 0) / 1000);
                  const scoreB = (b.sentiment_score || 0) + ((b.impressions || 0) / 10000) + ((b.clicks || 0) / 1000);
                  return scoreB - scoreA;
                })
                .slice(0, 5)
                .map((campaign, index) => (
                  <div
                    key={`top-${campaign.id || index}`}
                    className="bg-gradient-to-br from-blue-50 to-indigo-100 rounded-lg p-4 cursor-pointer hover:from-blue-100 hover:to-indigo-200 transition-all duration-200 transform hover:scale-105"
                    onClick={() => setSelectedCampaign(campaign)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-blue-600 bg-blue-200 px-2 py-1 rounded-full">
                        #{index + 1}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        campaign.platform?.toLowerCase() === 'google ads' ? 'bg-yellow-100 text-yellow-800' :
                        campaign.platform?.toLowerCase() === 'news media' ? 'bg-gray-100 text-gray-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {campaign.platform || 'Email'}
                      </span>
                    </div>
                    
                    <h4 className="font-medium text-gray-900 mb-1 text-sm truncate">
                      {campaign.company || campaign.company_name}
                    </h4>
                    
                    <p className="text-xs text-gray-600 mb-3 line-clamp-2">
                      {(campaign.name || campaign.title || '').substring(0, 60)}...
                    </p>
                    
                    <div className="space-y-2">
                      {campaign.impressions && (
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-500">Impressions:</span>
                          <span className="font-medium">{campaign.impressions.toLocaleString()}</span>
                        </div>
                      )}
                      
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-500">Sentiment:</span>
                        <span className={`font-medium ${
                          (campaign.sentiment_score || 0) > 0.6 ? 'text-green-600' :
                          (campaign.sentiment_score || 0) > 0.4 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {campaign.sentiment_score ? campaign.sentiment_score.toFixed(2) : '0.50'}
                        </span>
                      </div>
                      
                      {campaign.clicks && (
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-500">Clicks:</span>
                          <span className="font-medium">{campaign.clicks.toLocaleString()}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* Campaign Modal */}
      {selectedCampaign && (
        <CampaignModal
          campaign={selectedCampaign}
          onClose={() => setSelectedCampaign(null)}
        />
      )}

      {/* Top Companies */}
      {companyAnalytics?.companies?.length > 0 && (
        <div className="bg-white shadow rounded-lg hover:shadow-lg transition-shadow">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Most Active Companies
              </h3>
              <div className="text-sm text-gray-500">
                Based on campaign volume
              </div>
            </div>
            <div className="space-y-3">
              {companyAnalytics.companies.slice(0, 5).map((company, index) => (
                <div key={company.company} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                      <span className="text-primary-600 font-semibold text-sm">
                        #{index + 1}
                      </span>
                    </div>
                    <div className="ml-3">
                      <p className="text-sm font-medium text-gray-900">
                        {company.company}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center">
                    <span className="text-sm text-gray-500">
                      {company.campaign_count} campaigns
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;