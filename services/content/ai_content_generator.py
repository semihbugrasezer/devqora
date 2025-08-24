# /srv/auto-adsense/services/content/ai_content_generator.py
import os
import json
import time
import redis
import asyncio
import aiohttp
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import hashlib
import random
import re

class AIContentGenerator:
    """AI ile Profesyonel İçerik Üretimi (DeepSeek + Claude + Ücretsiz AI'lar)"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        
        # AI API Configurations
        self.ai_providers = {
            "deepseek": {
                "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
                "base_url": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",
                "cost_per_1k": 0.001,  # Çok ucuz
                "max_tokens": 4000,
                "priority": 1  # En yüksek öncelik
            },
            "claude": {
                "api_key": os.getenv("CLAUDE_API_KEY", ""),
                "base_url": "https://api.anthropic.com/v1",
                "model": "claude-3-haiku-20240307",
                "cost_per_1k": 0.0025,
                "max_tokens": 4000,
                "priority": 2
            },
            "groq": {
                "api_key": os.getenv("GROQ_API_KEY", ""),
                "base_url": "https://api.groq.com/openai/v1",
                "model": "llama3-8b-8192",
                "cost_per_1k": 0.0,  # Ücretsiz
                "max_tokens": 4000,
                "priority": 3
            },
            "huggingface": {
                "api_key": os.getenv("HUGGINGFACE_API_KEY", ""),
                "base_url": "https://api-inference.huggingface.co/models",
                "model": "microsoft/DialoGPT-large",
                "cost_per_1k": 0.0,  # Ücretsiz
                "max_tokens": 2000,
                "priority": 4
            }
        }
        
        # Content quality templates
        self.content_prompts = {
            "comprehensive_guide": """
Write a comprehensive, professional article about "{topic}" in the {niche} niche.

Requirements:
- 2000+ words, high-quality content
- Mobile-friendly formatting
- SEO optimized with natural keyword integration
- Value-focused, not promotional
- Include practical examples and actionable advice
- Write in an expert, authoritative tone
- Use clear headings and subheadings
- Include introduction, main content sections, and conclusion

Article Title: {title}
Main Topic: {main_topic}
Sub-topic: {sub_topic}
Target Keywords: {keywords}

Structure the article with:
1. Engaging introduction that hooks the reader
2. Clear explanation of concepts
3. Step-by-step guides where applicable
4. Best practices and expert tips
5. Common mistakes to avoid
6. Real-world examples or case studies
7. Tools and resources recommendations
8. Future trends or considerations
9. Actionable conclusion

Write naturally, avoid keyword stuffing, and focus on providing genuine value to readers interested in {topic}.
""",
            
            "beginner_tutorial": """
Create a beginner-friendly tutorial about "{topic}" in the {niche} field.

Requirements:
- 1500+ words, easy to understand
- Step-by-step instructions
- No jargon or assume prior knowledge
- Include practical examples
- Mobile-optimized formatting
- Encouraging and supportive tone

Article Title: {title}
Main Focus: {main_topic}
Specific Area: {sub_topic}
Keywords to include naturally: {keywords}

Structure:
1. Welcome introduction explaining what they'll learn
2. Basic concepts explained simply
3. Prerequisites (if any)
4. Step-by-step tutorial with clear instructions
5. Common beginner mistakes and how to avoid them
6. Next steps and progression path
7. Helpful resources for continued learning
8. Encouraging conclusion

Make it accessible, practical, and valuable for complete beginners.
""",
            
            "expert_analysis": """
Write an expert-level analysis article about "{topic}" in the {niche} industry.

Requirements:
- 2500+ words, in-depth analysis
- Professional, authoritative tone
- Data-driven insights where possible
- Advanced strategies and techniques
- Industry trends and future predictions
- Original insights and unique perspectives

Article Title: {title}
Primary Focus: {main_topic}
Specific Analysis: {sub_topic}
Key Terms: {keywords}

Include:
1. Executive summary
2. Current state analysis
3. Advanced strategies and methodologies
4. Industry trends and patterns
5. Expert predictions and insights
6. Case studies or real-world applications
7. Recommendations for professionals
8. Future outlook and implications

Write for industry professionals and serious enthusiasts who want deep, actionable insights.
""",
            
            "problem_solving": """
Create a comprehensive problem-solving guide for "{topic}" in {niche}.

Requirements:
- 1800+ words focused on solutions
- Problem-solution format
- Practical, actionable advice
- Multiple approaches for different situations
- Clear, solution-oriented structure

Article Title: {title}
Main Problem Area: {main_topic}
Specific Issue: {sub_topic}
Related Terms: {keywords}

Structure:
1. Problem identification and common symptoms
2. Root cause analysis
3. Multiple solution approaches
4. Step-by-step implementation guides
5. Tools and resources needed
6. Troubleshooting common issues
7. Prevention strategies
8. When to seek professional help
9. Success metrics and evaluation

Focus on practical solutions that readers can implement immediately.
"""
        }
        
        # Niche-specific content guidelines
        self.niche_guidelines = {
            "finance": {
                "tone": "professional, trustworthy, informative",
                "focus": "practical financial advice, data-driven insights, risk considerations",
                "avoid": "get-rich-quick schemes, financial advice without disclaimers",
                "include": "examples, calculations, real-world scenarios"
            },
            "technology": {
                "tone": "technical but accessible, innovative, forward-thinking",
                "focus": "practical implementation, latest trends, technical depth",
                "avoid": "overly complex jargon, outdated information",
                "include": "code examples, tool recommendations, step-by-step guides"
            },
            "gaming": {
                "tone": "enthusiastic, knowledgeable, community-focused",
                "focus": "strategies, reviews, community insights, practical tips",
                "avoid": "toxic gaming culture, excessive promotion",
                "include": "gameplay examples, community perspectives, practical strategies"
            },
            "health": {
                "tone": "caring, evidence-based, professional",
                "focus": "science-backed information, practical wellness tips",
                "avoid": "medical advice, unsubstantiated claims",
                "include": "research references, practical tips, holistic approaches"
            },
            "business": {
                "tone": "professional, strategic, results-focused",
                "focus": "actionable business strategies, case studies, ROI-focused",
                "avoid": "vague business speak, unrealistic promises",
                "include": "case studies, metrics, implementation frameworks"
            }
        }
        
        self.log_info("AI Content Generator initialized with multiple providers")
    
    async def generate_ai_article(self, article_request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """AI ile article üret"""
        try:
            main_topic = article_request["main_topic"]
            sub_topic = article_request["sub_topic"]
            title = article_request["title"]
            niche = article_request["niche"]
            angle = article_request.get("angle", "comprehensive_guide")
            domain = article_request["domain"]
            keywords = article_request.get("keywords", [])
            
            # AI provider seç (önceliğe göre)
            provider = await self.select_ai_provider()
            
            if not provider:
                self.log_error("No AI provider available")
                return None
            
            # Content prompt hazırla
            prompt = await self.prepare_content_prompt(
                main_topic, sub_topic, title, niche, angle, keywords
            )
            
            # AI'den content üret
            content = await self.call_ai_provider(provider, prompt, niche)
            
            if not content:
                # Fallback provider dene
                for fallback_name in ["groq", "huggingface"]:
                    if fallback_name in self.ai_providers and fallback_name != provider["name"]:
                        self.log_info(f"Trying fallback provider: {fallback_name}")
                        content = await self.call_ai_provider(
                            {**self.ai_providers[fallback_name], "name": fallback_name}, 
                            prompt, niche
                        )
                        if content:
                            break
            
            if not content:
                self.log_error("All AI providers failed")
                return None
            
            # Content'i optimize et
            optimized_content = await self.optimize_content(content, keywords, niche)
            
            # Article metadata oluştur
            article_data = {
                "domain": domain,
                "title": title,
                "body": optimized_content,
                "main_topic": main_topic,
                "sub_topic": sub_topic,
                "niche": niche,
                "keywords": keywords,
                "author": f"{niche.title()} AI Expert",
                "publish_date": datetime.now().isoformat(),
                "ai_provider": provider["name"],
                "content_quality": "ai_generated_high_quality",
                "word_count": len(optimized_content.split()),
                "reading_time": f"{max(1, len(optimized_content.split()) // 200)} min read",
                "seo_optimized": True,
                "mobile_friendly": True
            }
            
            # Usage'ı kaydet
            await self.record_ai_usage(provider["name"], len(optimized_content.split()))
            
            self.log_info(f"Generated {article_data['word_count']} word article with {provider['name']}")
            return article_data
            
        except Exception as e:
            self.log_error(f"Failed to generate AI article: {e}")
            return None
    
    async def select_ai_provider(self) -> Optional[Dict[str, Any]]:
        """En uygun AI provider'ı seç"""
        try:
            # Provider'ları öncelik ve kullanılabilirliğe göre sırala
            available_providers = []
            
            for name, config in self.ai_providers.items():
                if config["api_key"]:  # API key varsa
                    # Usage limitlerini kontrol et
                    daily_usage = await self.get_daily_usage(name)
                    
                    # Ücretsiz provider'lar için daily limit
                    if config["cost_per_1k"] == 0 and daily_usage > 50:  # 50 article/day limit
                        continue
                    
                    available_providers.append({
                        **config,
                        "name": name,
                        "daily_usage": daily_usage
                    })
            
            if not available_providers:
                return None
            
            # Önceliğe göre sırala
            available_providers.sort(key=lambda x: x["priority"])
            
            return available_providers[0]
            
        except Exception as e:
            self.log_error(f"Failed to select AI provider: {e}")
            return None
    
    async def prepare_content_prompt(self, main_topic: str, sub_topic: str, title: str, 
                                   niche: str, angle: str, keywords: List[str]) -> str:
        """Content prompt hazırla"""
        try:
            # Template seç
            prompt_template = self.content_prompts.get(angle, self.content_prompts["comprehensive_guide"])
            
            # Niche guidelines ekle
            guidelines = self.niche_guidelines.get(niche, self.niche_guidelines["technology"])
            
            # Prompt'u hazırla
            prompt = prompt_template.format(
                topic=f"{main_topic} - {sub_topic}",
                title=title,
                main_topic=main_topic,
                sub_topic=sub_topic,
                niche=niche,
                keywords=", ".join(keywords[:5])
            )
            
            # Niche-specific guidelines ekle
            prompt += f"\n\nContent Guidelines for {niche}:\n"
            prompt += f"- Tone: {guidelines['tone']}\n"
            prompt += f"- Focus on: {guidelines['focus']}\n"
            prompt += f"- Avoid: {guidelines['avoid']}\n"
            prompt += f"- Include: {guidelines['include']}\n"
            
            prompt += "\n\nIMPORTANT: Write original, valuable content that helps readers. Avoid promotional language and focus on education and practical value."
            
            return prompt
            
        except Exception as e:
            self.log_error(f"Failed to prepare prompt: {e}")
            return ""
    
    async def call_ai_provider(self, provider: Dict[str, Any], prompt: str, niche: str) -> Optional[str]:
        """AI provider'dan content al"""
        try:
            provider_name = provider["name"]
            
            if provider_name == "deepseek":
                return await self.call_deepseek(provider, prompt)
            elif provider_name == "claude":
                return await self.call_claude(provider, prompt)
            elif provider_name == "groq":
                return await self.call_groq(provider, prompt)
            elif provider_name == "huggingface":
                return await self.call_huggingface(provider, prompt)
            
        except Exception as e:
            self.log_error(f"Failed to call {provider['name']}: {e}")
        
        return None
    
    async def call_deepseek(self, provider: Dict[str, Any], prompt: str) -> Optional[str]:
        """DeepSeek API çağrısı"""
        try:
            headers = {
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": provider["model"],
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert content writer who creates high-quality, SEO-optimized articles. Write engaging, informative content that provides real value to readers."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": provider["max_tokens"],
                "temperature": 0.7,
                "top_p": 0.9,
                "stream": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{provider['base_url']}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        return content.strip()
                    else:
                        error_text = await response.text()
                        self.log_error(f"DeepSeek API error {response.status}: {error_text}")
            
        except Exception as e:
            self.log_error(f"DeepSeek API call failed: {e}")
        
        return None
    
    async def call_claude(self, provider: Dict[str, Any], prompt: str) -> Optional[str]:
        """Claude API çağrısı"""
        try:
            headers = {
                "x-api-key": provider['api_key'],
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": provider["model"],
                "max_tokens": provider["max_tokens"],
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{provider['base_url']}/messages",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result["content"][0]["text"]
                        return content.strip()
                    else:
                        error_text = await response.text()
                        self.log_error(f"Claude API error {response.status}: {error_text}")
            
        except Exception as e:
            self.log_error(f"Claude API call failed: {e}")
        
        return None
    
    async def call_groq(self, provider: Dict[str, Any], prompt: str) -> Optional[str]:
        """Groq API çağrısı (ücretsiz, hızlı)"""
        try:
            headers = {
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": provider["model"],
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional content writer specializing in creating valuable, engaging articles."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": provider["max_tokens"],
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{provider['base_url']}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        return content.strip()
                    else:
                        error_text = await response.text()
                        self.log_error(f"Groq API error {response.status}: {error_text}")
            
        except Exception as e:
            self.log_error(f"Groq API call failed: {e}")
        
        return None
    
    async def call_huggingface(self, provider: Dict[str, Any], prompt: str) -> Optional[str]:
        """Hugging Face API çağrısı (ücretsiz)"""
        try:
            headers = {
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json"
            }
            
            # Prompt'u kısalt (HuggingFace limitleri için)
            short_prompt = prompt[:1000] if len(prompt) > 1000 else prompt
            
            payload = {
                "inputs": short_prompt,
                "parameters": {
                    "max_length": provider["max_tokens"],
                    "temperature": 0.7,
                    "do_sample": True,
                    "top_p": 0.9
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{provider['base_url']}/{provider['model']}",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        if isinstance(result, list) and len(result) > 0:
                            content = result[0].get("generated_text", "")
                            # Input prompt'u çıkar
                            if content.startswith(short_prompt):
                                content = content[len(short_prompt):].strip()
                            return content
                    else:
                        error_text = await response.text()
                        self.log_error(f"HuggingFace API error {response.status}: {error_text}")
            
        except Exception as e:
            self.log_error(f"HuggingFace API call failed: {e}")
        
        return None
    
    async def optimize_content(self, content: str, keywords: List[str], niche: str) -> str:
        """Content'i SEO ve mobil için optimize et"""
        try:
            # Markdown formatting ekle
            optimized = content
            
            # Header'ları düzenle
            lines = optimized.split('\n')
            formatted_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    formatted_lines.append('')
                    continue
                
                # Ana başlıkları tespit et ve formatla
                if any(keyword in line.lower() for keyword in ['introduction', 'conclusion', 'getting started']):
                    formatted_lines.append(f"## {line}")
                elif line.endswith(':') and len(line) < 100:
                    formatted_lines.append(f"### {line}")
                elif line.startswith(('1.', '2.', '3.', '4.', '5.')):
                    formatted_lines.append(f"### {line}")
                else:
                    formatted_lines.append(line)
            
            optimized = '\n'.join(formatted_lines)
            
            # Mobil için paragraf kısaltma
            paragraphs = optimized.split('\n\n')
            mobile_optimized = []
            
            for para in paragraphs:
                if len(para) > 400:  # Uzun paragrafları böl
                    sentences = para.split('. ')
                    current_para = ""
                    
                    for sentence in sentences:
                        if len(current_para + sentence) < 300:
                            current_para += sentence + ". "
                        else:
                            mobile_optimized.append(current_para.strip())
                            current_para = sentence + ". "
                    
                    if current_para.strip():
                        mobile_optimized.append(current_para.strip())
                else:
                    mobile_optimized.append(para)
            
            optimized = '\n\n'.join(mobile_optimized)
            
            # Call-to-action ekle (subtle)
            cta_templates = {
                "finance": "Ready to improve your financial strategy? Explore our other financial guides for more expert insights.",
                "technology": "Want to stay updated with the latest tech trends? Check out our other technology articles.",
                "gaming": "Level up your gaming skills with our comprehensive gaming guides and strategies.",
                "health": "Transform your health journey with our evidence-based wellness guides.",
                "business": "Accelerate your business success with our proven strategies and expert insights."
            }
            
            cta = cta_templates.get(niche, "Explore our other expert guides for more valuable insights.")
            optimized += f"\n\n---\n\n*{cta}*"
            
            return optimized
            
        except Exception as e:
            self.log_error(f"Failed to optimize content: {e}")
            return content
    
    async def get_daily_usage(self, provider_name: str) -> int:
        """Günlük kullanım miktarını al"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            usage_key = f"ai_usage:{provider_name}:{today}"
            usage = self.redis_client.get(usage_key)
            return int(usage) if usage else 0
        except:
            return 0
    
    async def record_ai_usage(self, provider_name: str, word_count: int):
        """AI kullanımını kaydet"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            usage_key = f"ai_usage:{provider_name}:{today}"
            
            # Günlük usage increment et
            self.redis_client.incr(usage_key)
            self.redis_client.expire(usage_key, 86400)  # 24 saat
            
            # Word count kaydet
            word_key = f"ai_words:{provider_name}:{today}"
            self.redis_client.incrby(word_key, word_count)
            self.redis_client.expire(word_key, 86400)
            
            self.log_info(f"Recorded usage: {provider_name} - {word_count} words")
            
        except Exception as e:
            self.log_error(f"Failed to record AI usage: {e}")
    
    async def get_ai_stats(self) -> Dict[str, Any]:
        """AI kullanım istatistiklerini al"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            stats = {}
            
            for provider_name in self.ai_providers.keys():
                usage_key = f"ai_usage:{provider_name}:{today}"
                word_key = f"ai_words:{provider_name}:{today}"
                
                usage = self.redis_client.get(usage_key) or 0
                words = self.redis_client.get(word_key) or 0
                
                stats[provider_name] = {
                    "daily_requests": int(usage),
                    "daily_words": int(words),
                    "cost_estimate": int(words) * self.ai_providers[provider_name]["cost_per_1k"] / 1000
                }
            
            return stats
            
        except Exception as e:
            self.log_error(f"Failed to get AI stats: {e}")
            return {}
    
    def log_info(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] AI-CONTENT: {message}")
    
    def log_error(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] AI-CONTENT ERROR: {message}")

async def main():
    """AI Content Generator Worker"""
    generator = AIContentGenerator()
    
    print("🤖 AI Content Generator started")
    print("📝 Using DeepSeek, Claude, Groq, and HuggingFace APIs")
    
    # Günlük istatistikleri göster
    stats = await generator.get_ai_stats()
    for provider, data in stats.items():
        if data["daily_requests"] > 0:
            print(f"📊 {provider}: {data['daily_requests']} requests, {data['daily_words']} words, ${data['cost_estimate']:.4f}")
    
    while True:
        try:
            # AI content generation requests'leri kontrol et
            request = generator.redis_client.rpop("ai_content_queue")
            
            if request:
                request_data = json.loads(request)
                title = request_data.get("title", "Unknown")
                
                print(f"🤖 Generating AI content: {title}")
                
                article_data = await generator.generate_ai_article(request_data)
                
                if article_data:
                    print(f"✅ Generated {article_data['word_count']} words with {article_data['ai_provider']}")
                    
                    # Content API'ye gönder
                    response = requests.post(
                        "http://content-api:5055/ingest",
                        json=article_data,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        print(f"📄 Article published successfully")
                        
                        # Resim üretimi tetikle
                        generator.redis_client.lpush("nano_banana_queue", json.dumps({
                            "domain": article_data["domain"],
                            "title": article_data["title"],
                            "main_topic": article_data["main_topic"],
                            "sub_topic": article_data["sub_topic"],
                            "niche": article_data["niche"],
                            "keywords": article_data["keywords"],
                            "type": "ai_article_images"
                        }))
                        
                    else:
                        print(f"❌ Failed to publish article: {response.status_code}")
                else:
                    print("❌ Failed to generate AI content")
            
            await asyncio.sleep(10)  # 10 saniyede bir kontrol et
            
        except Exception as e:
            print(f"❌ AI Content Generator error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
