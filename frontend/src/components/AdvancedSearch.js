import React, { useState } from 'react';
import { debounce } from 'lodash';

const AdvancedSearch = ({ onSearch, onSaveSearch }) => {
  const [filters, setFilters] = useState({
    company: '',
    dateRange: {
      start: '',
      end: ''
    },
    keywords: '',
    channels: [],
    savedSearches: []
  });

  const channels = [
    'Email',
    'Social Media',
    'Display Ads',
    'Search Ads',
    'Video Ads',
    'Push Notification',
    'SMS'
  ];

  const handleSearch = debounce(() => {
    onSearch(filters);
  }, 300);

  const handleSaveSearch = () => {
    const searchName = prompt('Enter a name for this search:');
    if (searchName) {
      const savedSearch = {
        name: searchName,
        filters: { ...filters }
      };
      setFilters(prev => ({
        ...prev,
        savedSearches: [...prev.savedSearches, savedSearch]
      }));
      onSaveSearch(savedSearch);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }));
    handleSearch();
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Company Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700">Company</label>
            <input
              type="text"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              placeholder="Search companies..."
              value={filters.company}
              onChange={(e) => handleFilterChange('company', e.target.value)}
            />
          </div>

          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700">Date Range</label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="date"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                value={filters.dateRange.start}
                onChange={(e) => handleFilterChange('dateRange', { ...filters.dateRange, start: e.target.value })}
              />
              <input
                type="date"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                value={filters.dateRange.end}
                onChange={(e) => handleFilterChange('dateRange', { ...filters.dateRange, end: e.target.value })}
              />
            </div>
          </div>

          {/* Keyword Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700">Keywords</label>
            <input
              type="text"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              placeholder="Search keywords..."
              value={filters.keywords}
              onChange={(e) => handleFilterChange('keywords', e.target.value)}
            />
          </div>
        </div>

        {/* Channel Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Channels</label>
          <div className="flex flex-wrap gap-2">
            {channels.map(channel => (
              <button
                key={channel}
                className={`px-3 py-1 rounded-full text-sm ${
                  filters.channels.includes(channel)
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                }`}
                onClick={() => {
                  const newChannels = filters.channels.includes(channel)
                    ? filters.channels.filter(c => c !== channel)
                    : [...filters.channels, channel];
                  handleFilterChange('channels', newChannels);
                }}
              >
                {channel}
              </button>
            ))}
          </div>
        </div>

        {/* Save Search */}
        <div className="flex justify-end">
          <button
            onClick={handleSaveSearch}
            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition-colors"
          >
            Save Search
          </button>
        </div>

        {/* Saved Searches */}
        {filters.savedSearches.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Saved Searches</h4>
            <div className="flex flex-wrap gap-2">
              {filters.savedSearches.map((search, index) => (
                <button
                  key={index}
                  className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm hover:bg-gray-200"
                  onClick={() => setFilters({ ...filters, ...search.filters })}
                >
                  {search.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdvancedSearch;