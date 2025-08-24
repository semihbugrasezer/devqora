# /srv/auto-adsense/services/analytics/google_search_console.py
import os
import json
import time
import redis
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleSearchConsoleAPI:
    """Google Search Console API integration for real-time analytics"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        # API credentials
        self.service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        self.credentials = None
        self.service = None
        
        # Sites to monitor
        self.sites = [
            "https://hing.me/",
            "https://playu.co/"
        ]
        
        self.initialize_service()
    
    def initialize_service(self):
        """Initialize Google Search Console service"""
        try:
            if self.service_account_file and os.path.exists(self.service_account_file):
                # Use service account
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_file,
                    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
                )
                self.credentials = credentials
                self.service = build('searchconsole', 'v1', credentials=credentials)
                self.log_info("Google Search Console service initialized with service account")
            else:
                self.log_warning("Google Search Console credentials not found - using mock data")
                self.service = None
                
        except Exception as e:
            self.log_error(f"Failed to initialize Google Search Console service: {e}")
            self.service = None
    
    def is_configured(self) -> bool:
        """Check if Google Search Console API is properly configured"""
        return self.service is not None
    
    def get_search_analytics(self, site_url: str, days: int = 7) -> Dict[str, Any]:
        """Get search analytics data for a site"""
        try:
            if not self.is_configured():
                return self.get_mock_search_analytics(site_url, days)
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['query', 'page', 'date'],
                'rowLimit': 1000,
                'startRow': 0
            }
            
            response = self.service.searchanalytics().query(
                siteUrl=site_url,
                body=request
            ).execute()
            
            return self.process_search_analytics(response, site_url)
            
        except HttpError as e:
            self.log_error(f"Google Search Console API error: {e}")
            return self.get_mock_search_analytics(site_url, days)
        except Exception as e:
            self.log_error(f"Unexpected error in search analytics: {e}")
            return self.get_mock_search_analytics(site_url, days)
    
    def process_search_analytics(self, response: Dict[str, Any], site_url: str) -> Dict[str, Any]:
        """Process and structure search analytics data"""
        rows = response.get('rows', [])
        
        # Initialize metrics
        total_clicks = 0
        total_impressions = 0
        total_queries = len(set(row['keys'][0] for row in rows if len(row['keys']) > 0))
        
        # Process by date
        daily_data = {}
        top_queries = {}
        top_pages = {}
        
        for row in rows:
            keys = row.get('keys', [])
            if len(keys) >= 3:
                query, page, date = keys[0], keys[1], keys[2]
                
                clicks = row.get('clicks', 0)
                impressions = row.get('impressions', 0)
                ctr = row.get('ctr', 0)
                position = row.get('position', 0)
                
                total_clicks += clicks
                total_impressions += impressions
                
                # Daily data
                if date not in daily_data:
                    daily_data[date] = {'clicks': 0, 'impressions': 0, 'queries': 0}
                daily_data[date]['clicks'] += clicks
                daily_data[date]['impressions'] += impressions
                daily_data[date]['queries'] += 1
                
                # Top queries
                if query not in top_queries:
                    top_queries[query] = {'clicks': 0, 'impressions': 0, 'position': position}
                top_queries[query]['clicks'] += clicks
                top_queries[query]['impressions'] += impressions
                
                # Top pages
                if page not in top_pages:
                    top_pages[page] = {'clicks': 0, 'impressions': 0}
                top_pages[page]['clicks'] += clicks
                top_pages[page]['impressions'] += impressions
        
        # Sort and limit results
        top_queries_sorted = sorted(
            top_queries.items(), 
            key=lambda x: x[1]['clicks'], 
            reverse=True
        )[:10]
        
        top_pages_sorted = sorted(
            top_pages.items(), 
            key=lambda x: x[1]['clicks'], 
            reverse=True
        )[:10]
        
        # Calculate average CTR and position
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        avg_position = sum(row.get('position', 0) for row in rows) / len(rows) if rows else 0
        
        domain = site_url.replace('https://', '').replace('http://', '').rstrip('/')
        
        result = {
            'success': True,
            'domain': domain,
            'site_url': site_url,
            'summary': {
                'total_clicks': total_clicks,
                'total_impressions': total_impressions,
                'total_queries': total_queries,
                'avg_ctr': round(avg_ctr, 2),
                'avg_position': round(avg_position, 1)
            },
            'daily_data': daily_data,
            'top_queries': [
                {
                    'query': query,
                    'clicks': data['clicks'],
                    'impressions': data['impressions'],
                    'ctr': round((data['clicks'] / data['impressions'] * 100) if data['impressions'] > 0 else 0, 2),
                    'position': round(data['position'], 1)
                }
                for query, data in top_queries_sorted
            ],
            'top_pages': [
                {
                    'page': page.replace(site_url, ''),
                    'clicks': data['clicks'],
                    'impressions': data['impressions'],
                    'ctr': round((data['clicks'] / data['impressions'] * 100) if data['impressions'] > 0 else 0, 2)
                }
                for page, data in top_pages_sorted
            ],
            'updated_at': datetime.now().isoformat()
        }
        
        # Store in Redis for dashboard
        self.redis_client.setex(
            f"gsc_analytics:{domain}",
            3600,  # 1 hour cache
            json.dumps(result)
        )
        
        return result
    
    def get_mock_search_analytics(self, site_url: str, days: int = 7) -> Dict[str, Any]:
        """Generate mock search analytics data when API is not available"""
        domain = site_url.replace('https://', '').replace('http://', '').rstrip('/')
        
        # Domain-specific mock data
        if 'hing.me' in domain:
            queries = [
                {'query': 'investment guide 2025', 'clicks': 124, 'impressions': 2340, 'position': 8.2},
                {'query': 'how to invest money', 'clicks': 89, 'impressions': 1876, 'position': 12.1},
                {'query': 'best investment apps', 'clicks': 67, 'impressions': 1456, 'position': 15.3},
                {'query': 'cryptocurrency guide', 'clicks': 45, 'impressions': 987, 'position': 18.7},
                {'query': 'stock market basics', 'clicks': 34, 'impressions': 723, 'position': 22.1}
            ]
            pages = [
                {'page': '/articles/investment-guide-2025', 'clicks': 87, 'impressions': 1234},
                {'page': '/calculators/mortgage', 'clicks': 65, 'impressions': 987},
                {'page': '/articles/crypto-basics', 'clicks': 43, 'impressions': 765},
                {'page': '/guides', 'clicks': 32, 'impressions': 543}
            ]
        else:  # playu.co
            queries = [
                {'query': 'best gaming setup 2025', 'clicks': 98, 'impressions': 1876, 'position': 6.8},
                {'query': 'gaming chair reviews', 'clicks': 76, 'impressions': 1456, 'position': 9.4},
                {'query': 'pc build guide', 'clicks': 54, 'impressions': 1123, 'position': 13.7},
                {'query': 'gaming headset comparison', 'clicks': 42, 'impressions': 894, 'position': 16.2},
                {'query': 'stream setup guide', 'clicks': 31, 'impressions': 678, 'position': 19.8}
            ]
            pages = [
                {'page': '/articles/gaming-setup-guide', 'clicks': 76, 'impressions': 1123},
                {'page': '/articles/pc-build-2025', 'clicks': 54, 'impressions': 876},
                {'page': '/reviews/gaming-chairs', 'clicks': 43, 'impressions': 654},
                {'page': '/', 'clicks': 32, 'impressions': 543}
            ]
        
        # Generate daily data
        daily_data = {}
        end_date = datetime.now().date()
        
        for i in range(days):
            date = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
            daily_data[date] = {
                'clicks': max(10, int(sum(q['clicks'] for q in queries) * (0.8 + 0.4 * (i / days)))),
                'impressions': max(100, int(sum(q['impressions'] for q in queries) * (0.8 + 0.4 * (i / days)))),
                'queries': len(queries) + i
            }
        
        total_clicks = sum(q['clicks'] for q in queries)
        total_impressions = sum(q['impressions'] for q in queries)
        
        # Add CTR calculation to queries and pages
        for query in queries:
            query['ctr'] = round((query['clicks'] / query['impressions'] * 100) if query['impressions'] > 0 else 0, 2)
        
        for page in pages:
            page['ctr'] = round((page['clicks'] / page['impressions'] * 100) if page['impressions'] > 0 else 0, 2)
        
        result = {
            'success': True,
            'domain': domain,
            'site_url': site_url,
            'mock_data': True,
            'summary': {
                'total_clicks': total_clicks,
                'total_impressions': total_impressions,
                'total_queries': len(queries),
                'avg_ctr': round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
                'avg_position': round(sum(q['position'] for q in queries) / len(queries), 1)
            },
            'daily_data': daily_data,
            'top_queries': queries,
            'top_pages': pages,
            'updated_at': datetime.now().isoformat()
        }
        
        # Store in Redis
        self.redis_client.setex(
            f"gsc_analytics:{domain}",
            3600,
            json.dumps(result)
        )
        
        return result
    
    def get_site_index_status(self, site_url: str) -> Dict[str, Any]:
        """Get indexing status for site"""
        try:
            if not self.is_configured():
                return self.get_mock_index_status(site_url)
            
            # Get site index status from Search Console
            request = self.service.sites().get(siteUrl=site_url)
            response = request.execute()
            
            return {
                'success': True,
                'site_url': site_url,
                'permission_level': response.get('permissionLevel', 'unknown'),
                'verification_status': 'verified' if response else 'unverified'
            }
            
        except HttpError as e:
            self.log_error(f"Index status API error: {e}")
            return self.get_mock_index_status(site_url)
        except Exception as e:
            self.log_error(f"Unexpected error in index status: {e}")
            return self.get_mock_index_status(site_url)
    
    def get_mock_index_status(self, site_url: str) -> Dict[str, Any]:
        """Mock index status data"""
        domain = site_url.replace('https://', '').replace('http://', '').rstrip('/')
        
        return {
            'success': True,
            'site_url': site_url,
            'domain': domain,
            'mock_data': True,
            'permission_level': 'siteOwner',
            'verification_status': 'verified',
            'indexed_pages': 47 if 'hing.me' in domain else 38,
            'submitted_pages': 52 if 'hing.me' in domain else 41,
            'coverage_issues': 5 if 'hing.me' in domain else 3,
            'last_crawl': (datetime.now() - timedelta(hours=6)).isoformat()
        }
    
    def fetch_all_sites_analytics(self) -> Dict[str, Any]:
        """Fetch analytics for all configured sites"""
        results = {}
        
        for site_url in self.sites:
            domain = site_url.replace('https://', '').replace('http://', '').rstrip('/')
            
            self.log_info(f"Fetching analytics for {domain}")
            
            # Get search analytics
            analytics = self.get_search_analytics(site_url)
            
            # Get index status
            index_status = self.get_site_index_status(site_url)
            
            results[domain] = {
                'analytics': analytics,
                'index_status': index_status,
                'last_updated': datetime.now().isoformat()
            }
            
            # Small delay between requests
            time.sleep(1)
        
        # Store aggregated results
        self.redis_client.setex(
            "gsc_all_sites_analytics",
            1800,  # 30 minutes cache
            json.dumps(results)
        )
        
        return results
    
    def get_cached_analytics(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get cached analytics data for domain"""
        try:
            cached_data = self.redis_client.get(f"gsc_analytics:{domain}")
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            self.log_error(f"Error getting cached analytics: {e}")
        
        return None
    
    def update_analytics_cache(self):
        """Update analytics cache for all sites"""
        self.log_info("Starting analytics cache update")
        
        for site_url in self.sites:
            domain = site_url.replace('https://', '').replace('http://', '').rstrip('/')
            
            try:
                analytics = self.get_search_analytics(site_url)
                
                if analytics.get('success'):
                    self.log_info(f"Updated analytics cache for {domain}")
                else:
                    self.log_error(f"Failed to update analytics for {domain}")
                    
            except Exception as e:
                self.log_error(f"Error updating analytics for {domain}: {e}")
            
            time.sleep(2)  # Rate limiting
        
        self.log_info("Analytics cache update completed")
    
    def log_info(self, message: str):
        """Log info message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] GSC INFO: {message}")
    
    def log_warning(self, message: str):
        """Log warning message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] GSC WARNING: {message}")
    
    def log_error(self, message: str):
        """Log error message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] GSC ERROR: {message}")

# CLI for testing
def main():
    """Test Google Search Console integration"""
    gsc = GoogleSearchConsoleAPI()
    
    print("🔍 Testing Google Search Console Integration")
    print(f"Configured: {gsc.is_configured()}")
    
    # Test analytics for both sites
    for site_url in gsc.sites:
        domain = site_url.replace('https://', '').replace('http://', '').rstrip('/')
        print(f"\n📊 Fetching analytics for {domain}")
        
        analytics = gsc.get_search_analytics(site_url)
        
        if analytics.get('success'):
            summary = analytics['summary']
            print(f"✅ Clicks: {summary['total_clicks']}")
            print(f"✅ Impressions: {summary['total_impressions']}")
            print(f"✅ Avg CTR: {summary['avg_ctr']}%")
            print(f"✅ Avg Position: {summary['avg_position']}")
            print(f"✅ Top Query: {analytics['top_queries'][0]['query'] if analytics['top_queries'] else 'None'}")
        else:
            print(f"❌ Failed to fetch analytics: {analytics.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
