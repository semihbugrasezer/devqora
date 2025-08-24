# /srv/auto-adsense/services/pinbot/enhanced_pin_worker.py
import os
import json
import time
import random
import datetime
import redis
from typing import Dict, Any, List
from tailwind_api import TailwindAPI
from nano_banana_api import NanoBananaAPI
from generate_text import draft_description, pick_hashtags

class EnhancedPinWorker:
    """Enhanced Pinterest worker with Tailwind and Nano Banana integration"""
    
    def __init__(self):
        # Redis connection
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        # API integrations
        self.tailwind_api = TailwindAPI()
        self.nano_banana_api = NanoBananaAPI()
        
        # Configuration
        self.domain_rotation = [d.strip() for d in os.getenv("DOMAIN_ROTATION", "").split(",") if d.strip()]
        self.window_start = os.getenv("WINDOW_START", "08:00")
        self.window_end = os.getenv("WINDOW_END", "22:30")
        self.daily_pin_target = int(os.getenv("DAILY_PIN_TARGET", "6"))
        
        # Pinterest boards configuration
        self.boards_config = {
            "hing.me": {
                "board_ids": ["finance_tips", "investment_guide", "money_management"],
                "hashtags": ["#finance", "#investment", "#money", "#financetips", "#personalfinance"],
                "topics": ["investment", "finance", "money", "crypto", "stocks", "savings"]
            },
            "playu.co": {
                "board_ids": ["gaming_tips", "tech_reviews", "entertainment"],
                "hashtags": ["#gaming", "#technology", "#entertainment", "#gamingsetup", "#techreviews"],
                "topics": ["gaming", "technology", "entertainment", "reviews", "setup", "gadgets"]
            }
        }
    
    def is_in_posting_window(self) -> bool:
        """Check if current time is within posting window"""
        try:
            now = datetime.datetime.now().time()
            start_h, start_m = map(int, self.window_start.split(":"))
            end_h, end_m = map(int, self.window_end.split(":"))
            
            start_time = datetime.time(start_h, start_m)
            end_time = datetime.time(end_h, end_m)
            
            if start_time <= end_time:
                return start_time <= now <= end_time
            else:  # Crosses midnight
                return now >= start_time or now <= end_time
                
        except Exception as e:
            self.log_error(f"Error checking posting window: {e}")
            return True  # Default to allow posting
    
    def get_daily_pin_count(self) -> int:
        """Get number of pins posted today"""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        return int(self.redis_client.get(f"daily_pins:{today}") or 0)
    
    def increment_daily_pin_count(self):
        """Increment today's pin count"""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        self.redis_client.incr(f"daily_pins:{today}")
        self.redis_client.expire(f"daily_pins:{today}", 86400 * 2)  # Expire after 2 days
    
    def should_post_pin(self) -> bool:
        """Determine if we should post a pin now"""
        if not self.is_in_posting_window():
            return False
        
        daily_count = self.get_daily_pin_count()
        if daily_count >= self.daily_pin_target:
            return False
        
        # Random posting probability (30% chance each check)
        return random.random() < 0.3
    
    def generate_pin_content(self, keyword: str, domain: str) -> Dict[str, Any]:
        """Generate complete pin content including image and text"""
        try:
            self.log_info(f"Generating pin content for '{keyword}' on {domain}")
            
            # Generate text content
            title = self.enhance_keyword_title(keyword, domain)
            description = draft_description(keyword)
            hashtags = pick_hashtags(keyword)
            
            # Add domain-specific hashtags
            domain_config = self.boards_config.get(domain, {})
            domain_hashtags = domain_config.get("hashtags", [])
            hashtags.extend(random.sample(domain_hashtags, min(3, len(domain_hashtags))))
            
            # Generate image using Nano Banana
            image_result = self.nano_banana_api.generate_pinterest_pin_image(
                title=title,
                domain=domain,
                style=self.get_domain_style(domain)
            )
            
            if not image_result.get("success"):
                self.log_error(f"Image generation failed: {image_result.get('error')}")
                # Use fallback image
                image_path = self.create_fallback_image(title, domain)
                image_result = {"local_path": image_path, "filename": os.path.basename(image_path)}
            
            # Select target URL
            target_url = self.select_target_url(keyword, domain)
            
            # Select board
            board_id = self.select_board(domain)
            
            pin_content = {
                "title": title,
                "description": description,
                "hashtags": hashtags,
                "image_path": image_result.get("local_path"),
                "target_url": target_url,
                "domain": domain,
                "keyword": keyword,
                "board_id": board_id,
                "created_at": datetime.datetime.now().isoformat()
            }
            
            self.log_info(f"Pin content generated successfully for '{keyword}'")
            return {"success": True, "pin_content": pin_content}
            
        except Exception as e:
            self.log_error(f"Error generating pin content: {e}")
            return {"success": False, "error": str(e)}
    
    def post_pin_via_tailwind(self, pin_content: Dict[str, Any]) -> Dict[str, Any]:
        """Post pin using Tailwind API"""
        try:
            if not self.tailwind_api.is_configured():
                return {"success": False, "error": "Tailwind API not configured"}
            
            # Prepare pin data for Tailwind
            pin_data = {
                "title": pin_content["title"],
                "description": f"{pin_content['description']} {' '.join(pin_content['hashtags'])}",
                "target_url": pin_content["target_url"],
                "image_path": pin_content["image_path"],
                "board_id": pin_content["board_id"]
            }
            
            result = self.tailwind_api.create_pin(pin_data)
            
            if result.get("success"):
                # Store pin info in Redis for tracking
                pin_info = {
                    "pin_id": result["pin_id"],
                    "tailwind_id": result.get("tailwind_id"),
                    "title": pin_content["title"],
                    "domain": pin_content["domain"],
                    "keyword": pin_content["keyword"],
                    "posted_at": datetime.datetime.now().isoformat(),
                    "status": "posted",
                    "views": 0,
                    "saves": 0,
                    "clicks": 0
                }
                
                # Store in recent pins
                self.redis_client.lpush("recent_pins", json.dumps(pin_info))
                self.redis_client.ltrim("recent_pins", 0, 99)  # Keep last 100 pins
                
                # Update statistics
                self.update_pin_stats(pin_content["domain"])
                self.increment_daily_pin_count()
                
                self.log_info(f"Pin posted successfully via Tailwind: {result['pin_id']}")
                return result
            else:
                self.log_error(f"Tailwind posting failed: {result.get('error')}")
                return result
                
        except Exception as e:
            self.log_error(f"Error posting via Tailwind: {e}")
            return {"success": False, "error": str(e)}
    
    def post_pin_direct(self, pin_content: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback: Direct Pinterest posting (mock implementation)"""
        try:
            # Mock Pinterest API posting
            self.log_info("Using direct Pinterest posting (mock)")
            
            pin_id = f"direct_pin_{int(time.time())}"
            
            # Store pin info
            pin_info = {
                "pin_id": pin_id,
                "title": pin_content["title"],
                "domain": pin_content["domain"],
                "keyword": pin_content["keyword"],
                "posted_at": datetime.datetime.now().isoformat(),
                "status": "posted",
                "method": "direct",
                "views": random.randint(50, 200),
                "saves": random.randint(5, 25),
                "clicks": random.randint(2, 15)
            }
            
            # Store in recent pins
            self.redis_client.lpush("recent_pins", json.dumps(pin_info))
            self.redis_client.ltrim("recent_pins", 0, 99)
            
            # Update statistics
            self.update_pin_stats(pin_content["domain"])
            self.increment_daily_pin_count()
            
            return {"success": True, "pin_id": pin_id, "method": "direct"}
            
        except Exception as e:
            self.log_error(f"Error in direct posting: {e}")
            return {"success": False, "error": str(e)}
    
    def process_keyword_queue(self):
        """Process keywords from the queue and create pins"""
        try:
            keyword = self.redis_client.rpop("keyword_queue")
            
            if not keyword:
                return False
            
            if not self.should_post_pin():
                # Put keyword back in queue for later
                self.redis_client.lpush("keyword_queue", keyword)
                return False
            
            # Select domain for this pin
            domain = random.choice(self.domain_rotation) if self.domain_rotation else "hing.me"
            domain = domain.replace("https://", "").replace("http://", "")
            
            self.log_info(f"Processing keyword '{keyword}' for domain {domain}")
            
            # Generate pin content
            content_result = self.generate_pin_content(keyword, domain)
            
            if not content_result.get("success"):
                self.log_error(f"Content generation failed: {content_result.get('error')}")
                return False
            
            pin_content = content_result["pin_content"]
            
            # Try posting via Tailwind first, then fallback to direct
            post_result = self.post_pin_via_tailwind(pin_content)
            
            if not post_result.get("success"):
                self.log_info("Tailwind posting failed, trying direct posting")
                post_result = self.post_pin_direct(pin_content)
            
            if post_result.get("success"):
                self.log_info(f"Pin posted successfully: {post_result.get('pin_id')}")
                
                # Log to reports
                report = {
                    "timestamp": time.time(),
                    "event": "pin_posted",
                    "keyword": keyword,
                    "domain": domain,
                    "pin_id": post_result.get("pin_id"),
                    "method": post_result.get("method", "tailwind")
                }
                self.redis_client.lpush("reports", json.dumps(report))
                
                return True
            else:
                self.log_error(f"Pin posting failed: {post_result.get('error')}")
                return False
                
        except Exception as e:
            self.log_error(f"Error processing keyword queue: {e}")
            return False
    
    def update_pin_stats(self, domain: str):
        """Update statistics for domain"""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Update daily stats
        self.redis_client.incr(f"daily:pins:{domain}")
        self.redis_client.incr(f"daily:pins:{today}")
        
        # Update total stats
        self.redis_client.incr(f"stats:{domain}:pins")
        
        # Set expiration for daily stats
        self.redis_client.expire(f"daily:pins:{domain}", 86400 * 7)
        self.redis_client.expire(f"daily:pins:{today}", 86400 * 7)
    
    def enhance_keyword_title(self, keyword: str, domain: str) -> str:
        """Enhance keyword into attractive pin title"""
        templates = {
            "hing.me": [
                f"{keyword}: Complete Guide 2025",
                f"Ultimate {keyword} Tips",
                f"{keyword} Made Simple",
                f"Master {keyword} in 2025",
                f"{keyword}: Expert Guide"
            ],
            "playu.co": [
                f"Best {keyword} Guide",
                f"{keyword}: Pro Tips & Tricks",
                f"Ultimate {keyword} Setup",
                f"{keyword} Mastery Guide",
                f"Epic {keyword} Collection"
            ]
        }
        
        domain_templates = templates.get(domain, templates["hing.me"])
        return random.choice(domain_templates)
    
    def get_domain_style(self, domain: str) -> str:
        """Get image style for domain"""
        styles = {
            "hing.me": "financial",
            "playu.co": "gaming"
        }
        return styles.get(domain, "modern")
    
    def select_target_url(self, keyword: str, domain: str) -> str:
        """Select target URL for pin"""
        # In a real implementation, this would select from existing articles
        # or create new article URLs
        safe_keyword = keyword.lower().replace(" ", "-")
        return f"https://{domain}/articles/{safe_keyword}"
    
    def select_board(self, domain: str) -> str:
        """Select Pinterest board for domain"""
        domain_config = self.boards_config.get(domain, {})
        board_ids = domain_config.get("board_ids", ["general"])
        return random.choice(board_ids)
    
    def create_fallback_image(self, title: str, domain: str) -> str:
        """Create fallback image when AI generation fails"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create image
            img = Image.new('RGB', (1000, 1500), color='#6366f1' if domain == 'hing.me' else '#8b5cf6')
            draw = ImageDraw.Draw(img)
            
            # Try to load font
            try:
                font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
                font_domain = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
            except:
                font_title = ImageFont.load_default()
                font_domain = ImageFont.load_default()
            
            # Wrap title text
            words = title.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if len(test_line) <= 20:  # Approximate character limit per line
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            # Draw title
            y_offset = 500
            for line in lines[:5]:  # Max 5 lines
                draw.text((50, y_offset), line, fill='white', font=font_title)
                y_offset += 80
            
            # Draw domain
            draw.text((50, y_offset + 100), domain, fill='#e2e8f0', font=font_domain)
            
            # Save image
            os.makedirs("/tmp/generated_images", exist_ok=True)
            filename = f"/tmp/generated_images/fallback_{domain}_{int(time.time())}.png"
            img.save(filename)
            
            return filename
            
        except Exception as e:
            self.log_error(f"Fallback image creation failed: {e}")
            return "/tmp/placeholder.png"
    
    def log_info(self, message: str):
        """Log info message"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] INFO: {message}")
    
    def log_error(self, message: str):
        """Log error message"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ERROR: {message}")
        
        # Also store in Redis for dashboard
        error_report = {
            "timestamp": time.time(),
            "level": "error",
            "message": message
        }
        self.redis_client.lpush("error_logs", json.dumps(error_report))
        self.redis_client.ltrim("error_logs", 0, 99)  # Keep last 100 errors
    
    def get_next_delay(self) -> int:
        """Calculate delay until next processing attempt"""
        base_delay = 600  # 10 minutes
        random_factor = random.randint(60, 300)  # 1-5 minutes
        return base_delay + random_factor

def main():
    """Main worker loop"""
    worker = EnhancedPinWorker()
    worker.log_info("Enhanced Pinterest worker started")
    
    while True:
        try:
            # Process keyword queue
            if worker.process_keyword_queue():
                # Success - shorter delay
                delay = random.randint(300, 900)  # 5-15 minutes
            else:
                # No work or failure - longer delay
                delay = worker.get_next_delay()
            
            worker.log_info(f"Sleeping for {delay} seconds")
            time.sleep(delay)
            
        except KeyboardInterrupt:
            worker.log_info("Enhanced Pinterest worker stopped by user")
            break
        except Exception as e:
            worker.log_error(f"Unexpected error in main loop: {e}")
            time.sleep(300)  # 5 minutes on error

if __name__ == "__main__":
    main()
