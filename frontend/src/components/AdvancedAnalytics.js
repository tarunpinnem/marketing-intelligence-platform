import React from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const AdvancedAnalytics = ({ campaigns, crossChannelMetrics, trendingKeywords }) => {
  // Calculate campaign frequency trends (week-over-week)
  const calculateWeeklyTrends = () => {
    const weeklyData = {};
    campaigns.forEach(campaign => {
      const week = new Date(campaign.start_date).toISOString().slice(0, 10);
      weeklyData[week] = (weeklyData[week] || 0) + 1;
    });
    return Object.entries(weeklyData).map(([date, count]) => ({
      date,
      campaigns: count
    }));
  };

  // Process cross-channel analysis data
  const processChannelData = () => {
    const channelData = {};
    campaigns.forEach(campaign => {
      const platform = campaign.platform;
      channelData[platform] = (channelData[platform] || 0) + 1;
    });
    return Object.entries(channelData).map(([platform, count]) => ({
      platform,
      campaigns: count
    }));
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
      {/* Weekly Campaign Trends */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-xl font-semibold mb-4">Campaign Frequency Trends</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={calculateWeeklyTrends()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="campaigns" stroke="#4F46E5" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Cross-Channel Analysis */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-xl font-semibold mb-4">Channel Distribution</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={processChannelData()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="platform" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="campaigns" fill="#4F46E5" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Trending Keywords */}
      <div className="bg-white rounded-lg shadow-md p-6 col-span-2">
        <h3 className="text-xl font-semibold mb-4">Trending Keywords</h3>
        <div className="flex flex-wrap gap-2">
          {trendingKeywords.map((keyword, index) => (
            <span
              key={index}
              className="px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-sm"
              style={{ fontSize: `${Math.max(0.8, keyword.weight)}em` }}
            >
              {keyword.text}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AdvancedAnalytics;