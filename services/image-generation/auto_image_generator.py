# /srv/auto-adsense/services/image-generation/auto_image_generator.py
import os
import json
import time
import redis
import asyncio
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import threading
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import io
import base64
import hashlib
import random

class AutoImageGenerator:
    """Popüler Title'lara Göre Otomatik Resim Üretimi Sistemi"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        self.output_path = Path("/srv/auto-adsense/multidomain_site_kit/generated_images")
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Pinterest optimal image sizes (mobile-first)
        self.image_sizes = {
            "pinterest_mobile": (600, 900),  # 2:3 ratio - perfect for mobile Pinterest
            "pinterest_standard": (735, 1102),  # Standard Pinterest size
            "article_hero": (800, 450),  # Article header (16:9)
            "article_inline": (600, 400),  # Inline article images
            "social_share": (1200, 630),  # Social media sharing
        }
        
        # Niche-specific design templates
        self.design_templates = {
            "finance": {
                "colors": ["#1E40AF", "#3B82F6", "#60A5FA", "#93C5FD", "#DBEAFE"],
                "fonts": ["Arial Bold", "Helvetica", "Inter"],
                "styles": ["professional", "clean", "trustworthy"],
                "elements": ["charts", "money", "growth", "calculator"],
                "backgrounds": ["gradient", "clean", "professional"]
            },
            "technology": {
                "colors": ["#7C3AED", "#8B5CF6", "#A78BFA", "#C4B5FD", "#EDE9FE"],
                "fonts": ["Arial Bold", "Roboto", "Inter"],
                "styles": ["modern", "futuristic", "clean"],
                "elements": ["code", "devices", "network", "AI"],
                "backgrounds": ["tech", "gradient", "geometric"]
            },
            "gaming": {
                "colors": ["#DC2626", "#EF4444", "#F87171", "#FCA5A5", "#FECACA"],
                "fonts": ["Arial Bold", "Impact", "Roboto"],
                "styles": ["dynamic", "energetic", "bold"],
                "elements": ["controller", "setup", "esports", "gaming"],
                "backgrounds": ["dark", "neon", "action"]
            },
            "health": {
                "colors": ["#059669", "#10B981", "#34D399", "#6EE7B7", "#A7F3D0"],
                "fonts": ["Arial", "Helvetica", "Inter"],
                "styles": ["clean", "natural", "calming"],
                "elements": ["fitness", "wellness", "nature", "medical"],
                "backgrounds": ["natural", "clean", "gradient"]
            },
            "business": {
                "colors": ["#D97706", "#F59E0B", "#FBBF24", "#FCD34D", "#FEF3C7"],
                "fonts": ["Arial Bold", "Helvetica", "Inter"],
                "styles": ["professional", "success", "growth"],
                "elements": ["graph", "success", "meeting", "growth"],
                "backgrounds": ["professional", "gradient", "clean"]
            }
        }
        
        # Mobile-optimized text layouts
        self.mobile_layouts = {
            "hero": {
                "title_size": 48,
                "title_position": (50, 200),
                "subtitle_size": 28,
                "subtitle_position": (50, 300),
                "max_width": 500
            },
            "list": {
                "title_size": 42,
                "title_position": (50, 150),
                "list_start": (50, 250),
                "list_item_height": 60,
                "max_width": 500
            },
            "quote": {
                "quote_size": 36,
                "quote_position": (50, 200),
                "author_size": 24,
                "author_position": (50, 400),
                "max_width": 500
            }
        }
        
        self.log_info("Auto Image Generator initialized")
    
    async def generate_article_images(self, article_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Article için otomatik resim üretimi"""
        try:
            title = article_data["title"]
            domain = article_data["domain"]
            niche = article_data.get("niche", "technology")
            keywords = article_data.get("keywords", [])
            
            generated_images = []
            
            # 1. Hero image (article başında)
            hero_image = await self.generate_hero_image(title, niche, "article_hero")
            if hero_image:
                generated_images.append({
                    "type": "hero",
                    "filename": hero_image["filename"],
                    "url": hero_image["url"],
                    "alt_text": f"Complete guide to {title}",
                    "position": "top"
                })
            
            # 2. Pinterest optimized images (mobile-first)
            pinterest_images = await self.generate_pinterest_images(title, niche, keywords)
            generated_images.extend(pinterest_images)
            
            # 3. Inline images (article içinde)
            inline_images = await self.generate_inline_images(title, niche, keywords[:3])
            generated_images.extend(inline_images)
            
            # 4. Social sharing image
            social_image = await self.generate_social_image(title, niche, domain)
            if social_image:
                generated_images.append({
                    "type": "social",
                    "filename": social_image["filename"],
                    "url": social_image["url"],
                    "alt_text": f"Share: {title}",
                    "position": "meta"
                })
            
            # Store generated images info
            await self.store_generated_images(domain, title, generated_images)
            
            self.log_info(f"Generated {len(generated_images)} images for '{title}'")
            return generated_images
            
        except Exception as e:
            self.log_error(f"Failed to generate images for article: {e}")
            return []
    
    async def generate_hero_image(self, title: str, niche: str, size_key: str) -> Optional[Dict[str, Any]]:
        """Article hero resmi oluştur"""
        try:
            size = self.image_sizes[size_key]
            design = self.design_templates[niche]
            
            # Create image
            img = Image.new('RGB', size, color=design["colors"][0])
            draw = ImageDraw.Draw(img)
            
            # Add gradient background
            await self.add_gradient_background(img, design["colors"][:3])
            
            # Add title text (mobile-optimized)
            await self.add_mobile_title_text(draw, title, size, design)
            
            # Add design elements
            await self.add_design_elements(img, draw, niche, "hero")
            
            # Save image
            filename = f"hero_{hashlib.md5(title.encode()).hexdigest()[:8]}.jpg"
            filepath = self.output_path / filename
            
            # Optimize for mobile (smaller file size)
            img = img.convert('RGB')
            img.save(filepath, 'JPEG', quality=85, optimize=True)
            
            return {
                "filename": filename,
                "url": f"/images/{filename}",
                "size": size,
                "type": "hero"
            }
            
        except Exception as e:
            self.log_error(f"Failed to generate hero image: {e}")
            return None
    
    async def generate_pinterest_images(self, title: str, niche: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """Pinterest için optimize edilmiş resimler (mobile-first)"""
        pinterest_images = []
        
        try:
            design = self.design_templates[niche]
            
            # 2:3 ratio for mobile Pinterest (600x900)
            mobile_size = self.image_sizes["pinterest_mobile"]
            
            # Generate 3 different Pinterest variations
            variations = [
                {"style": "list", "bg": "gradient"},
                {"style": "quote", "bg": "clean"},
                {"style": "tip", "bg": "professional"}
            ]
            
            for i, variation in enumerate(variations):
                img = Image.new('RGB', mobile_size, color=design["colors"][0])
                draw = ImageDraw.Draw(img)
                
                # Background
                await self.add_pinterest_background(img, design, variation["bg"])
                
                # Title optimized for mobile viewing
                await self.add_pinterest_title(draw, title, mobile_size, design, variation["style"])
                
                # Add Pinterest-specific elements
                await self.add_pinterest_elements(img, draw, niche, keywords[:2], variation["style"])
                
                # Add branding (subtle)
                await self.add_mobile_branding(draw, mobile_size, design)
                
                # Save optimized for Pinterest
                filename = f"pinterest_{niche}_{i+1}_{hashlib.md5(title.encode()).hexdigest()[:8]}.jpg"
                filepath = self.output_path / filename
                
                # High quality for Pinterest (mobile users zoom in)
                img = img.convert('RGB')
                img.save(filepath, 'JPEG', quality=90, optimize=True)
                
                pinterest_images.append({
                    "type": "pinterest",
                    "filename": filename,
                    "url": f"/images/{filename}",
                    "alt_text": f"Pinterest: {title}",
                    "size": mobile_size,
                    "variation": variation["style"],
                    "optimized_for": "mobile"
                })
            
            return pinterest_images
            
        except Exception as e:
            self.log_error(f"Failed to generate Pinterest images: {e}")
            return []
    
    async def generate_inline_images(self, title: str, niche: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """Article içi resimler (mobile-responsive)"""
        inline_images = []
        
        try:
            design = self.design_templates[niche]
            size = self.image_sizes["article_inline"]
            
            for i, keyword in enumerate(keywords):
                img = Image.new('RGB', size, color=design["colors"][1])
                draw = ImageDraw.Draw(img)
                
                # Simple, clean design for article content
                await self.add_clean_background(img, design["colors"])
                
                # Keyword-focused content
                await self.add_keyword_focus(draw, keyword, size, design)
                
                # Mobile-optimized elements
                await self.add_inline_elements(img, draw, niche, keyword)
                
                filename = f"inline_{niche}_{i+1}_{hashlib.md5(keyword.encode()).hexdigest()[:8]}.jpg"
                filepath = self.output_path / filename
                
                img = img.convert('RGB')
                img.save(filepath, 'JPEG', quality=85, optimize=True)
                
                inline_images.append({
                    "type": "inline",
                    "filename": filename,
                    "url": f"/images/{filename}",
                    "alt_text": f"Guide to {keyword}",
                    "keyword": keyword,
                    "position": f"section_{i+1}"
                })
            
            return inline_images
            
        except Exception as e:
            self.log_error(f"Failed to generate inline images: {e}")
            return []
    
    async def add_gradient_background(self, img: Image.Image, colors: List[str]):
        """Gradient background ekle"""
        width, height = img.size
        
        # Create gradient
        for y in range(height):
            ratio = y / height
            if ratio < 0.5:
                # Top half
                blend_ratio = ratio * 2
                r1, g1, b1 = self.hex_to_rgb(colors[0])
                r2, g2, b2 = self.hex_to_rgb(colors[1])
            else:
                # Bottom half
                blend_ratio = (ratio - 0.5) * 2
                r1, g1, b1 = self.hex_to_rgb(colors[1])
                r2, g2, b2 = self.hex_to_rgb(colors[2])
            
            r = int(r1 + (r2 - r1) * blend_ratio)
            g = int(g1 + (g2 - g1) * blend_ratio)
            b = int(b1 + (b2 - b1) * blend_ratio)
            
            # Draw line
            draw = ImageDraw.Draw(img)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    async def add_mobile_title_text(self, draw: ImageDraw.Draw, title: str, size: tuple, design: Dict[str, Any]):
        """Mobile için optimize edilmiş title text"""
        width, height = size
        
        # Font size based on screen size
        font_size = min(48, width // 12)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Word wrap for mobile
        words = title.split()
        lines = []
        current_line = ""
        max_width = width - 100  # Padding
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Center text vertically
        total_height = len(lines) * font_size * 1.2
        start_y = (height - total_height) // 2
        
        # Draw text with shadow for mobile readability
        for i, line in enumerate(lines):
            y = start_y + i * font_size * 1.2
            x = 50  # Left margin
            
            # Shadow
            draw.text((x + 2, y + 2), line, font=font, fill="rgba(0,0,0,0.3)")
            # Main text
            draw.text((x, y), line, font=font, fill="white")
    
    async def add_pinterest_title(self, draw: ImageDraw.Draw, title: str, size: tuple, design: Dict[str, Any], style: str):
        """Pinterest için özel title layout (mobile-optimized)"""
        width, height = size
        
        # Pinterest'te mobile'da daha büyük fontlar daha iyi
        font_size = 52 if style == "list" else 46
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Pinterest için özel word wrapping
        words = title.split()
        lines = []
        current_line = ""
        max_width = width - 80  # Pinterest mobile padding
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Pinterest'te üst kısım daha etkili
        start_y = 120
        
        # High contrast for mobile
        for i, line in enumerate(lines):
            y = start_y + i * font_size * 1.1
            x = 40
            
            # Strong shadow for mobile readability
            draw.text((x + 3, y + 3), line, font=font, fill="rgba(0,0,0,0.6)")
            # Bright main text
            draw.text((x, y), line, font=font, fill="white")
    
    async def add_mobile_branding(self, draw: ImageDraw.Draw, size: tuple, design: Dict[str, Any]):
        """Mobile için subtle branding"""
        width, height = size
        
        # Small branding at bottom
        try:
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            small_font = ImageFont.load_default()
        
        branding_text = "Expert Guide"
        x = width - 150
        y = height - 60
        
        # Subtle branding
        draw.text((x, y), branding_text, font=small_font, fill="rgba(255,255,255,0.7)")
    
    async def add_pinterest_background(self, img: Image.Image, design: Dict[str, Any], bg_type: str):
        """Pinterest için background"""
        if bg_type == "gradient":
            await self.add_gradient_background(img, design["colors"][:3])
        elif bg_type == "clean":
            # Solid color with texture
            img.paste(design["colors"][0], (0, 0, img.width, img.height))
        else:
            # Professional gradient
            await self.add_gradient_background(img, [design["colors"][0], design["colors"][1], design["colors"][2]])
    
    async def add_pinterest_elements(self, img: Image.Image, draw: ImageDraw.Draw, niche: str, keywords: List[str], style: str):
        """Pinterest için özel elementler"""
        width, height = img.size
        
        if style == "list" and keywords:
            # List style elements
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            except:
                font = ImageFont.load_default()
            
            start_y = height // 2 + 50
            for i, keyword in enumerate(keywords[:3]):
                y = start_y + i * 50
                draw.text((60, y), f"• {keyword.title()}", font=font, fill="white")
        
        elif style == "quote":
            # Quote marks
            try:
                quote_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
            except:
                quote_font = ImageFont.load_default()
            
            draw.text((50, height//2 + 100), '"', font=quote_font, fill="rgba(255,255,255,0.3)")
            draw.text((width-100, height//2 + 200), '"', font=quote_font, fill="rgba(255,255,255,0.3)")
    
    async def add_design_elements(self, img: Image.Image, draw: ImageDraw.Draw, niche: str, image_type: str):
        """Niche'e göre design elementleri"""
        width, height = img.size
        design = self.design_templates[niche]
        
        # Simple geometric elements for mobile clarity
        if niche == "finance":
            # Simple chart bars
            bar_width = 20
            for i in range(3):
                x = width - 150 + i * 30
                bar_height = 50 + i * 30
                y = height - 100 - bar_height
                draw.rectangle([x, y, x + bar_width, height - 100], fill="rgba(255,255,255,0.3)")
        
        elif niche == "technology":
            # Simple tech grid
            for i in range(3):
                for j in range(3):
                    x = width - 120 + i * 25
                    y = height - 120 + j * 25
                    draw.rectangle([x, y, x + 15, y + 15], fill="rgba(255,255,255,0.2)")
        
        # Add more niche-specific elements as needed
    
    async def add_clean_background(self, img: Image.Image, colors: List[str]):
        """Clean background for inline images"""
        # Light gradient
        await self.add_gradient_background(img, [colors[3], colors[4], "white"])
    
    async def add_keyword_focus(self, draw: ImageDraw.Draw, keyword: str, size: tuple, design: Dict[str, Any]):
        """Keyword odaklı content"""
        width, height = size
        
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        # Keyword as main text
        x = 50
        y = height // 2 - 50
        
        draw.text((x, y), keyword.title(), font=title_font, fill=design["colors"][0])
        draw.text((x, y + 50), "Complete Guide", font=subtitle_font, fill=design["colors"][1])
    
    async def add_inline_elements(self, img: Image.Image, draw: ImageDraw.Draw, niche: str, keyword: str):
        """Inline image elementleri"""
        # Simple, clean elements that work well in articles
        pass
    
    async def generate_social_image(self, title: str, niche: str, domain: str) -> Optional[Dict[str, Any]]:
        """Social sharing için resim"""
        try:
            size = self.image_sizes["social_share"]
            design = self.design_templates[niche]
            
            img = Image.new('RGB', size, color=design["colors"][0])
            draw = ImageDraw.Draw(img)
            
            # Social sharing optimized layout
            await self.add_gradient_background(img, design["colors"][:2])
            await self.add_social_title(draw, title, size, design)
            await self.add_social_branding(draw, domain, size, design)
            
            filename = f"social_{hashlib.md5(title.encode()).hexdigest()[:8]}.jpg"
            filepath = self.output_path / filename
            
            img = img.convert('RGB')
            img.save(filepath, 'JPEG', quality=90, optimize=True)
            
            return {
                "filename": filename,
                "url": f"/images/{filename}",
                "size": size,
                "type": "social"
            }
            
        except Exception as e:
            self.log_error(f"Failed to generate social image: {e}")
            return None
    
    async def add_social_title(self, draw: ImageDraw.Draw, title: str, size: tuple, design: Dict[str, Any]):
        """Social media için title"""
        width, height = size
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        except:
            font = ImageFont.load_default()
        
        # Center the title
        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Shadow
        draw.text((x + 2, y + 2), title, font=font, fill="rgba(0,0,0,0.3)")
        # Main text
        draw.text((x, y), title, font=font, fill="white")
    
    async def add_social_branding(self, draw: ImageDraw.Draw, domain: str, size: tuple, design: Dict[str, Any]):
        """Social media için branding"""
        width, height = size
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Domain at bottom
        x = 50
        y = height - 80
        
        draw.text((x, y), domain, font=font, fill="rgba(255,255,255,0.8)")
    
    async def store_generated_images(self, domain: str, title: str, images: List[Dict[str, Any]]):
        """Üretilen resimleri kaydet"""
        image_data = {
            "domain": domain,
            "title": title,
            "images": images,
            "generated_at": datetime.now().isoformat(),
            "total_count": len(images)
        }
        
        # Store in Redis
        key = f"generated_images:{domain}:{hashlib.md5(title.encode()).hexdigest()[:8]}"
        self.redis_client.set(key, json.dumps(image_data), ex=86400 * 7)  # 7 days
        
        # Add to domain's image list
        self.redis_client.lpush(f"domain_images:{domain}", key)
        self.redis_client.ltrim(f"domain_images:{domain}", 0, 999)  # Keep last 1000
    
    def hex_to_rgb(self, hex_color: str) -> tuple:
        """Hex color'u RGB'ye çevir"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def log_info(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] IMAGE-GEN: {message}")
    
    def log_error(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] IMAGE-GEN ERROR: {message}")

async def main():
    """Image Generator Worker"""
    generator = AutoImageGenerator()
    
    print("🎨 Auto Image Generator started")
    print("📱 Optimized for mobile Pinterest users")
    
    while True:
        try:
            # Check for image generation requests
            request = generator.redis_client.rpop("image_generation_queue")
            
            if request:
                request_data = json.loads(request)
                print(f"🖼️ Generating images for: {request_data.get('title', 'Unknown')}")
                
                images = await generator.generate_article_images(request_data)
                
                if images:
                    print(f"✅ Generated {len(images)} images")
                    
                    # Update content with generated images
                    generator.redis_client.lpush("content_update_queue", json.dumps({
                        "domain": request_data["domain"],
                        "title": request_data["title"],
                        "images": images,
                        "type": "add_images"
                    }))
                else:
                    print("❌ Failed to generate images")
            
            await asyncio.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"❌ Image Generator error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
