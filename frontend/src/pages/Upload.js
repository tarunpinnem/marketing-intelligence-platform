import React, { useState } from 'react';
import { useMutation, useQueryClient } from 'react-query';
import { campaignService } from '../services/api';

const Upload = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('idle'); // idle, uploading, success, error
  const [uploadMessage, setUploadMessage] = useState('');
  
  const queryClient = useQueryClient();

  const uploadMutation = useMutation(campaignService.uploadData, {
    onMutate: () => {
      setUploadStatus('uploading');
      setUploadMessage('');
    },
    onSuccess: (data) => {
      setUploadStatus('success');
      setUploadMessage(data.message);
      setSelectedFile(null);
      // Invalidate queries to refresh data
      queryClient.invalidateQueries('campaigns');
      queryClient.invalidateQueries('company-analytics');
    },
    onError: (error) => {
      setUploadStatus('error');
      setUploadMessage(error.response?.data?.detail || 'Upload failed');
    }
  });

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
    setUploadStatus('idle');
    setUploadMessage('');
  };

  const handleUpload = () => {
    if (!selectedFile) return;
    uploadMutation.mutate(selectedFile);
  };

  const downloadSampleCSV = () => {
    const sampleData = `company_name,title,subject_line,campaign_type,channel,launch_date,content,keywords
Chase Bank,"Chase Sapphire Preferred Credit Card","Earn 100K bonus points",promotional,email,2024-01-15,"Apply for the Chase Sapphire Preferred and earn 100,000 bonus points after spending $4,000 in the first 3 months.","credit card,bonus points,travel rewards"
Capital One,"What's in Your Wallet?","No Foreign Transaction Fees",brand_awareness,email,2024-01-20,"Discover the freedom of no foreign transaction fees with Capital One Venture cards.","credit card,no fees,travel"
American Express,"Gold Card Benefits","Earn 4X points on dining",promotional,email,2024-01-25,"The Gold Card from American Express. Earn 4X Membership Rewards points at restaurants worldwide.","credit card,dining rewards,gold card"`;
    
    const blob = new Blob([sampleData], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sample_campaigns.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
          Upload Campaign Data
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Upload CSV or JSON files containing marketing campaign data
        </p>
      </div>

      {/* Upload Form */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="space-y-6">
            {/* File Input */}
            <div>
              <label htmlFor="file-upload" className="block text-sm font-medium text-gray-700">
                Select file
              </label>
              <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md hover:border-gray-400 transition-colors">
                <div className="space-y-1 text-center">
                  <div className="text-6xl text-gray-400">📁</div>
                  <div className="flex text-sm text-gray-600">
                    <label
                      htmlFor="file-upload"
                      className="relative cursor-pointer bg-white rounded-md font-medium text-primary-600 hover:text-primary-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-primary-500"
                    >
                      <span>Upload a file</span>
                      <input
                        id="file-upload"
                        name="file-upload"
                        type="file"
                        className="sr-only"
                        accept=".csv,.json"
                        onChange={handleFileSelect}
                      />
                    </label>
                    <p className="pl-1">or drag and drop</p>
                  </div>
                  <p className="text-xs text-gray-500">CSV or JSON up to 10MB</p>
                  
                  {selectedFile && (
                    <div className="mt-4 p-3 bg-gray-50 rounded-md">
                      <div className="flex items-center justify-center space-x-2">
                        <span className="text-sm font-medium text-gray-900">
                          {selectedFile.name}
                        </span>
                        <span className="text-sm text-gray-500">
                          ({(selectedFile.size / 1024).toFixed(1)} KB)
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Upload Button */}
            <div className="flex justify-between items-center">
              <button
                type="button"
                onClick={downloadSampleCSV}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                📥 Download Sample CSV
              </button>
              
              <button
                type="button"
                onClick={handleUpload}
                disabled={!selectedFile || uploadStatus === 'uploading'}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {uploadStatus === 'uploading' ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Uploading...
                  </>
                ) : (
                  '📤 Upload Data'
                )}
              </button>
            </div>

            {/* Status Messages */}
            {uploadMessage && (
              <div className={`rounded-md p-4 ${
                uploadStatus === 'success' 
                  ? 'bg-green-50 border border-green-200' 
                  : uploadStatus === 'error'
                  ? 'bg-red-50 border border-red-200'
                  : 'bg-blue-50 border border-blue-200'
              }`}>
                <div className={`text-sm ${
                  uploadStatus === 'success' 
                    ? 'text-green-700' 
                    : uploadStatus === 'error'
                    ? 'text-red-700'
                    : 'text-blue-700'
                }`}>
                  {uploadMessage}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
            Data Format Instructions
          </h3>
          
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-semibold text-gray-700">Required Fields:</h4>
              <ul className="mt-1 text-sm text-gray-600 list-disc list-inside space-y-1">
                <li><code className="bg-gray-100 px-1 rounded">company_name</code> - Name of the company</li>
                <li><code className="bg-gray-100 px-1 rounded">title</code> - Campaign title</li>
                <li><code className="bg-gray-100 px-1 rounded">content</code> - Campaign content/copy</li>
              </ul>
            </div>
            
            <div>
              <h4 className="text-sm font-semibold text-gray-700">Optional Fields:</h4>
              <ul className="mt-1 text-sm text-gray-600 list-disc list-inside space-y-1">
                <li><code className="bg-gray-100 px-1 rounded">subject_line</code> - Email subject line</li>
                <li><code className="bg-gray-100 px-1 rounded">campaign_type</code> - Type (promotional, educational, etc.)</li>
                <li><code className="bg-gray-100 px-1 rounded">channel</code> - Marketing channel (email, social, etc.)</li>
                <li><code className="bg-gray-100 px-1 rounded">launch_date</code> - Launch date (YYYY-MM-DD)</li>
                <li><code className="bg-gray-100 px-1 rounded">keywords</code> - Comma-separated keywords</li>
              </ul>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
              <div className="text-sm text-blue-700">
                <strong>💡 Pro Tip:</strong> The system will automatically analyze your campaign content for sentiment and classification using AI. Make sure your content field contains the actual marketing copy for best results.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Uploads */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
            What happens after upload?
          </h3>
          
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-3xl mb-2">🔍</div>
              <h4 className="text-sm font-medium text-gray-900">Analysis</h4>
              <p className="text-xs text-gray-600 mt-1">
                Content is analyzed for sentiment and classification using AI
              </p>
            </div>
            
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-3xl mb-2">📊</div>
              <h4 className="text-sm font-medium text-gray-900">Indexing</h4>
              <p className="text-xs text-gray-600 mt-1">
                Campaigns are indexed for fast full-text search
              </p>
            </div>
            
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-3xl mb-2">📈</div>
              <h4 className="text-sm font-medium text-gray-900">Insights</h4>
              <p className="text-xs text-gray-600 mt-1">
                Data becomes available in dashboard and analytics
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;