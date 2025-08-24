#!/usr/bin/env python3
"""
Google AdSense Management API Integration
- Real revenue data fetching
- Account management
- Performance analytics
- Auto optimization
"""

import os
import json
import time
import redis
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
import googleapiclient.discovery

class AdSenseManager:
    """Google AdSense API Manager for Real Revenue Data"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        # AdSense API Configuration
        self.publisher_id = "pub-7970408813538482"  # Your publisher ID
        self.scopes = [
            'https://www.googleapis.com/auth/adsense.readonly'
        ]
        
        # Initialize credentials
        self.service = None
        self.initialize_service()
        
        print(f"📊 AdSense Manager initialized for publisher: {self.publisher_id}")
    
    def initialize_service(self):
        """Initialize Google AdSense API service"""
        try:
            # Get service account credentials from environment
            private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace('\\n', '\n')
            client_email = os.getenv("GOOGLE_CLIENT_EMAIL", "")
            
            if not private_key or not client_email:
                print("❌ Google Service Account credentials not found")
                return
            
            # Create credentials dict
            creds_dict = {
                "type": "service_account",
                "project_id": "your-project-id",
                "private_key_id": "key-id",
                "private_key": private_key,
                "client_email": client_email,
                "client_id": "client-id",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
            }
            
            # Create credentials
            credentials = Credentials.from_service_account_info(
                creds_dict, 
                scopes=self.scopes
            )
            
            # Build service
            self.service = googleapiclient.discovery.build(
                'adsense', 'v2', 
                credentials=credentials,
                cache_discovery=False
            )
            
            print("✅ AdSense API service initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize AdSense API: {e}")
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get AdSense account information"""
        try:
            if not self.service:
                return {"error": "AdSense service not initialized"}
            
            # Get account list
            accounts = self.service.accounts().list().execute()
            
            if 'accounts' not in accounts or len(accounts['accounts']) == 0:
                return {"error": "No AdSense accounts found"}
            
            account = accounts['accounts'][0]
            
            account_info = {
                "name": account.get('name', ''),
                "display_name": account.get('displayName', ''),
                "publisher_id": self.publisher_id,
                "currency_code": account.get('currencyCode', 'USD'),
                "timezone": account.get('timezone', 'UTC'),
                "state": account.get('state', 'UNKNOWN'),
                "creation_time": account.get('createTime', ''),
                "premium": account.get('premium', False)
            }
            
            # Cache account info
            self.redis_client.set(
                "adsense_account_info", 
                json.dumps(account_info), 
                ex=3600  # 1 hour cache
            )
            
            return account_info
            
        except Exception as e:
            print(f"❌ Error fetching account info: {e}")
            return {"error": str(e)}
    
    def get_revenue_data(self, days: int = 30) -> Dict[str, Any]:
        """Get revenue data for specified period"""
        try:
            if not self.service:
                return self._get_fallback_revenue_data(days)
            
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for API
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # Generate report
            report = self.service.accounts().reports().generate(
                account=f"accounts/{self.publisher_id}",
                dateRange=f"{start_date_str}..{end_date_str}",
                metrics=['TOTAL_EARNINGS', 'PAGE_VIEWS', 'CLICKS', 'IMPRESSIONS', 'CTR', 'CPC'],
                dimensions=['DATE'],
                orderBy=['+DATE']
            ).execute()
            
            # Process report data
            revenue_data = self._process_revenue_report(report, days)
            
            # Cache the data
            self.redis_client.set(
                f"adsense_revenue_{days}d", 
                json.dumps(revenue_data), 
                ex=300  # 5 minutes cache
            )
            
            return revenue_data
            
        except Exception as e:
            print(f"❌ Error fetching revenue data: {e}")
            return self._get_fallback_revenue_data(days)
    
    def _process_revenue_report(self, report: Dict, days: int) -> Dict[str, Any]:
        """Process AdSense revenue report"""
        if 'rows' not in report or not report['rows']:
            return self._get_fallback_revenue_data(days)
        
        total_earnings = 0.0
        total_pageviews = 0
        total_clicks = 0
        total_impressions = 0
        daily_data = []
        
        for row in report['rows']:
            # Extract metrics
            date = row['cells'][0]['value']
            earnings = float(row['cells'][1]['value']) if len(row['cells']) > 1 else 0.0
            pageviews = int(row['cells'][2]['value']) if len(row['cells']) > 2 else 0
            clicks = int(row['cells'][3]['value']) if len(row['cells']) > 3 else 0
            impressions = int(row['cells'][4]['value']) if len(row['cells']) > 4 else 0
            ctr = float(row['cells'][5]['value']) if len(row['cells']) > 5 else 0.0
            cpc = float(row['cells'][6]['value']) if len(row['cells']) > 6 else 0.0
            
            # Accumulate totals
            total_earnings += earnings
            total_pageviews += pageviews
            total_clicks += clicks
            total_impressions += impressions
            
            # Add to daily data
            daily_data.append({
                "date": date,
                "earnings": earnings,
                "pageviews": pageviews,
                "clicks": clicks,
                "impressions": impressions,
                "ctr": ctr,
                "cpc": cpc
            })
        
        # Calculate averages
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        avg_cpc = (total_earnings / total_clicks) if total_clicks > 0 else 0
        
        return {
            "period_days": days,
            "total_earnings": total_earnings,
            "total_pageviews": total_pageviews,
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "average_ctr": avg_ctr,
            "average_cpc": avg_cpc,
            "daily_data": daily_data[-7:],  # Last 7 days for charts
            "currency": "USD",
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_fallback_revenue_data(self, days: int) -> Dict[str, Any]:
        """Fallback revenue data when API is unavailable"""
        return {
            "period_days": days,
            "total_earnings": 0.0,
            "total_pageviews": 0,
            "total_clicks": 0,
            "total_impressions": 0,
            "average_ctr": 0.0,
            "average_cpc": 0.0,
            "daily_data": [],
            "currency": "USD",
            "last_updated": datetime.now().isoformat(),
            "status": "fallback_mode",
            "message": "Using fallback data - API not configured"
        }
    
    def get_site_performance(self, site_url: str) -> Dict[str, Any]:
        """Get performance data for specific site"""
        try:
            if not self.service:
                return {"error": "AdSense service not initialized"}
            
            # Get sites list first
            sites = self.service.accounts().sites().list(
                parent=f"accounts/{self.publisher_id}"
            ).execute()
            
            target_site = None
            for site in sites.get('sites', []):
                if site_url in site.get('domain', ''):
                    target_site = site
                    break
            
            if not target_site:
                return {"error": f"Site {site_url} not found in AdSense"}
            
            # Get performance data for the site
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            report = self.service.accounts().reports().generate(
                account=f"accounts/{self.publisher_id}",
                dateRange=f"{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}",
                metrics=['TOTAL_EARNINGS', 'CLICKS', 'IMPRESSIONS'],
                dimensions=['SITE_NAME'],
                filters=[f'SITE_NAME=={target_site["name"]}']
            ).execute()
            
            if 'rows' not in report or not report['rows']:
                return {"earnings": 0.0, "clicks": 0, "impressions": 0}
            
            row = report['rows'][0]
            return {
                "site_url": site_url,
                "earnings": float(row['cells'][1]['value']) if len(row['cells']) > 1 else 0.0,
                "clicks": int(row['cells'][2]['value']) if len(row['cells']) > 2 else 0,
                "impressions": int(row['cells'][3]['value']) if len(row['cells']) > 3 else 0,
                "period": "30_days"
            }
            
        except Exception as e:
            print(f"❌ Error fetching site performance: {e}")
            return {"error": str(e)}
    
    def get_top_pages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing pages"""
        try:
            if not self.service:
                return []
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
            
            report = self.service.accounts().reports().generate(
                account=f"accounts/{self.publisher_id}",
                dateRange=f"{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}",
                metrics=['TOTAL_EARNINGS', 'CLICKS', 'IMPRESSIONS'],
                dimensions=['PAGE_URL'],
                orderBy=['-TOTAL_EARNINGS'],
                limit=limit
            ).execute()
            
            top_pages = []
            for row in report.get('rows', []):
                top_pages.append({
                    "url": row['cells'][0]['value'],
                    "earnings": float(row['cells'][1]['value']) if len(row['cells']) > 1 else 0.0,
                    "clicks": int(row['cells'][2]['value']) if len(row['cells']) > 2 else 0,
                    "impressions": int(row['cells'][3]['value']) if len(row['cells']) > 3 else 0
                })
            
            return top_pages
            
        except Exception as e:
            print(f"❌ Error fetching top pages: {e}")
            return []
    
    def optimize_ad_placement(self, site_url: str) -> Dict[str, Any]:
        """Analyze and suggest ad placement optimization"""
        try:
            site_performance = self.get_site_performance(site_url)
            
            if "error" in site_performance:
                return site_performance
            
            impressions = site_performance.get("impressions", 0)
            clicks = site_performance.get("clicks", 0)
            earnings = site_performance.get("earnings", 0.0)
            
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            cpc = (earnings / clicks) if clicks > 0 else 0
            
            # Generate optimization suggestions
            suggestions = []
            
            if ctr < 1.0:
                suggestions.append({
                    "type": "ctr_improvement",
                    "priority": "high",
                    "suggestion": "CTR is below 1%. Consider adding more responsive ad units.",
                    "action": "Add sticky bottom banner and in-article ads"
                })
            
            if cpc < 0.1:
                suggestions.append({
                    "type": "cpc_improvement", 
                    "priority": "medium",
                    "suggestion": "CPC is low. Focus on high-value content topics.",
                    "action": "Create content around finance, tech, and business topics"
                })
            
            if impressions < 1000:
                suggestions.append({
                    "type": "traffic_improvement",
                    "priority": "high", 
                    "suggestion": "Low impressions. Focus on SEO and content marketing.",
                    "action": "Increase publishing frequency and optimize for search"
                })
            
            return {
                "site_url": site_url,
                "current_performance": {
                    "ctr": round(ctr, 2),
                    "cpc": round(cpc, 2),
                    "impressions": impressions,
                    "earnings": round(earnings, 2)
                },
                "suggestions": suggestions,
                "optimization_score": min(100, max(0, int((ctr * 20) + (cpc * 100) + (impressions / 100))))
            }
            
        except Exception as e:
            print(f"❌ Error generating optimization suggestions: {e}")
            return {"error": str(e)}

def main():
    """AdSense Manager service entry point"""
    try:
        manager = AdSenseManager()
        
        print("📊 Starting AdSense Manager Service")
        print("🔄 Fetching account information...")
        
        # Test API connection
        account_info = manager.get_account_info()
        if "error" not in account_info:
            print(f"✅ Connected to AdSense account: {account_info.get('display_name', 'Unknown')}")
        
        # Continuous operation - update data every 5 minutes
        while True:
            try:
                # Fetch latest revenue data
                revenue_data = manager.get_revenue_data(30)
                print(f"💰 Revenue (30d): ${revenue_data.get('total_earnings', 0):.2f}")
                
                # Cache current stats
                stats = {
                    "total_earnings": revenue_data.get('total_earnings', 0),
                    "total_impressions": revenue_data.get('total_impressions', 0),
                    "total_clicks": revenue_data.get('total_clicks', 0),
                    "last_updated": datetime.now().isoformat()
                }
                
                manager.redis_client.set("adsense_current_stats", json.dumps(stats), ex=300)
                
                # Sleep for 5 minutes
                time.sleep(300)
                
            except KeyboardInterrupt:
                print("📱 AdSense Manager stopped")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(60)
                
    except Exception as e:
        print(f"❌ Failed to start AdSense Manager: {e}")

if __name__ == "__main__":
    main()