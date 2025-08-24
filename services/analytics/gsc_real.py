# /srv/auto-adsense/services/analytics/gsc_real.py
import os
import json
import time
import redis
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

class RealGoogleSearchConsole:
    """Real Google Search Console integration - no mock data"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        # Real API credentials (required)
        self.client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
        self.private_key = os.getenv("GOOGLE_PRIVATE_KEY")
        self.access_token = None
        self.token_expiry = None
        
        # Sites to monitor
        self.sites = ["https://hing.me/", "https://playu.co/"]
        
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Google APIs using service account"""
        if not self.client_email or not self.private_key:
            raise Exception("Google credentials not configured. Set GOOGLE_CLIENT_EMAIL and GOOGLE_PRIVATE_KEY")
        
        try:
            # Use Google OAuth2 service account flow
            import jwt
            
            now = int(time.time())
            payload = {
                'iss': self.client_email,
                'scope': 'https://www.googleapis.com/auth/webmasters.readonly',
                'aud': 'https://oauth2.googleapis.com/token',
                'iat': now,
                'exp': now + 3600,
            }
            
            assertion = jwt.encode(payload, self.private_key, algorithm='RS256')
            
            token_request = {
                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'assertion': assertion
            }
            
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data=token_request,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                self.token_expiry = now + token_data.get('expires_in', 3600)
                print("✅ Google Search Console authenticated successfully")
            else:
                raise Exception(f"Authentication failed: {response.text}")
                
        except ImportError:
            raise Exception("PyJWT library required: pip install PyJWT")
        except Exception as e:
            raise Exception(f"Authentication error: {e}")
    
    def is_token_valid(self) -> bool:
        """Check if current token is valid"""
        return self.access_token and self.token_expiry and time.time() < self.token_expiry
    
    def refresh_token_if_needed(self):
        """Refresh token if expired"""
        if not self.is_token_valid():
            self.authenticate()
    
    def make_api_request(self, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make authenticated request to Search Console API"""
        self.refresh_token_if_needed()
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"https://www.googleapis.com/webmasters/v3/{endpoint}"
        
        if data:
            response = requests.post(url, headers=headers, json=data)
        else:
            response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
    
    def get_real_search_analytics(self, site_url: str, days: int = 7) -> Dict[str, Any]:
        """Get REAL search analytics data from Google Search Console"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Search Console API request
            request_data = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['query', 'page', 'date'],
                'rowLimit': 1000
            }
            
            endpoint = f"sites/{requests.utils.quote(site_url, safe='')}/searchAnalytics/query"
            response = self.make_api_request(endpoint, request_data)
            
            return self.process_real_analytics(response, site_url)
            
        except Exception as e:
            print(f"❌ Real Search Console API error: {e}")
            raise e  # Don't fall back to mock data - force real data
    
    def process_real_analytics(self, response: Dict[str, Any], site_url: str) -> Dict[str, Any]:
        """Process real API response"""
        rows = response.get('rows', [])
        domain = site_url.replace('https://', '').replace('http://', '').rstrip('/')
        
        if not rows:
            return {
                'success': True,
                'domain': domain,
                'site_url': site_url,
                'summary': {
                    'total_clicks': 0,
                    'total_impressions': 0,
                    'total_queries': 0,
                    'avg_ctr': 0,
                    'avg_position': 0
                },
                'daily_data': {},
                'top_queries': [],
                'top_pages': [],
                'updated_at': datetime.now().isoformat()
            }
        
        # Process real data
        total_clicks = sum(row.get('clicks', 0) for row in rows)
        total_impressions = sum(row.get('impressions', 0) for row in rows)
        unique_queries = len(set(row['keys'][0] for row in rows if len(row['keys']) > 0))
        
        # Group by queries and pages
        queries_data = {}
        pages_data = {}
        daily_data = {}
        
        for row in rows:
            keys = row.get('keys', [])
            if len(keys) >= 3:
                query, page, date = keys[0], keys[1], keys[2]
                
                clicks = row.get('clicks', 0)
                impressions = row.get('impressions', 0)
                ctr = row.get('ctr', 0)
                position = row.get('position', 0)
                
                # Query aggregation
                if query not in queries_data:
                    queries_data[query] = {
                        'clicks': 0, 'impressions': 0, 'positions': []
                    }
                queries_data[query]['clicks'] += clicks
                queries_data[query]['impressions'] += impressions
                queries_data[query]['positions'].append(position)
                
                # Page aggregation
                if page not in pages_data:
                    pages_data[page] = {'clicks': 0, 'impressions': 0}
                pages_data[page]['clicks'] += clicks
                pages_data[page]['impressions'] += impressions
                
                # Daily aggregation
                if date not in daily_data:
                    daily_data[date] = {'clicks': 0, 'impressions': 0}
                daily_data[date]['clicks'] += clicks
                daily_data[date]['impressions'] += impressions
        
        # Sort and format results
        top_queries = []
        for query, data in sorted(queries_data.items(), key=lambda x: x[1]['clicks'], reverse=True)[:10]:
            avg_position = sum(data['positions']) / len(data['positions']) if data['positions'] else 0
            ctr = (data['clicks'] / data['impressions'] * 100) if data['impressions'] > 0 else 0
            
            top_queries.append({
                'query': query,
                'clicks': data['clicks'],
                'impressions': data['impressions'],
                'ctr': round(ctr, 2),
                'position': round(avg_position, 1)
            })
        
        top_pages = []
        for page, data in sorted(pages_data.items(), key=lambda x: x[1]['clicks'], reverse=True)[:10]:
            ctr = (data['clicks'] / data['impressions'] * 100) if data['impressions'] > 0 else 0
            top_pages.append({
                'page': page.replace(site_url, ''),
                'clicks': data['clicks'],
                'impressions': data['impressions'],
                'ctr': round(ctr, 2)
            })
        
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        all_positions = [row.get('position', 0) for row in rows]
        avg_position = sum(all_positions) / len(all_positions) if all_positions else 0
        
        result = {
            'success': True,
            'domain': domain,
            'site_url': site_url,
            'summary': {
                'total_clicks': total_clicks,
                'total_impressions': total_impressions,
                'total_queries': unique_queries,
                'avg_ctr': round(avg_ctr, 2),
                'avg_position': round(avg_position, 1)
            },
            'daily_data': daily_data,
            'top_queries': top_queries,
            'top_pages': top_pages,
            'updated_at': datetime.now().isoformat()
        }
        
        # Cache real data
        self.redis_client.setex(
            f"real_gsc:{domain}",
            1800,  # 30 minutes cache
            json.dumps(result)
        )
        
        return result
    
    def get_all_sites_real_analytics(self) -> Dict[str, Any]:
        """Get real analytics for all sites"""
        results = {}
        
        for site_url in self.sites:
            domain = site_url.replace('https://', '').replace('http://', '').rstrip('/')
            
            try:
                print(f"🔍 Fetching REAL analytics for {domain}")
                analytics = self.get_real_search_analytics(site_url)
                results[domain] = analytics
                
                print(f"✅ {domain}: {analytics['summary']['total_clicks']} clicks, {analytics['summary']['total_impressions']} impressions")
                
            except Exception as e:
                print(f"❌ Failed to get real data for {domain}: {e}")
                # Don't add mock data - only real data
                results[domain] = {
                    'success': False,
                    'error': str(e),
                    'domain': domain
                }
            
            # Rate limiting
            time.sleep(2)
        
        # Cache aggregated results
        self.redis_client.setex(
            "all_real_gsc_data",
            1800,
            json.dumps(results)
        )
        
        return results

# Real-time data fetcher service
def main():
    """Run real-time data fetcher"""
    try:
        gsc = RealGoogleSearchConsole()
        
        print("🚀 Starting real-time Google Search Console data fetcher")
        print("📍 Configured sites:", gsc.sites)
        
        while True:
            try:
                print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Fetching real data...")
                
                results = gsc.get_all_sites_real_analytics()
                
                total_clicks = sum(
                    result.get('summary', {}).get('total_clicks', 0) 
                    for result in results.values() 
                    if result.get('success')
                )
                
                total_impressions = sum(
                    result.get('summary', {}).get('total_impressions', 0) 
                    for result in results.values() 
                    if result.get('success')
                )
                
                print(f"📊 Total across all sites: {total_clicks} clicks, {total_impressions} impressions")
                
                # Store summary stats
                summary_stats = {
                    'total_clicks': total_clicks,
                    'total_impressions': total_impressions,
                    'sites_updated': len([r for r in results.values() if r.get('success')]),
                    'last_update': datetime.now().isoformat()
                }
                
                gsc.redis_client.setex(
                    "gsc_summary_stats",
                    1800,
                    json.dumps(summary_stats)
                )
                
                print("💾 Data cached successfully")
                
                # Wait 30 minutes before next update
                print("⏳ Waiting 30 minutes for next update...")
                time.sleep(1800)
                
            except KeyboardInterrupt:
                print("\n🛑 Stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                print("⏳ Waiting 5 minutes before retry...")
                time.sleep(300)
                
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        print("Please check your Google API credentials:")
        print("- GOOGLE_CLIENT_EMAIL")
        print("- GOOGLE_PRIVATE_KEY")

if __name__ == "__main__":
    main()
