import React from 'react';

const AIInsights = ({ campaign }) => {
  // AI classification types
  const campaignTypes = {
    promotional: {
      color: 'bg-blue-100 text-blue-800',
      description: 'Direct promotional content aimed at driving sales or conversions'
    },
    retention: {
      color: 'bg-green-100 text-green-800',
      description: 'Content focused on maintaining customer relationships'
    },
    awareness: {
      color: 'bg-purple-100 text-purple-800',
      description: 'Brand awareness and market positioning content'
    },
    competitive: {
      color: 'bg-red-100 text-red-800',
      description: 'Content addressing competitor actions or market position'
    }
  };

  // Advanced sentiment analysis
  const sentimentTypes = {
    urgent: {
      threshold: 0.8,
      color: 'text-red-600'
    },
    excited: {
      threshold: 0.7,
      color: 'text-green-600'
    },
    informational: {
      threshold: 0.5,
      color: 'text-blue-600'
    },
    neutral: {
      threshold: 0,
      color: 'text-gray-600'
    }
  };

  const determineCampaignType = (campaign) => {
    // Implement AI logic to determine campaign type
    // This is a placeholder implementation
    const types = Object.keys(campaignTypes);
    return types[Math.floor(Math.random() * types.length)];
  };

  const determineDetailedSentiment = (sentimentScore) => {
    if (sentimentScore >= sentimentTypes.urgent.threshold) return 'urgent';
    if (sentimentScore >= sentimentTypes.excited.threshold) return 'excited';
    if (sentimentScore >= sentimentTypes.informational.threshold) return 'informational';
    return 'neutral';
  };

  const campaignType = determineCampaignType(campaign);
  const sentimentType = determineDetailedSentiment(campaign.metrics?.sentiment_score || 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <span className={`px-3 py-1 rounded-full text-sm ${campaignTypes[campaignType].color}`}>
            {campaignType.charAt(0).toUpperCase() + campaignType.slice(1)}
          </span>
        </div>
        <div className={`text-sm font-medium ${sentimentTypes[sentimentType].color}`}>
          {sentimentType.charAt(0).toUpperCase() + sentimentType.slice(1)}
        </div>
      </div>
      
      <div className="text-sm text-gray-600">
        {campaignTypes[campaignType].description}
      </div>
      
      <div className="border-t pt-2 mt-2">
        <div className="text-xs text-gray-500">
          Confidence Score: {((campaign.metrics?.sentiment_score || 0) * 100).toFixed(1)}%
        </div>
      </div>
    </div>
  );
};

export default AIInsights;