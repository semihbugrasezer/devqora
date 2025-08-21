# Fully Automated, Multi-Domain AdSense System (Debian 12)

**Pinterest + Programmatic Content + n8n + Redis + Cloudflare Pages**  
**Goal:** Sleep-mode traffic engine that can scale from **2 domains** to **10+ domains** and maximize USD AdSense revenue in high-CPC niches.

> This guide is a single, copy-paste friendly **Markdown playbook**.  
> It uses **heredoc** blocks to generate all files directly on your server.  
> Assumes you run commands as **root**. If you’re not root, prefix commands with `sudo`.

---

## 0) Prerequisites (Docker, Node, pnpm, Wrangler)

```bash
# System update
apt update && apt -y upgrade

# Docker & Compose
apt -y install ca-certificates curl gnupg lsb-release
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
> /etc/apt/sources.list.d/docker.list
apt update
apt -y install docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker $USER  # re-login to use Docker without sudo

# Node 20 + pnpm + wrangler (for Cloudflare Pages)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt -y install nodejs
npm i -g pnpm wrangler
```

**DNS:** Create an A record for `n8n.your-domain.com` → server IP (ports **80/443** open).

---

## 1) CORE Stack (n8n + Redis + Content API + Pinterest Bot)

This brings up:

* **Traefik** (only exposes :80/:443, avoiding port conflicts)  
* **n8n** (workflows & schedulers)  
* **Redis** (queues)  
* **Content API** (writes `.astro` pages into your multi-domain repo)  
* **Pinterest bot** (keyword→image/description→pin jobs)

```bash
mkdir -p ~/auto_adsense_system/{services/pinbot,services/content-api,scripts}
cd ~/auto_adsense_system
```

### 1.1 `.env`

```bash
cat > .env << 'EOF'
TZ=Europe/Istanbul
DOMAINS=example.com,example-two.com
N8N_SUBDOMAIN=n8n.your-domain.com
EMAIL_FOR_TLS=admin@your-domain.com

# Optional (text/image generation)
OPENAI_API_KEY=
SD_API_BASE=http://sd:7860

# Optional (real posting)
PINTEREST_ACCESS_TOKEN=
PINTEREST_BOARD_ID=
TAILWIND_API_KEY=

REDIS_HOST=redis
REDIS_PORT=6379

# Bot behavior
DAILY_PIN_TARGET=6
DAILY_REPIN_TARGET=3
DAILY_COMMENT_TARGET=2
DAILY_FOLLOW_TARGET=2
DOMAIN_ROTATION=https://domain1.com,https://domain2.com
WINDOW_START=08:00
WINDOW_END=22:30
EOF
```

### 1.2 `docker-compose.yml`

```bash
cat > docker-compose.yml << 'EOF'
version: "3.9"
networks: { edge: { }, internal: { } }
volumes: { traefik_acme: {}, n8n_data: {}, redis_data: {}, content_data: {} }

services:
  traefik:
    image: traefik:v3.1
    command:
      - --api.dashboard=false
      - --providers.docker=true
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --certificatesresolvers.le.acme.httpchallenge=true
      - --certificatesresolvers.le.acme.httpchallenge.entrypoint=web
      - --certificatesresolvers.le.acme.email=${EMAIL_FOR_TLS}
      - --certificatesresolvers.le.acme.storage=/letsencrypt/acme.json
    ports: ["80:80","443:443"]
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_acme:/letsencrypt
    networks: [edge]
    restart: unless-stopped

  n8n:
    image: n8nio/n8n:latest
    environment:
      - TZ=${TZ}
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - N8N_HOST=${N8N_SUBDOMAIN}
      - N8N_PUBLIC_URL=https://${N8N_SUBDOMAIN}
      - WEBHOOK_URL=https://${N8N_SUBDOMAIN}
      - N8N_DIAGNOSTICS_ENABLED=false
    labels:
      - traefik.enable=true
      - traefik.http.routers.n8n.rule=Host(`${N8N_SUBDOMAIN}`)
      - traefik.http.routers.n8n.entrypoints=websecure
      - traefik.http.routers.n8n.tls.certresolver=le
      - traefik.http.services.n8n.loadbalancer.server.port=5678
    volumes: [ "n8n_data:/home/node/.n8n" ]
    depends_on: [redis]
    networks: [edge, internal]
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: ["redis-server","--appendonly","yes"]
    volumes: [ "redis_data:/data" ]
    networks: [internal]
    restart: unless-stopped

  # Content API (writes .astro pages into your site repo)
  content-api:
    build: ./services/content-api
    env_file: .env
    volumes:
      - /opt/multidomain_site_kit/sites:/content   # bind-mount to your site repo
    networks: [internal]
    restart: unless-stopped

  # Pinterest bot API & workers
  bot-api:
    build: ./services/pinbot
    env_file: .env
    networks: [internal]
    restart: unless-stopped
    command: ["python","/app/bot_api.py"]

  pin-worker:
    build: ./services/pinbot
    env_file: .env
    networks: [internal]
    restart: unless-stopped
    command: ["python","/app/pin_worker.py"]

  poster-worker:
    build: ./services/pinbot
    env_file: .env
    networks: [internal]
    restart: unless-stopped
    command: ["python","/app/poster_worker.py"]
EOF
```

### 1.3 Content API (Dockerfile + app)

```bash
cat > services/content-api/Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY content_api.py .
ENV CONTENT_ROOT=/content
CMD ["python","/app/content_api.py"]
EOF

cat > services/content-api/requirements.txt << 'EOF'
flask==3.0.3
EOF

cat > services/content-api/content_api.py << 'EOF'
import os, json, re
from flask import Flask, request, jsonify
CONTENT_ROOT = os.environ.get("CONTENT_ROOT","/content")
app = Flask(__name__)
def slugify(s):
    import re
    s = re.sub(r'[^a-zA-Z0-9\\- ]', '', (s or '')).strip().lower()
    s = re.sub(r'\\s+', '-', s)
    return s[:80] or 'post'
@app.post("/ingest")
def ingest():
    data = request.get_json(force=True)
    domain = data.get("domain"); title  = data.get("title")
    body   = data.get("body",""); slug   = data.get("slug") or slugify(title)
    if not domain or not title: return {"ok":False,"error":"domain and title required"},400
    site_dir = os.path.join(CONTENT_ROOT, domain, "src", "pages", "articles")
    os.makedirs(site_dir, exist_ok=True)
    page_path = os.path.join(site_dir, f"{slug}.astro")
    astro = f\"\"\"---
import Base from '@mdkit/shared/src/layouts/Base.astro'
import AdSlot from '@mdkit/shared/src/components/AdSlot.astro'
import domains from '../../config.json'
const cfg = domains['{domain}']
const title = {json.dumps(title)}
const desc = {json.dumps(body[:160])}
---
<Base title={{title}} description={{desc}} locale={{cfg.locale}} adsenseClient={{cfg.adsense_client}}>
  <h1>{{title}}</h1>
  <AdSlot client={{cfg.adsense_client}} slot={{cfg.adsense_slots.in_article}} />
  <article>
    {body}
  </article>
</Base>
\"\"\"
    with open(page_path, "w", encoding="utf-8") as f: f.write(astro)
    return {"ok": True, "page": f"/articles/{slug}"}
@app.get("/health")
def health(): return {"ok": True}
if __name__ == "__main__": app.run(host="0.0.0.0", port=5055)
EOF
```

### 1.4 Pinterest bot (Dockerfile + workers)

```bash
cat > services/pinbot/Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py /app/
CMD ["python","/app/bot_api.py"]
EOF

cat > services/pinbot/requirements.txt << 'EOF'
redis==5.0.8
requests==2.32.3
pillow==10.4.0
python-dotenv==1.0.1
flask==3.0.3
EOF

cat > services/pinbot/bot_api.py << 'EOF'
import os, json, redis
from flask import Flask, request, jsonify
r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), port=int(os.getenv("REDIS_PORT","6379")), decode_responses=True)
app = Flask(__name__)
@app.get("/health")
def health(): return {"ok": True}
@app.post("/enqueue/keyword")
def enqueue_keyword():
    kw = request.get_json(force=True).get("keyword")
    if not kw: return {"ok": False, "error":"keyword required"}, 400
    r.lpush("keyword_queue", kw); return {"ok": True, "queued": kw}
@app.get("/stats")
def stats():
    return {"keyword_queue": r.llen("keyword_queue"), "pin_jobs": r.llen("pin_jobs"), "reports": r.llen("reports")}
if __name__ == "__main__": app.run(host="0.0.0.0", port=5001)
EOF

cat > services/pinbot/generate_text.py << 'EOF'
import random
def draft_description(keyword: str) -> str:
    templates = [
        f"{keyword} quick and practical guide—see full details on the blog.",
        f"We collected the most effective methods for {keyword}. Full list in the article.",
        f"{keyword}: common mistakes and fixes, neatly summarized."
    ]
    return random.choice(templates)
def pick_hashtags(keyword: str):
    base = keyword.lower().replace(" ","")
    return [f"#{base}", "#guide", "#howto"]
EOF

cat > services/pinbot/generate_image.py << 'EOF'
from PIL import Image, ImageDraw, ImageFont
import os, time
def make_pin_image(text: str, out_path: str, size=(1000,1500)):
    img = Image.new("RGB", size, (255,255,255))
    d = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("DejaVuSans.ttf", 56)
    except: font = ImageFont.load_default()
    words = text.split(); lines=[]; line=""
    for w in words:
        if len(line + " " + w) < 22: line += (" " if line else "") + w
        else: lines.append(line); line = w
    if line: lines.append(line)
    y=120
    for ln in lines[:9]:
        d.text((80,y), ln, fill=(0,0,0), font=font); y+=80
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "JPEG", quality=90); return out_path
EOF

cat > services/pinbot/pin_worker.py << 'EOF'
import os, json, time, random, datetime, redis
from generate_text import draft_description, pick_hashtags
from generate_image import make_pin_image
r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), port=int(os.getenv("REDIS_PORT","6379")), decode_responses=True)
DOMAIN_ROTATION = [d.strip() for d in os.getenv("DOMAIN_ROTATION","").split(",") if d.strip()]
WINDOW_START = os.getenv("WINDOW_START","08:00"); WINDOW_END = os.getenv("WINDOW_END","22:30")
def in_window():
    now = datetime.datetime.now().time()
    s_h,s_m = map(int, WINDOW_START.split(":")); e_h,e_m = map(int, WINDOW_END.split(":"))
    start_t = datetime.time(s_h,s_m); end_t = datetime.time(e_h,e_m)
    return (start_t <= now <= end_t) if start_t <= end_t else (now >= start_t or now <= end_t)
def schedule_delay(): return random.randint(600, 2400)
def build_job(keyword: str):
    desc = draft_description(keyword); tags = pick_hashtags(keyword)
    link = random.choice(DOMAIN_ROTATION) if DOMAIN_ROTATION else "https://example.com"
    out_img = f"/tmp/pin_{int(time.time())}.jpg"; make_pin_image(keyword, out_img)
    return {"keyword": keyword, "description": desc, "hashtags": tags, "image_path": out_img, "target_url": link}
while True:
    try:
        if not in_window(): time.sleep(60); continue
        if random.random() < 0.3: time.sleep(60); continue
        kw = r.rpop("keyword_queue")
        if not kw: time.sleep(30); continue
        job = build_job(kw); r.lpush("pin_jobs", json.dumps(job))
        r.lpush("reports", json.dumps({"ts": time.time(), "event": "enqueued", "kw": kw}))
    except Exception as e:
        r.lpush("reports", json.dumps({"ts": time.time(), "event": "error", "error": str(e)}))
    time.sleep(schedule_delay())
EOF

cat > services/pinbot/poster_worker.py << 'EOF'
import os, json, time, random, redis
r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), port=int(os.getenv("REDIS_PORT","6379")), decode_responses=True)
def post_to_tailwind(job):
    # TODO: Replace with real Tailwind API call.
    time.sleep(random.randint(2,5)); return {"status":"ok","id":f"tw_{int(time.time())}"}
def post_to_pinterest(job):
    # TODO: Replace with real Pinterest Publishing API call.
    time.sleep(random.randint(2,5)); return {"status":"ok","id":f"pin_{int(time.time())}"}
USE_TAILWIND = bool(os.getenv("TAILWIND_API_KEY"))
while True:
    job_raw = r.rpop("pin_jobs")
    if not job_raw: time.sleep(10); continue
    job = json.loads(job_raw)
    res = post_to_tailwind(job) if USE_TAILWIND else post_to_pinterest(job)
    r.lpush("reports", json.dumps({"event":"posted","res":res,"job":job,"ts":time.time()}))
    time.sleep(random.randint(20,80))
EOF
```

### 1.5 Health script

```bash
cat > scripts/health.sh << 'EOF'
#!/usr/bin/env bash
set -e
docker compose ps
docker compose logs -n 50 content-api bot-api pin-worker poster-worker | tail -n 200 || true
EOF
chmod +x scripts/health.sh
```

### 1.6 Demo n8n workflow (import file)

```bash
cat > n8n_workflow_demo.json << 'EOF'
{
  "name": "Daily Seed → Keywords → Enqueue + Content Ingest",
  "nodes": [
    { "parameters": { "triggerTimes": [ { "mode": "everyDay", "hour": 9 } ] }, "id": "cron", "name": "Cron", "type": "n8n-nodes-base.cron", "typeVersion": 2, "position": [200,300] },
    { "parameters": { "url": "https://api.publicapis.org/entries", "responseFormat": "json" }, "id": "http", "name": "Fetch Seed (demo)", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4, "position": [450,300] },
    { "parameters": { "functionCode": "const out=[]; for (let i=0;i<10;i++){ out.push({ json: { keyword: $json.entries[i].API + ' guide' }});} return out;" }, "id": "func", "name": "Build Keywords", "type": "n8n-nodes-base.function", "typeVersion": 2, "position": [700,300] },
    { "parameters": { "url": "http://bot-api:5001/enqueue/keyword", "responseFormat": "json" }, "id": "enqueue", "name": "Enqueue Keyword", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4, "position": [950,300] },
    { "parameters": { "url": "http://content-api:5055/ingest", "responseFormat": "json" }, "id": "ingest", "name": "Create Article (demo)", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4, "position": [950,480] }
  ],
  "connections": {
    "Cron": { "main": [ [ { "node": "Fetch Seed (demo)", "type": "main", "index": 0 } ] ] },
    "Fetch Seed (demo)": { "main": [ [ { "node": "Build Keywords", "type": "main", "index": 0 } ] ] },
    "Build Keywords": { "main": [ [ { "node": "Enqueue Keyword", "type": "main", "index": 0 }, { "node": "Create Article (demo)", "type": "main", "index": 0 } ] ] }
  },
  "active": false
}
EOF
```

### 1.7 Bring CORE up

```bash
docker compose up -d --build
bash scripts/health.sh
# All containers should be "running".
```

**n8n UI:** open `https://n8n.your-domain.com` (create admin on first run).  
**Import** the `n8n_workflow_demo.json`. In **Create Article (demo)** set `"domain": "yourdomain.com"`.

---

## 2) Multi-Domain SSG (Astro) + Cloudflare Pages

This repo hosts **all sites**: `sites/<domain>` with shared components.

```bash
mkdir -p /opt/multidomain_site_kit
chown -R $USER:$USER /opt/multidomain_site_kit
cd /opt/multidomain_site_kit
```

### 2.1 Shared package & config

```bash
mkdir -p packages/shared/src/{components,layouts} config sites scripts tools
```

**`config/domains.json`**

```bash
cat > config/domains.json << 'EOF'
{
  "playu.co": {
    "locale": "en-US",
    "country": "US",
    "adsense_client": "ca-pub-SIZIN-ADSENSE-ID",
    "adsense_slots": { "header": "HEADER-SLOT", "in_article": "ARTICLE-SLOT", "footer": "FOOTER-SLOT" },
    "title": "PlayU - Finance Guides and Calculation Tools",
    "description": "Credit, mortgage, investment calculators and practical finance guides.",
    "theme_color": "#3b82f6",
    "keywords": ["finance", "credit", "mortgage", "calculator", "investment", "money"]
  },
  "example.com": {
    "locale": "en-US",
    "country": "US",
    "adsense_client": "ca-pub-XXXXXXX",
    "adsense_slots": { "header": "111", "in_article": "112", "footer": "113" },
    "title": "Example Finance Guides",
    "description": "Clear guides and calculators for finance decisions."
  }
}
EOF
```

**AdSense slot component**

```bash
cat > packages/shared/src/components/AdSlot.astro << 'EOF'
---
const { client, slot } = Astro.props;
---
<div style="min-height: 280px; display: block; margin: 16px 0;">
  <ins class="adsbygoogle"
       style="display:block"
       data-ad-client={client}
       data-ad-slot={slot}
       data-ad-format="auto"
       data-full-width-responsive="true"></ins>
  <script>
    (adsbygoogle = window.adsbygoogle || []).push({});
  </script>
</div>
EOF
```

**Base layout**

```bash
cat > packages/shared/src/layouts/Base.astro << 'EOF'
---
const { title, description, locale, adsenseClient } = Astro.props;
---
<html lang={locale}>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <meta name="description" content={description} />
    <script async src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${adsenseClient}`} crossorigin="anonymous"></script>
    <style>
      body { margin:0; font-family:system-ui,-apple-system,sans-serif; line-height:1.6; }
      .container { max-width:900px; margin:0 auto; padding:0 16px; }
      header { background:#f8f9fa; border-bottom:1px solid #e9ecef; padding:12px 0; }
      .nav { display:flex; flex-wrap:wrap; gap:8px 16px; }
      .nav a { color:#495057; text-decoration:none; padding:4px 8px; border-radius:4px; }
      .nav a:hover { background:#e9ecef; }
      main { padding:24px 0; }
      footer { background:#f8f9fa; color:#6c757d; text-align:center; padding:24px 0; margin-top:48px; }
      @media (max-width:768px) {
        .container { padding:0 12px; }
        main { padding:16px 0; }
        .nav { font-size:14px; }
      }
    </style>
  </head>
  <body>
    <header>
      <div class="container">
        <nav class="nav">
          <a href="/">🏠 Home</a>
          <a href="/calculators/mortgage">🏠 Mortgage</a>
          <a href="/calculators/loan">💰 Loan</a>
          <a href="/articles">📰 Guides</a>
        </nav>
      </div>
    </header>
    <main>
      <div class="container">
        <slot />
      </div>
    </main>
    <footer>
      <div class="container">
        © <script>document.write(new Date().getFullYear())</script> — PlayU Finance Rehberleri
      </div>
    </footer>
  </body>
</html>
EOF
```

**Shared package.json**

```bash
cat > packages/shared/package.json << 'EOF'
{ "name": "@mdkit/shared", "version": "0.0.1", "type": "module" }
EOF
```

### 2.2 Scaffold 2 example domains (replace with yours anytime)

```bash
for D in example.com example-two.com; do
  mkdir -p sites/$D/src/{pages/articles,layouts,content}
  cp config/domains.json sites/$D/src/config.json

  cat > sites/$D/package.json << 'JSON'
{
  "name": "site-DOMAIN",
  "version": "0.0.1",
  "private": true,
  "type": "module",
  "scripts": { "dev":"astro dev", "build":"astro build", "preview":"astro preview" },
  "dependencies": { "astro":"^4.10.0", "@mdkit/shared":"file:../../packages/shared" }
}
JSON
  sed -i "s/site-DOMAIN/site-$D/" sites/$D/package.json

  cat > sites/$D/astro.config.mjs << EOF
import { defineConfig } from 'astro/config'
export default defineConfig({ site: 'https://$D' })
EOF

  cat > sites/$D/src/pages/index.astro << EOF
---
import Base from '@mdkit/shared/src/layouts/Base.astro'
import AdSlot from '@mdkit/shared/src/components/AdSlot.astro'
import domains from '../config.json'
const cfg = domains['$D']
---
<Base title={cfg.title} description={cfg.description} locale={cfg.locale} adsenseClient={cfg.adsense_client}>
  <h1>$D</h1>
  <p>Welcome! Fresh calculators, comparisons, and practical guides.</p>
  <AdSlot client={cfg.adsense_client} slot={cfg.adsense_slots.header} />
  <ul>
    <li><a href="/articles/hello-auto">Hello Auto Site</a></li>
    <li><a href="/calculators/mortgage">Mortgage Calculator</a></li>
    <li><a href="/calculators/loan">Loan Estimator</a></li>
  </ul>
</Base>
EOF

  cat > sites/$D/src/pages/articles/hello-auto.astro << EOF
---
import Base from '@mdkit/shared/src/layouts/Base.astro'
import AdSlot from '@mdkit/shared/src/components/AdSlot.astro'
import domains from '../../config.json'
const cfg = domains['$D']; const title="Hello Automated Site"; const desc="Scaffolded page"
---
<Base title={title} description={desc} locale={cfg.locale} adsenseClient={cfg.adsense_client}>
  <h1>{title}</h1>
  <p>{desc}</p>
  <AdSlot client={cfg.adsense_client} slot={cfg.adsense_slots.in_article} />
  <p>Use Content API to create real articles.</p>
</Base>
EOF

  cat > sites/$D/src/pages/calculators/mortgage.astro << 'EOF2'
---
import Base from '@mdkit/shared/src/layouts/Base.astro'
import AdSlot from '@mdkit/shared/src/components/AdSlot.astro'
import domains from '../../config.json'
const cfg = domains[Object.keys(domains)[0]]
const title = "Mortgage Calculator"; const desc = "Estimate monthly payments quickly."
---
<Base title={title} description={desc} locale={cfg.locale} adsenseClient={cfg.adsense_client}>
  <h1>{title}</h1>
  <div id="app"></div>
  <script type="module">
    const el = document.getElementById('app')
    el.innerHTML = `
      <label>Amount <input id="amt" type="number" value="300000"></label>
      <label>APR % <input id="apr" type="number" value="5"></label>
      <label>Years <input id="yrs" type="number" value="30"></label>
      <div>Monthly: <b id="out"></b></div>`
    function calc(){
      const P = parseFloat(document.getElementById('amt').value||0)
      const r = parseFloat(document.getElementById('apr').value||0)/100/12
      const n = parseFloat(document.getElementById('yrs').value||0)*12
      const m = (r===0||n===0)?0:(P*r*Math.pow(1+r,n))/(Math.pow(1+r,n)-1)
      document.getElementById('out').textContent = m.toFixed(2)
    }
    ;['amt','apr','yrs'].forEach(id=>document.getElementById(id).addEventListener('input', calc)); calc()
  </script>
  <AdSlot client={cfg.adsense_client} slot={cfg.adsense_slots.footer} />
</Base>
EOF2

  cat > sites/$D/src/pages/calculators/loan.astro << 'EOF3'
---
import Base from '@mdkit/shared/src/layouts/Base.astro'
import AdSlot from '@mdkit/shared/src/components/AdSlot.astro'
import domains from '../../config.json'
const cfg = domains[Object.keys(domains)[0]]
const title = "Loan Payoff Estimator"; const desc = "Plan your payoff schedule easily."
---
<Base title={title} description={desc} locale={cfg.locale} adsenseClient={cfg.adsense_client}>
  <h1>{title}</h1>
  <div id="loan"></div>
  <script type="module">
    const el = document.getElementById('loan')
    el.innerHTML = `
      <label>Balance <input id="bal" type="number" value="15000"></label>
      <label>APR % <input id="apr2" type="number" value="18"></label>
      <label>Monthly Payment <input id="pay" type="number" value="400"></label>
      <div>Months to Zero: <b id="out2"></b></div>`
    function calc(){
      let B = parseFloat(document.getElementById('bal').value||0)
      const r = parseFloat(document.getElementById('apr2').value||0)/100/12
      const p = parseFloat(document.getElementById('pay').value||0)
      let months = 0
      while (B>0 && months < 600){ B = B*(1+r) - p; months++ }
      document.getElementById('out2').textContent = months >= 600 ? 'Too low payment' : months
    }
    ;['bal','apr2','pay'].forEach(id=>document.getElementById(id).addEventListener('input', calc)); calc()
  </script>
  <AdSlot client={cfg.adsense_client} slot={cfg.adsense_slots.footer} />
</Base>
EOF3

done
```

### 2.3 Build & first deploy (Cloudflare Pages)

```bash
for d in sites/*; do (cd "$d" && pnpm install && pnpm build); done

wrangler login
for d in sites/*; do
  DOMAIN=$(basename "$d")
  PROJECT=${DOMAIN//./-}
  npx wrangler pages deploy "$d/dist" --project-name "$PROJECT"
done
```

**ads.txt:** from your AdSense account, create `sites/<domain>/public/ads.txt`, then re-deploy.  
**Custom Domain:** add **CNAME** to the `*.pages.dev` domain for each project and bind it in Pages.

---

## 3) Wire CORE ↔ Sites & Automate

* The `docker-compose.yml` already bind-mounts `/opt/multidomain_site_kit/sites:/content` into Content API.  
* n8n imports **`n8n_workflow_demo.json`** → set `"domain":"yourdomain.com"` in the **Create Article (demo)** node.  
* (Optional) After Content API writes articles, add an **Execute Command** node to n8n to build & deploy:

```bash
bash /opt/multidomain_site_kit/scripts/build-all.sh && \
for d in /opt/multidomain_site_kit/sites/*; do \
  DOMAIN=$(basename "$d"); PROJECT=${DOMAIN//./-}; \
  npx wrangler pages deploy "$d/dist" --project-name "$PROJECT"; \
done
```

**Bring CORE up (or rebuild after edits):**

```bash
cd ~/auto_adsense_system
docker compose up -d --build
bash scripts/health.sh
```

---

## 4) Pinterest Bot: Anti-Spam Strategy & Real Posting

* `.env` → set `DOMAIN_ROTATION=https://domain1.com,https://domain2.com,...`  
* **Warm-up (first 2 weeks):** 3–5 pins/day, ~30% repins/comments/follows, random delays in `WINDOW_START/END`.  
* Replace mock functions in `poster_worker.py` with **Tailwind** or **Pinterest Publishing API**.

**Tailwind / Pinterest stubs (to replace):**

```python
def post_to_tailwind(job):
    # requests.post("https://api.tailwindapp.com/v1/pins", headers={...},
    #               files={"image": open(job["image_path"],"rb")},
    #               data={"board_id":..., "title": job["keyword"],
    #                     "link": job["target_url"], "notes": job["description"]})
    ...

def post_to_pinterest(job):
    # requests.post("https://api.pinterest.com/v5/pins", headers={...},
    #               json={"board_id":..., "title": job["keyword"],
    #                     "link": job["target_url"], "description": job["description"]})
    ...
```
```

**Logs / status:**

```bash
cd ~/auto_adsense_system
bash scripts/health.sh
# Look for "enqueued" and "posted" events.
```

---

## 5) Revenue Playbook (USD-focused, policy-safe)

* **High-CPC niches:** Finance, Insurance, Credit, Hosting/SaaS.  
* **Traffic funnel:** Pinterest → informative **How-to/Calculator page** → internal link → monetized article.  
* **Layouts:** Header + In-article + Footer ad slots (already built with CLS-safe heights).  
* **Programmatic content:** Use n8n to generate **3–5 articles/day per domain** (FAQ, comparisons, templates).  
* **A/B testing:** Create alternative templates (ad positions, intro length) to lift RPM.  
* **Diversify referrals:** Add Medium/Quora/Reddit/X drip posts in n8n with canonical back to your site.

---

## 6) Scale from 2 → 10+ Domains

Add a domain in minutes:

```bash
cd /opt/multidomain_site_kit
# Duplicate one site folder or re-run scaffold pattern with your new domain (manually or via a small script)
cp -r sites/example.com sites/new-highcpc.com
# Update /sites/new-highcpc.com/src/config.json and astro.config.mjs for the new domain
# Update config/domains.json with AdSense client & slots

# Build & deploy
(cd sites/new-highcpc.com && pnpm install && pnpm build)
DOMAIN=new-highcpc.com
PROJECT=${DOMAIN//./-}
npx wrangler pages deploy "sites/$DOMAIN/dist" --project-name "$PROJECT"
```

Then add it to rotation:

```bash
# Add the new domain to .env → DOMAIN_ROTATION
nano ~/auto_adsense_system/.env
docker compose up -d
```

---

## 7) Final Checklist (Path to 200,000 TRY+/mo)

* [ ] All domains live on Cloudflare Pages + `ads.txt` present  
* [ ] n8n workflow active (daily cron → keywords → Content API)  
* [ ] Auto build & deploy wired into n8n (or run periodically)  
* [ ] Pinterest bot enqueues & posts with randomized behavior  
* [ ] Funnel points to **informational page first**, then to high-CPC content  
* [ ] Ad placements render without CLS, visible in live pages  
* [ ] GA4 + AdSense connected; monitor CTR/RPM per domain  
* [ ] After week 2, increase pins/day & content volume; add new domains

---

## Notes & Compliance

* No one can **guarantee** income, but this architecture maximizes probability via high-CPC topics + multi-channel traffic + automation + iterative A/B tests.  
* Stay within **platform policies** (no click-baiting or incentive to click ads).  
* Keep **content quality** (tools, calculators, unique structure) to ensure SEO & platform trust.

---

### Quick Start TL;DR

```bash
# CORE
cd ~/auto_adsense_system
docker compose up -d --build

# SITES
cd /opt/multidomain_site_kit
for d in sites/*; do (cd "$d" && pnpm install && pnpm build); done
wrangler login
for d in sites/*; do DOMAIN=$(basename "$d"); PROJECT=${DOMAIN//./-}; npx wrangler pages deploy "$d/dist" --project-name "$PROJECT"; done

# n8n
open https://n8n.your-domain.com  # import workflow, set "domain", activate

# Check bot
cd ~/auto_adsense_system && bash scripts/health.sh
```
