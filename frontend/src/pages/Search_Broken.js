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

  const { data: searchResults, isLoading, error } = useQuery(
    ['search', searchQuery, filters, searchTrigger],
    async () => {
      if (!searchQuery.trim()) return { results: [], total: 0 };
      try {
        const response = await campaignService.searchCampaigns({
          q: searchQuery,
          company: filters.company,
          channel: filters.channel,
          date_from: filters.date_from,
          date_to: filters.date_to
        });
        return {
          results: response?.campaigns || [],
          total: response?.total || 0,
          query: response?.query || searchQuery
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
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
          Search Campaigns
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Find competitor campaigns using keywords, company names, and filters
        </p>
      </div>

      {/* Search Form */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <form onSubmit={handleSearch} className="space-y-4">
            {/* Main Search Bar */}
            <div>
              <label htmlFor="search" className="block text-sm font-medium text-gray-700">
                Search campaigns
              </label>
              <div className="mt-1 flex rounded-md shadow-sm">
                <input
                  type="text"
                  id="search"
                  className="flex-1 min-w-0 block w-full px-3 py-2 rounded-none rounded-l-md border-gray-300 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  placeholder="Enter keywords (e.g., 'credit card', '0% APR', 'mortgage')..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <button
                  type="submit"
                  className="inline-flex items-center px-4 py-2 border border-l-0 border-gray-300 rounded-r-md bg-primary-600 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  🔍 Search
                </button>
              </div>
            </div>

            {/* Filters */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label htmlFor="company" className="block text-sm font-medium text-gray-700">
                  Company
                </label>
                <input
                  type="text"
                  id="company"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  placeholder="Company name"
                  value={filters.company}
                  onChange={(e) => handleFilterChange('company', e.target.value)}
                />
              </div>

              <div>
                <label htmlFor="channel" className="block text-sm font-medium text-gray-700">
                  Channel
                </label>
                <select
                  id="channel"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  value={filters.channel}
                  onChange={(e) => handleFilterChange('channel', e.target.value)}
                >
                  <option value="">All channels</option>
                  <option value="email">Email</option>
                  <option value="social">Social Media</option>
                  <option value="display">Display Ads</option>
                  <option value="search">Search Ads</option>
                </select>
              </div>

              <div>
                <label htmlFor="date_from" className="block text-sm font-medium text-gray-700">
                  From Date
                </label>
                <input
                  type="date"
                  id="date_from"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  value={filters.date_from}
                  onChange={(e) => handleFilterChange('date_from', e.target.value)}
                />
              </div>

              <div>
                <label htmlFor="date_to" className="block text-sm font-medium text-gray-700">
                  To Date
                </label>
                <input
                  type="date"
                  id="date_to"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  value={filters.date_to}
                  onChange={(e) => handleFilterChange('date_to', e.target.value)}
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={clearFilters}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                Clear Filters
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Search Results */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          {isLoading && (
            <div className="flex justify-center items-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <span className="ml-2 text-sm text-gray-600">Searching...</span>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="flex items-center">
                <svg className="h-5 w-5 text-red-400 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div>
                  <h3 className="text-sm font-medium text-red-800 mb-1">Search Error</h3>
                  <div className="text-sm text-red-700">
                    {error.message}
                  </div>
                  <div className="mt-2 text-xs text-red-600">
                    Please try again or adjust your search criteria. If the problem persists, contact support.
                  </div>
                </div>
              </div>
            </div>
          )}

          {searchResults && !isLoading && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-gray-900">
                  Search Results
                </h3>
                <span className="text-sm text-gray-500">
                  {searchResults?.total || 0} results found
                </span>
              </div>

              {searchResults?.results?.length > 0 ? (
                <div className="space-y-4">
                  {searchResults?.results?.map((campaign) => (
                    <div
                      key={campaign.id}
                      className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-2">
                            <h4 className="text-lg font-semibold text-gray-900">
                              {campaign.name || campaign.title || 'Untitled Campaign'}
                            </h4>
                            <span className="text-sm text-gray-500">
                              by {campaign.company || campaign.company_name || 'Unknown Company'}
                            </span>
                          </div>
                          
                          {campaign.subject_line && (
                            <p className="text-sm text-gray-600 mb-2">
                              <strong>Subject:</strong> {campaign.subject_line}
                            </p>
                          )}

                          {campaign.content && (
                            <p className="text-sm text-gray-600 mb-2">
                              <strong>Content:</strong> {campaign.content.substring(0, 150)}
                              {campaign.content.length > 150 ? '...' : ''}
                            </p>
                          )}
                        </div>
                        
                        <div className="flex flex-col items-end space-y-2">
                          {campaign.sentiment_score && (
                            <span className={`text-xs px-2 py-1 rounded-full ${
                              campaign.sentiment_score > 0.6 ? 'bg-green-100 text-green-800' :
                              campaign.sentiment_score > 0.4 ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              Score: {campaign.sentiment_score > 0.6 ? 'Positive' : 
                                     campaign.sentiment_score > 0.4 ? 'Neutral' : 'Negative'}
                            </span>
                          )}
                          </span>
                          
                          {campaign.sentiment_score !== undefined && (
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              campaign.sentiment_score > 0 
                                ? 'bg-green-100 text-green-800' 
                                : campaign.sentiment_score < 0 
                                ? 'bg-red-100 text-red-800' 
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {campaign.sentiment_score > 0 ? 'Positive' : 
                               campaign.sentiment_score < 0 ? 'Negative' : 'Neutral'}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2 mb-3">
                        {campaign.channel && (
                          <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                            {campaign.channel}
                          </span>
                        )}
                        
                        {campaign.classification && (
                          <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-purple-100 text-purple-800">
                            {campaign.classification}
                          </span>
                        )}
                        
                        {campaign.launch_date && (
                          <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
                            {campaign.launch_date}
                          </span>
                        )}
                      </div>

                      <div className="text-sm text-gray-600 mb-3">
                        <p className="line-clamp-3">
                          {campaign.content?.substring(0, 200)}...
                        </p>
                      </div>

                      {campaign.keywords && campaign.keywords.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          <span className="text-xs text-gray-500">Keywords:</span>
                          {campaign.keywords.slice(0, 5).map((keyword, index) => (
                            <span
                              key={index}
                              className="inline-flex px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800"
                            >
                              {keyword}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : searchQuery && (
                <div className="text-center py-12">
                  <div className="text-gray-400 text-6xl mb-4">🔍</div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    No results found
                  </h3>
                  <p className="text-gray-500">
                    Try different keywords or adjust your filters.
                  </p>
                </div>
              )}
            </div>
          )}

          {!searchQuery && !isLoading && (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">🎯</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Start your search
              </h3>
              <p className="text-gray-500">
                Enter keywords to find competitor campaigns and marketing insights.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Search;