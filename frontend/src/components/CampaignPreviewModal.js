import React from 'react';

const CampaignPreviewModal = ({ campaign, onClose }) => {
  if (!campaign) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
          <h3 className="text-xl font-semibold">Campaign Details</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div className="p-6">
          {/* Header Information */}
          <div className="mb-6">
            <div className="text-2xl font-bold text-gray-900 mb-2">{campaign.name}</div>
            <div className="text-lg text-gray-600">{campaign.company}</div>
          </div>

          {/* Campaign Status */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-sm text-gray-500">Status</div>
              <div className={`text-lg font-semibold ${
                campaign.status === 'active' ? 'text-green-600' :
                campaign.status === 'paused' ? 'text-yellow-600' :
                'text-gray-600'
              }`}>
                {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-sm text-gray-500">Platform</div>
              <div className="text-lg font-semibold text-gray-900">{campaign.platform}</div>
            </div>
          </div>

          {/* Metrics */}
          <div className="bg-gray-50 rounded-lg p-6 mb-6">
            <h4 className="text-lg font-semibold mb-4">Performance Metrics</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-500">Impressions</div>
                <div className="text-xl font-semibold text-gray-900">
                  {campaign.metrics?.impressions?.toLocaleString() || '0'}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-500">CTR</div>
                <div className="text-xl font-semibold text-gray-900">
                  {campaign.metrics?.ctr?.toFixed(2) || '0.00'}%
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-500">Conversions</div>
                <div className="text-xl font-semibold text-gray-900">
                  {campaign.metrics?.conversions?.toLocaleString() || '0'}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-500">Spend</div>
                <div className="text-xl font-semibold text-gray-900">
                  ${campaign.metrics?.spend?.toLocaleString() || '0'}
                </div>
              </div>
            </div>
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <div className="text-sm text-gray-500">Start Date</div>
              <div className="text-base text-gray-900">
                {new Date(campaign.start_date).toLocaleDateString()}
              </div>
            </div>
            {campaign.end_date && (
              <div>
                <div className="text-sm text-gray-500">End Date</div>
                <div className="text-base text-gray-900">
                  {new Date(campaign.end_date).toLocaleDateString()}
                </div>
              </div>
            )}
          </div>

          {/* Additional Information */}
          {campaign.description && (
            <div className="mb-6">
              <h4 className="text-lg font-semibold mb-2">Campaign Description</h4>
              <div className="text-gray-600">{campaign.description}</div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Close
            </button>
            <button
              onClick={() => {/* Implement export */}}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              Export Details
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CampaignPreviewModal;