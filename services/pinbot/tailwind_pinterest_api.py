#!/usr/bin/env python3
"""
Tailwind API entegrasyonu ile Pinterest otomasyonu
Pinterest API'nin daha kolay ve güvenilir alternatifi
"""

import os
import json
import time
import requests
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class TailwindPinterestAPI:
    def __init__(self):
        self.api_key = os.getenv("TAILWIND_API_KEY")
        self.base_url = "https://api.tailwindapp.com/v1"
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"), 
            port=int(os.getenv("REDIS_PORT", "6379")), 
            decode_responses=True
        )
        
        if not self.api_key:
            raise ValueError("TAILWIND_API_KEY environment variable required")
    
    def _make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """Tailwind API'ye güvenli istek gönder"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AutoAdSense-Bot/1.0"
        }
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Tailwind API Error: {e}")
            return {"error": str(e), "success": False}
    
    def get_pinterest_accounts(self) -> List[Dict]:
        """Bağlı Pinterest hesaplarını listele"""
        accounts = self._make_request("accounts")
        
        if accounts.get("success"):
            pinterest_accounts = [
                acc for acc in accounts.get("data", []) 
                if acc.get("platform") == "pinterest"
            ]
            
            # Redis'e kaydet
            self.redis_client.set("pinterest_accounts", json.dumps(pinterest_accounts))
            return pinterest_accounts
        
        return []
    
    def get_pinterest_boards(self, account_id: str) -> List[Dict]:
        """Belirli hesabın board'larını getir"""
        boards = self._make_request(f"accounts/{account_id}/boards")
        
        if boards.get("success"):
            board_list = boards.get("data", [])
            self.redis_client.set(f"pinterest_boards_{account_id}", json.dumps(board_list))
            return board_list
        
        return []
    
    def create_pin(self, pin_data: Dict) -> Dict:
        """
        Yeni pin oluştur
        pin_data = {
            "account_id": "xxx",
            "board_id": "yyy", 
            "image_url": "https://...",
            "title": "Pin title",
            "description": "Pin description",
            "link": "https://your-website.com/article",
            "schedule_time": "2024-01-01T12:00:00Z" (optional)
        }
        """
        
        # Pin verisini hazırla
        pin_payload = {
            "account_id": pin_data["account_id"],
            "board_id": pin_data["board_id"],
            "media_url": pin_data["image_url"],
            "title": pin_data["title"][:100],  # Pinterest title limit
            "description": pin_data["description"][:500],  # Pinterest desc limit
            "link": pin_data["link"]
        }
        
        # Zamanlanmış pin ise
        if pin_data.get("schedule_time"):
            pin_payload["schedule_time"] = pin_data["schedule_time"]
            endpoint = "pins/schedule"
        else:
            endpoint = "pins"
        
        result = self._make_request(endpoint, method="POST", data=pin_payload)
        
        if result.get("success"):
            # Başarılı pin'i Redis'e kaydet
            pin_info = {
                "pin_id": result.get("data", {}).get("id"),
                "title": pin_data["title"],
                "link": pin_data["link"],
                "created_at": datetime.now().isoformat(),
                "status": "scheduled" if pin_data.get("schedule_time") else "posted"
            }
            
            self.redis_client.lpush("successful_pins", json.dumps(pin_info))
            self.redis_client.ltrim("successful_pins", 0, 99)  # Son 100 pin'i tut
            
            print(f"✅ Pin başarıyla oluşturuldu: {pin_data['title']}")
            return {"success": True, "pin_id": pin_info["pin_id"]}
        else:
            print(f"❌ Pin oluşturulamadı: {result.get('error', 'Unknown error')}")
            return {"success": False, "error": result.get("error")}
    
    def get_pin_analytics(self, pin_id: str) -> Dict:
        """Pin analytics verilerini getir"""
        analytics = self._make_request(f"pins/{pin_id}/analytics")
        
        if analytics.get("success"):
            return analytics.get("data", {})
        
        return {}
    
    def get_account_analytics(self, account_id: str, days: int = 7) -> Dict:
        """Hesap analytics verilerini getir"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        analytics = self._make_request(
            f"accounts/{account_id}/analytics", 
            data={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        
        if analytics.get("success"):
            data = analytics.get("data", {})
            
            # Redis'e kaydet
            cache_key = f"pinterest_analytics_{account_id}_{days}d"
            self.redis_client.set(cache_key, json.dumps(data), ex=3600)  # 1 saat cache
            
            return data
        
        return {}
    
    def bulk_schedule_pins(self, pins_data: List[Dict]) -> Dict:
        """Toplu pin zamanlama"""
        results = {"success": 0, "failed": 0, "errors": []}
        
        for pin_data in pins_data:
            result = self.create_pin(pin_data)
            
            if result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "pin": pin_data.get("title", "Unknown"),
                    "error": result.get("error", "Unknown error")
                })
            
            # Rate limiting - Tailwind genelde cömert ama yine de nazik olalım
            time.sleep(2)
        
        print(f"📊 Bulk pin results: {results['success']} success, {results['failed']} failed")
        return results
    
    def get_dashboard_stats(self) -> Dict:
        """Dashboard için Pinterest istatistikleri"""
        stats = {
            "total_accounts": 0,
            "total_boards": 0,
            "pins_today": 0,
            "pins_this_week": 0,
            "total_impressions": 0,
            "total_clicks": 0,
            "accounts": []
        }
        
        try:
            # Hesapları getir
            accounts = self.get_pinterest_accounts()
            stats["total_accounts"] = len(accounts)
            
            for account in accounts:
                account_id = account.get("id")
                account_stats = {
                    "id": account_id,
                    "username": account.get("username", "Unknown"),
                    "status": account.get("status", "Active"),
                    "boards": 0,
                    "pins_today": 0,
                    "impressions": 0,
                    "clicks": 0
                }
                
                # Board sayısı
                boards = self.get_pinterest_boards(account_id)
                account_stats["boards"] = len(boards)
                stats["total_boards"] += len(boards)
                
                # Analytics
                analytics = self.get_account_analytics(account_id, days=1)  # Bugün
                account_stats["pins_today"] = analytics.get("pins_created", 0)
                account_stats["impressions"] = analytics.get("impressions", 0)
                account_stats["clicks"] = analytics.get("clicks", 0)
                
                stats["pins_today"] += account_stats["pins_today"]
                stats["total_impressions"] += account_stats["impressions"]
                stats["total_clicks"] += account_stats["clicks"]
                
                stats["accounts"].append(account_stats)
            
            # Haftalık pin sayısı
            weekly_analytics = self.get_account_analytics(accounts[0].get("id") if accounts else "", days=7)
            stats["pins_this_week"] = weekly_analytics.get("pins_created", 0)
            
        except Exception as e:
            print(f"❌ Dashboard stats error: {e}")
        
        return stats


def main():
    """Test Tailwind API bağlantısı"""
    try:
        tailwind = TailwindPinterestAPI()
        
        print("🔄 Tailwind Pinterest API Test...")
        
        # Hesapları listele
        accounts = tailwind.get_pinterest_accounts()
        print(f"📱 Bağlı Pinterest hesapları: {len(accounts)}")
        
        for account in accounts:
            print(f"  - {account.get('username', 'Unknown')} ({account.get('status', 'Unknown')})")
            
            # Board'ları listele
            boards = tailwind.get_pinterest_boards(account.get("id"))
            print(f"    Boards: {len(boards)}")
        
        # Dashboard stats
        stats = tailwind.get_dashboard_stats()
        print(f"📊 Dashboard stats: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()
