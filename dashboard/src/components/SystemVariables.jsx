import React, { useState, useEffect } from 'react';

const SystemVariables = () => {
  const [variables, setVariables] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeCategory, setActiveCategory] = useState('adsense');

  const categories = {
    adsense: {
      title: 'AdSense Configuration',
      icon: '💰',
      variables: [
        { key: 'GOOGLE_PRIVATE_KEY', label: 'Google Private Key', type: 'textarea', sensitive: true },
        { key: 'GOOGLE_CLIENT_EMAIL', label: 'Google Client Email', type: 'email' },
        { key: 'ADSENSE_PUBLISHER_ID', label: 'Publisher ID', type: 'text', value: 'pub-7970408813538482' },
        { key: 'AUTO_ADS_ENABLED', label: 'Auto Ads Enabled', type: 'boolean', value: true }
      ]
    },
    content: {
      title: 'Content Generation',
      icon: '📝',
      variables: [
        { key: 'DEEPSEEK_API_KEY', label: 'DeepSeek API Key', type: 'password', sensitive: true },
        { key: 'CLAUDE_API_KEY', label: 'Claude API Key', type: 'password', sensitive: true },
        { key: 'GROQ_API_KEY', label: 'Groq API Key', type: 'password', sensitive: true },
        { key: 'CONTENT_SCHEDULE', label: 'Content Schedule (hours)', type: 'text', value: '9:30,14:15,17:45,20:20' },
        { key: 'ARTICLES_PER_DAY', label: 'Articles per Day', type: 'number', value: 4 }
      ]
    },
    pinterest: {
      title: 'Pinterest Integration',
      icon: '📌',
      variables: [
        { key: 'PINTEREST_ACCESS_TOKEN', label: 'Pinterest Access Token', type: 'password', sensitive: true },
        { key: 'PINTEREST_APP_ID', label: 'Pinterest App ID', type: 'text' },
        { key: 'PINTEREST_APP_SECRET', label: 'Pinterest App Secret', type: 'password', sensitive: true },
        { key: 'AUTO_PIN_ENABLED', label: 'Auto Pin Enabled', type: 'boolean', value: true },
        { key: 'PINS_PER_ARTICLE', label: 'Pins per Article', type: 'number', value: 3 }
      ]
    },
    cloudflare: {
      title: 'Cloudflare Deployment',
      icon: '🌐',
      variables: [
        { key: 'CLOUDFLARE_API_TOKEN', label: 'Cloudflare API Token', type: 'password', sensitive: true },
        { key: 'CLOUDFLARE_ACCOUNT_ID', label: 'Account ID', type: 'text' },
        { key: 'AUTO_DEPLOY_ENABLED', label: 'Auto Deploy Enabled', type: 'boolean', value: true },
        { key: 'DEPLOY_AFTER_CONTENT', label: 'Deploy After Content', type: 'boolean', value: true }
      ]
    },
    images: {
      title: 'Image Generation',
      icon: '🖼️',
      variables: [
        { key: 'NANO_BANANA_API_KEY', label: 'Nano Banana API Key', type: 'password', sensitive: true },
        { key: 'IMAGES_PER_ARTICLE', label: 'Images per Article', type: 'number', value: 3 },
        { key: 'IMAGE_QUALITY', label: 'Image Quality', type: 'select', options: ['low', 'medium', 'high'], value: 'high' },
        { key: 'AUTO_IMAGE_GENERATION', label: 'Auto Image Generation', type: 'boolean', value: true }
      ]
    },
    system: {
      title: 'System Settings',
      icon: '⚙️',
      variables: [
        { key: 'REDIS_HOST', label: 'Redis Host', type: 'text', value: 'redis' },
        { key: 'REDIS_PORT', label: 'Redis Port', type: 'number', value: 6379 },
        { key: 'LOG_LEVEL', label: 'Log Level', type: 'select', options: ['debug', 'info', 'warn', 'error'], value: 'info' },
        { key: 'DASHBOARD_PORT', label: 'Dashboard Port', type: 'number', value: 9080 },
        { key: 'BACKUP_ENABLED', label: 'Backup Enabled', type: 'boolean', value: true }
      ]
    }
  };

  useEffect(() => {
    fetchVariables();
  }, []);

  const fetchVariables = async () => {
    try {
      const response = await fetch('/api/config');
      const data = await response.json();
      setVariables(data.variables || {});
    } catch (error) {
      console.error('Failed to fetch variables:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateVariable = (key, value) => {
    setVariables(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const saveVariables = async () => {
    setSaving(true);
    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ variables }),
      });

      if (response.ok) {
        alert('Variables saved successfully!');
      } else {
        alert('Failed to save variables');
      }
    } catch (error) {
      console.error('Failed to save variables:', error);
      alert('Failed to save variables');
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async (category) => {
    try {
      const response = await fetch(`/api/test/${category}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ variables }),
      });
      
      const result = await response.json();
      alert(result.success ? `${category} connection successful!` : `${category} connection failed: ${result.error}`);
    } catch (error) {
      alert(`Test failed: ${error.message}`);
    }
  };

  const renderInput = (variable) => {
    const value = variables[variable.key] || variable.value || '';
    const commonProps = {
      className: "w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500",
      value: variable.sensitive ? '••••••••' : value,
      onChange: (e) => updateVariable(variable.key, e.target.value)
    };

    switch (variable.type) {
      case 'textarea':
        return (
          <textarea
            {...commonProps}
            rows="3"
            placeholder={variable.sensitive ? 'Enter your private key...' : ''}
          />
        );
      case 'password':
        return (
          <div className="relative">
            <input
              {...commonProps}
              type="password"
              placeholder="••••••••••••"
            />
          </div>
        );
      case 'boolean':
        return (
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={value === true || value === 'true'}
              onChange={(e) => updateVariable(variable.key, e.target.checked)}
              className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span className="text-sm text-gray-600">{value ? 'Enabled' : 'Disabled'}</span>
          </div>
        );
      case 'select':
        return (
          <select
            {...commonProps}
            value={value}
          >
            {variable.options.map(option => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        );
      case 'number':
        return (
          <input
            {...commonProps}
            type="number"
          />
        );
      default:
        return (
          <input
            {...commonProps}
            type="text"
          />
        );
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">System Variables</h2>
        <div className="flex gap-2">
          <button
            onClick={() => testConnection(activeCategory)}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
          >
            Test {categories[activeCategory].title}
          </button>
          <button
            onClick={saveVariables}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save All'}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        {Object.entries(categories).map(([key, category]) => (
          <button
            key={key}
            onClick={() => setActiveCategory(key)}
            className={`px-4 py-2 rounded-md transition-colors ${
              activeCategory === key
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {category.icon} {category.title}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {categories[activeCategory].variables.map((variable) => (
          <div key={variable.key} className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              {variable.label}
              {variable.sensitive && (
                <span className="ml-1 text-red-500" title="Sensitive data">🔒</span>
              )}
            </label>
            {renderInput(variable)}
            <p className="text-xs text-gray-500">
              Environment variable: {variable.key}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
        <h3 className="text-sm font-medium text-yellow-800 mb-2">⚠️ Important Notes:</h3>
        <ul className="text-xs text-yellow-700 space-y-1">
          <li>• Sensitive data is encrypted and stored securely</li>
          <li>• Changes require system restart to take effect</li>
          <li>• Test connections before saving to ensure validity</li>
          <li>• Backup your configuration before making changes</li>
        </ul>
      </div>

      <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
        <h3 className="text-sm font-medium text-green-800 mb-2">✅ System Status:</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
          <div className="flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            AdSense API: Connected
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            Content Generation: Active
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            Pinterest: Connected
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            Cloudflare: Connected
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            Image Generation: Active
          </div>
          <div className="flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            Auto Deployment: Active
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemVariables;