#!/usr/bin/env python3
"""
Content Scheduler - 100% Otomatik İçerik Pipeline
- AI ile subtitle üretimi
- Makale oluşturma 
- Resim üretimi ve ekleme
- Otomatik deploy
- Pinterest pinleme
"""

import os
import json
import time
import redis
import asyncio
import requests
import schedule
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List
import threading
import subprocess

class ContentScheduler:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        self.domains = ["hing.me", "playu.co"]
        self.niches = {
            "hing.me": {
                "main": "technology",
                "subtopics": ["ai", "blockchain", "mobile", "web development", "cybersecurity", "gadgets", "software"],
                "language": "tr",
                "country": "TR"
            },
            "playu.co": {
                "main": "gaming", 
                "subtopics": ["mobile games", "pc gaming", "console", "esports", "game reviews", "gaming setup"],
                "language": "en",
                "country": "US"
            }
        }
        
        self.running = False
        print("🎯 Content Scheduler initialized")
    
    def start_scheduler(self):
        """Scheduler'ı başlat"""
        self.running = True
        
        # Her gün farklı saatlerde content üretimi
        schedule.every().day.at("09:30").do(self.trigger_content_cycle)
        schedule.every().day.at("14:15").do(self.trigger_content_cycle) 
        schedule.every().day.at("17:45").do(self.trigger_content_cycle)
        schedule.every().day.at("20:20").do(self.trigger_content_cycle)
        
        print("⏰ Content scheduler started - 4 daily cycles")
        print("🕘 Schedule: 09:30, 14:15, 17:45, 20:20")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                print("📱 Scheduler stopped by user")
                break
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
                time.sleep(300)  # 5 minutes on error
    
    def trigger_content_cycle(self):
        """Tam otomatik content döngüsü başlat"""
        try:
            print("🚀 Starting automated content cycle...")
            
            # Random domain seç (organic görünüm için)
            domain = random.choice(self.domains)
            niche_config = self.niches[domain]
            
            print(f"🌐 Selected domain: {domain}")
            print(f"📂 Niche: {niche_config['main']}")
            
            # 1. AI ile subtitle oluştur
            subtitle = self.generate_ai_subtitle(domain, niche_config)
            
            if not subtitle:
                print("❌ Failed to generate subtitle")
                return
            
            print(f"📝 Generated subtitle: {subtitle}")
            
            # 2. Content pipeline başlat
            self.execute_content_pipeline(domain, subtitle, niche_config)
            
        except Exception as e:
            print(f"❌ Content cycle error: {e}")
    
    def generate_ai_subtitle(self, domain: str, niche_config: Dict) -> str:
        """AI ile akıllı subtitle üretimi"""
        try:
            # Random subtopic seç
            subtopic = random.choice(niche_config["subtopics"])
            
            # AI prompt hazırla
            prompt_templates = {
                "technology": [
                    f"Write a catchy blog post title about {subtopic} that would rank well on Google",
                    f"Create an engaging title for a {subtopic} article that tech enthusiasts would click",
                    f"Generate a SEO-friendly title about {subtopic} for a Turkish tech blog",
                    f"Write a compelling headline about {subtopic} trends in 2025"
                ],
                "gaming": [
                    f"Write an exciting blog post title about {subtopic} for gamers",
                    f"Create a clickable title for a {subtopic} guide or review",
                    f"Generate a trending title about {subtopic} that gamers would share",
                    f"Write a catchy headline about {subtopic} for a gaming blog"
                ]
            }
            
            prompt = random.choice(prompt_templates[niche_config["main"]])
            
            # AI API çağrısı (Free APIs kullan)
            ai_response = self.call_ai_api(prompt, niche_config["language"])
            
            if ai_response:
                # Title'ı temizle ve optimize et
                subtitle = ai_response.strip().strip('"').strip("'")
                return subtitle
            
            # Fallback titles
            fallback_titles = {
                "technology": [
                    f"Latest {subtopic.title()} Trends You Should Know",
                    f"Complete Guide to {subtopic.title()} in 2025",
                    f"How {subtopic.title()} is Changing Technology",
                    f"Expert Tips for {subtopic.title()} Success"
                ],
                "gaming": [
                    f"Ultimate {subtopic.title()} Guide for Gamers", 
                    f"Best {subtopic.title()} Tips and Tricks",
                    f"Master {subtopic.title()}: Pro Strategies",
                    f"{subtopic.title()} Review: What You Need to Know"
                ]
            }
            
            return random.choice(fallback_titles[niche_config["main"]])
            
        except Exception as e:
            print(f"❌ AI subtitle generation error: {e}")
            return None
    
    def call_ai_api(self, prompt: str, language: str) -> str:
        """Free AI APIs ile title üretimi"""
        try:
            # Groq API (Free)
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    json={
                        "model": "llama3-8b-8192",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 100,
                        "temperature": 0.7
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
            
            # HuggingFace API (Free)
            hf_key = os.getenv("HUGGINGFACE_API_KEY")
            if hf_key:
                response = requests.post(
                    "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium",
                    headers={"Authorization": f"Bearer {hf_key}"},
                    json={"inputs": prompt},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        return result[0].get("generated_text", "")
            
        except Exception as e:
            print(f"❌ AI API call error: {e}")
        
        return None
    
    def execute_content_pipeline(self, domain: str, subtitle: str, niche_config: Dict):
        """Tam otomatik content pipeline"""
        try:
            print(f"🔄 Starting content pipeline for: {subtitle}")
            
            # 1. Makale üret
            article_data = self.generate_article(domain, subtitle, niche_config)
            
            if not article_data:
                print("❌ Article generation failed")
                return
            
            print(f"📄 Article generated: {len(article_data.get('content', ''))} chars")
            
            # 2. Resim üret ve ekle
            image_url = self.generate_and_add_image(article_data, subtitle)
            article_data["featured_image"] = image_url
            
            print(f"🖼️ Image generated: {image_url}")
            
            # 3. Website'e deploy et
            deploy_success = self.deploy_to_website(domain, article_data)
            
            if not deploy_success:
                print("❌ Website deployment failed")
                return
                
            print(f"🚀 Deployed to {domain}")
            
            # 4. Pinterest'e pin (delay ile)
            self.schedule_pinterest_pin(domain, article_data, delay_minutes=random.randint(30, 120))
            
            # 5. Analytics kaydet
            self.log_content_creation(domain, article_data)
            
            print("✅ Content pipeline completed successfully")
            
        except Exception as e:
            print(f"❌ Content pipeline error: {e}")
    
    def generate_article(self, domain: str, title: str, niche_config: Dict) -> Dict:
        """AI ile makale üretimi"""
        try:
            # Content API'ye makale üretimi talebi
            payload = {
                "domain": domain,
                "title": title,
                "niche": niche_config["main"],
                "language": niche_config["language"],
                "country": niche_config["country"],
                "auto_generate": True,
                "min_length": 1500,
                "max_length": 2500,
                "include_seo": True
            }
            
            response = requests.post(
                "http://content-api:5055/generate",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Content API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Article generation error: {e}")
            return None
    
    def generate_and_add_image(self, article_data: Dict, title: str) -> str:
        """Resim üret ve makaleye ekle"""
        try:
            # Nano Banana API ile resim üretimi
            image_payload = {
                "prompt": f"Professional blog featured image for: {title}",
                "style": "modern",
                "size": "1200x630",
                "quality": "high"
            }
            
            response = requests.post(
                "http://nano-banana-generator:8080/generate",
                json=image_payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("image_url", "")
            else:
                print(f"❌ Image generation error: {response.status_code}")
                return ""
                
        except Exception as e:
            print(f"❌ Image generation error: {e}")
            return ""
    
    def deploy_to_website(self, domain: str, article_data: Dict) -> bool:
        """Cloudflare Pages'e otomatik deploy"""
        try:
            print(f"🚀 Deploying to Cloudflare Pages: {domain}")
            
            # Site path
            site_path = f"/srv/auto-adsense/multidomain_site_kit/sites/{domain}"
            
            # Article dosyası oluştur
            slug = self.create_slug(article_data["title"])
            article_path = f"{site_path}/src/pages/articles/{slug}.astro"
            
            # Article content hazırla
            article_content = self.create_astro_article(article_data, domain)
            
            # Dosyayı yaz
            os.makedirs(os.path.dirname(article_path), exist_ok=True)
            with open(article_path, 'w', encoding='utf-8') as f:
                f.write(article_content)
            
            print(f"📄 Article saved: {article_path}")
            
            # Site build et
            build_result = subprocess.run(
                ["pnpm", "build"], 
                cwd=site_path, 
                capture_output=True, 
                text=True,
                timeout=300
            )
            
            if build_result.returncode != 0:
                print(f"❌ Build failed: {build_result.stderr}")
                return False
            
            print(f"🔨 Build successful")
            
            # Cloudflare Pages'e deploy
            project_name = domain.replace(".", "-")
            deploy_result = subprocess.run([
                "npx", "wrangler", "pages", "deploy", 
                f"{site_path}/dist",
                "--project-name", project_name,
                "--compatibility-date", "2025-01-01"
            ], capture_output=True, text=True, timeout=300)
            
            if deploy_result.returncode == 0:
                print(f"✅ Deployed successfully to {domain}")
                
                # Deploy URL'yi kaydet
                deploy_url = f"https://{project_name}.pages.dev"
                self.redis_client.set(f"last_deploy:{domain}", deploy_url)
                
                return True
            else:
                print(f"❌ Deploy failed: {deploy_result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Deploy error: {e}")
            return False
    
    def create_slug(self, title: str) -> str:
        """SEO-friendly slug oluştur"""
        import re
        
        # Türkçe karakterleri dönüştür
        char_map = {
            'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
            'Ç': 'c', 'Ğ': 'g', 'İ': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u'
        }
        
        slug = title.lower()
        for tr_char, en_char in char_map.items():
            slug = slug.replace(tr_char, en_char)
        
        # Özel karakterleri temizle
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        
        return slug[:100]  # Max 100 karakter
    
    def create_astro_article(self, article_data: Dict, domain: str) -> str:
        """Astro article template oluştur"""
        
        template = f"""---
import Base from '@mdkit/shared/src/layouts/Base.astro'
import AdSlot from '@mdkit/shared/src/components/AdSlot.astro'
import domains from '../../config.json'

const cfg = domains['{domain}']
const title = "{article_data['title']}"
const description = "{article_data.get('description', article_data['title'][:150])}"
const publishDate = new Date('{datetime.now().isoformat()}')
const featuredImage = "{article_data.get('featured_image', '')}"
---

<Base title={{title}} description={{description}} locale={{cfg.locale}} adsenseClient={{cfg.adsense_client}}>
  <article class="max-w-4xl mx-auto px-4 py-8">
    <!-- Header -->
    <header class="mb-8">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">{{title}}</h1>
      <div class="flex items-center text-gray-600 text-sm mb-4">
        <time datetime={{publishDate.toISOString()}}>
          {{publishDate.toLocaleDateString('tr-TR')}}
        </time>
      </div>
      
      {{featuredImage && (
        <img 
          src={{featuredImage}} 
          alt={{title}}
          class="w-full h-64 md:h-96 object-cover rounded-lg shadow-lg mb-6"
          loading="lazy"
        />
      )}}
    </header>
    
    <!-- AdSense - Header -->
    <AdSlot client={{cfg.adsense_client}} slot={{cfg.adsense_slots.header}} />
    
    <!-- Article Content -->
    <div class="prose prose-lg max-w-none">
{article_data.get('content', '')}
    </div>
    
    <!-- AdSense - In Article -->
    <div class="my-8">
      <AdSlot client={{cfg.adsense_client}} slot={{cfg.adsense_slots.in_article}} />
    </div>
    
    <!-- Article Footer -->
    <footer class="mt-12 pt-8 border-t border-gray-200">
      <div class="text-sm text-gray-600">
        <p>Bu makale {domain} tarafından hazırlanmıştır.</p>
        <p>Son güncelleme: {{publishDate.toLocaleDateString('tr-TR')}}</p>
      </div>
    </footer>
    
    <!-- AdSense - Footer -->
    <AdSlot client={{cfg.adsense_client}} slot={{cfg.adsense_slots.footer}} />
  </article>
</Base>

<style>
  .prose {{
    @apply text-gray-800;
  }}
  
  .prose h2 {{
    @apply text-2xl font-bold text-gray-900 mt-8 mb-4;
  }}
  
  .prose h3 {{
    @apply text-xl font-semibold text-gray-900 mt-6 mb-3;
  }}
  
  .prose p {{
    @apply mb-4 leading-relaxed;
  }}
  
  .prose ul, .prose ol {{
    @apply mb-4 pl-6;
  }}
  
  .prose li {{
    @apply mb-2;
  }}
  
  .prose blockquote {{
    @apply border-l-4 border-blue-500 pl-4 italic text-gray-700 my-6;
  }}
  
  .prose img {{
    @apply rounded-lg shadow-md my-6;
  }}
  
  @media (max-width: 768px) {{
    .prose {{
      @apply text-base;
    }}
  }}
</style>
"""
        
        return template
    
    def schedule_pinterest_pin(self, domain: str, article_data: Dict, delay_minutes: int):
        """Pinterest pin'ini zamanla"""
        def pin_worker():
            time.sleep(delay_minutes * 60)  # Delay
            
            try:
                print(f"📌 Pinning to Pinterest: {article_data['title']}")
                
                pin_data = {
                    "domain": domain,
                    "title": article_data["title"],
                    "description": article_data.get("description", article_data["title"]),
                    "image_url": article_data.get("featured_image", ""),
                    "link_url": f"https://{domain}/articles/{self.create_slug(article_data['title'])}",
                    "auto_schedule": True
                }
                
                response = requests.post(
                    "http://tailwind-pinterest-worker:8080/pin",
                    json=pin_data,
                    timeout=60
                )
                
                if response.status_code == 200:
                    print(f"✅ Pinterest pin successful")
                    
                    # Pinterest pin analytics
                    self.redis_client.incr(f"pinterest_pins:{domain}:daily")
                    self.redis_client.incr("pinterest_pins:total")
                    
                else:
                    print(f"❌ Pinterest pin failed: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Pinterest pin error: {e}")
        
        # Background thread ile pin et
        pin_thread = threading.Thread(target=pin_worker)
        pin_thread.daemon = True
        pin_thread.start()
        
        print(f"⏱️ Pinterest pin scheduled for {delay_minutes} minutes")
    
    def log_content_creation(self, domain: str, article_data: Dict):
        """Content creation analytics"""
        try:
            # Redis'e analytics kaydet
            today = datetime.now().strftime("%Y-%m-%d")
            
            self.redis_client.incr(f"articles_created:{domain}:{today}")
            self.redis_client.incr(f"articles_created:{domain}:total") 
            self.redis_client.incr("articles_created:total")
            
            # Event log
            event_data = {
                "domain": domain,
                "title": article_data["title"],
                "type": "article_created",
                "timestamp": datetime.now().isoformat(),
                "chars": len(article_data.get("content", "")),
                "has_image": bool(article_data.get("featured_image"))
            }
            
            self.redis_client.lpush("content_events", json.dumps(event_data))
            self.redis_client.ltrim("content_events", 0, 999)  # Keep last 1000
            
            print(f"📊 Analytics logged for {domain}")
            
        except Exception as e:
            print(f"❌ Analytics logging error: {e}")

def main():
    """Scheduler başlatıcı"""
    try:
        scheduler = ContentScheduler()
        
        print("🎯 Starting Content Scheduler")
        print("⚡ Fully automated content pipeline")
        print("🔄 AI → Article → Image → Deploy → Pinterest")
        
        scheduler.start_scheduler()
        
    except Exception as e:
        print(f"❌ Scheduler failed to start: {e}")

if __name__ == "__main__":
    main()