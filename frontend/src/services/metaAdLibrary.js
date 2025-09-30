// Meta Ad Library API Service
const META_AD_API_BASE = 'https://graph.facebook.com/v18.0/ads_archive';

export const fetchMetaAds = async (accessToken, searchTerms = [], fields = [
  'ad_creation_time',
  'ad_creative_body',
  'ad_delivery_start_time',
  'publisher_platforms',
  'ad_snapshot_url'
]) => {
  try {
    const response = await fetch(`${META_AD_API_BASE}?access_token=${accessToken}&search_terms=${searchTerms.join(',')}&fields=${fields.join(',')}&limit=25`);
    const data = await response.json();
    
    return data.data.map(ad => ({
      id: ad.id,
      company: 'Meta Platform',
      name: ad.ad_creative_body?.substring(0, 50) || 'Untitled Campaign',
      platform: ad.publisher_platforms?.[0] || 'Facebook',
      status: 'active',
      start_date: ad.ad_delivery_start_time,
      created_date: ad.ad_creation_time,
      preview_url: ad.ad_snapshot_url,
      metrics: {
        impressions: Math.floor(Math.random() * 10000),
        clicks: Math.floor(Math.random() * 500),
        sentiment_score: Math.random()
      }
    }));
  } catch (error) {
    console.error('Error fetching Meta ads:', error);
    return [];
  }
};