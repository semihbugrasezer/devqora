# /srv/auto-adsense/services/analytics/real_analytics_service.py
import os
import json
import time
import redis
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from typing import Dict, Any, List

class RealAnalyticsService:
    """Real Analytics Service - NO MOCK DATA, only real integrations"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        # Real API credentials (required)
        self.google_analytics_key = os.getenv("GOOGLE_ANALYTICS_API_KEY")
        self.google_search_console_key = os.getenv("GOOGLE_SEARCH_CONSOLE_API_KEY")
        self.adsense_api_key = os.getenv("GOOGLE_ADSENSE_API_KEY")
        
        # Site configurations
        self.sites = {
            "hing.me": {
                "ga_property_id": os.getenv("HING_GA_PROPERTY_ID"),
                "gsc_site_url": "https://hing.me/",
                "adsense_client": os.getenv("HING_ADSENSE_CLIENT_ID")
            },
            "playu.co": {
                "ga_property_id": os.getenv("PLAYU_GA_PROPERTY_ID"),
                "gsc_site_url": "https://playu.co/",
                "adsense_client": os.getenv("PLAYU_ADSENSE_CLIENT_ID")
            }
        }
        
        self.validate_configuration()
    
    def validate_configuration(self):
        """Validate all required configurations"""
        missing = []
        
        if not self.google_analytics_key:
            missing.append("GOOGLE_ANALYTICS_API_KEY")
        if not self.google_search_console_key:
            missing.append("GOOGLE_SEARCH_CONSOLE_API_KEY")
        if not self.adsense_api_key:
            missing.append("GOOGLE_ADSENSE_API_KEY")
        
        for domain, config in self.sites.items():
            if not config["ga_property_id"]:
                missing.append(f"{domain.upper().replace('.', '_')}_GA_PROPERTY_ID")
            if not config["adsense_client"]:
                missing.append(f"{domain.upper().replace('.', '_')}_ADSENSE_CLIENT_ID")
        
        if missing:
            raise Exception(f"Missing required configuration: {', '.join(missing)}")
        
        print("✅ All analytics configurations validated")
    
    def fetch_real_google_analytics(self, domain: str, days: int = 7) -> Dict[str, Any]:
        """Fetch REAL Google Analytics data"""
        try:
            site_config = self.sites[domain]
            property_id = site_config["ga_property_id"]
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Google Analytics Data API v1
            url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
            
            headers = {
                "Authorization": f"Bearer {self.google_analytics_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "dateRanges": [{
                    "startDate": start_date.strftime("%Y-%m-%d"),
                    "endDate": end_date.strftime("%Y-%m-%d")
                }],
                "dimensions": [
                    {"name": "date"},
                    {"name": "pagePath"},
                    {"name": "deviceCategory"}
                ],
                "metrics": [
                    {"name": "activeUsers"},
                    {"name": "sessions"},
                    {"name": "pageviews"},
                    {"name": "bounceRate"},
                    {"name": "sessionDuration"}
                ]
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return self.process_ga_data(data, domain)
            else:
                raise Exception(f"GA API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Google Analytics error for {domain}: {e}")
            raise e
    
    def process_ga_data(self, raw_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Process Google Analytics API response"""
        rows = raw_data.get("rows", [])
        
        if not rows:
            return {
                "domain": domain,
                "total_users": 0,
                "total_sessions": 0,
                "total_pageviews": 0,
                "bounce_rate": 0,
                "avg_session_duration": 0,
                "daily_data": {},
                "top_pages": [],
                "device_breakdown": {},
                "updated_at": datetime.now().isoformat()
            }
        
        # Aggregate data
        total_users = 0
        total_sessions = 0
        total_pageviews = 0
        total_bounce_rate = 0
        total_duration = 0
        
        daily_data = {}
        page_data = {}
        device_data = {"desktop": 0, "mobile": 0, "tablet": 0}
        
        for row in rows:
            dimensions = row.get("dimensionValues", [])
            metrics = row.get("metricValues", [])
            
            if len(dimensions) >= 3 and len(metrics) >= 5:
                date = dimensions[0]["value"]
                page = dimensions[1]["value"]
                device = dimensions[2]["value"]
                
                users = int(metrics[0]["value"])
                sessions = int(metrics[1]["value"])
                pageviews = int(metrics[2]["value"])
                bounce_rate = float(metrics[3]["value"])
                duration = float(metrics[4]["value"])
                
                # Totals
                total_users += users
                total_sessions += sessions
                total_pageviews += pageviews
                total_bounce_rate += bounce_rate
                total_duration += duration
                
                # Daily data
                if date not in daily_data:
                    daily_data[date] = {"users": 0, "sessions": 0, "pageviews": 0}
                daily_data[date]["users"] += users
                daily_data[date]["sessions"] += sessions
                daily_data[date]["pageviews"] += pageviews
                
                # Page data
                if page not in page_data:
                    page_data[page] = {"users": 0, "pageviews": 0}
                page_data[page]["users"] += users
                page_data[page]["pageviews"] += pageviews
                
                # Device data
                if device.lower() in device_data:
                    device_data[device.lower()] += users
        
        # Sort top pages
        top_pages = sorted(
            [{"page": page, **data} for page, data in page_data.items()],
            key=lambda x: x["pageviews"],
            reverse=True
        )[:10]
        
        result = {
            "domain": domain,
            "total_users": total_users,
            "total_sessions": total_sessions,
            "total_pageviews": total_pageviews,
            "bounce_rate": round(total_bounce_rate / len(rows) if rows else 0, 2),
            "avg_session_duration": round(total_duration / len(rows) if rows else 0, 2),
            "daily_data": daily_data,
            "top_pages": top_pages,
            "device_breakdown": device_data,
            "updated_at": datetime.now().isoformat()
        }
        
        # Cache real data
        self.redis_client.setex(
            f"real_ga:{domain}",
            1800,  # 30 minutes
            json.dumps(result)
        )
        
        return result
    
    def fetch_real_adsense_revenue(self, domain: str, days: int = 7) -> Dict[str, Any]:
        """Fetch REAL AdSense revenue data"""
        try:
            site_config = self.sites[domain]
            client_id = site_config["adsense_client"]
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # AdSense Management API
            url = f"https://adsense.googleapis.com/v2/accounts/{client_id}/reports:generate"
            
            headers = {
                "Authorization": f"Bearer {self.adsense_api_key}",
                "Content-Type": "application/json"
            }
            
            params = {
                "dateRange.startDate.year": start_date.year,
                "dateRange.startDate.month": start_date.month,
                "dateRange.startDate.day": start_date.day,
                "dateRange.endDate.year": end_date.year,
                "dateRange.endDate.month": end_date.month,
                "dateRange.endDate.day": end_date.day,
                "dimensions": ["DATE"],
                "metrics": ["EARNINGS", "CLICKS", "IMPRESSIONS", "CTR", "CPC"]
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return self.process_adsense_data(data, domain)
            else:
                raise Exception(f"AdSense API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ AdSense error for {domain}: {e}")
            raise e
    
    def process_adsense_data(self, raw_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Process AdSense API response"""
        rows = raw_data.get("rows", [])
        
        total_earnings = 0
        total_clicks = 0
        total_impressions = 0
        daily_revenue = {}
        
        for row in rows:
            cells = row.get("cells", [])
            if len(cells) >= 6:
                date = cells[0]["value"]
                earnings = float(cells[1]["value"])
                clicks = int(cells[2]["value"])
                impressions = int(cells[3]["value"])
                ctr = float(cells[4]["value"])
                cpc = float(cells[5]["value"])
                
                total_earnings += earnings
                total_clicks += clicks
                total_impressions += impressions
                
                daily_revenue[date] = {
                    "earnings": earnings,
                    "clicks": clicks,
                    "impressions": impressions,
                    "ctr": ctr,
                    "cpc": cpc
                }
        
        result = {
            "domain": domain,
            "total_earnings": round(total_earnings, 2),
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "average_ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
            "average_cpc": round(total_earnings / total_clicks if total_clicks > 0 else 0, 2),
            "daily_revenue": daily_revenue,
            "updated_at": datetime.now().isoformat()
        }
        
        # Cache real data
        self.redis_client.setex(
            f"real_adsense:{domain}",
            1800,
            json.dumps(result)
        )
        
        return result
    
    def fetch_all_real_analytics(self) -> Dict[str, Any]:
        """Fetch all real analytics for all sites"""
        results = {}
        
        for domain in self.sites.keys():
            try:
                print(f"🔍 Fetching real analytics for {domain}")
                
                # Google Analytics
                ga_data = self.fetch_real_google_analytics(domain)
                
                # AdSense Revenue
                adsense_data = self.fetch_real_adsense_revenue(domain)
                
                results[domain] = {
                    "google_analytics": ga_data,
                    "adsense": adsense_data,
                    "last_updated": datetime.now().isoformat()
                }
                
                print(f"✅ {domain}: {ga_data['total_pageviews']} pageviews, ${adsense_data['total_earnings']} revenue")
                
            except Exception as e:
                print(f"❌ Failed to fetch analytics for {domain}: {e}")
                results[domain] = {
                    "error": str(e),
                    "last_updated": datetime.now().isoformat()
                }
            
            # Rate limiting
            time.sleep(2)
        
        # Cache aggregated results
        self.redis_client.setex(
            "all_real_analytics",
            1800,
            json.dumps(results)
        )
        
        return results

# Flask API for real-time analytics
app = Flask(__name__)
analytics_service = None

@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "real_analytics"})

@app.route('/analytics/<domain>')
def get_domain_analytics(domain):
    try:
        if domain not in analytics_service.sites:
            return jsonify({"error": "Domain not configured"}), 404
        
        # Try to get cached data first
        cached_ga = analytics_service.redis_client.get(f"real_ga:{domain}")
        cached_adsense = analytics_service.redis_client.get(f"real_adsense:{domain}")
        
        if cached_ga and cached_adsense:
            return jsonify({
                "google_analytics": json.loads(cached_ga),
                "adsense": json.loads(cached_adsense),
                "cached": True
            })
        
        # Fetch fresh data
        ga_data = analytics_service.fetch_real_google_analytics(domain)
        adsense_data = analytics_service.fetch_real_adsense_revenue(domain)
        
        return jsonify({
            "google_analytics": ga_data,
            "adsense": adsense_data,
            "cached": False
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analytics/refresh', methods=['POST'])
def refresh_analytics():
    try:
        results = analytics_service.fetch_all_real_analytics()
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analytics/summary')
def get_analytics_summary():
    try:
        cached = analytics_service.redis_client.get("all_real_analytics")
        if cached:
            data = json.loads(cached)
            
            total_pageviews = 0
            total_revenue = 0
            
            for domain_data in data.values():
                if "google_analytics" in domain_data:
                    total_pageviews += domain_data["google_analytics"].get("total_pageviews", 0)
                if "adsense" in domain_data:
                    total_revenue += domain_data["adsense"].get("total_earnings", 0)
            
            return jsonify({
                "total_pageviews": total_pageviews,
                "total_revenue": round(total_revenue, 2),
                "sites_count": len(data),
                "last_updated": datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "No cached data available"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def main():
    """Run real analytics service"""
    global analytics_service
    
    try:
        analytics_service = RealAnalyticsService()
        print("🚀 Real Analytics Service started - NO MOCK DATA")
        
        # Initial data fetch
        print("📊 Fetching initial analytics data...")
        analytics_service.fetch_all_real_analytics()
        
        # Start Flask API
        app.run(host="0.0.0.0", port=5060, debug=False)
        
    except Exception as e:
        print(f"❌ Failed to start Real Analytics Service: {e}")
        print("Required environment variables:")
        print("- GOOGLE_ANALYTICS_API_KEY")
        print("- GOOGLE_SEARCH_CONSOLE_API_KEY") 
        print("- GOOGLE_ADSENSE_API_KEY")
        print("- HING_GA_PROPERTY_ID, HING_ADSENSE_CLIENT_ID")
        print("- PLAYU_GA_PROPERTY_ID, PLAYU_ADSENSE_CLIENT_ID")

if __name__ == "__main__":
    main()
