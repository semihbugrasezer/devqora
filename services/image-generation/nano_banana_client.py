# /srv/auto-adsense/services/image-generation/nano_banana_client.py
import os
import json
import time
import redis
import asyncio
import aiohttp
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import hashlib
import base64
from PIL import Image
import io

class NanoBananaClient:
    """Nano Banana API ile Profesyonel Resim Üretimi"""
    
    def __init__(self):
        self.api_key = os.getenv("NANO_BANANA_API_KEY", "")
        self.base_url = "https://api.nanobana.com/v1"  # Nano Banana API endpoint
        
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        self.output_path = Path("/srv/auto-adsense/multidomain_site_kit/generated_images")
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Pinterest için optimize edilmiş boyutlar
        self.image_specifications = {
            "pinterest_mobile": {
                "width": 600,
                "height": 900,
                "aspect_ratio": "2:3",
                "style": "pinterest-optimized",
                "quality": "high"
            },
            "article_hero": {
                "width": 800,
                "height": 450,
                "aspect_ratio": "16:9",
                "style": "article-header",
                "quality": "high"
            },
            "article_inline": {
                "width": 600,
                "height": 400,
                "aspect_ratio": "3:2",
                "style": "content-supportive",
                "quality": "medium"
            },
            "social_share": {
                "width": 1200,
                "height": 630,
                "aspect_ratio": "1.91:1",
                "style": "social-media",
                "quality": "high"
            }
        }
        
        # Niche'e özel stil ve prompt templates
        self.niche_prompts = {
            "finance": {
                "style_keywords": "professional, clean, modern, financial, trustworthy, corporate",
                "color_palette": "blue, navy, gold, silver, white",
                "mood": "confident, professional, reliable",
                "templates": {
                    "hero": "Professional financial illustration about {topic}, modern corporate style, clean design, blue and gold color scheme, high-quality, detailed",
                    "pinterest": "Eye-catching financial infographic about {topic}, Pinterest-style vertical layout, modern typography, professional blue colors, mobile-optimized, engaging",
                    "inline": "Simple clean illustration representing {topic}, minimalist financial concept, professional blue tones, easy to understand",
                    "social": "Social media graphic about {topic}, professional financial design, corporate blue color scheme, clear typography"
                }
            },
            "technology": {
                "style_keywords": "futuristic, digital, high-tech, modern, innovative, sleek",
                "color_palette": "purple, blue, cyan, silver, black",
                "mood": "innovative, cutting-edge, dynamic",
                "templates": {
                    "hero": "Futuristic technology illustration about {topic}, digital art style, purple and cyan color scheme, high-tech aesthetic, detailed",
                    "pinterest": "Tech infographic about {topic}, vertical Pinterest format, modern digital design, purple gradients, mobile-friendly, engaging",
                    "inline": "Simple tech icon illustration for {topic}, minimalist digital style, purple and blue tones, clean design",
                    "social": "Technology social media graphic about {topic}, futuristic design, digital purple color scheme, modern typography"
                }
            },
            "gaming": {
                "style_keywords": "dynamic, energetic, colorful, gaming, esports, action",
                "color_palette": "red, orange, yellow, black, neon",
                "mood": "exciting, energetic, competitive",
                "templates": {
                    "hero": "Dynamic gaming illustration about {topic}, action-packed design, red and orange color scheme, high-energy aesthetic, detailed",
                    "pinterest": "Gaming infographic about {topic}, vertical Pinterest layout, energetic design, red and black colors, mobile-optimized, engaging",
                    "inline": "Gaming icon illustration for {topic}, simple but dynamic style, red and orange tones, clean gaming aesthetic",
                    "social": "Gaming social media graphic about {topic}, action-packed design, red color scheme, bold gaming typography"
                }
            },
            "health": {
                "style_keywords": "natural, clean, healthy, fresh, calming, medical",
                "color_palette": "green, blue, white, natural, soft",
                "mood": "healthy, calming, trustworthy",
                "templates": {
                    "hero": "Clean health and wellness illustration about {topic}, natural design, green and blue color scheme, calming aesthetic, detailed",
                    "pinterest": "Health infographic about {topic}, vertical Pinterest format, natural green design, wellness-focused, mobile-friendly, engaging",
                    "inline": "Simple health icon illustration for {topic}, minimalist wellness style, green and blue tones, clean medical design",
                    "social": "Health social media graphic about {topic}, wellness design, natural green color scheme, clean typography"
                }
            },
            "business": {
                "style_keywords": "professional, corporate, success, growth, business",
                "color_palette": "orange, gold, blue, black, white",
                "mood": "successful, professional, growth-oriented",
                "templates": {
                    "hero": "Professional business illustration about {topic}, corporate success style, orange and gold color scheme, growth-focused aesthetic, detailed",
                    "pinterest": "Business infographic about {topic}, vertical Pinterest layout, professional orange design, success-oriented, mobile-optimized, engaging",
                    "inline": "Business icon illustration for {topic}, minimalist corporate style, orange and gold tones, professional design",
                    "social": "Business social media graphic about {topic}, corporate success design, orange color scheme, professional typography"
                }
            }
        }
        
        self.log_info("Nano Banana Client initialized")
    
    async def generate_article_images(self, article_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ana konu odaklı makale resimleri üret"""
        try:
            title = article_data["title"]
            main_topic = article_data.get("main_topic", title.split(":")[0])
            domain = article_data["domain"]
            niche = article_data.get("niche", "technology")
            keywords = article_data.get("keywords", [])
            
            generated_images = []
            
            self.log_info(f"Generating images for main topic: {main_topic}")
            
            # 1. Hero image (article başında)
            hero_image = await self.generate_hero_image(main_topic, title, niche)
            if hero_image:
                generated_images.append(hero_image)
            
            # 2. Pinterest optimized images (3 farklı varyasyon)
            pinterest_images = await self.generate_pinterest_variations(main_topic, niche, keywords)
            generated_images.extend(pinterest_images)
            
            # 3. Article içi supporting images (alt konular için)
            inline_images = await self.generate_supporting_images(main_topic, keywords[:3], niche)
            generated_images.extend(inline_images)
            
            # 4. Social sharing image
            social_image = await self.generate_social_image(main_topic, title, niche, domain)
            if social_image:
                generated_images.append(social_image)
            
            # Store generated images
            await self.store_generated_images(domain, main_topic, generated_images)
            
            self.log_info(f"Generated {len(generated_images)} images for '{main_topic}'")
            return generated_images
            
        except Exception as e:
            self.log_error(f"Failed to generate images: {e}")
            return []
    
    async def generate_hero_image(self, main_topic: str, title: str, niche: str) -> Optional[Dict[str, Any]]:
        """Article hero resmi üret"""
        try:
            niche_config = self.niche_prompts[niche]
            spec = self.image_specifications["article_hero"]
            
            prompt = niche_config["templates"]["hero"].format(topic=main_topic)
            
            # Enhanced prompt for better quality
            enhanced_prompt = f"{prompt}, {niche_config['style_keywords']}, {niche_config['color_palette']}, {niche_config['mood']}, 4K quality, professional photography"
            
            image_data = await self.call_nano_banana_api(
                prompt=enhanced_prompt,
                width=spec["width"],
                height=spec["height"],
                style=spec["style"],
                quality=spec["quality"]
            )
            
            if image_data:
                filename = f"hero_{self.safe_filename(main_topic)}_{int(time.time())}.jpg"
                filepath = await self.save_image(image_data, filename)
                
                return {
                    "type": "hero",
                    "filename": filename,
                    "url": f"/images/{filename}",
                    "alt_text": f"Complete guide to {main_topic}",
                    "position": "top",
                    "main_topic": main_topic,
                    "size": f"{spec['width']}x{spec['height']}"
                }
            
        except Exception as e:
            self.log_error(f"Failed to generate hero image: {e}")
        
        return None
    
    async def generate_pinterest_variations(self, main_topic: str, niche: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """Pinterest için 3 farklı varyasyon üret"""
        pinterest_images = []
        
        try:
            niche_config = self.niche_prompts[niche]
            spec = self.image_specifications["pinterest_mobile"]
            
            # 3 farklı Pinterest varyasyonu
            variations = [
                {
                    "style": "infographic",
                    "focus": "step-by-step guide",
                    "layout": "vertical list"
                },
                {
                    "style": "quote",
                    "focus": "key insight",
                    "layout": "centered text"
                },
                {
                    "style": "visual",
                    "focus": "main concept",
                    "layout": "illustration with title"
                }
            ]
            
            for i, variation in enumerate(variations):
                # Her varyasyon için farklı prompt
                base_prompt = niche_config["templates"]["pinterest"].format(topic=main_topic)
                
                enhanced_prompt = f"{base_prompt}, {variation['style']} style, {variation['focus']}, {variation['layout']}, {niche_config['style_keywords']}, Pinterest mobile optimized, high engagement design"
                
                image_data = await self.call_nano_banana_api(
                    prompt=enhanced_prompt,
                    width=spec["width"],
                    height=spec["height"],
                    style="pinterest-optimized",
                    quality=spec["quality"]
                )
                
                if image_data:
                    filename = f"pinterest_{self.safe_filename(main_topic)}_{i+1}_{int(time.time())}.jpg"
                    filepath = await self.save_image(image_data, filename)
                    
                    pinterest_images.append({
                        "type": "pinterest",
                        "filename": filename,
                        "url": f"/images/{filename}",
                        "alt_text": f"Pinterest: {main_topic} - {variation['style']}",
                        "variation": variation["style"],
                        "main_topic": main_topic,
                        "optimized_for": "mobile_pinterest",
                        "size": f"{spec['width']}x{spec['height']}"
                    })
                
                # Rate limiting between API calls
                await asyncio.sleep(2)
            
        except Exception as e:
            self.log_error(f"Failed to generate Pinterest images: {e}")
        
        return pinterest_images
    
    async def generate_supporting_images(self, main_topic: str, sub_topics: List[str], niche: str) -> List[Dict[str, Any]]:
        """Ana konuyu destekleyen alt konu resimleri"""
        supporting_images = []
        
        try:
            niche_config = self.niche_prompts[niche]
            spec = self.image_specifications["article_inline"]
            
            for i, sub_topic in enumerate(sub_topics):
                # Alt konu main topic'e bağlı prompt
                prompt = f"Simple illustration of {sub_topic} related to {main_topic}, {niche_config['templates']['inline'].format(topic=sub_topic)}, supporting content style"
                
                enhanced_prompt = f"{prompt}, {niche_config['style_keywords']}, clean design, article support, mobile-friendly"
                
                image_data = await self.call_nano_banana_api(
                    prompt=enhanced_prompt,
                    width=spec["width"],
                    height=spec["height"],
                    style=spec["style"],
                    quality=spec["quality"]
                )
                
                if image_data:
                    filename = f"inline_{self.safe_filename(main_topic)}_{self.safe_filename(sub_topic)}_{int(time.time())}.jpg"
                    filepath = await self.save_image(image_data, filename)
                    
                    supporting_images.append({
                        "type": "inline",
                        "filename": filename,
                        "url": f"/images/{filename}",
                        "alt_text": f"{sub_topic} guide - part of {main_topic}",
                        "sub_topic": sub_topic,
                        "main_topic": main_topic,
                        "position": f"section_{i+1}",
                        "size": f"{spec['width']}x{spec['height']}"
                    })
                
                await asyncio.sleep(2)
        
        except Exception as e:
            self.log_error(f"Failed to generate supporting images: {e}")
        
        return supporting_images
    
    async def generate_social_image(self, main_topic: str, title: str, niche: str, domain: str) -> Optional[Dict[str, Any]]:
        """Social sharing resmi üret"""
        try:
            niche_config = self.niche_prompts[niche]
            spec = self.image_specifications["social_share"]
            
            prompt = niche_config["templates"]["social"].format(topic=main_topic)
            enhanced_prompt = f"{prompt}, social media optimized, {domain} branding, {niche_config['color_palette']}, professional"
            
            image_data = await self.call_nano_banana_api(
                prompt=enhanced_prompt,
                width=spec["width"],
                height=spec["height"],
                style=spec["style"],
                quality=spec["quality"]
            )
            
            if image_data:
                filename = f"social_{self.safe_filename(main_topic)}_{int(time.time())}.jpg"
                filepath = await self.save_image(image_data, filename)
                
                return {
                    "type": "social",
                    "filename": filename,
                    "url": f"/images/{filename}",
                    "alt_text": f"Share: {title}",
                    "main_topic": main_topic,
                    "domain": domain,
                    "size": f"{spec['width']}x{spec['height']}"
                }
            
        except Exception as e:
            self.log_error(f"Failed to generate social image: {e}")
        
        return None
    
    async def call_nano_banana_api(self, prompt: str, width: int, height: int, style: str, quality: str) -> Optional[bytes]:
        """Nano Banana API çağrısı"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "style": style,
                "quality": quality,
                "format": "jpeg",
                "steps": 30,  # High quality için daha fazla step
                "guidance_scale": 7.5,  # Prompt'a sadakat
                "negative_prompt": "blurry, low quality, watermark, text overlay, bad composition, distorted"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/generate",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)  # 2 dakika timeout
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Base64 encoded image data
                        if "image_data" in result:
                            image_bytes = base64.b64decode(result["image_data"])
                            return image_bytes
                        
                        # Direct download URL
                        elif "image_url" in result:
                            async with session.get(result["image_url"]) as img_response:
                                if img_response.status == 200:
                                    return await img_response.read()
                    
                    else:
                        error_text = await response.text()
                        self.log_error(f"Nano Banana API error {response.status}: {error_text}")
            
        except asyncio.TimeoutError:
            self.log_error("Nano Banana API timeout")
        except Exception as e:
            self.log_error(f"Nano Banana API call failed: {e}")
        
        return None
    
    async def save_image(self, image_data: bytes, filename: str) -> Path:
        """Resmi kaydet ve optimize et"""
        try:
            filepath = self.output_path / filename
            
            # PIL ile resmi aç ve optimize et
            image = Image.open(io.BytesIO(image_data))
            
            # RGB'ye çevir (JPEG için)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Mobile için optimize et
            image.save(
                filepath,
                'JPEG',
                quality=85,
                optimize=True,
                progressive=True  # Progressive JPEG for faster mobile loading
            )
            
            self.log_info(f"Saved optimized image: {filename}")
            return filepath
            
        except Exception as e:
            self.log_error(f"Failed to save image {filename}: {e}")
            raise
    
    def safe_filename(self, text: str) -> str:
        """Güvenli dosya adı oluştur"""
        import re
        # Sadece harf, rakam ve tire
        safe = re.sub(r'[^a-zA-Z0-9\-_]', '', text.replace(' ', '-'))
        return safe[:50].lower()  # Max 50 karakter
    
    async def store_generated_images(self, domain: str, main_topic: str, images: List[Dict[str, Any]]):
        """Üretilen resimleri Redis'e kaydet"""
        try:
            image_data = {
                "domain": domain,
                "main_topic": main_topic,
                "images": images,
                "generated_at": datetime.now().isoformat(),
                "total_count": len(images),
                "generator": "nano_banana"
            }
            
            # Redis'e kaydet
            key = f"generated_images:{domain}:{self.safe_filename(main_topic)}"
            self.redis_client.set(key, json.dumps(image_data), ex=86400 * 7)  # 7 gün
            
            # Domain'in resim listesine ekle
            self.redis_client.lpush(f"domain_images:{domain}", key)
            self.redis_client.ltrim(f"domain_images:{domain}", 0, 999)  # Son 1000'i tut
            
            self.log_info(f"Stored {len(images)} images for {main_topic}")
            
        except Exception as e:
            self.log_error(f"Failed to store image data: {e}")
    
    async def check_api_status(self) -> bool:
        """Nano Banana API durumunu kontrol et"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/status",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    return response.status == 200
            
        except Exception as e:
            self.log_error(f"API status check failed: {e}")
            return False
    
    async def get_remaining_credits(self) -> Optional[int]:
        """Kalan kredi sayısını öğren"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/credits",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return result.get("remaining_credits")
            
        except Exception as e:
            self.log_error(f"Failed to get credits: {e}")
        
        return None
    
    def log_info(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] NANO-BANANA: {message}")
    
    def log_error(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] NANO-BANANA ERROR: {message}")

async def main():
    """Nano Banana Image Generator Worker"""
    client = NanoBananaClient()
    
    print("🍌 Nano Banana Image Generator started")
    print("🎨 Generating high-quality images for main topics")
    
    # API durumunu kontrol et
    if not await client.check_api_status():
        print("❌ Nano Banana API is not available")
        return
    
    # Kredi durumunu kontrol et
    credits = await client.get_remaining_credits()
    if credits is not None:
        print(f"💳 Remaining credits: {credits}")
    
    while True:
        try:
            # Image generation requests'leri kontrol et
            request = client.redis_client.rpop("nano_banana_queue")
            
            if request:
                request_data = json.loads(request)
                main_topic = request_data.get("main_topic", "Unknown")
                
                print(f"🎨 Generating images for main topic: {main_topic}")
                
                images = await client.generate_article_images(request_data)
                
                if images:
                    print(f"✅ Generated {len(images)} high-quality images")
                    
                    # Content API'ye resim bilgilerini gönder
                    client.redis_client.lpush("content_images_queue", json.dumps({
                        "domain": request_data["domain"],
                        "main_topic": main_topic,
                        "images": images,
                        "type": "nano_banana_generated"
                    }))
                    
                    # Pinterest queue'ya ekle
                    for image in images:
                        if image["type"] == "pinterest":
                            client.redis_client.lpush("pinterest_pin_queue", json.dumps({
                                "domain": request_data["domain"],
                                "main_topic": main_topic,
                                "image_url": image["url"],
                                "image_filename": image["filename"],
                                "title": f"{main_topic} - {image['variation']}",
                                "description": f"Complete guide to {main_topic}. Professional insights and expert tips.",
                                "type": "auto_generated"
                            }))
                else:
                    print("❌ Failed to generate images")
            
            await asyncio.sleep(5)  # 5 saniyede bir kontrol et
            
        except Exception as e:
            print(f"❌ Nano Banana Generator error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
