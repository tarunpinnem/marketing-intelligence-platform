import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const campaignService = {
  // Get all campaigns
  getCampaigns: async (params = {}) => {
    const response = await api.get('/api/campaigns', { params });
    return response.data;
  },

  // Create a new campaign
  createCampaign: async (campaignData) => {
    const response = await api.post('/api/campaigns', campaignData);
    return response.data;
  },

  // Search campaigns (fallback to filtering campaigns)
  searchCampaigns: async (searchData) => {
    try {
      // First try the dedicated search endpoint
      const params = new URLSearchParams();
      if (searchData.query) params.append('query', searchData.query);
      if (searchData.company) params.append('company', searchData.company);
      if (searchData.channel) params.append('channel', searchData.channel);
      if (searchData.date_from) params.append('date_from', searchData.date_from);
      if (searchData.date_to) params.append('date_to', searchData.date_to);
      
      const response = await api.get(`/api/search?${params.toString()}`);
      return response.data;
    } catch (error) {
      // Fallback: Get all campaigns and filter client-side
      console.log('Search endpoint not available, using client-side filtering');
      const response = await api.get('/api/campaigns?limit=1000');
      const allCampaigns = response.data.campaigns || [];
      
      let filteredCampaigns = allCampaigns;
      
      // Apply client-side filtering
      if (searchData.query) {
        const query = searchData.query.toLowerCase();
        filteredCampaigns = filteredCampaigns.filter(campaign => 
          campaign.name.toLowerCase().includes(query) ||
          campaign.company.toLowerCase().includes(query) ||
          campaign.content?.toLowerCase().includes(query) ||
          campaign.platform.toLowerCase().includes(query)
        );
      }
      
      if (searchData.company) {
        filteredCampaigns = filteredCampaigns.filter(campaign => 
          campaign.company.toLowerCase().includes(searchData.company.toLowerCase())
        );
      }
      
      if (searchData.channel) {
        filteredCampaigns = filteredCampaigns.filter(campaign => 
          campaign.platform.toLowerCase().includes(searchData.channel.toLowerCase())
        );
      }
      
      return {
        results: filteredCampaigns,
        campaigns: filteredCampaigns,
        total: filteredCampaigns.length
      };
    }
  },

  // Upload data
  uploadData: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get analytics
  getCompanyAnalytics: async () => {
    const response = await api.get('/api/analytics');
    // Extract company data from competitor_analysis
    return {
      companies: response.data.competitor_analysis || [],
      total: response.data.competitor_analysis?.length || 0
    };
  },

  getTrends: async () => {
    const response = await api.get('/api/analytics');
    return {
      trends: response.data.campaign_trends || [],
      insights: response.data,
      weekly_data: response.data.campaign_trends || []
    };
  },

  // Health check
  healthCheck: async () => {
    const response = await api.get('/api/health');
    return response.data;
  },
};

export default api;