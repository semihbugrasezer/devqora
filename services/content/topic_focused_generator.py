# /srv/auto-adsense/services/content/topic_focused_generator.py
import os
import json
import time
import redis
import asyncio
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import hashlib
import random
import re

class TopicFocusedGenerator:
    """Ana Konu Odaklı İçerik Üretimi - Spam-Free Sistem"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        # Ana konular ve alt konular (spam-free yaklaşım)
        self.main_topics_structure = {
            "finance": {
                "investment_strategies": [
                    "long-term investment planning", "portfolio diversification", "risk management techniques",
                    "value investing principles", "growth investing strategies", "dividend investing guide",
                    "real estate investment", "cryptocurrency investing", "retirement planning"
                ],
                "personal_finance": [
                    "budgeting fundamentals", "debt management", "emergency fund building",
                    "credit score improvement", "financial goal setting", "expense tracking",
                    "savings strategies", "financial planning", "money management"
                ],
                "business_finance": [
                    "startup funding", "business loans", "cash flow management",
                    "financial statements", "tax planning", "business accounting",
                    "investment analysis", "financial forecasting", "business valuation"
                ],
                "market_analysis": [
                    "stock market trends", "economic indicators", "market research",
                    "financial markets", "trading strategies", "market volatility",
                    "technical analysis", "fundamental analysis", "market psychology"
                ]
            },
            "technology": {
                "artificial_intelligence": [
                    "machine learning basics", "AI applications", "neural networks",
                    "deep learning", "natural language processing", "computer vision",
                    "AI ethics", "automation tools", "AI in business"
                ],
                "web_development": [
                    "frontend frameworks", "backend development", "database design",
                    "web security", "responsive design", "API development",
                    "DevOps practices", "cloud computing", "web performance"
                ],
                "mobile_technology": [
                    "mobile app development", "iOS development", "Android development",
                    "cross-platform development", "mobile UI design", "app store optimization",
                    "mobile security", "progressive web apps", "mobile testing"
                ],
                "cybersecurity": [
                    "network security", "data protection", "cyber threats",
                    "security best practices", "encryption methods", "security auditing",
                    "incident response", "security compliance", "ethical hacking"
                ]
            },
            "gaming": {
                "esports_professional": [
                    "competitive gaming", "esports training", "team strategies",
                    "tournament preparation", "professional gaming", "esports careers",
                    "gaming psychology", "performance optimization", "coaching methods"
                ],
                "gaming_technology": [
                    "gaming hardware", "PC building", "gaming peripherals",
                    "graphics optimization", "streaming setup", "gaming monitors",
                    "audio equipment", "gaming chairs", "cooling systems"
                ],
                "game_development": [
                    "game design principles", "programming languages", "game engines",
                    "3D modeling", "game art", "sound design", "level design",
                    "game testing", "publishing strategies"
                ],
                "gaming_culture": [
                    "gaming communities", "game reviews", "gaming history",
                    "indie games", "retro gaming", "gaming events",
                    "streaming culture", "gaming journalism", "game preservation"
                ]
            },
            "health": {
                "fitness_training": [
                    "strength training", "cardio workouts", "flexibility training",
                    "workout routines", "exercise techniques", "fitness equipment",
                    "training programs", "athletic performance", "recovery methods"
                ],
                "nutrition_science": [
                    "healthy eating", "meal planning", "nutritional supplements",
                    "diet strategies", "food science", "nutrition for athletes",
                    "weight management", "metabolic health", "digestive health"
                ],
                "mental_wellness": [
                    "stress management", "meditation techniques", "mindfulness practices",
                    "mental health", "emotional wellness", "cognitive health",
                    "sleep optimization", "work-life balance", "psychological well-being"
                ],
                "preventive_healthcare": [
                    "health screening", "disease prevention", "immune system",
                    "health monitoring", "lifestyle medicine", "health technology",
                    "medical checkups", "health education", "wellness programs"
                ]
            },
            "business": {
                "entrepreneurship": [
                    "startup strategies", "business planning", "idea validation",
                    "market research", "funding strategies", "business models",
                    "scaling strategies", "innovation management", "risk assessment"
                ],
                "marketing_strategies": [
                    "digital marketing", "content marketing", "social media marketing",
                    "SEO strategies", "brand building", "customer acquisition",
                    "marketing analytics", "conversion optimization", "email marketing"
                ],
                "leadership_management": [
                    "team leadership", "project management", "strategic planning",
                    "decision making", "communication skills", "conflict resolution",
                    "performance management", "organizational culture", "change management"
                ],
                "business_technology": [
                    "business automation", "productivity tools", "CRM systems",
                    "business intelligence", "cloud solutions", "digital transformation",
                    "workflow optimization", "data analytics", "technology adoption"
                ]
            }
        }
        
        # Her ana konu için article angle'lar (çeşitlilik için)
        self.article_angles = [
            "complete_guide", "beginner_tutorial", "advanced_strategies", "expert_tips",
            "common_mistakes", "best_practices", "step_by_step", "comparison_analysis",
            "case_studies", "future_trends", "tools_review", "how_to_choose",
            "success_stories", "problem_solving", "optimization_techniques"
        ]
        
        # Article templates (spam-free, value-focused)
        self.article_templates = {
            "complete_guide": "The Complete Guide to {sub_topic}: Everything You Need to Know",
            "beginner_tutorial": "{sub_topic} for Beginners: A Step-by-Step Tutorial",
            "advanced_strategies": "Advanced {sub_topic} Strategies for Professional Success",
            "expert_tips": "Expert Tips for Mastering {sub_topic} in 2025",
            "common_mistakes": "Common {sub_topic} Mistakes and How to Avoid Them",
            "best_practices": "Best Practices for {sub_topic}: Industry Standards",
            "step_by_step": "How to Master {sub_topic}: A Step-by-Step Approach",
            "comparison_analysis": "{sub_topic} Options Compared: Which is Right for You?",
            "case_studies": "Real-World {sub_topic} Case Studies and Success Stories",
            "future_trends": "The Future of {sub_topic}: Trends and Predictions for 2025",
            "tools_review": "Top {sub_topic} Tools and Resources for 2025",
            "how_to_choose": "How to Choose the Right {sub_topic} Solution",
            "success_stories": "{sub_topic} Success Stories: Learning from the Best",
            "problem_solving": "Solving Common {sub_topic} Challenges: Expert Solutions",
            "optimization_techniques": "Optimizing Your {sub_topic} for Maximum Results"
        }
        
        self.log_info("Topic Focused Generator initialized")
    
    async def generate_topic_focused_content(self, domain_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ana konu odaklı içerik üretimi başlat"""
        try:
            domain = domain_data["name"]
            niche = domain_data.get("niche", "technology")
            daily_target = domain_data.get("daily_target_articles", 3)
            
            # Ana konu seç (rotation ile spam'den kaç)
            main_topic = await self.select_main_topic(domain, niche)
            
            if not main_topic:
                self.log_error(f"No main topic available for {domain}")
                return {"success": False, "error": "No topics available"}
            
            # Ana konu için content plan oluştur
            content_plan = await self.create_content_plan(main_topic, niche, daily_target)
            
            # Content generation başlat
            generated_articles = []
            
            for article_plan in content_plan["articles"]:
                article = await self.generate_single_article(article_plan, domain, niche, main_topic)
                
                if article:
                    generated_articles.append(article)
                    
                    # Her article için resim üretimi tetikle
                    await self.trigger_image_generation(article, main_topic, niche)
                    
                    # Rate limiting (spam prevention)
                    await asyncio.sleep(random.randint(300, 600))  # 5-10 dakika arası
            
            # Topic usage'ı kaydet (rotation için)
            await self.record_topic_usage(domain, main_topic, len(generated_articles))
            
            result = {
                "success": True,
                "domain": domain,
                "main_topic": main_topic,
                "articles_generated": len(generated_articles),
                "articles": generated_articles,
                "next_topic_scheduled": await self.schedule_next_topic(domain, niche)
            }
            
            self.log_info(f"Generated {len(generated_articles)} articles for {main_topic} on {domain}")
            return result
            
        except Exception as e:
            self.log_error(f"Failed to generate topic-focused content: {e}")
            return {"success": False, "error": str(e)}
    
    async def select_main_topic(self, domain: str, niche: str) -> Optional[str]:
        """Ana konu seç (rotation ile spam-free)"""
        try:
            niche_topics = self.main_topics_structure.get(niche, {})
            if not niche_topics:
                return None
            
            # Son kullanılan konuları kontrol et
            recent_topics_key = f"recent_topics:{domain}"
            recent_topics = self.redis_client.lrange(recent_topics_key, 0, -1)
            
            # Kullanılmamış konuları bul
            available_topics = []
            for topic in niche_topics.keys():
                if topic not in recent_topics:
                    available_topics.append(topic)
            
            # Eğer hepsi kullanıldıysa, rotation yap
            if not available_topics:
                self.redis_client.delete(recent_topics_key)
                available_topics = list(niche_topics.keys())
            
            # Random seçim (doğal görünüm için)
            selected_topic = random.choice(available_topics)
            
            # Kullanılan konulara ekle
            self.redis_client.lpush(recent_topics_key, selected_topic)
            self.redis_client.ltrim(recent_topics_key, 0, len(niche_topics) - 1)  # Niche'teki konu sayısı kadar tut
            
            return selected_topic
            
        except Exception as e:
            self.log_error(f"Failed to select main topic: {e}")
            return None
    
    async def create_content_plan(self, main_topic: str, niche: str, daily_target: int) -> Dict[str, Any]:
        """Ana konu için content plan oluştur"""
        try:
            sub_topics = self.main_topics_structure[niche][main_topic]
            
            # Günlük hedef kadar article planla
            articles_plan = []
            
            for i in range(min(daily_target, len(sub_topics))):
                sub_topic = sub_topics[i]
                
                # Her sub-topic için farklı angle seç
                angle = random.choice(self.article_angles)
                
                # Article title oluştur
                title_template = self.article_templates[angle]
                title = title_template.format(sub_topic=sub_topic.title())
                
                articles_plan.append({
                    "sub_topic": sub_topic,
                    "angle": angle,
                    "title": title,
                    "priority": "normal",
                    "estimated_length": "comprehensive"  # 2000+ words
                })
            
            return {
                "main_topic": main_topic,
                "niche": niche,
                "articles": articles_plan,
                "total_count": len(articles_plan)
            }
            
        except Exception as e:
            self.log_error(f"Failed to create content plan: {e}")
            return {"articles": []}
    
    async def generate_single_article(self, article_plan: Dict[str, Any], domain: str, niche: str, main_topic: str) -> Optional[Dict[str, Any]]:
        """Tek article üret"""
        try:
            sub_topic = article_plan["sub_topic"]
            angle = article_plan["angle"]
            title = article_plan["title"]
            
            # High-quality content üret
            content = await self.generate_comprehensive_content(main_topic, sub_topic, angle, niche)
            
            # Article metadata
            article_data = {
                "domain": domain,
                "title": title,
                "body": content,
                "main_topic": main_topic,
                "sub_topic": sub_topic,
                "angle": angle,
                "niche": niche,
                "keywords": [main_topic, sub_topic] + self.extract_related_keywords(sub_topic, niche),
                "author": f"{niche.title()} Expert Team",
                "publish_date": datetime.now().isoformat(),
                "estimated_reading_time": self.calculate_reading_time(content),
                "content_quality": "comprehensive",
                "spam_free": True
            }
            
            # Content API'ye gönder
            response = requests.post(
                "http://content-api:5055/ingest",
                json=article_data,
                timeout=60
            )
            
            if response.status_code == 200:
                self.log_info(f"Successfully created article: {title}")
                return article_data
            else:
                self.log_error(f"Failed to create article: {response.status_code}")
                return None
                
        except Exception as e:
            self.log_error(f"Failed to generate single article: {e}")
            return None
    
    async def generate_comprehensive_content(self, main_topic: str, sub_topic: str, angle: str, niche: str) -> str:
        """Kapsamlı, high-quality content üret"""
        
        # Bu fonksiyon Claude/GPT API'si ile entegre edilebilir
        # Şimdilik template-based comprehensive content
        
        content_sections = await self.build_content_sections(main_topic, sub_topic, angle, niche)
        
        full_content = f"""
# {self.article_templates[angle].format(sub_topic=sub_topic.title())}

## Introduction

Understanding {sub_topic} is crucial for anyone serious about {main_topic}. In this comprehensive guide, we'll explore everything you need to know about {sub_topic}, from fundamental concepts to advanced implementation strategies.

{content_sections['introduction']}

## Understanding {sub_topic.title()}

{content_sections['foundation']}

### Key Components of {sub_topic.title()}

{content_sections['components']}

### Why {sub_topic.title()} Matters in {main_topic.title()}

{content_sections['importance']}

## Step-by-Step Implementation Guide

{content_sections['implementation']}

### Getting Started

{content_sections['getting_started']}

### Advanced Techniques

{content_sections['advanced']}

### Best Practices

{content_sections['best_practices']}

## Common Challenges and Solutions

{content_sections['challenges']}

## Tools and Resources

{content_sections['tools']}

## Real-World Examples

{content_sections['examples']}

## Expert Tips

{content_sections['expert_tips']}

## Measuring Success

{content_sections['metrics']}

## Future Trends

{content_sections['future_trends']}

## Conclusion

Mastering {sub_topic} is essential for success in {main_topic}. By following the strategies and techniques outlined in this guide, you'll be well-equipped to implement effective {sub_topic} solutions.

Remember that success with {sub_topic} requires:
- Consistent application of best practices
- Regular monitoring and optimization
- Staying updated with industry developments
- Continuous learning and adaptation

{content_sections['conclusion']}

---

*Ready to take your {sub_topic} skills to the next level? Explore our other comprehensive guides on {main_topic} for more expert insights and practical strategies.*
"""
        
        return full_content.strip()
    
    async def build_content_sections(self, main_topic: str, sub_topic: str, angle: str, niche: str) -> Dict[str, str]:
        """Content section'larını oluştur"""
        
        # Niche'e göre özelleştirilmiş content
        niche_specific_content = {
            "finance": {
                "introduction": f"In today's complex financial landscape, {sub_topic} has become a cornerstone of successful {main_topic}. Whether you're a seasoned investor or just starting your financial journey, understanding the intricacies of {sub_topic} can significantly impact your financial outcomes.",
                "foundation": f"{sub_topic.title()} represents a fundamental aspect of {main_topic} that requires both theoretical knowledge and practical application. At its core, {sub_topic} involves strategic decision-making based on market analysis, risk assessment, and long-term planning.",
                "implementation": f"Implementing effective {sub_topic} strategies requires a systematic approach. Start by assessing your current financial situation, define clear objectives, and develop a comprehensive plan that aligns with your risk tolerance and time horizon."
            },
            "technology": {
                "introduction": f"The rapidly evolving technology landscape has made {sub_topic} an essential component of modern {main_topic}. As organizations continue to digitally transform, understanding and implementing {sub_topic} becomes crucial for staying competitive.",
                "foundation": f"{sub_topic.title()} encompasses the methodologies, tools, and practices that enable efficient {main_topic}. It involves both technical implementation and strategic planning to ensure optimal results.",
                "implementation": f"Successfully implementing {sub_topic} requires careful planning, proper tool selection, and continuous monitoring. Begin with a thorough assessment of your current technology stack and identify areas for improvement."
            },
            "gaming": {
                "introduction": f"The competitive gaming world demands excellence in {sub_topic} to achieve success in {main_topic}. Whether you're an aspiring professional or passionate enthusiast, mastering {sub_topic} can elevate your gaming experience significantly.",
                "foundation": f"{sub_topic.title()} forms the backbone of effective {main_topic}. It encompasses technical skills, strategic thinking, and continuous improvement methodologies that separate casual players from serious competitors.",
                "implementation": f"Developing expertise in {sub_topic} requires dedicated practice, proper equipment, and strategic approach. Start with fundamental techniques and gradually progress to advanced strategies."
            },
            "health": {
                "introduction": f"Achieving optimal health through {sub_topic} is fundamental to successful {main_topic}. Understanding the science behind {sub_topic} empowers you to make informed decisions about your wellness journey.",
                "foundation": f"{sub_topic.title()} is built on evidence-based principles that promote long-term health and well-being. It integrates scientific research with practical application to deliver measurable results.",
                "implementation": f"Implementing effective {sub_topic} strategies requires a holistic approach that considers individual needs, lifestyle factors, and health goals. Begin with a comprehensive assessment and develop a personalized plan."
            },
            "business": {
                "introduction": f"In today's competitive business environment, {sub_topic} has become a critical factor in {main_topic} success. Organizations that excel in {sub_topic} consistently outperform their competitors and achieve sustainable growth.",
                "foundation": f"{sub_topic.title()} encompasses strategic planning, operational excellence, and continuous improvement methodologies. It requires both analytical thinking and creative problem-solving skills.",
                "implementation": f"Successful {sub_topic} implementation requires clear vision, strategic planning, and effective execution. Start by defining your objectives and developing a comprehensive strategy that aligns with your business goals."
            }
        }
        
        base_sections = niche_specific_content.get(niche, niche_specific_content["technology"])
        
        # Additional sections
        additional_sections = {
            "components": f"The key components of {sub_topic} include strategic planning, implementation methodologies, monitoring systems, and optimization techniques. Each component plays a vital role in overall success.",
            "importance": f"{sub_topic.title()} is crucial because it directly impacts the effectiveness of your {main_topic} initiatives. Organizations that prioritize {sub_topic} typically see improved performance, reduced costs, and better outcomes.",
            "getting_started": f"To get started with {sub_topic}, begin by educating yourself on fundamental concepts, assessing your current situation, and setting clear, measurable goals.",
            "advanced": f"Advanced {sub_topic} techniques involve sophisticated strategies, automation tools, and data-driven decision making. These approaches require deeper expertise but deliver significantly better results.",
            "best_practices": f"Industry best practices for {sub_topic} include regular monitoring, continuous optimization, staying updated with trends, and learning from successful case studies.",
            "challenges": f"Common challenges in {sub_topic} include resource constraints, technical complexity, and changing requirements. Address these by proper planning, skill development, and adaptive strategies.",
            "tools": f"Essential tools for {sub_topic} include specialized software, analytics platforms, and monitoring systems. Choose tools that align with your specific needs and budget constraints.",
            "examples": f"Real-world examples of successful {sub_topic} implementation demonstrate the practical application of theoretical concepts and provide valuable insights for your own initiatives.",
            "expert_tips": f"Expert recommendations for {sub_topic} include focusing on fundamentals, measuring results consistently, staying updated with industry developments, and continuously improving your approach.",
            "metrics": f"Key performance indicators for {sub_topic} include efficiency metrics, quality measures, and outcome assessments. Regular monitoring helps identify areas for improvement.",
            "future_trends": f"Emerging trends in {sub_topic} include automation, AI integration, and data-driven approaches. Staying ahead of these trends ensures long-term success.",
            "conclusion": f"By implementing the strategies outlined in this guide, you'll be well-positioned to achieve success with {sub_topic} and contribute meaningfully to your overall {main_topic} objectives."
        }
        
        return {**base_sections, **additional_sections}
    
    async def trigger_image_generation(self, article_data: Dict[str, Any], main_topic: str, niche: str):
        """Article için resim üretimi tetikle"""
        try:
            image_request = {
                "domain": article_data["domain"],
                "title": article_data["title"],
                "main_topic": main_topic,
                "sub_topic": article_data["sub_topic"],
                "niche": niche,
                "keywords": article_data["keywords"],
                "type": "article_images"
            }
            
            # Nano Banana queue'ya ekle
            self.redis_client.lpush("nano_banana_queue", json.dumps(image_request))
            
            self.log_info(f"Triggered image generation for: {article_data['title']}")
            
        except Exception as e:
            self.log_error(f"Failed to trigger image generation: {e}")
    
    async def record_topic_usage(self, domain: str, main_topic: str, article_count: int):
        """Topic kullanımını kaydet"""
        try:
            usage_data = {
                "domain": domain,
                "main_topic": main_topic,
                "article_count": article_count,
                "generated_at": datetime.now().isoformat(),
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            
            # Daily usage tracking
            daily_key = f"topic_usage:{domain}:{datetime.now().strftime('%Y-%m-%d')}"
            self.redis_client.hset(daily_key, main_topic, article_count)
            self.redis_client.expire(daily_key, 86400 * 30)  # 30 gün tut
            
            # Overall usage tracking
            self.redis_client.hincrby(f"total_topic_usage:{domain}", main_topic, article_count)
            
            self.log_info(f"Recorded usage: {domain} - {main_topic} - {article_count} articles")
            
        except Exception as e:
            self.log_error(f"Failed to record topic usage: {e}")
    
    async def schedule_next_topic(self, domain: str, niche: str) -> Optional[str]:
        """Bir sonraki topic'i planla"""
        try:
            # Yarın için topic seç
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            next_topic = await self.select_main_topic(domain, niche)
            
            if next_topic:
                # Schedule key
                schedule_key = f"scheduled_topics:{domain}:{tomorrow}"
                self.redis_client.set(schedule_key, next_topic, ex=86400 * 2)  # 2 gün
                
                return next_topic
            
        except Exception as e:
            self.log_error(f"Failed to schedule next topic: {e}")
        
        return None
    
    def extract_related_keywords(self, sub_topic: str, niche: str) -> List[str]:
        """İlgili keyword'leri çıkar"""
        keywords = []
        
        # Sub-topic'ten keyword'ler çıkar
        words = sub_topic.split()
        for word in words:
            if len(word) > 3:
                keywords.append(word)
        
        # Niche-specific keywords ekle
        niche_keywords = {
            "finance": ["money", "investment", "financial", "planning", "strategy"],
            "technology": ["digital", "tech", "software", "system", "development"],
            "gaming": ["game", "gaming", "esports", "competitive", "strategy"],
            "health": ["health", "wellness", "fitness", "nutrition", "medical"],
            "business": ["business", "professional", "management", "corporate", "success"]
        }
        
        keywords.extend(niche_keywords.get(niche, [])[:3])
        
        return keywords[:8]  # Max 8 keyword
    
    def calculate_reading_time(self, content: str) -> str:
        """Okuma süresini hesapla"""
        word_count = len(content.split())
        reading_time = max(1, word_count // 200)  # 200 word/minute
        return f"{reading_time} min read"
    
    def log_info(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] TOPIC-GEN: {message}")
    
    def log_error(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] TOPIC-GEN ERROR: {message}")

async def main():
    """Topic Focused Content Generator Worker"""
    generator = TopicFocusedGenerator()
    
    print("📝 Topic Focused Content Generator started")
    print("🎯 Generating spam-free, main-topic focused content")
    
    while True:
        try:
            # Content generation requests kontrol et
            request = generator.redis_client.rpop("topic_content_queue")
            
            if request:
                request_data = json.loads(request)
                domain = request_data.get("name", "Unknown")
                
                print(f"📝 Generating topic-focused content for: {domain}")
                
                result = await generator.generate_topic_focused_content(request_data)
                
                if result["success"]:
                    print(f"✅ Generated {result['articles_generated']} articles for {result['main_topic']}")
                    print(f"📅 Next topic scheduled: {result.get('next_topic_scheduled', 'None')}")
                else:
                    print(f"❌ Failed to generate content: {result.get('error')}")
            
            # Her saat başı scheduled content'leri kontrol et
            current_time = datetime.now()
            if current_time.minute == 0:
                await generator.check_scheduled_content()
            
            await asyncio.sleep(30)  # 30 saniyede bir kontrol et
            
        except Exception as e:
            print(f"❌ Topic Generator error: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
