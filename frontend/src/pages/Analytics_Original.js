import React, { useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'rech              <div className="flex-shrink-0">
                <div className="w-                <div className="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                  <span className="text-white text-sm font-semibold">I</span>
                </div>-8 bg-blue-500 rounded-md flex items-center justify-center">
                  <span className="text-white text-sm font-semibold">#</span>
                </div>
              </div>;
import { campaignService } from '../services/api';

const Analytics = () => {
  const [analysisMode, setAnalysisMode] = useState('overview'); // 'overview', 'sentiment', 'performance', 'competitive'

  // Fetch real campaign data for analysis
  const { data: campaignsResponse, isLoading: loadingCampaigns } = useQuery(
    'campaigns-for-analytics',
    () => campaignService.getCampaigns({ limit: 100 }),
    {
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  );

  const { isLoading: loadingAnalytics } = useQuery(
    'analytics-data',
    campaignService.getCompanyAnalytics,
    {
      refetchInterval: 30000,
    }
  );

  const campaigns = useMemo(() => campaignsResponse?.campaigns || [], [campaignsResponse]);

  // Real-time analytics calculations
  const analyticsResults = useMemo(() => {
    if (!campaigns.length) return null;

    // 1. Sentiment Analysis
    const sentimentScores = campaigns.map(c => c.sentiment_score || 0.5);
    const avgSentiment = sentimentScores.reduce((a, b) => a + b, 0) / sentimentScores.length;
    
    const sentimentDistribution = {
      positive: campaigns.filter(c => (c.sentiment_score || 0.5) > 0.6).length,
      neutral: campaigns.filter(c => (c.sentiment_score || 0.5) >= 0.4 && (c.sentiment_score || 0.5) <= 0.6).length,
      negative: campaigns.filter(c => (c.sentiment_score || 0.5) < 0.4).length
    };

    // 2. Company Performance Analysis
    const companyStats = {};
    campaigns.forEach(campaign => {
      const company = campaign.company || campaign.company_name || 'Unknown';
      if (!companyStats[company]) {
        companyStats[company] = {
          name: company,
          campaign_count: 0,
          total_spend: 0,
          total_impressions: 0,
          total_clicks: 0,
          total_conversions: 0,
          sentiment_scores: [],
          platforms: new Set(),
          active_campaigns: 0
        };
      }
      
      const stats = companyStats[company];
      stats.campaign_count++;
      stats.total_spend += campaign.spend || campaign.metrics?.spend || 0;
      stats.total_impressions += campaign.impressions || campaign.metrics?.impressions || 0;
      stats.total_clicks += campaign.clicks || campaign.metrics?.clicks || 0;
      stats.total_conversions += campaign.conversions || campaign.metrics?.conversions || 0;
      stats.sentiment_scores.push(campaign.sentiment_score || 0.5);
      stats.platforms.add(campaign.platform || campaign.channel || 'Email');
      if (campaign.status === 'active') stats.active_campaigns++;
    });

    // Calculate derived metrics for each company
    const companyAnalysis = Object.values(companyStats).map(company => ({
      ...company,
      avg_sentiment: company.sentiment_scores.reduce((a, b) => a + b, 0) / company.sentiment_scores.length,
      ctr: company.total_impressions > 0 ? (company.total_clicks / company.total_impressions) * 100 : 0,
      conversion_rate: company.total_clicks > 0 ? (company.total_conversions / company.total_clicks) * 100 : 0,
      avg_cpc: company.total_clicks > 0 ? company.total_spend / company.total_clicks : 0,
      platform_diversity: company.platforms.size,
      platforms: Array.from(company.platforms)
    })).sort((a, b) => b.campaign_count - a.campaign_count);

    // 3. Channel/Platform Analysis
    const platformStats = {};
    campaigns.forEach(campaign => {
      const platform = campaign.platform || campaign.channel || 'Email';
      if (!platformStats[platform]) {
        platformStats[platform] = { name: platform, campaigns: 0, total_spend: 0, avg_sentiment: 0 };
      }
      platformStats[platform].campaigns++;
      platformStats[platform].total_spend += campaign.spend || campaign.metrics?.spend || 0;
    });

    const channelAnalysis = Object.values(platformStats).map(platform => ({
      ...platform,
      percentage: (platform.campaigns / campaigns.length) * 100
    })).sort((a, b) => b.campaigns - a.campaigns);

    // 4. Time-based Trend Analysis
    const monthlyTrends = {};
    campaigns.forEach(campaign => {
      const date = new Date(campaign.start_date || campaign.launch_date || campaign.created_at || Date.now());
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      
      if (!monthlyTrends[monthKey]) {
        monthlyTrends[monthKey] = {
          month: date.toISOString(),
          campaign_count: 0,
          total_spend: 0,
          avg_sentiment: 0,
          sentiment_scores: []
        };
      }
      
      monthlyTrends[monthKey].campaign_count++;
      monthlyTrends[monthKey].total_spend += campaign.spend || campaign.metrics?.spend || 0;
      monthlyTrends[monthKey].sentiment_scores.push(campaign.sentiment_score || 0.5);
    });

    const trendAnalysis = Object.values(monthlyTrends).map(trend => ({
      ...trend,
      avg_sentiment: trend.sentiment_scores.reduce((a, b) => a + b, 0) / trend.sentiment_scores.length
    })).sort((a, b) => new Date(a.month) - new Date(b.month));

    // 5. Performance Insights
    const topPerformer = companyAnalysis.reduce((prev, current) => 
      (current.conversion_rate > prev.conversion_rate) ? current : prev
    );

    const mostActive = companyAnalysis[0]; // Already sorted by campaign count
    const highestSpender = companyAnalysis.reduce((prev, current) => 
      (current.total_spend > prev.total_spend) ? current : prev
    );

    const bestSentiment = companyAnalysis.reduce((prev, current) => 
      (current.avg_sentiment > prev.avg_sentiment) ? current : prev
    );

    return {
      overview: {
        totalCampaigns: campaigns.length,
        activeCampaigns: campaigns.filter(c => c.status === 'active').length,
        totalCompanies: companyAnalysis.length,
        avgSentiment,
        totalSpend: companyAnalysis.reduce((sum, c) => sum + c.total_spend, 0),
        totalImpressions: companyAnalysis.reduce((sum, c) => sum + c.total_impressions, 0),
        avgCTR: companyAnalysis.reduce((sum, c) => sum + c.ctr, 0) / companyAnalysis.length
      },
      sentiment: {
        distribution: [
          { name: 'Positive', value: Math.round((sentimentDistribution.positive / campaigns.length) * 100), color: '#10B981', count: sentimentDistribution.positive },
          { name: 'Neutral', value: Math.round((sentimentDistribution.neutral / campaigns.length) * 100), color: '#6B7280', count: sentimentDistribution.neutral },
          { name: 'Negative', value: Math.round((sentimentDistribution.negative / campaigns.length) * 100), color: '#EF4444', count: sentimentDistribution.negative }
        ],
        avgScore: avgSentiment
      },
      companies: companyAnalysis,
      channels: channelAnalysis,
      trends: trendAnalysis,
      insights: {
        mostActive,
        topPerformer,
        highestSpender,
        bestSentiment,
        trendingPlatform: channelAnalysis[0]?.name || 'Email'
      }
    };
  }, [campaigns]);

  // Colors for charts
  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4'];

  if (loadingCampaigns || loadingAnalytics || !analyticsResults) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">🧠 Analyzing campaign data...</p>
          <p className="text-sm text-gray-500 mt-1">
            Processing {campaigns.length} campaigns for insights
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Analysis Mode Tabs */}
      <div>
        <div className="md:flex md:items-center md:justify-between">
          <div className="min-w-0 flex-1">
            <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
              Real-Time Analytics & Insights
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              AI-powered analysis of {analyticsResults.overview.totalCampaigns} campaigns from {analyticsResults.overview.totalCompanies} companies
            </p>
          </div>
        </div>
        
        {/* Analysis Mode Tabs */}
        <div className="mt-4">
          <nav className="flex space-x-8">
            {[
              { id: 'overview', name: 'Overview', desc: 'Key metrics' },
              { id: 'sentiment', name: 'Sentiment', desc: 'Emotion analysis' },
              { id: 'performance', name: 'Performance', desc: 'ROI & metrics' },
              { id: 'competitive', name: 'Competitive', desc: 'Market position' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setAnalysisMode(tab.id)}
                className={`${
                  analysisMode === tab.id
                    ? 'border-primary-500 text-primary-600 bg-primary-50'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-2 px-3 border-b-2 font-medium text-sm rounded-t-lg transition-colors`}
              >
                <div className="text-center">
                  <div>{tab.name}</div>
                  <div className="text-xs text-gray-400">{tab.desc}</div>
                </div>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Real-time Key Metrics Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white overflow-hidden shadow rounded-lg border-l-4 border-blue-500">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                  <span className="text-white text-sm">�</span>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Campaigns (Live)
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {analyticsResults.overview.totalCampaigns.toLocaleString()}
                  </dd>
                  <dd className="text-xs text-green-600">
                    {analyticsResults.overview.activeCampaigns} active
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg border-l-4 border-green-500">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                  <span className="text-white text-sm font-semibold">S</span>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Avg Sentiment (Real)
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {analyticsResults.overview.avgSentiment.toFixed(3)}
                  </dd>
                  <dd className={`text-xs ${analyticsResults.overview.avgSentiment > 0.6 ? 'text-green-600' : analyticsResults.overview.avgSentiment > 0.4 ? 'text-yellow-600' : 'text-red-600'}`}>
                    {analyticsResults.overview.avgSentiment > 0.6 ? '↗ Positive' : analyticsResults.overview.avgSentiment > 0.4 ? '→ Neutral' : '↘ Negative'} trend
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg border-l-4 border-purple-500">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                  <span className="text-white text-sm font-semibold">$</span>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Ad Spend
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    ${analyticsResults.overview.totalSpend.toLocaleString()}
                  </dd>
                  <dd className="text-xs text-blue-600">
                    Avg CTR: {analyticsResults.overview.avgCTR.toFixed(2)}%
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg border-l-4 border-yellow-500">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                  <span className="text-white text-sm">�️</span>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Impressions
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {analyticsResults.overview.totalImpressions.toLocaleString()}
                  </dd>
                  <dd className="text-xs text-purple-600">
                    {analyticsResults.overview.totalCompanies} companies
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Dynamic Charts Grid based on Analysis Mode */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Company Performance Analysis */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              🏢 Real Company Performance Analysis
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analyticsResults.companies.slice(0, 8)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="name" 
                  tick={{ fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis />
                <Tooltip 
                  formatter={(value, name) => [
                    name === 'campaign_count' ? `${value} campaigns` : 
                    name === 'total_spend' ? `$${value.toLocaleString()}` :
                    name === 'ctr' ? `${value.toFixed(2)}%` :
                    value.toFixed(3),
                    name === 'campaign_count' ? 'Campaigns' :
                    name === 'total_spend' ? 'Total Spend' :
                    name === 'ctr' ? 'CTR' :
                    name === 'avg_sentiment' ? 'Avg Sentiment' :
                    name
                  ]}
                  labelFormatter={(label) => `Company: ${label}`}
                />
                {analysisMode === 'overview' && <Bar dataKey="campaign_count" fill="#3B82F6" name="campaign_count" />}
                {analysisMode === 'performance' && <Bar dataKey="total_spend" fill="#10B981" name="total_spend" />}
                {analysisMode === 'sentiment' && <Bar dataKey="avg_sentiment" fill="#F59E0B" name="avg_sentiment" />}
                {analysisMode === 'competitive' && <Bar dataKey="ctr" fill="#8B5CF6" name="ctr" />}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Real-Time Trends Analysis */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              📈 Campaign Trends Over Time (Real Data)
            </h3>
            {analyticsResults.trends.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={analyticsResults.trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="month" 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => {
                      const date = new Date(value);
                      return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
                    }}
                  />
                  <YAxis />
                  <Tooltip 
                    labelFormatter={(value) => {
                      const date = new Date(value);
                      return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
                    }}
                    formatter={(value, name) => [
                      name === 'campaign_count' ? `${value} campaigns` :
                      name === 'total_spend' ? `$${value.toLocaleString()}` :
                      name === 'avg_sentiment' ? value.toFixed(3) :
                      value,
                      name === 'campaign_count' ? 'Campaigns' :
                      name === 'total_spend' ? 'Spend' :
                      name === 'avg_sentiment' ? 'Sentiment' :
                      name
                    ]}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="campaign_count" 
                    stroke="#10B981" 
                    strokeWidth={2}
                    dot={{ fill: '#10B981' }}
                    name="campaign_count"
                  />
                  {analysisMode === 'sentiment' && (
                    <Line 
                      type="monotone" 
                      dataKey="avg_sentiment" 
                      stroke="#F59E0B" 
                      strokeWidth={2}
                      dot={{ fill: '#F59E0B' }}
                      name="avg_sentiment"
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex justify-center items-center h-64 text-gray-500">
                <div className="text-center">
                  <div className="text-6xl mb-4">📊</div>
                  <p>Collecting trend data...</p>
                  <p className="text-sm">More data needed for timeline analysis</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Real Sentiment Distribution */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              😊 Live Sentiment Analysis
              <span className="text-sm text-gray-500 ml-2">
                (Analyzed {campaigns.length} campaigns)
              </span>
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={analyticsResults.sentiment.distribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value, count }) => `${name}: ${value}% (${count})`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {analyticsResults.sentiment.distribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(value, name, props) => [
                    `${value}% (${props.payload.count} campaigns)`,
                    name
                  ]}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">
                Overall Sentiment Score: <span className={`font-bold ${
                  analyticsResults.sentiment.avgScore > 0.6 ? 'text-green-600' :
                  analyticsResults.sentiment.avgScore > 0.4 ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {analyticsResults.sentiment.avgScore.toFixed(3)}
                </span>
              </p>
            </div>
          </div>
        </div>

        {/* Real Channel Distribution */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              📱 Channel Distribution (Live Data)
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analyticsResults.channels} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={80} />
                <Tooltip 
                  formatter={(value, name) => [
                    name === 'campaigns' ? `${value} campaigns` :
                    name === 'percentage' ? `${value.toFixed(1)}%` :
                    name === 'total_spend' ? `$${value.toLocaleString()}` :
                    value,
                    name === 'campaigns' ? 'Campaign Count' :
                    name === 'percentage' ? 'Percentage' :
                    name === 'total_spend' ? 'Total Spend' :
                    name
                  ]}
                />
                <Bar dataKey="campaigns" fill="#8B5CF6" name="campaigns" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Real-Time AI Insights Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* AI-Generated Insights */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              🧠 AI-Powered Insights (Live Analysis)
            </h3>
            <div className="space-y-4">
              <div className="border-l-4 border-blue-400 pl-4">
                <p className="text-sm text-gray-700">
                  <strong>Most Active Competitor:</strong> {analyticsResults.insights.mostActive.name} leads with {analyticsResults.insights.mostActive.campaign_count} campaigns and ${analyticsResults.insights.mostActive.total_spend.toLocaleString()} total spend.
                </p>
              </div>
              <div className="border-l-4 border-green-400 pl-4">
                <p className="text-sm text-gray-700">
                  <strong>Best Performer:</strong> {analyticsResults.insights.topPerformer.name} achieves {analyticsResults.insights.topPerformer.conversion_rate.toFixed(2)}% conversion rate with {analyticsResults.insights.topPerformer.platform_diversity} different channels.
                </p>
              </div>
              <div className="border-l-4 border-yellow-400 pl-4">
                <p className="text-sm text-gray-700">
                  <strong>Sentiment Leader:</strong> {analyticsResults.insights.bestSentiment.name} maintains the highest sentiment score of {analyticsResults.insights.bestSentiment.avg_sentiment.toFixed(3)} across their campaigns.
                </p>
              </div>
              <div className="border-l-4 border-purple-400 pl-4">
                <p className="text-sm text-gray-700">
                  <strong>Channel Trend:</strong> {analyticsResults.insights.trendingPlatform} dominates with {analyticsResults.channels[0]?.campaigns} campaigns ({analyticsResults.channels[0]?.percentage.toFixed(1)}% of total activity).
                </p>
              </div>
              <div className="border-l-4 border-red-400 pl-4">
                <p className="text-sm text-gray-700">
                  <strong>Spending Analysis:</strong> {analyticsResults.insights.highestSpender.name} has the largest ad budget of ${analyticsResults.insights.highestSpender.total_spend.toLocaleString()} with ${analyticsResults.insights.highestSpender.avg_cpc.toFixed(2)} average CPC.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Live Competitive Intelligence */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              🎯 Live Competitive Intelligence
            </h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-900">Top Campaign Volume</p>
                  <p className="text-xs text-gray-500">Highest activity competitor</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-primary-600">{analyticsResults.insights.mostActive.name}</p>
                  <p className="text-xs text-gray-500">{analyticsResults.insights.mostActive.campaign_count} campaigns</p>
                </div>
              </div>
              
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-900">Best Conversion Rate</p>
                  <p className="text-xs text-gray-500">Most efficient campaigns</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-green-600">{analyticsResults.insights.topPerformer.name}</p>
                  <p className="text-xs text-gray-500">{analyticsResults.insights.topPerformer.conversion_rate.toFixed(2)}% CVR</p>
                </div>
              </div>
              
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-900">Highest Ad Spend</p>
                  <p className="text-xs text-gray-500">Largest advertising budget</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-blue-600">{analyticsResults.insights.highestSpender.name}</p>
                  <p className="text-xs text-gray-500">${analyticsResults.insights.highestSpender.total_spend.toLocaleString()}</p>
                </div>
              </div>
              
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-900">Best Customer Sentiment</p>
                  <p className="text-xs text-gray-500">Most positive messaging</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-purple-600">{analyticsResults.insights.bestSentiment.name}</p>
                  <p className="text-xs text-gray-500">{analyticsResults.insights.bestSentiment.avg_sentiment.toFixed(3)} score</p>
                </div>
              </div>

              <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div>
                  <p className="text-sm font-medium text-blue-900">Market Overview</p>
                  <p className="text-xs text-blue-700">Current competitive landscape</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-blue-800">{analyticsResults.overview.totalCompanies} Competitors</p>
                  <p className="text-xs text-blue-600">{analyticsResults.overview.activeCampaigns} active campaigns</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Matrix - Advanced Analytics */}
      {analysisMode === 'performance' && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              🚀 Advanced Performance Matrix
            </h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-300">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Company</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Campaigns</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total Spend</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">CTR</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Conversion Rate</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg CPC</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Channels</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sentiment</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {analyticsResults.companies.slice(0, 10).map((company) => (
                    <tr key={company.name} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {company.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div className="flex items-center">
                          <span className="mr-2">{company.campaign_count}</span>
                          <span className="text-xs text-green-600">({company.active_campaigns} active)</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${company.total_spend.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          company.ctr > 2 ? 'bg-green-100 text-green-800' :
                          company.ctr > 1 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {company.ctr.toFixed(2)}%
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          company.conversion_rate > 5 ? 'bg-green-100 text-green-800' :
                          company.conversion_rate > 2 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {company.conversion_rate.toFixed(2)}%
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${company.avg_cpc.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div className="flex flex-wrap gap-1">
                          {company.platforms.slice(0, 2).map((platform, idx) => (
                            <span key={idx} className="inline-flex px-1 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">
                              {platform}
                            </span>
                          ))}
                          {company.platforms.length > 2 && (
                            <span className="text-xs text-gray-500">+{company.platforms.length - 2}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div className="flex items-center">
                          <div className={`w-3 h-3 rounded-full mr-2 ${
                            company.avg_sentiment > 0.6 ? 'bg-green-500' :
                            company.avg_sentiment > 0.4 ? 'bg-yellow-500' :
                            'bg-red-500'
                          }`}></div>
                          <span className={`text-sm font-medium ${
                            company.avg_sentiment > 0.6 ? 'text-green-600' :
                            company.avg_sentiment > 0.4 ? 'text-yellow-600' :
                            'text-red-600'
                          }`}>
                            {company.avg_sentiment.toFixed(3)}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Export Options */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                📊 Export Real-Time Analytics
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                Download live analysis reports and insights based on {analyticsResults.overview.totalCampaigns} campaigns
              </p>
            </div>
            <div className="flex space-x-3">
              <button 
                onClick={() => {
                  const dataStr = JSON.stringify(analyticsResults, null, 2);
                  const dataBlob = new Blob([dataStr], {type:'application/json'});
                  const url = URL.createObjectURL(dataBlob);
                  const link = document.createElement('a');
                  link.href = url;
                  link.download = `competiscan-analytics-${new Date().toISOString().split('T')[0]}.json`;
                  link.click();
                }}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                � Export Data
              </button>
              <button 
                onClick={() => {
                  const reportContent = `# Competiscan Analytics Report
Generated: ${new Date().toLocaleString()}

## Overview
- Total Campaigns: ${analyticsResults.overview.totalCampaigns}
- Active Campaigns: ${analyticsResults.overview.activeCampaigns}
- Companies Analyzed: ${analyticsResults.overview.totalCompanies}
- Average Sentiment: ${analyticsResults.overview.avgSentiment.toFixed(3)}
- Total Ad Spend: $${analyticsResults.overview.totalSpend.toLocaleString()}

## Top Performers
- Most Active: ${analyticsResults.insights.mostActive.name} (${analyticsResults.insights.mostActive.campaign_count} campaigns)
- Best Conversion: ${analyticsResults.insights.topPerformer.name} (${analyticsResults.insights.topPerformer.conversion_rate.toFixed(2)}%)
- Highest Spend: ${analyticsResults.insights.highestSpender.name} ($${analyticsResults.insights.highestSpender.total_spend.toLocaleString()})
- Best Sentiment: ${analyticsResults.insights.bestSentiment.name} (${analyticsResults.insights.bestSentiment.avg_sentiment.toFixed(3)})

## Channel Distribution
${analyticsResults.channels.map(c => `- ${c.name}: ${c.campaigns} campaigns (${c.percentage.toFixed(1)}%)`).join('\n')}

## Sentiment Analysis
- Positive: ${analyticsResults.sentiment.distribution.find(s => s.name === 'Positive')?.value || 0}% (${analyticsResults.sentiment.distribution.find(s => s.name === 'Positive')?.count || 0} campaigns)
- Neutral: ${analyticsResults.sentiment.distribution.find(s => s.name === 'Neutral')?.value || 0}% (${analyticsResults.sentiment.distribution.find(s => s.name === 'Neutral')?.count || 0} campaigns)
- Negative: ${analyticsResults.sentiment.distribution.find(s => s.name === 'Negative')?.value || 0}% (${analyticsResults.sentiment.distribution.find(s => s.name === 'Negative')?.count || 0} campaigns)
`;
                  
                  const reportBlob = new Blob([reportContent], {type:'text/markdown'});
                  const url = URL.createObjectURL(reportBlob);
                  const link = document.createElement('a');
                  link.href = url;
                  link.download = `competiscan-report-${new Date().toISOString().split('T')[0]}.md`;
                  link.click();
                }}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                📈 Download Report
              </button>
              <button 
                className="inline-flex items-center px-4 py-2 bg-primary-600 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                onClick={() => window.location.reload()}
              >
                🔄 Refresh Analysis
              </button>
            </div>
          </div>
          
          {/* Analysis Summary */}
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="flex items-center">
                <div className="text-blue-500 text-2xl mr-3">🎯</div>
                <div>
                  <h4 className="text-sm font-medium text-blue-900">Analysis Scope</h4>
                  <p className="text-sm text-blue-700">{analyticsResults.overview.totalCampaigns} campaigns analyzed across {analyticsResults.overview.totalCompanies} companies</p>
                </div>
              </div>
            </div>
            
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="flex items-center">
                <div className="text-green-500 text-2xl mr-3">💰</div>
                <div>
                  <h4 className="text-sm font-medium text-green-900">Market Value</h4>
                  <p className="text-sm text-green-700">Total tracked spend: ${analyticsResults.overview.totalSpend.toLocaleString()}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="flex items-center">
                <div className="text-purple-500 text-2xl mr-3">📊</div>
                <div>
                  <h4 className="text-sm font-medium text-purple-900">Live Updates</h4>
                  <p className="text-sm text-purple-700">Data refreshes every 30 seconds automatically</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;