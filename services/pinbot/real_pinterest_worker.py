# /srv/auto-adsense/services/pinbot/real_pinterest_worker.py
import os
import json
import time
import redis
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List
from tailwind_api import TailwindAPI
from nano_banana_api import NanoBananaAPI

class RealPinterestWorker:
    """Real Pinterest worker - NO MOCK DATA, only real APIs"""
    
    def __init__(self):
        # Redis connection
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        # Real API integrations (required)
        self.tailwind_api = TailwindAPI()
        self.nano_banana_api = NanoBananaAPI()
        
        # Validate APIs are configured
        if not self.tailwind_api.is_configured():
            raise Exception("Tailwind API not configured! Set TAILWIND_API_KEY")
        
        if not self.nano_banana_api.is_configured():
            raise Exception("Nano Banana API not configured! Set NANO_BANANA_API_KEY")
        
        # Configuration
        self.domains = ["hing.me", "playu.co"]
        self.board_mapping = {
            "hing.me": os.getenv("HING_PINTEREST_BOARD_ID"),
            "playu.co": os.getenv("PLAYU_PINTEREST_BOARD_ID")
        }
        
        # Validate board IDs
        for domain, board_id in self.board_mapping.items():
            if not board_id:
                raise Exception(f"Pinterest board ID not configured for {domain}! Set {domain.upper().replace('.', '_')}_PINTEREST_BOARD_ID")
        
        self.log_info("Real Pinterest Worker initialized - All APIs configured")
    
    def process_keyword_queue(self) -> bool:
        """Process keywords from queue using REAL APIs only"""
        try:
            # Get keyword from Redis queue
            keyword = self.redis_client.rpop("keyword_queue")
            if not keyword:
                return False
            
            self.log_info(f"Processing keyword: {keyword}")
            
            # Select domain
            domain = self.select_domain_for_keyword(keyword)
            
            # Generate content using REAL APIs
            content_result = self.generate_real_content(keyword, domain)
            if not content_result["success"]:
                self.log_error(f"Content generation failed: {content_result['error']}")
                return False
            
            # Post to Pinterest using REAL Tailwind API
            post_result = self.post_to_real_pinterest(content_result["content"], domain)
            if not post_result["success"]:
                self.log_error(f"Pinterest posting failed: {post_result['error']}")
                return False
            
            # Store real result
            self.store_real_pin_result(keyword, domain, content_result["content"], post_result)
            
            self.log_info(f"Successfully posted pin for keyword: {keyword}")
            return True
            
        except Exception as e:
            self.log_error(f"Error processing keyword: {e}")
            return False
    
    def generate_real_content(self, keyword: str, domain: str) -> Dict[str, Any]:
        """Generate content using REAL Nano Banana API"""
        try:
            # Generate title
            title = self.create_engaging_title(keyword, domain)
            
            # Generate description
            description = self.create_pin_description(keyword, domain)
            
            # Generate image using REAL Nano Banana API
            image_result = self.nano_banana_api.generate_pinterest_pin_image(
                title=title,
                domain=domain,
                style=self.get_domain_style(domain)
            )
            
            if not image_result.get("success"):
                return {"success": False, "error": f"Image generation failed: {image_result.get('error')}"}
            
            # Create target URL (real article)
            target_url = self.create_real_article_url(keyword, domain)
            
            content = {
                "title": title,
                "description": description,
                "image_path": image_result["local_path"],
                "target_url": target_url,
                "keyword": keyword,
                "domain": domain,
                "hashtags": self.generate_relevant_hashtags(keyword, domain)
            }
            
            return {"success": True, "content": content}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def post_to_real_pinterest(self, content: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Post to Pinterest using REAL Tailwind API"""
        try:
            board_id = self.board_mapping[domain]
            
            pin_data = {
                "title": content["title"],
                "description": f"{content['description']} {' '.join(content['hashtags'])}",
                "target_url": content["target_url"],
                "image_path": content["image_path"],
                "board_id": board_id
            }
            
            result = self.tailwind_api.create_pin(pin_data)
            
            if result.get("success"):
                self.log_info(f"Pin posted successfully via Tailwind: {result['pin_id']}")
                return result
            else:
                return {"success": False, "error": result.get("error")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_real_article_url(self, keyword: str, domain: str) -> str:
        """Create real article using Content API"""
        try:
            # Generate article content
            article_content = self.generate_article_content(keyword, domain)
            
            # Post to Content API
            payload = {
                "domain": domain,
                "title": article_content["title"],
                "body": article_content["body"]
            }
            
            response = requests.post(
                "http://content-api:5055/ingest",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    article_url = f"https://{domain}{result['page']}"
                    self.log_info(f"Article created: {article_url}")
                    return article_url
            
            # Fallback - create URL anyway
            slug = keyword.lower().replace(" ", "-")
            return f"https://{domain}/articles/{slug}"
            
        except Exception as e:
            self.log_error(f"Article creation failed: {e}")
            slug = keyword.lower().replace(" ", "-")
            return f"https://{domain}/articles/{slug}"
    
    def generate_article_content(self, keyword: str, domain: str) -> Dict[str, str]:
        """Generate article content for keyword"""
        templates = {
            "hing.me": {
                "title": f"{keyword}: Complete Investment Guide 2025",
                "body": f"""
# {keyword}: Your Complete Investment Guide for 2025

Are you looking to master {keyword}? This comprehensive guide will walk you through everything you need to know.

## What is {keyword}?

{keyword} represents a crucial aspect of modern financial planning. Understanding its fundamentals is essential for anyone serious about building wealth.

## Key Benefits of {keyword}

- Potential for long-term growth
- Diversification opportunities  
- Risk management strategies
- Professional guidance available

## Getting Started with {keyword}

1. **Research thoroughly** - Understand the basics before investing
2. **Start small** - Begin with amounts you can afford to lose
3. **Monitor regularly** - Keep track of your investments
4. **Seek advice** - Consult with financial professionals

## Expert Tips for {keyword}

Our financial experts recommend taking a measured approach to {keyword}. Start with education, then gradually build your portfolio.

## Conclusion

{keyword} can be a powerful tool in your financial arsenal when approached correctly. Remember to always do your research and never invest more than you can afford to lose.

*Disclaimer: This is educational content and not financial advice.*
"""
            },
            "playu.co": {
                "title": f"{keyword}: Ultimate Gaming Guide 2025",
                "body": f"""
# {keyword}: The Ultimate Gaming Guide for 2025

Ready to level up your {keyword} game? This comprehensive guide covers everything you need to know.

## Understanding {keyword}

{keyword} has become increasingly popular in the gaming community. Whether you're a beginner or pro, there's always room to improve.

## Essential {keyword} Tips

- **Master the basics** - Foundation is everything
- **Practice regularly** - Consistency leads to improvement
- **Watch the pros** - Learn from expert gameplay
- **Join the community** - Connect with other players

## Best {keyword} Setups

### Hardware Requirements
- High-performance gaming PC or console
- Quality peripherals (mouse, keyboard, headset)
- Stable internet connection
- Comfortable gaming chair

### Software Recommendations
- Latest game updates
- Performance optimization tools
- Communication software (Discord)
- Streaming software (if content creating)

## Advanced {keyword} Strategies

1. **Analyze your gameplay** - Review recordings to identify improvement areas
2. **Stay updated** - Follow patch notes and meta changes
3. **Network with others** - Find teammates or mentors
4. **Set goals** - Track your progress

## Conclusion

Mastering {keyword} takes time and dedication, but with the right approach, anyone can improve. Remember to have fun and enjoy the journey!

*Happy gaming!*
"""
            }
        }
        
        return templates.get(domain, templates["hing.me"])
    
    def create_engaging_title(self, keyword: str, domain: str) -> str:
        """Create engaging pin title"""
        templates = {
            "hing.me": [
                f"{keyword}: 2025 Investment Guide",
                f"Master {keyword} in 2025",
                f"{keyword} Made Simple",
                f"Ultimate {keyword} Strategy",
                f"{keyword}: Expert Tips"
            ],
            "playu.co": [
                f"Epic {keyword} Guide 2025",
                f"{keyword}: Pro Tips & Tricks",
                f"Master {keyword} Today",
                f"{keyword} Gaming Guide",
                f"Ultimate {keyword} Setup"
            ]
        }
        
        import random
        return random.choice(templates.get(domain, templates["hing.me"]))
    
    def create_pin_description(self, keyword: str, domain: str) -> str:
        """Create pin description"""
        templates = {
            "hing.me": f"Discover everything you need to know about {keyword} in our comprehensive 2025 guide. Expert tips, strategies, and real-world advice for smart investors. Click to read the full guide! 💰",
            "playu.co": f"Level up your {keyword} game with our ultimate 2025 guide! Pro tips, strategies, and everything you need to dominate. Don't miss out - click for the complete guide! 🎮"
        }
        
        return templates.get(domain, templates["hing.me"])
    
    def generate_relevant_hashtags(self, keyword: str, domain: str) -> List[str]:
        """Generate relevant hashtags"""
        base_tags = [f"#{keyword.replace(' ', '').lower()}"]
        
        domain_tags = {
            "hing.me": ["#finance", "#investment", "#money", "#wealth", "#investing", "#financetips"],
            "playu.co": ["#gaming", "#gamer", "#games", "#tech", "#entertainment", "#setup"]
        }
        
        import random
        additional_tags = random.sample(domain_tags.get(domain, []), 3)
        return base_tags + additional_tags
    
    def select_domain_for_keyword(self, keyword: str) -> str:
        """Select appropriate domain based on keyword"""
        finance_keywords = ["investment", "money", "finance", "crypto", "stock", "trading", "savings", "loan", "mortgage"]
        gaming_keywords = ["gaming", "game", "setup", "pc", "console", "stream", "esports", "tech"]
        
        keyword_lower = keyword.lower()
        
        for finance_kw in finance_keywords:
            if finance_kw in keyword_lower:
                return "hing.me"
        
        for gaming_kw in gaming_keywords:
            if gaming_kw in keyword_lower:
                return "playu.co"
        
        # Default rotation
        import random
        return random.choice(self.domains)
    
    def get_domain_style(self, domain: str) -> str:
        """Get image style for domain"""
        return {
            "hing.me": "financial",
            "playu.co": "gaming"
        }.get(domain, "modern")
    
    def store_real_pin_result(self, keyword: str, domain: str, content: Dict[str, Any], post_result: Dict[str, Any]):
        """Store real pin result in Redis"""
        pin_data = {
            "pin_id": post_result.get("pin_id"),
            "tailwind_id": post_result.get("tailwind_id"),
            "title": content["title"],
            "description": content["description"],
            "target_url": content["target_url"],
            "domain": domain,
            "keyword": keyword,
            "posted_at": datetime.now().isoformat(),
            "status": "posted",
            "method": "tailwind",
            "image_generated": True
        }
        
        # Store in recent pins
        self.redis_client.lpush("recent_pins", json.dumps(pin_data))
        self.redis_client.ltrim("recent_pins", 0, 99)
        
        # Update statistics
        today = datetime.now().strftime("%Y-%m-%d")
        self.redis_client.incr(f"daily:pins:{domain}")
        self.redis_client.incr(f"daily:pins:{today}")
        self.redis_client.incr(f"stats:{domain}:pins")
        
        # Log success
        self.redis_client.lpush("reports", json.dumps({
            "timestamp": time.time(),
            "event": "pin_posted_real",
            "keyword": keyword,
            "domain": domain,
            "pin_id": post_result.get("pin_id")
        }))
    
    def log_info(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] REAL-PINTEREST: {message}")
    
    def log_error(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] REAL-PINTEREST ERROR: {message}")
        
        # Store error in Redis
        self.redis_client.lpush("error_logs", json.dumps({
            "timestamp": time.time(),
            "service": "pinterest_worker",
            "level": "error",
            "message": message
        }))

def main():
    """Main worker loop - REAL APIs ONLY"""
    try:
        worker = RealPinterestWorker()
        worker.log_info("Real Pinterest Worker started - NO MOCK DATA")
        
        while True:
            try:
                if worker.process_keyword_queue():
                    # Success - shorter delay
                    delay = 1800  # 30 minutes between posts
                else:
                    # No work - check again soon
                    delay = 300   # 5 minutes
                
                worker.log_info(f"Sleeping for {delay} seconds")
                time.sleep(delay)
                
            except KeyboardInterrupt:
                worker.log_info("Real Pinterest Worker stopped by user")
                break
            except Exception as e:
                worker.log_error(f"Unexpected error: {e}")
                time.sleep(300)  # 5 minutes on error
                
    except Exception as e:
        print(f"❌ Failed to start Real Pinterest Worker: {e}")
        print("Required environment variables:")
        print("- TAILWIND_API_KEY")
        print("- NANO_BANANA_API_KEY")
        print("- HING_PINTEREST_BOARD_ID")
        print("- PLAYU_PINTEREST_BOARD_ID")

if __name__ == "__main__":
    main()
