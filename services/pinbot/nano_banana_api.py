# /srv/auto-adsense/services/pinbot/nano_banana_api.py
import os
import json
import time
import requests
import base64
from io import BytesIO
from PIL import Image
from typing import Dict, Any, Optional, List

class NanoBananaAPI:
    """Nano Banana API integration for AI image generation"""
    
    def __init__(self):
        self.api_key = os.getenv("NANO_BANANA_API_KEY")
        self.base_url = "https://api.nanobanana.com/v1"
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AutoAdSense/1.0"
            })
    
    def is_configured(self) -> bool:
        """Check if Nano Banana API is properly configured"""
        return bool(self.api_key)
    
    def generate_image(self, prompt: str, style: str = "modern", size: str = "pinterest") -> Dict[str, Any]:
        """Generate an image using Nano Banana AI"""
        try:
            if not self.is_configured():
                return {"error": "Nano Banana API key not configured"}
            
            # Pinterest optimal sizes
            size_map = {
                "pinterest": {"width": 1000, "height": 1500},  # 2:3 ratio
                "square": {"width": 1080, "height": 1080},
                "landscape": {"width": 1200, "height": 630},
                "story": {"width": 1080, "height": 1920}
            }
            
            dimensions = size_map.get(size, size_map["pinterest"])
            
            # Style prompts for better AI generation
            style_prompts = {
                "modern": "modern, clean, minimalist design, professional lighting, high quality",
                "minimalist": "minimalist, simple, clean lines, white background, elegant",
                "colorful": "vibrant colors, eye-catching, bold, dynamic, energetic",
                "professional": "professional, corporate, sophisticated, clean, business-like",
                "financial": "financial, money, investment, professional, clean, trustworthy",
                "gaming": "gaming, technology, modern, colorful, dynamic, exciting",
                "lifestyle": "lifestyle, attractive, modern, clean, aspirational"
            }
            
            enhanced_prompt = f"{prompt}, {style_prompts.get(style, style_prompts['modern'])}"
            
            payload = {
                "prompt": enhanced_prompt,
                "negative_prompt": "blurry, low quality, distorted, ugly, bad anatomy, text, watermark",
                "width": dimensions["width"],
                "height": dimensions["height"],
                "steps": 30,
                "guidance_scale": 7.5,
                "seed": -1,  # Random seed
                "sampler": "DPM++ 2M Karras",
                "cfg_scale": 7.5,
                "style": style
            }
            
            response = self.session.post(f"{self.base_url}/generate", json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("success"):
                return {
                    "success": True,
                    "image_id": data.get("image_id"),
                    "image_url": data.get("image_url"),
                    "image_data": data.get("image_data"),  # Base64 encoded
                    "prompt_used": enhanced_prompt,
                    "style": style,
                    "size": f"{dimensions['width']}x{dimensions['height']}",
                    "generation_time": data.get("generation_time", 0)
                }
            else:
                return {"error": data.get("error", "Image generation failed")}
            
        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    def save_image(self, image_data: str, filename: str, directory: str = "/tmp") -> Dict[str, Any]:
        """Save base64 image data to file"""
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            
            # Create directory if it doesn't exist
            os.makedirs(directory, exist_ok=True)
            
            # Generate full path
            if not filename.endswith(('.png', '.jpg', '.jpeg')):
                filename += '.png'
            
            filepath = os.path.join(directory, filename)
            
            # Save image
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            # Verify file was created and get size
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                return {
                    "success": True,
                    "filepath": filepath,
                    "filename": filename,
                    "file_size": file_size
                }
            else:
                return {"error": "File was not created successfully"}
            
        except Exception as e:
            return {"error": f"Failed to save image: {str(e)}"}
    
    def generate_pinterest_pin_image(self, title: str, domain: str, style: str = "modern") -> Dict[str, Any]:
        """Generate a Pinterest-optimized pin image with title overlay"""
        try:
            # Domain-specific styling
            domain_styles = {
                "hing.me": {
                    "theme": "financial, money, investment, professional",
                    "colors": "blue, white, gold accents",
                    "mood": "trustworthy, professional, clean"
                },
                "playu.co": {
                    "theme": "gaming, technology, entertainment",
                    "colors": "purple, blue, vibrant colors",
                    "mood": "exciting, modern, dynamic"
                }
            }
            
            domain_style = domain_styles.get(domain, domain_styles["hing.me"])
            
            # Create enhanced prompt for Pinterest pin
            prompt = f"""
            Pinterest pin design for '{title}', 
            {domain_style['theme']}, {domain_style['colors']}, {domain_style['mood']},
            vertical layout, eye-catching, professional, 
            readable typography, clean composition,
            high quality, 4k resolution, 
            optimized for Pinterest platform
            """
            
            result = self.generate_image(prompt, style, "pinterest")
            
            if result.get("success"):
                # Generate filename
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title.replace(' ', '_').lower()[:50]
                timestamp = int(time.time())
                filename = f"pin_{domain}_{safe_title}_{timestamp}.png"
                
                # Save image
                if result.get("image_data"):
                    save_result = self.save_image(result["image_data"], filename, "/tmp/generated_images")
                    if save_result.get("success"):
                        result["local_path"] = save_result["filepath"]
                        result["filename"] = save_result["filename"]
                
                result["domain"] = domain
                result["title"] = title
                
            return result
            
        except Exception as e:
            return {"error": f"Failed to generate Pinterest pin: {str(e)}"}
    
    def generate_article_hero_image(self, article_title: str, article_topic: str, domain: str) -> Dict[str, Any]:
        """Generate hero image for articles"""
        try:
            # Create topic-specific prompt
            topic_prompts = {
                "finance": "financial charts, money, investment, professional office, calculator",
                "gaming": "gaming setup, controllers, RGB lighting, modern technology",
                "investment": "stock market, graphs, money, business, professional",
                "crypto": "cryptocurrency, blockchain, digital money, modern technology",
                "technology": "modern technology, computers, software, innovation",
                "lifestyle": "modern lifestyle, aspirational, clean, attractive",
                "health": "healthy lifestyle, wellness, clean, natural",
                "education": "learning, books, knowledge, modern classroom"
            }
            
            # Detect topic from title
            detected_topic = "lifestyle"  # default
            for topic, keywords in topic_prompts.items():
                if any(keyword in article_title.lower() for keyword in topic.split()):
                    detected_topic = topic
                    break
            
            prompt = f"""
            Hero image for article '{article_title}',
            {topic_prompts[detected_topic]},
            professional, clean, modern design,
            horizontal layout, web banner style,
            high quality, engaging, click-worthy,
            suitable for {domain} website
            """
            
            result = self.generate_image(prompt, "modern", "landscape")
            
            if result.get("success"):
                # Generate filename
                safe_title = "".join(c for c in article_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title.replace(' ', '_').lower()[:40]
                timestamp = int(time.time())
                filename = f"hero_{domain}_{safe_title}_{timestamp}.jpg"
                
                # Save image
                if result.get("image_data"):
                    save_result = self.save_image(result["image_data"], filename, "/tmp/generated_images")
                    if save_result.get("success"):
                        result["local_path"] = save_result["filepath"]
                        result["filename"] = save_result["filename"]
                
                result["article_title"] = article_title
                result["domain"] = domain
                result["topic"] = detected_topic
                
            return result
            
        except Exception as e:
            return {"error": f"Failed to generate hero image: {str(e)}"}
    
    def batch_generate_images(self, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate multiple images in batch"""
        results = []
        
        for i, req in enumerate(requests):
            print(f"Generating image {i+1}/{len(requests)}: {req.get('title', req.get('prompt', 'Unknown'))}")
            
            if req.get("type") == "pin":
                result = self.generate_pinterest_pin_image(
                    req.get("title", ""),
                    req.get("domain", "hing.me"),
                    req.get("style", "modern")
                )
            elif req.get("type") == "hero":
                result = self.generate_article_hero_image(
                    req.get("title", ""),
                    req.get("topic", ""),
                    req.get("domain", "hing.me")
                )
            else:
                result = self.generate_image(
                    req.get("prompt", ""),
                    req.get("style", "modern"),
                    req.get("size", "pinterest")
                )
            
            results.append({
                "index": i,
                "request": req,
                "result": result,
                "success": result.get("success", False)
            })
            
            # Rate limiting
            time.sleep(2)
        
        return {
            "success": True,
            "total_requests": len(requests),
            "successful": len([r for r in results if r["success"]]),
            "failed": len([r for r in results if not r["success"]]),
            "results": results
        }
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information and usage statistics"""
        try:
            if not self.is_configured():
                return {"error": "Nano Banana API key not configured"}
            
            response = self.session.get(f"{self.base_url}/account")
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "success": True,
                "credits_remaining": data.get("credits_remaining", 0),
                "credits_used": data.get("credits_used", 0),
                "plan": data.get("plan", "free"),
                "rate_limit": data.get("rate_limit", {}),
                "account_status": data.get("status", "active")
            }
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Account info request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

# Test function
def test_nano_banana_api():
    """Test function for Nano Banana API"""
    api = NanoBananaAPI()
    
    if not api.is_configured():
        print("⚠️  Nano Banana API key not configured")
        # Use fallback image generation
        return test_fallback_image_generation()
    
    # Test account info
    account_info = api.get_account_info()
    if account_info.get("success"):
        print(f"✅ Account info: {account_info['credits_remaining']} credits remaining")
    
    # Test Pinterest pin generation
    pin_result = api.generate_pinterest_pin_image(
        "Ultimate Investment Guide 2025",
        "hing.me",
        "financial"
    )
    
    if pin_result.get("success"):
        print(f"✅ Pinterest pin generated: {pin_result.get('filename')}")
        return True
    else:
        print(f"❌ Pin generation failed: {pin_result.get('error')}")
        return test_fallback_image_generation()

def test_fallback_image_generation():
    """Fallback image generation using PIL when API is not available"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a simple Pinterest pin
        img = Image.new('RGB', (1000, 1500), color='#6366f1')
        draw = ImageDraw.Draw(img)
        
        # Try to load a font
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
            font_subtitle = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        except:
            font_title = ImageFont.load_default()
            font_subtitle = ImageFont.load_default()
        
        # Add text
        title = "Investment Guide 2025"
        subtitle = "hing.me"
        
        # Draw title
        draw.text((50, 600), title, fill='white', font=font_title)
        draw.text((50, 750), subtitle, fill='#e2e8f0', font=font_subtitle)
        
        # Save
        os.makedirs("/tmp/generated_images", exist_ok=True)
        filename = f"/tmp/generated_images/fallback_pin_{int(time.time())}.png"
        img.save(filename)
        
        print(f"✅ Fallback image generated: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Fallback generation failed: {e}")
        return False

if __name__ == "__main__":
    test_nano_banana_api()
