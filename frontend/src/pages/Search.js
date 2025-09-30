import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { campaignService } from '../services/api';

const Search = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    company: '',
    channel: '',
    date_from: '',
    date_to: ''
  });
  const [searchTrigger, setSearchTrigger] = useState(0);
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [showInsights, setShowInsights] = useState(false);

  const { data: searchResults, isLoading, error } = useQuery(
    ['search', searchQuery, filters, searchTrigger],
    async () => {
      if (!searchQuery.trim()) return { results: [], total: 0 };
      try {
        const response = await campaignService.searchCampaigns({
          query: searchQuery,
          company: filters.company,
          channel: filters.channel,
          date_from: filters.date_from,
          date_to: filters.date_to
        });
        return {
          results: response?.campaigns || [],
          total: response?.total || 0,
          query: response?.query || searchQuery,
          message: response?.message || ''
        };
      } catch (err) {
        console.error('Search error:', err);
        throw new Error(err.response?.data?.detail || 'Failed to fetch search results');
      }
    },
    {
      enabled: !!searchQuery.trim(),
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      onError: (err) => {
        console.error('Search query error:', err);
      }
    }
  );

  const handleSearch = (e) => {
    e.preventDefault();
    setSearchTrigger(prev => prev + 1);
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const clearFilters = () => {
    setFilters({
      company: '',
      channel: '',
      date_from: '',
      date_to: ''
    });
    setSearchQuery('');
  };

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="sm:flex sm:items-center sm:justify-between">
            <div>
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Search Campaigns
              </h3>
              <p className="mt-1 max-w-2xl text-sm text-gray-500">
                Find competitor campaigns using keywords, company names, and filters
              </p>
            </div>
          </div>

          <form onSubmit={handleSearch} className="mt-6 space-y-4">
            <div>
              <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-2">
                Search campaigns
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  id="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Enter keywords, campaign names, or company names..."
                  className="flex-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
                <button
                  type="submit"
                  disabled={!searchQuery.trim() || isLoading}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? 'Searching...' : 'Search'}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
              <div>
                <label htmlFor="company" className="block text-sm font-medium text-gray-700 mb-1">
                  Company
                </label>
                <input
                  type="text"
                  id="company"
                  value={filters.company}
                  onChange={(e) => handleFilterChange('company', e.target.value)}
                  placeholder="Company name"
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <div>
                <label htmlFor="channel" className="block text-sm font-medium text-gray-700 mb-1">
                  Channel
                </label>
                <select
                  id="channel"
                  value={filters.channel}
                  onChange={(e) => handleFilterChange('channel', e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                >
                  <option value="">All channels</option>
                  <option value="email">Email</option>
                  <option value="social">Social Media</option>
                  <option value="display">Display</option>
                  <option value="search">Search</option>
                  <option value="video">Video</option>
                </select>
              </div>

              <div>
                <label htmlFor="date_from" className="block text-sm font-medium text-gray-700 mb-1">
                  From Date
                </label>
                <input
                  type="date"
                  id="date_from"
                  value={filters.date_from}
                  onChange={(e) => handleFilterChange('date_from', e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <div>
                <label htmlFor="date_to" className="block text-sm font-medium text-gray-700 mb-1">
                  To Date
                </label>
                <input
                  type="date"
                  id="date_to"
                  value={filters.date_to}
                  onChange={(e) => handleFilterChange('date_to', e.target.value)}
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={clearFilters}
                className="mr-3 inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Clear Filters
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">Searching campaigns...</span>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="rounded-md bg-red-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800 mb-1">Search Error</h3>
                  <div className="text-sm text-red-700">
                    {error.message}
                  </div>
                  <div className="mt-2 text-xs text-red-600">
                    Please try again or adjust your search criteria.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Search Results */}
      {searchResults && !isLoading && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                Search Results
              </h3>
              <span className="text-sm text-gray-500">
                {searchResults?.total || 0} results found
              </span>
            </div>

            {searchResults?.message && (
              <div className="mb-4 p-3 bg-blue-50 rounded-md">
                <p className="text-sm text-blue-700">{searchResults.message}</p>
              </div>
            )}

            {searchResults?.results?.length > 0 ? (
              <div className="space-y-4">
                {searchResults.results.map((campaign) => (
                  <div
                    key={campaign.id}
                    className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <h4 className="text-lg font-semibold text-gray-900">
                            {campaign.name || 'Untitled Campaign'}
                          </h4>
                          <span className="text-sm text-gray-500">
                            by {campaign.company || 'Unknown Company'}
                          </span>
                        </div>
                        
                        {campaign.content && (
                          <p className="text-sm text-gray-600 mb-2">
                            {campaign.content.length > 200 ? 
                              `${campaign.content.substring(0, 200)}...` : 
                              campaign.content
                            }
                          </p>
                        )}
                      </div>
                      
                      <div className="flex flex-col items-end space-y-2">
                        {campaign.sentiment_score !== undefined && (
                          <span className={`text-xs px-2 py-1 rounded-full ${
                            campaign.sentiment_score > 0.6 ? 'bg-green-100 text-green-800' :
                            campaign.sentiment_score > 0.4 ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {campaign.sentiment_score > 0.6 ? 'Positive' : 
                             campaign.sentiment_score > 0.4 ? 'Neutral' : 'Negative'}
                          </span>
                        )}
                        
                        <span className="text-xs text-gray-500">
                          {campaign.platform || 'Unknown Platform'}
                        </span>
                      </div>
                    </div>
                    
                    <div className="mt-3 flex flex-wrap gap-2">
                      {campaign.status && (
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          campaign.status === 'active' ? 'bg-green-100 text-green-800' : 
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {campaign.status}
                        </span>
                      )}
                      
                      {campaign.budget && (
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                          Budget: ${campaign.budget.toLocaleString()}
                        </span>
                      )}
                    </div>
                    
                    {(campaign.impressions || campaign.clicks || campaign.conversions) && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <div className="grid grid-cols-3 gap-4">
                          {campaign.impressions && (
                            <div className="text-center">
                              <div className="text-lg font-semibold text-gray-900">{campaign.impressions.toLocaleString()}</div>
                              <div className="text-xs text-gray-500">Impressions</div>
                            </div>
                          )}
                          {campaign.clicks && (
                            <div className="text-center">
                              <div className="text-lg font-semibold text-gray-900">{campaign.clicks.toLocaleString()}</div>
                              <div className="text-xs text-gray-500">Clicks</div>
                            </div>
                          )}
                          {campaign.conversions && (
                            <div className="text-center">
                              <div className="text-lg font-semibold text-gray-900">{campaign.conversions.toLocaleString()}</div>
                              <div className="text-xs text-gray-500">Conversions</div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : searchQuery && (
              <div className="text-center py-8">
                <div className="text-gray-500">
                  <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                    <path d="M21 21l6 6M15 21a6 6 0 112.086-11.657L21 15" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No results found</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Try adjusting your search query or filters.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Search;