# /srv/auto-adsense/services/orchestrator/ai_orchestrator.py
import os
import json
import time
import redis
import asyncio
import schedule
from datetime import datetime, timedelta
from typing import Dict, Any, List
import requests

class AIContentOrchestrator:
    """AI İçerik Üretimi Orchestrator - Ana Kontrol Merkezi"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        # Domain configurations
        self.domains = {
            "hing.me": {
                "niche": "finance",
                "daily_target_articles": 3,
                "main_topics_rotation": ["investment_strategies", "personal_finance", "business_finance", "market_analysis"],
                "pinterest_boards": ["finance-tips", "investment-guide", "money-management"],
                "content_angles": ["comprehensive_guide", "beginner_tutorial", "expert_analysis", "problem_solving"]
            },
            "playu.co": {
                "niche": "gaming",
                "daily_target_articles": 3,
                "main_topics_rotation": ["esports_professional", "gaming_technology", "game_development", "gaming_culture"],
                "pinterest_boards": ["gaming-tips", "esports-guide", "gaming-setup"],
                "content_angles": ["comprehensive_guide", "beginner_tutorial", "expert_analysis", "problem_solving"]
            }
        }
        
        # AI Workflow configuration
        self.workflow_schedule = {
            "morning": {
                "time": "09:00",
                "tasks": ["plan_daily_content", "generate_morning_articles", "trigger_images"]
            },
            "afternoon": {
                "time": "14:00", 
                "tasks": ["generate_afternoon_articles", "trigger_images", "check_ai_status"]
            },
            "evening": {
                "time": "19:00",
                "tasks": ["generate_evening_articles", "trigger_images", "pinterest_posting"]
            },
            "night": {
                "time": "23:00",
                "tasks": ["daily_report", "schedule_tomorrow", "cleanup_old_data"]
            }
        }
        
        self.log_info("AI Content Orchestrator initialized")
    
    async def run_orchestrator(self):
        """Ana orchestrator loop"""
        print("🎯 AI Content Orchestrator started")
        print("📝 Managing AI content generation workflow")
        
        # Schedule tasks
        schedule.every().day.at("09:00").do(self.morning_workflow)
        schedule.every().day.at("14:00").do(self.afternoon_workflow)
        schedule.every().day.at("19:00").do(self.evening_workflow)
        schedule.every().day.at("23:00").do(self.night_workflow)
        
        # İlk başlangıçta hemen çalıştır
        await self.morning_workflow()
        
        while True:
            try:
                # Scheduled tasks çalıştır
                schedule.run_pending()
                
                # Manual triggers kontrol et
                await self.check_manual_triggers()
                
                # System health check
                await self.system_health_check()
                
                await asyncio.sleep(60)  # Her dakika kontrol et
                
            except Exception as e:
                self.log_error(f"Orchestrator error: {e}")
                await asyncio.sleep(300)  # 5 dakika bekle
    
    async def morning_workflow(self):
        """Sabah iş akışı - Günlük planlama ve ilk içerikler"""
        try:
            self.log_info("🌅 Starting morning workflow")
            
            # 1. Günlük content planını oluştur
            await self.plan_daily_content()
            
            # 2. Her domain için sabah makalesi üret
            for domain_name, config in self.domains.items():
                await self.generate_domain_content(domain_name, config, "morning")
                
                # Rate limiting
                await asyncio.sleep(300)  # 5 dakika ara
            
            # 3. AI provider durumlarını kontrol et
            await self.check_ai_providers()
            
            self.log_info("✅ Morning workflow completed")
            
        except Exception as e:
            self.log_error(f"Morning workflow failed: {e}")
    
    async def afternoon_workflow(self):
        """Öğlen iş akışı - İkinci turne içerikler"""
        try:
            self.log_info("☀️ Starting afternoon workflow")
            
            # Her domain için öğlen makalesi
            for domain_name, config in self.domains.items():
                await self.generate_domain_content(domain_name, config, "afternoon")
                await asyncio.sleep(300)
            
            # AI usage statistics kontrol et
            await self.monitor_ai_usage()
            
            self.log_info("✅ Afternoon workflow completed")
            
        except Exception as e:
            self.log_error(f"Afternoon workflow failed: {e}")
    
    async def evening_workflow(self):
        """Akşam iş akışı - Son içerikler ve Pinterest posting"""
        try:
            self.log_info("🌆 Starting evening workflow")
            
            # Son makale turnesu
            for domain_name, config in self.domains.items():
                await self.generate_domain_content(domain_name, config, "evening")
                await asyncio.sleep(300)
            
            # Pinterest posting'leri tetikle
            await self.trigger_pinterest_posting()
            
            self.log_info("✅ Evening workflow completed")
            
        except Exception as e:
            self.log_error(f"Evening workflow failed: {e}")
    
    async def night_workflow(self):
        """Gece iş akışı - Raporlama ve temizlik"""
        try:
            self.log_info("🌙 Starting night workflow")
            
            # Günlük rapor oluştur
            await self.generate_daily_report()
            
            # Yarının content'ini planla
            await self.schedule_tomorrow_content()
            
            # Eski verileri temizle
            await self.cleanup_old_data()
            
            self.log_info("✅ Night workflow completed")
            
        except Exception as e:
            self.log_error(f"Night workflow failed: {e}")
    
    async def plan_daily_content(self):
        """Günlük content planını oluştur"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            for domain_name, config in self.domains.items():
                # Ana konu seç (rotation ile)
                main_topic = await self.select_daily_main_topic(domain_name, config)
                
                # Sub-topics planla
                sub_topics = await self.plan_sub_topics(main_topic, config)
                
                # Article angles seç
                angles = config["content_angles"][:config["daily_target_articles"]]
                
                # Günlük plan oluştur
                daily_plan = {
                    "domain": domain_name,
                    "date": today,
                    "main_topic": main_topic,
                    "target_articles": config["daily_target_articles"],
                    "planned_articles": []
                }
                
                for i, (sub_topic, angle) in enumerate(zip(sub_topics, angles)):
                    article_plan = {
                        "id": f"{domain_name}_{today}_{i+1}",
                        "sub_topic": sub_topic,
                        "angle": angle,
                        "scheduled_time": self.calculate_article_time(i),
                        "status": "planned"
                    }
                    daily_plan["planned_articles"].append(article_plan)
                
                # Redis'e kaydet
                plan_key = f"daily_plan:{domain_name}:{today}"
                self.redis_client.set(plan_key, json.dumps(daily_plan), ex=86400)
                
                self.log_info(f"📋 Daily plan created for {domain_name}: {main_topic}")
            
        except Exception as e:
            self.log_error(f"Failed to plan daily content: {e}")
    
    async def generate_domain_content(self, domain_name: str, config: Dict[str, Any], session: str):
        """Bir domain için içerik üret"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            plan_key = f"daily_plan:{domain_name}:{today}"
            
            plan_data = self.redis_client.get(plan_key)
            if not plan_data:
                self.log_error(f"No daily plan found for {domain_name}")
                return
            
            plan = json.loads(plan_data)
            
            # Session'a göre makale seç
            session_mapping = {"morning": 0, "afternoon": 1, "evening": 2}
            article_index = session_mapping.get(session, 0)
            
            if article_index >= len(plan["planned_articles"]):
                return
            
            article_plan = plan["planned_articles"][article_index]
            
            if article_plan["status"] != "planned":
                return  # Zaten işlenmiş
            
            # AI content generation tetikle
            ai_request = {
                "domain": domain_name,
                "main_topic": plan["main_topic"],
                "sub_topic": article_plan["sub_topic"],
                "angle": article_plan["angle"],
                "niche": config["niche"],
                "title": await self.generate_article_title(
                    plan["main_topic"], 
                    article_plan["sub_topic"], 
                    article_plan["angle"]
                ),
                "keywords": await self.generate_keywords(
                    plan["main_topic"], 
                    article_plan["sub_topic"], 
                    config["niche"]
                ),
                "session": session,
                "priority": "normal"
            }
            
            # AI content queue'ya ekle
            self.redis_client.lpush("ai_content_queue", json.dumps(ai_request))
            
            # Status'u güncelle
            article_plan["status"] = "generating"
            article_plan["started_at"] = datetime.now().isoformat()
            plan["planned_articles"][article_index] = article_plan
            self.redis_client.set(plan_key, json.dumps(plan), ex=86400)
            
            self.log_info(f"🤖 Triggered AI content generation: {domain_name} - {article_plan['sub_topic']}")
            
        except Exception as e:
            self.log_error(f"Failed to generate domain content: {e}")
    
    async def select_daily_main_topic(self, domain_name: str, config: Dict[str, Any]) -> str:
        """Günlük ana konu seç (rotation ile spam'den kaç)"""
        try:
            # Son kullanılan konuları kontrol et
            recent_key = f"recent_main_topics:{domain_name}"
            recent_topics = self.redis_client.lrange(recent_key, 0, -1)
            
            # Rotation listesinden kullanılmamış konu seç
            available_topics = [t for t in config["main_topics_rotation"] if t not in recent_topics]
            
            if not available_topics:
                # Hepsi kullanıldıysa rotation'u sıfırla
                self.redis_client.delete(recent_key)
                available_topics = config["main_topics_rotation"]
            
            # Random seç
            import random
            selected_topic = random.choice(available_topics)
            
            # Kullanılan konulara ekle
            self.redis_client.lpush(recent_key, selected_topic)
            self.redis_client.ltrim(recent_key, 0, len(config["main_topics_rotation"]) - 1)
            
            return selected_topic
            
        except Exception as e:
            self.log_error(f"Failed to select main topic: {e}")
            return config["main_topics_rotation"][0]
    
    async def plan_sub_topics(self, main_topic: str, config: Dict[str, Any]) -> List[str]:
        """Ana konu için alt konular planla"""
        # Bu kısım topic_focused_generator.py'deki main_topics_structure'dan gelecek
        # Şimdilik basit bir mapping
        
        topic_mapping = {
            "investment_strategies": ["portfolio diversification", "risk management", "value investing"],
            "personal_finance": ["budgeting fundamentals", "debt management", "emergency fund"],
            "business_finance": ["startup funding", "cash flow management", "financial planning"],
            "market_analysis": ["stock market trends", "economic indicators", "trading strategies"],
            "esports_professional": ["competitive gaming", "tournament preparation", "team strategies"],
            "gaming_technology": ["gaming hardware", "PC building", "streaming setup"],
            "game_development": ["game design principles", "programming languages", "game engines"],
            "gaming_culture": ["gaming communities", "game reviews", "gaming history"]
        }
        
        return topic_mapping.get(main_topic, ["general topic 1", "general topic 2", "general topic 3"])
    
    async def generate_article_title(self, main_topic: str, sub_topic: str, angle: str) -> str:
        """Article title oluştur"""
        title_templates = {
            "comprehensive_guide": f"The Complete Guide to {sub_topic.title()}: {main_topic.title()} Edition",
            "beginner_tutorial": f"{sub_topic.title()} for Beginners: Step-by-Step Tutorial",
            "expert_analysis": f"Expert Analysis: Advanced {sub_topic.title()} Strategies",
            "problem_solving": f"Solving {sub_topic.title()} Problems: Expert Solutions"
        }
        
        return title_templates.get(angle, f"Professional Guide to {sub_topic.title()}")
    
    async def generate_keywords(self, main_topic: str, sub_topic: str, niche: str) -> List[str]:
        """Keywords oluştur"""
        base_keywords = [main_topic.replace("_", " "), sub_topic.replace("_", " ")]
        
        niche_keywords = {
            "finance": ["financial planning", "investment", "money management", "wealth building"],
            "gaming": ["gaming guide", "esports", "game strategy", "gaming tips"],
            "technology": ["tech guide", "digital solution", "technology trends", "innovation"],
            "health": ["wellness", "health tips", "fitness guide", "nutrition"],
            "business": ["business strategy", "entrepreneurship", "professional growth", "success"]
        }
        
        base_keywords.extend(niche_keywords.get(niche, [])[:3])
        return base_keywords[:6]
    
    def calculate_article_time(self, index: int) -> str:
        """Makale yayın saatini hesapla"""
        base_times = ["09:30", "14:30", "19:30"]
        return base_times[index] if index < len(base_times) else "12:00"
    
    async def check_ai_providers(self):
        """AI provider'ların durumunu kontrol et"""
        try:
            # Bu kısım ai_content_generator'dan status alacak
            providers = ["deepseek", "claude", "groq", "huggingface"]
            
            for provider in providers:
                # Provider status check
                status_key = f"ai_provider_status:{provider}"
                status = self.redis_client.get(status_key) or "unknown"
                
                if status == "error":
                    self.log_error(f"⚠️ AI Provider {provider} has issues")
                    # Email notification tetikle
                    await self.send_notification(f"AI Provider {provider} Error", "urgent")
            
        except Exception as e:
            self.log_error(f"Failed to check AI providers: {e}")
    
    async def monitor_ai_usage(self):
        """AI kullanım istatistiklerini monitor et"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            total_requests = 0
            total_cost = 0
            
            providers = ["deepseek", "claude", "groq", "huggingface"]
            
            for provider in providers:
                usage_key = f"ai_usage:{provider}:{today}"
                words_key = f"ai_words:{provider}:{today}"
                
                requests = int(self.redis_client.get(usage_key) or 0)
                words = int(self.redis_client.get(words_key) or 0)
                
                total_requests += requests
                
                # Rough cost calculation
                if provider == "deepseek":
                    total_cost += words * 0.0014 / 1000
                elif provider == "claude":
                    total_cost += words * 0.25 / 1000000
            
            # Daily limits check
            if total_requests > 50:  # Günlük limit
                self.log_info(f"⚠️ High AI usage today: {total_requests} requests, ~${total_cost:.4f}")
            
            # Stats'i kaydet
            self.redis_client.hset(f"daily_ai_stats:{today}", mapping={
                "total_requests": total_requests,
                "estimated_cost": total_cost,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            self.log_error(f"Failed to monitor AI usage: {e}")
    
    async def trigger_pinterest_posting(self):
        """Pinterest posting'leri tetikle"""
        try:
            # Bugün üretilen makaleleri al
            today = datetime.now().strftime("%Y-%m-%d")
            
            for domain_name in self.domains.keys():
                # Domain'in generated images'larını bul
                images_key = f"domain_images:{domain_name}"
                recent_images = self.redis_client.lrange(images_key, 0, 9)  # Son 10 resim
                
                for image_key in recent_images:
                    image_data = self.redis_client.get(image_key)
                    if image_data:
                        image_info = json.loads(image_data)
                        
                        # Pinterest pin job oluştur
                        pin_job = {
                            "domain": domain_name,
                            "main_topic": image_info["main_topic"],
                            "image_url": image_info["images"][0]["url"] if image_info["images"] else "",
                            "title": f"{image_info['main_topic'].title()} Guide",
                            "description": f"Complete guide to {image_info['main_topic']}. Expert tips and strategies.",
                            "hashtags": [f"#{image_info['main_topic']}", "#guide", "#tips"],
                            "type": "auto_evening_post"
                        }
                        
                        self.redis_client.lpush("pinterest_pin_queue", json.dumps(pin_job))
            
            self.log_info("📌 Pinterest posting triggered")
            
        except Exception as e:
            self.log_error(f"Failed to trigger Pinterest posting: {e}")
    
    async def generate_daily_report(self):
        """Günlük rapor oluştur"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            report = {
                "date": today,
                "domains": {},
                "ai_usage": {},
                "content_generated": 0,
                "images_generated": 0,
                "pinterest_posts": 0
            }
            
            # Domain bazlı istatistikler
            for domain_name in self.domains.keys():
                plan_key = f"daily_plan:{domain_name}:{today}"
                plan_data = self.redis_client.get(plan_key)
                
                if plan_data:
                    plan = json.loads(plan_data)
                    completed = len([a for a in plan["planned_articles"] if a["status"] == "completed"])
                    
                    report["domains"][domain_name] = {
                        "planned_articles": plan["target_articles"],
                        "completed_articles": completed,
                        "main_topic": plan["main_topic"]
                    }
                    
                    report["content_generated"] += completed
            
            # AI usage stats
            ai_stats = self.redis_client.hgetall(f"daily_ai_stats:{today}")
            if ai_stats:
                report["ai_usage"] = ai_stats
            
            # Pinterest stats
            pinterest_count = self.redis_client.llen("pinterest_pin_queue")
            report["pinterest_posts"] = pinterest_count
            
            # Raporu kaydet
            self.redis_client.set(f"daily_report:{today}", json.dumps(report), ex=86400*7)
            
            self.log_info(f"📊 Daily report: {report['content_generated']} articles, ~${report['ai_usage'].get('estimated_cost', 0)}")
            
        except Exception as e:
            self.log_error(f"Failed to generate daily report: {e}")
    
    async def schedule_tomorrow_content(self):
        """Yarının content'ini planla"""
        try:
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            
            for domain_name, config in self.domains.items():
                # Yarın için ana konu seç
                main_topic = await self.select_daily_main_topic(domain_name, config)
                
                # Yarının planını Redis'e kaydet
                schedule_key = f"scheduled_main_topic:{domain_name}:{tomorrow}"
                self.redis_client.set(schedule_key, main_topic, ex=86400*2)
            
            self.log_info(f"📅 Tomorrow's content scheduled for {tomorrow}")
            
        except Exception as e:
            self.log_error(f"Failed to schedule tomorrow content: {e}")
    
    async def cleanup_old_data(self):
        """Eski verileri temizle"""
        try:
            # 7 günden eski planları sil
            cutoff_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            for domain_name in self.domains.keys():
                old_keys = [
                    f"daily_plan:{domain_name}:{cutoff_date}",
                    f"daily_report:{cutoff_date}",
                    f"ai_stats:{cutoff_date}"
                ]
                
                for key in old_keys:
                    self.redis_client.delete(key)
            
            self.log_info("🧹 Old data cleaned up")
            
        except Exception as e:
            self.log_error(f"Failed to cleanup old data: {e}")
    
    async def check_manual_triggers(self):
        """Manuel tetiklemeleri kontrol et"""
        try:
            # Manual content generation request
            manual_request = self.redis_client.rpop("manual_content_trigger")
            
            if manual_request:
                request_data = json.loads(manual_request)
                domain = request_data.get("domain")
                
                if domain in self.domains:
                    self.log_info(f"🎯 Manual content generation triggered for {domain}")
                    await self.generate_domain_content(domain, self.domains[domain], "manual")
            
        except Exception as e:
            self.log_error(f"Failed to check manual triggers: {e}")
    
    async def system_health_check(self):
        """Sistem sağlık kontrolü"""
        try:
            # Redis connection check
            self.redis_client.ping()
            
            # AI content queue check
            queue_length = self.redis_client.llen("ai_content_queue")
            if queue_length > 20:  # Queue çok doluysa
                self.log_error(f"⚠️ AI content queue is full: {queue_length} items")
                await self.send_notification("AI Content Queue Full", "warning")
            
            # Pinterest queue check
            pinterest_queue = self.redis_client.llen("pinterest_pin_queue")
            if pinterest_queue > 50:
                self.log_error(f"⚠️ Pinterest queue is full: {pinterest_queue} items")
            
        except Exception as e:
            self.log_error(f"System health check failed: {e}")
    
    async def send_notification(self, message: str, priority: str):
        """Notification gönder"""
        try:
            notification = {
                "message": message,
                "priority": priority,
                "timestamp": datetime.now().isoformat(),
                "source": "ai_orchestrator"
            }
            
            self.redis_client.lpush("notifications_queue", json.dumps(notification))
            
        except Exception as e:
            self.log_error(f"Failed to send notification: {e}")
    
    def log_info(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] AI-ORCHESTRATOR: {message}")
    
    def log_error(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] AI-ORCHESTRATOR ERROR: {message}")

async def main():
    """AI Content Orchestrator Ana Loop"""
    orchestrator = AIContentOrchestrator()
    await orchestrator.run_orchestrator()

if __name__ == "__main__":
    asyncio.run(main())
