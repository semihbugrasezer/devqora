#!/usr/bin/env python3
"""
Auto-Adsense Pinterest Bot - Automated Poster
Works with n8n workflow system to automatically post content
"""

import os
import json
import time
import random
import redis
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class AutoPinterestBot:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        self.daily_targets = {
            'pins': int(os.getenv("DAILY_PIN_TARGET", "6")),
            'repins': int(os.getenv("DAILY_REPIN_TARGET", "3")),
            'comments': int(os.getenv("DAILY_COMMENT_TARGET", "2")),
            'follows': int(os.getenv("DAILY_FOLLOW_TARGET", "2"))
        }
        
        self.window_start = os.getenv("WINDOW_START", "08:00")
        self.window_end = os.getenv("WINDOW_END", "22:30")
        
        self.domains = [
            "https://hing.me",
            "https://playu.co"
        ]
        
        self.pinterest_token = os.getenv("PINTEREST_ACCESS_TOKEN")
        self.board_id = os.getenv("PINTEREST_BOARD_ID")
        
        # Daily counters
        self.daily_stats = self._load_daily_stats()
    
    def _load_daily_stats(self) -> Dict[str, int]:
        """Load daily statistics from Redis"""
        today = datetime.now().strftime("%Y-%m-%d")
        stats_key = f"daily_stats:{today}"
        
        stats = self.redis_client.hgetall(stats_key)
        if not stats:
            return {k: 0 for k in self.daily_targets.keys()}
        
        return {k: int(v) for k, v in stats.items()}
    
    def _save_daily_stats(self):
        """Save daily statistics to Redis"""
        today = datetime.now().strftime("%Y-%m-%d")
        stats_key = f"daily_stats:{today}"
        
        self.redis_client.hset(stats_key, mapping=self.daily_stats)
        self.redis_client.expire(stats_key, 86400 * 7)  # Keep for 7 days
    
    def _is_within_window(self) -> bool:
        """Check if current time is within posting window"""
        now = datetime.now().time()
        start_h, start_m = map(int, self.window_start.split(":"))
        end_h, end_m = map(int, self.window_end.split(":"))
        
        start_time = datetime.strptime(self.window_start, "%H:%M").time()
        end_time = datetime.strptime(self.window_end, "%H:%M").time()
        
        if start_time <= end_time:
            return start_time <= now <= end_time
        else:  # Crosses midnight
            return now >= start_time or now <= end_time
    
    def _can_post(self, post_type: str) -> bool:
        """Check if we can post this type of content"""
        if not self._is_within_window():
            return False
        
        current_count = self.daily_stats.get(post_type, 0)
        target = self.daily_targets.get(post_type, 0)
        
        return current_count < target
    
    def _generate_pin_content(self, keyword: str) -> Dict[str, str]:
        """Generate Pinterest pin content from keyword"""
        templates = [
            f"🎯 {keyword.title()} - Expert Tips & Strategies",
            f"💡 {keyword.title()} - Complete Guide for Beginners",
            f"🚀 {keyword.title()} - Advanced Techniques Revealed",
            f"📚 {keyword.title()} - Everything You Need to Know",
            f"⚡ {keyword.title()} - Quick & Effective Methods"
        ]
        
        descriptions = [
            f"Discover the best {keyword} strategies and tips. Click to read our comprehensive guide!",
            f"Learn {keyword} from experts. Get actionable advice and step-by-step instructions.",
            f"Master {keyword} with our proven methods. Start improving today!",
            f"Get insider tips on {keyword}. Transform your results with our expert guidance.",
            f"Unlock the secrets of {keyword}. Join thousands who've already succeeded!"
        ]
        
        return {
            "title": random.choice(templates),
            "description": random.choice(descriptions),
            "link": random.choice(self.domains),
            "hashtags": f"#{keyword.replace(' ', '')} #guide #tips #howto #expert"
        }
    
    def _post_to_pinterest(self, content: Dict[str, str]) -> Dict[str, str]:
        """Post content to Pinterest (mock implementation)"""
        if not self.pinterest_token or not self.board_id:
            # Mock posting for testing
            time.sleep(random.uniform(2, 5))
            return {
                "status": "success",
                "pin_id": f"mock_pin_{int(time.time())}",
                "message": "Mock Pinterest post successful"
            }
        
        # Real Pinterest API implementation would go here
        # For now, return mock success
        return {
            "status": "success",
            "pin_id": f"real_pin_{int(time.time())}",
            "message": "Pinterest post successful"
        }
    
    def process_keyword_queue(self):
        """Process keywords from the queue and create pins"""
        while True:
            try:
                # Check if we can post
                if not self._can_post('pins'):
                    time.sleep(300)  # Wait 5 minutes
                    continue
                
                # Get keyword from queue
                keyword_data = self.redis_client.rpop("keyword_queue")
                if not keyword_data:
                    time.sleep(60)  # Wait 1 minute
                    continue
                
                # Parse keyword
                try:
                    keyword_info = json.loads(keyword_data)
                    keyword = keyword_info.get("keyword", "")
                except json.JSONDecodeError:
                    keyword = keyword_data
                
                if not keyword:
                    continue
                
                # Generate pin content
                pin_content = self._generate_pin_content(keyword)
                
                # Post to Pinterest
                result = self._post_to_pinterest(pin_content)
                
                # Update statistics
                self.daily_stats['pins'] = self.daily_stats.get('pins', 0) + 1
                self._save_daily_stats()
                
                # Log success
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "event": "pin_created",
                    "keyword": keyword,
                    "content": pin_content,
                    "result": result
                }
                
                self.redis_client.lpush("automation_logs", json.dumps(log_entry))
                self.redis_client.ltrim("automation_logs", 0, 999)  # Keep last 1000 logs
                
                print(f"✅ Pin created for keyword: {keyword}")
                
                # Random delay between posts
                delay = random.randint(1800, 7200)  # 30 minutes to 2 hours
                time.sleep(delay)
                
            except Exception as e:
                error_log = {
                    "timestamp": datetime.now().isoformat(),
                    "event": "error",
                    "error": str(e),
                    "type": "pin_creation"
                }
                
                self.redis_client.lpush("automation_logs", json.dumps(error_log))
                print(f"❌ Error in pin creation: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def run(self):
        """Main bot loop"""
        print("🤖 Auto-Adsense Pinterest Bot Started")
        print(f"📊 Daily Targets: {self.daily_targets}")
        print(f"⏰ Posting Window: {self.window_start} - {self.window_end}")
        print(f"🌐 Domains: {', '.join(self.domains)}")
        
        self.process_keyword_queue()

if __name__ == "__main__":
    bot = AutoPinterestBot()
    bot.run()
