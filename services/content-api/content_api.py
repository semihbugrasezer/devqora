import os, json, re
from flask import Flask, request, jsonify

CONTENT_ROOT = os.environ.get("CONTENT_ROOT","/content")
app = Flask(__name__)

def slugify(s):
    import re
    s = re.sub(r'[^a-zA-Z0-9\- ]', '', (s or '')).strip().lower()
    s = re.sub(r'\s+', '-', s)
    return s[:80] or 'post'

@app.post("/ingest")
def ingest():
    data = request.get_json(force=True)
    domain = data.get("domain"); title  = data.get("title")
    body   = data.get("body",""); slug   = data.get("slug") or slugify(title)
    
    if not domain or not title: 
        return {"ok":False,"error":"domain and title required"},400
    
    site_dir = os.path.join(CONTENT_ROOT, domain, "src", "pages", "articles")
    os.makedirs(site_dir, exist_ok=True)
    page_path = os.path.join(site_dir, f"{slug}.astro")
    
    # Choose layout and niche based on domain
    if domain == "hing.me":
        layout = "ModernBase"
        niche = "finance"
        logo_emoji = "💰"
        site_name = "Hing.me"
        tagline = "Your Smart Finance Guide"
    else:
        layout = "ModernBase"
        niche = "tech"
        logo_emoji = "🎮"
        site_name = "PlayU.co"
        tagline = "Your Ultimate Gaming & Entertainment Hub"
    
    astro = f"""---
import {layout} from '@mdkit/shared/src/layouts/{layout}.astro'
import ModernAdSlot from '@mdkit/shared/src/components/ModernAdSlot.astro'
import domains from '../../config.json'
const cfg = domains['{domain}']
const title = {json.dumps(title)}
const desc = {json.dumps(body[:160])}
---
<{layout} title={{title}} description={{desc}} locale={{cfg.locale}} adsenseClient={{cfg.adsense_client}} niche="{niche}">
  <!-- Hero Section -->
  <section style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); padding: 60px 0;">
    <div class="container">
      <h1 style="font-size: clamp(28px, 4vw, 48px); font-weight: 800; color: #0f172a; margin-bottom: 20px; line-height: 1.2;">
        {{title}}
      </h1>
      <p style="font-size: 18px; color: #64748b; max-width: 700px; line-height: 1.6; margin-bottom: 24px;">
        Latest insights and expert analysis
      </p>
      <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(34, 197, 94, 0.1); padding: 8px 16px; border-radius: 50px; font-size: 14px; color: #16a34a; font-weight: 500;">
        <span>✅</span>
        Expert Verified Content
      </div>
    </div>
  </section>

  <!-- Header Ad -->
  <div class="container">
    <ModernAdSlot client={{cfg.adsense_client}} slot={{cfg.adsense_slots.header}} layout="header" />
  </div>

  <!-- Article Content -->
  <section style="padding: 80px 0;">
    <div class="container">
      <div style="max-width: 800px; margin: 0 auto;">
        <article style="background: white; padding: 48px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); line-height: 1.7; font-size: 16px; color: #374151;">
          {body}
        </article>
        
        <!-- In-Article Ad -->
        <div style="margin: 48px 0;">
          <ModernAdSlot client={{cfg.adsense_client}} slot={{cfg.adsense_slots.in_article}} layout="in-article" />
        </div>
        
        <!-- Related Actions -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 24px; margin-top: 48px;">
          <div style="background: linear-gradient(135deg, #2563eb, #1d4ed8); padding: 32px; border-radius: 12px; text-align: center; color: white;">
            <div style="font-size: 32px; margin-bottom: 16px;">🧮</div>
            <h3 style="font-size: 18px; font-weight: 600; margin-bottom: 12px;">Free Calculator</h3>
            <p style="opacity: 0.9; font-size: 14px; margin-bottom: 20px;">Professional tools & analysis</p>
            <a href="/calculators" style="background: rgba(255,255,255,0.2); color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 500; display: inline-block; backdrop-filter: blur(10px);">
              Use Tools →
            </a>
          </div>
          
          <div style="background: linear-gradient(135deg, #16a34a, #15803d); padding: 32px; border-radius: 12px; text-align: center; color: white;">
            <div style="font-size: 32px; margin-bottom: 16px;">📚</div>
            <h3 style="font-size: 18px; font-weight: 600; margin-bottom: 12px;">Expert Guides</h3>
            <p style="opacity: 0.9; font-size: 14px; margin-bottom: 20px;">In-depth analysis & tips</p>
            <a href="/articles" style="background: rgba(255,255,255,0.2); color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 500; display: inline-block; backdrop-filter: blur(10px);">
              Read More →
            </a>
          </div>
          
          <div style="background: linear-gradient(135deg, #dc2626, #b91c1c); padding: 32px; border-radius: 12px; text-align: center; color: white;">
            <div style="font-size: 32px; margin-bottom: 16px;">💡</div>
            <h3 style="font-size: 18px; font-weight: 600; margin-bottom: 12px;">Pro Tips</h3>
            <p style="opacity: 0.9; font-size: 14px; margin-bottom: 20px;">Advanced strategies</p>
            <a href="/guides" style="background: rgba(255,255,255,0.2); color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 500; display: inline-block; backdrop-filter: blur(10px);">
              Learn Now →
            </a>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Footer Ad -->
  <div class="container">
    <ModernAdSlot client={{cfg.adsense_client}} slot={{cfg.adsense_slots.footer}} layout="footer" />
  </div>
</{layout}>"""
    
    with open(page_path, "w", encoding="utf-8") as f: 
        f.write(astro)
    return {"ok": True, "page": f"/articles/{slug}"}

@app.get("/health")
def health(): 
    return {"ok": True}

if __name__ == "__main__": 
    app.run(host="0.0.0.0", port=5055)
