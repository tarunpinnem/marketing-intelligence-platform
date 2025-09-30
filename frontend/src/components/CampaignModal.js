import React from 'react';
import {
  DocumentTextIcon,
  XMarkIcon,
  ArrowTopRightOnSquareIcon,
  CalendarIcon,
  TagIcon,
  UserGroupIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

const CampaignModal = ({ campaign, onClose }) => {
  if (!campaign) return null;

  const metrics = campaign.metrics || {};
  
  // Channel colors mapping
  const channelColors = {
    email: 'bg-blue-100 text-blue-800',
    social: 'bg-purple-100 text-purple-800',
    display: 'bg-green-100 text-green-800',
    search: 'bg-yellow-100 text-yellow-800',
    default: 'bg-gray-100 text-gray-800'
  };

  // Get color class for channel badge
  const getChannelColor = (channel) => {
    return channelColors[channel?.toLowerCase()] || channelColors.default;
  };

  // Format numbers with commas
  const formatNumber = (num) => {
    return num?.toLocaleString() || '0';
  };

  // Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount || 0);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true"></div>

        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

        <div className="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full sm:p-6">
          {/* Header */}
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="text-2xl font-semibold text-gray-900">{campaign.name || campaign.title}</h3>
              <p className="mt-1 text-sm text-gray-500">by {campaign.company || campaign.company_name}</p>
            </div>
            <button
              onClick={onClose}
              className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {/* Campaign Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left Column - Main Info */}
            <div className="space-y-6">
              {/* Channel & Status */}
              <div className="flex flex-wrap gap-2">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getChannelColor(campaign.platform || campaign.channel)}`}>
                  {campaign.platform || campaign.channel || 'Email'}
                </span>
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                  campaign.status === 'active' ? 'bg-green-100 text-green-800' :
                  campaign.status === 'paused' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {campaign.status || 'Active'}
                </span>
              </div>

              {/* Content */}
              {campaign.content && (
                <div className="prose max-w-none">
                  <h4 className="flex items-center text-sm font-medium text-gray-900 mb-2">
                    <DocumentTextIcon className="h-5 w-5 mr-2 text-gray-400" />
                    Campaign Content
                  </h4>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600 whitespace-pre-line">
                      {campaign.content}
                    </p>
                  </div>
                </div>
              )}

              {/* Subject Line for Email Campaigns */}
              {campaign.subject_line && (
                <div>
                  <h4 className="flex items-center text-sm font-medium text-gray-900 mb-2">
                    <ArrowTopRightOnSquareIcon className="h-5 w-5 mr-2 text-gray-400" />
                    Subject Line
                  </h4>
                  <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
                    {campaign.subject_line}
                  </p>
                </div>
              )}

              {/* Campaign Details */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="flex items-center text-sm font-medium text-gray-900 mb-2">
                    <CalendarIcon className="h-5 w-5 mr-2 text-gray-400" />
                    Launch Date
                  </h4>
                  <p className="text-sm text-gray-600">
                    {campaign.launch_date || 'Not specified'}
                  </p>
                </div>
                <div>
                  <h4 className="flex items-center text-sm font-medium text-gray-900 mb-2">
                    <TagIcon className="h-5 w-5 mr-2 text-gray-400" />
                    Category
                  </h4>
                  <p className="text-sm text-gray-600">
                    {campaign.classification || 'General'}
                  </p>
                </div>
              </div>
            </div>

            {/* Right Column - Metrics & Analytics */}
            <div className="space-y-6">
              {/* Performance Metrics */}
              <div>
                <h4 className="flex items-center text-sm font-medium text-gray-900 mb-4">
                  <ChartBarIcon className="h-5 w-5 mr-2 text-gray-400" />
                  Performance Metrics
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500">Impressions</p>
                    <p className="mt-1 text-lg font-semibold text-gray-900">
                      {formatNumber(metrics.impressions)}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500">Clicks</p>
                    <p className="mt-1 text-lg font-semibold text-gray-900">
                      {formatNumber(metrics.clicks)}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500">CTR</p>
                    <p className="mt-1 text-lg font-semibold text-gray-900">
                      {(metrics.ctr || 0).toFixed(2)}%
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500">Conversions</p>
                    <p className="mt-1 text-lg font-semibold text-gray-900">
                      {formatNumber(metrics.conversions)}
                    </p>
                  </div>
                </div>
              </div>

              {/* Engagement & Sentiment */}
              <div>
                <h4 className="flex items-center text-sm font-medium text-gray-900 mb-4">
                  <UserGroupIcon className="h-5 w-5 mr-2 text-gray-400" />
                  Engagement & Sentiment
                </h4>
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-500">Sentiment Score</span>
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      (metrics.sentiment_score || campaign.sentiment_score || 0) > 0.7 
                        ? 'bg-green-100 text-green-800'
                        : (metrics.sentiment_score || campaign.sentiment_score || 0) > 0.4
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {((metrics.sentiment_score || campaign.sentiment_score || 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        (metrics.sentiment_score || campaign.sentiment_score || 0) > 0.7
                          ? 'bg-green-500'
                          : (metrics.sentiment_score || campaign.sentiment_score || 0) > 0.4
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{
                        width: `${((metrics.sentiment_score || campaign.sentiment_score || 0) * 100)}%`
                      }}
                    ></div>
                  </div>
                </div>
              </div>

              {/* Budget & ROI if available */}
              {(metrics.spend || campaign.budget) && (
                <div>
                  <h4 className="flex items-center text-sm font-medium text-gray-900 mb-4">
                    <CurrencyDollarIcon className="h-5 w-5 mr-2 text-gray-400" />
                    Budget & ROI
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-500">Total Spend</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">
                        {formatCurrency(metrics.spend || campaign.budget)}
                      </p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm text-gray-500">Cost per Click</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">
                        {formatCurrency((metrics.spend || campaign.budget) / (metrics.clicks || 1))}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Keywords/Tags */}
              {campaign.keywords && campaign.keywords.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Keywords</h4>
                  <div className="flex flex-wrap gap-2">
                    {campaign.keywords.map((keyword, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800"
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CampaignModal;