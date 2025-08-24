#!/usr/bin/env python3
"""
Gelişmiş Tailwind Pinterest Worker
- Otomatik pin scheduling
- Smart timing
- Anti-spam koruma
- Multi-account management
"""

import os
import json
import time
import random
import redis
from datetime import datetime, timedelta
from typing import Dict, Optional
from typing import List
from tailwind_pinterest_api import TailwindPinterestAPI

class EnhancedTailwindWorker:
    def __init__(self):
        self.tailwind = TailwindPinterestAPI()
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"), 
            port=int(os.getenv("REDIS_PORT", "6379")), 
            decode_responses=True
        )
        
        # Ayarlar
        self.daily_pin_target = int(os.getenv("DAILY_PIN_TARGET", "6"))
        self.window_start = os.getenv("WINDOW_START", "08:00")
        self.window_end = os.getenv("WINDOW_END", "22:30")
        self.domain_rotation = [
            d.strip() for d in os.getenv("DOMAIN_ROTATION", "").split(",") 
            if d.strip()
        ]
        
        print(f"🎯 Enhanced Tailwind Worker başlatıldı")
        print(f"📌 Daily pin target: {self.daily_pin_target}")
        print(f"🕐 Active window: {self.window_start} - {self.window_end}")
        print(f"🌐 Domain rotation: {len(self.domain_rotation)} domains")
    
    def is_active_window(self) -> bool:
        """Aktif çalışma saati kontrolü"""
        now = datetime.now().time()
        start_time = datetime.strptime(self.window_start, "%H:%M").time()
        end_time = datetime.strptime(self.window_end, "%H:%M").time()
        
        if start_time <= end_time:
            return start_time <= now <= end_time
        else:  # Gece geçen saat aralığı
            return now >= start_time or now <= end_time
    
    def get_today_pin_count(self, account_id: str) -> int:
        """Bugün atılan pin sayısını getir"""
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"pins_today_{account_id}_{today}"
        
        count = self.redis_client.get(cache_key)
        return int(count) if count else 0
    
    def increment_today_pin_count(self, account_id: str):
        """Bugünkü pin sayısını artır"""
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"pins_today_{account_id}_{today}"
        
        self.redis_client.incr(cache_key)
        self.redis_client.expire(cache_key, 86400)  # 24 saat
    
    def get_optimal_posting_times(self) -> List[str]:
        """Pinterest için optimal posting zamanları"""
        optimal_hours = [
            "08:00", "09:30", "11:00", "14:00", "16:30", 
            "18:00", "19:30", "20:00", "21:00"
        ]
        
        today = datetime.now().date()
        times = []
        
        for hour in optimal_hours:
            post_time = datetime.combine(today, datetime.strptime(hour, "%H:%M").time())
            
            # Gelecek zamanlara sadece bugün için
            if post_time > datetime.now():
                times.append(post_time.isoformat() + "Z")
        
        return times
    
    def create_smart_pin(self, content_data: Dict) -> bool:
        """Akıllı pin oluşturma"""
        try:
            # Pinterest hesaplarını getir
            accounts = self.tailwind.get_pinterest_accounts()
            
            if not accounts:
                print("❌ Pinterest hesabı bulunamadı")
                return False
            
            # En az kullanılan hesabı seç
            selected_account = None
            min_pins_today = float('inf')
            
            for account in accounts:
                account_id = account.get("id")
                pins_today = self.get_today_pin_count(account_id)
                
                if pins_today < min_pins_today and pins_today < self.daily_pin_target:
                    min_pins_today = pins_today
                    selected_account = account
            
            if not selected_account:
                print("📌 Tüm hesaplar günlük limite ulaştı")
                return False
            
            account_id = selected_account.get("id")
            
            # Board'ları getir
            boards = self.tailwind.get_pinterest_boards(account_id)
            if not boards:
                print(f"❌ {selected_account.get('username')} hesabında board bulunamadı")
                return False
            
            # Rastgele board seç
            selected_board = random.choice(boards)
            
            # Domain rotasyonu
            target_url = random.choice(self.domain_rotation) if self.domain_rotation else "https://example.com"
            if not target_url.startswith("http"):
                target_url = f"https://{target_url}"
            
            # Pin verisini hazırla
            pin_data = {
                "account_id": account_id,
                "board_id": selected_board.get("id"),
                "image_url": content_data.get("image_url"),
                "title": content_data.get("title", "")[:100],
                "description": content_data.get("description", "")[:500],
                "link": f"{target_url.rstrip('/')}/{content_data.get('slug', '')}"
            }
            
            # Zamanlanmış pin için optimal zaman seç
            optimal_times = self.get_optimal_posting_times()
            if optimal_times and random.choice([True, False]):  # %50 şans ile zamanla
                pin_data["schedule_time"] = random.choice(optimal_times)
            
            # Pin'i oluştur
            result = self.tailwind.create_pin(pin_data)
            
            if result.get("success"):
                # Başarı istatistikleri
                self.increment_today_pin_count(account_id)
                
                # Redis'e log
                pin_log = {
                    "timestamp": datetime.now().isoformat(),
                    "account": selected_account.get("username"),
                    "board": selected_board.get("name"),
                    "title": pin_data["title"],
                    "url": pin_data["link"],
                    "scheduled": bool(pin_data.get("schedule_time")),
                    "status": "success"
                }
                
                self.redis_client.lpush("pin_logs", json.dumps(pin_log))
                self.redis_client.ltrim("pin_logs", 0, 199)  # Son 200 log
                
                print(f"✅ Pin created: {pin_data['title']} -> {selected_account.get('username')}")
                return True
            else:
                print(f"❌ Pin creation failed: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ Smart pin creation error: {e}")
            return False
    
    def process_content_queue(self):
        """İçerik kuyruğunu işle"""
        try:
            # İçerik kuyruğundan al
            content_raw = self.redis_client.rpop("content_for_pinterest")
            
            if not content_raw:
                return False
            
            content_data = json.loads(content_raw)
            
            # Pin oluştur
            success = self.create_smart_pin(content_data)
            
            if success:
                # Başarı istatistikleri
                self.redis_client.incr("total_pins_sent")
                self.redis_client.incr(f"pins_sent_{datetime.now().strftime('%Y-%m-%d')}")
            else:
                # Başarısız pin'i tekrar kuyruğa ekle (max 3 deneme)
                retry_count = content_data.get("retry_count", 0)
                if retry_count < 3:
                    content_data["retry_count"] = retry_count + 1
                    self.redis_client.lpush("content_for_pinterest", json.dumps(content_data))
            
            return success
            
        except Exception as e:
            print(f"❌ Content queue processing error: {e}")
            return False
    
    def run_worker_cycle(self):
        """Ana worker döngüsü"""
        print(f"🔄 Worker cycle started at {datetime.now().strftime('%H:%M:%S')}")
        
        # Aktif saatlerde çalış
        if not self.is_active_window():
            print(f"⏰ Outside active window ({self.window_start}-{self.window_end})")
            return
        
        # İçerik işle
        processed = self.process_content_queue()
        
        if processed:
            print("✅ Content processed successfully")
        else:
            print("ℹ️ No content to process")
        
        # Dashboard stats güncelle
        self.update_dashboard_stats()
    
    def update_dashboard_stats(self):
        """Dashboard istatistiklerini güncelle"""
        try:
            stats = self.tailwind.get_dashboard_stats()
            self.redis_client.set("pinterest_dashboard_stats", json.dumps(stats), ex=300)  # 5 dakika cache
        except Exception as e:
            print(f"❌ Dashboard stats update error: {e}")
    
    def run(self):
        """Ana worker loop"""
        print("🚀 Enhanced Tailwind Worker started!")
        
        while True:
            try:
                self.run_worker_cycle()
                
                # Rastgele bekleme (10-30 dakika)
                wait_time = random.randint(600, 1800)
                print(f"⏰ Waiting {wait_time//60} minutes until next cycle...")
                time.sleep(wait_time)
                
            except KeyboardInterrupt:
                print("\n👋 Worker stopped by user")
                break
            except Exception as e:
                print(f"❌ Worker error: {e}")
                print("🔄 Restarting in 5 minutes...")
                time.sleep(300)

def main():
    """Worker'ı başlat"""
    worker = EnhancedTailwindWorker()
    worker.run()

if __name__ == "__main__":
    main()
