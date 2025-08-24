# 🚀 Auto-AdSense Multi-Domain Automation System

> **Fully Automated, Multi-Domain AdSense System with Pinterest Integration, AI Content Generation, and Real-Time Analytics**

A sophisticated automation platform that generates high-CPC content, manages multiple domains, and maximizes AdSense revenue through intelligent Pinterest marketing and AI-powered content creation.

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Auto-AdSense System                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Caddy     │  │     n8n     │  │   Redis     │            │
│  │  (Reverse   │  │ (Workflows) │  │  (Queue)    │            │
│  │   Proxy)    │  │             │  │             │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Content   │  │   Pinterest │  │    AI       │            │
│  │     API     │  │     Bot     │  │  Content    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Analytics  │  │  AdSense    │  │   Image     │            │
│  │   Service   │  │  Manager    │  │ Generator   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Content    │  │   Auto      │  │  Security   │            │
│  │ Scheduler   │  │ Deployment  │  │  Scanner    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 Core Features

- **🤖 AI-Powered Content Generation** - DeepSeek, Claude, Groq, HuggingFace integration
- **📌 Pinterest Automation** - Real Pinterest API integration with Tailwind support
- **🌐 Multi-Domain Management** - Astro-based static sites with shared components
- **💰 AdSense Optimization** - Real-time revenue tracking and optimization
- **📊 Analytics Dashboard** - Google Search Console, AdSense, and custom metrics
- **🔒 Security Scanning** - Semgrep integration for code security
- **🚀 Auto-Deployment** - Cloudflare Pages integration
- **📱 Modern Dashboard** - Go-based web interface for system monitoring

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ with pnpm
- Cloudflare account (for domain deployment)
- Pinterest Developer access
- Google AdSense account

### 1. Clone and Setup

```bash
git clone <repository-url>
cd auto-adsense

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
nano .env
```

### 2. Start Core Services

```bash
# Start all services
docker compose up -d

# Check system health
bash scripts/health.sh

# View dashboard
open http://localhost:8090
```

### 3. Access Key Interfaces

- **Dashboard**: http://localhost:8090
- **n8n Workflows**: http://localhost:8091
- **Content API**: http://localhost:5055
- **Pinterest Bot**: http://localhost:5001

## 📁 Project Structure

```
auto-adsense/
├── 📁 services/                    # Microservices
│   ├── 📁 analytics/              # Real-time analytics & GSC integration
│   ├── 📁 auto-deployment/        # Cloudflare auto-deployment
│   ├── 📁 content/                # AI content generation
│   ├── 📁 content-api/            # Content ingestion API
│   ├── 📁 image-generation/       # AI image generation (Nano Banana)
│   ├── 📁 notifications/          # Alert system
│   ├── 📁 orchestrator/           # Content scheduling & orchestration
│   ├── 📁 pinbot/                 # Pinterest automation
│   ├── 📁 pinterest/              # Pinterest API integration
│   ├── 📁 security/               # Security scanning (Semgrep)
│   └── 📁 adsense/                # AdSense revenue management
├── 📁 multidomain_site_kit/       # Multi-domain site management
│   ├── 📁 sites/                  # Individual domain sites
│   │   ├── 📁 hing.me/           # Finance & Investment site
│   │   └── 📁 playu.co/          # Gaming & Entertainment site
│   ├── 📁 packages/               # Shared components
│   │   └── 📁 shared/            # Common layouts & components
│   ├── 📁 config/                 # Domain configurations
│   └── 📁 scripts/                # Build & deployment scripts
├── 📁 dashboard/                   # Go-based monitoring dashboard
├── 📁 workflows/                   # n8n workflow definitions
├── 📁 scripts/                     # System management scripts
├── 📁 backups/                     # System backups
├── 📄 docker-compose.yml          # Service orchestration
├── 📄 Caddyfile                   # Reverse proxy configuration
└── 📄 README.md                   # This file
```

## 🔧 Core Services

### 1. **Content API** (`services/content-api/`)
- **Purpose**: Ingests content and generates Astro pages
- **Features**: 
  - Automatic slug generation
  - Template-based page creation
  - Multi-domain support
- **Port**: 5055

### 2. **Pinterest Bot** (`services/pinbot/`)
- **Purpose**: Pinterest automation and content distribution
- **Features**:
  - Real Pinterest API integration
  - Tailwind support
  - Anti-spam algorithms
  - Image generation
- **Components**:
  - `bot_api.py` - Main API
  - `enhanced_tailwind_worker.py` - Tailwind integration
  - `real_pinterest_worker.py` - Pinterest posting
  - `nano_banana_api.py` - Free image generation

### 3. **AI Content Generator** (`services/content/`)
- **Purpose**: AI-powered content creation
- **Features**:
  - Multiple AI providers (DeepSeek, Claude, Groq)
  - Topic-focused generation
  - Anti-spam content strategies
  - High-CPC niche targeting

### 4. **Analytics Service** (`services/analytics/`)
- **Purpose**: Real-time analytics and reporting
- **Features**:
  - Google Search Console integration
  - AdSense revenue tracking
  - Custom metrics dashboard
  - Performance monitoring

### 5. **Auto-Deployment** (`services/auto-deployment/`)
- **Purpose**: Automatic domain deployment
- **Features**:
  - Cloudflare Pages integration
  - Build automation
  - Multi-domain deployment
  - CI/CD pipeline

### 6. **Security Scanner** (`services/security/`)
- **Purpose**: Code security and vulnerability scanning
- **Features**:
  - Semgrep integration
  - Automated security checks
  - Vulnerability reporting
  - Compliance monitoring

## 🌐 Multi-Domain Site Kit

### Site Structure
Each domain follows this structure:
```
sites/domain.com/
├── 📁 src/
│   ├── 📁 pages/          # Astro pages
│   ├── 📁 layouts/        # Custom layouts
│   └── 📁 content/        # Static content
├── 📄 package.json        # Dependencies
├── 📄 astro.config.mjs   # Astro configuration
└── 📄 config.json         # Domain-specific config
```

### Shared Components
- **Base Layout**: Common HTML structure with AdSense integration
- **AdSlot Component**: Responsive AdSense ad placement
- **Shared Utilities**: Common functions and helpers

### Configuration
Domain-specific settings in `config/domains.json`:
```json
{
  "domain.com": {
    "locale": "en-US",
    "country": "US",
    "adsense_client": "ca-pub-XXXXXXX",
    "adsense_slots": {
      "header": "111",
      "in_article": "112",
      "footer": "113"
    },
    "title": "Site Title",
    "description": "Site Description"
  }
}
```

## 🔄 Workflow Automation

### n8n Workflows
1. **Daily Content Generator** (`workflows/daily-content-generator.json`)
   - Triggers daily at 9:00 AM
   - Generates high-CPC keywords
   - Creates AI-generated content
   - Enqueues Pinterest pins
   - Ingests content via API

2. **Pinterest Accelerator** (`workflows/pinterest-accelerator.json`)
   - Pinterest automation workflows
   - Content scheduling
   - Engagement optimization

### Content Pipeline
```
Keyword Generation → AI Content → Content API → Astro Pages → Build → Deploy
       ↓
Pinterest Queue → Image Generation → Pin Creation → Posting → Analytics
```

## 📊 Dashboard

### Features
- **Real-time Monitoring**: Service status and health checks
- **Analytics Dashboard**: Revenue, traffic, and performance metrics
- **System Management**: Service control and configuration
- **Security Overview**: Vulnerability reports and compliance status

### Access
- **Local**: http://localhost:8090
- **External**: Configured via Caddy reverse proxy

## 🚀 Deployment

### Local Development
```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f [service-name]

# Rebuild service
docker compose up -d --build [service-name]
```

### Production Deployment
```bash
# Build all sites
cd multidomain_site_kit
bash scripts/build-all.sh

# Deploy to Cloudflare
bash scripts/quick-deploy.sh

# Backup system
bash scripts/quick-backup.sh
```

### Domain Management
```bash
# Add new domain
# 1. Copy existing site folder
cp -r sites/example.com sites/newdomain.com

# 2. Update configuration
nano sites/newdomain.com/src/config.json
nano config/domains.json

# 3. Build and deploy
cd sites/newdomain.com && pnpm build
npx wrangler pages deploy dist --project-name newdomain
```

## 🔧 Configuration

### Environment Variables
Key configuration in `.env`:
```bash
# Core settings
TZ=Europe/Istanbul
DOMAINS=domain1.com,domain2.com
N8N_SUBDOMAIN=n8n.yourdomain.com

# API Keys
OPENAI_API_KEY=your_key
PINTEREST_ACCESS_TOKEN=your_token
TAILWIND_API_KEY=your_key

# Bot behavior
DAILY_PIN_TARGET=6
DAILY_REPIN_TARGET=3
WINDOW_START=08:00
WINDOW_END=22:30
```

### Service Configuration
- **Redis**: Queue management and caching
- **Caddy**: Reverse proxy and SSL termination
- **n8n**: Workflow automation and scheduling

## 📈 Revenue Optimization

### High-CPC Niches
- Finance & Investment
- Insurance & Credit
- Business & SaaS
- Health & Wellness
- Technology & Hosting

### Content Strategy
- **Calculator Pages**: Interactive tools for user engagement
- **Comparison Content**: Product/service comparisons
- **How-to Guides**: Step-by-step tutorials
- **FAQ Pages**: Common questions and answers

### Ad Placement
- **Header**: Above-the-fold visibility
- **In-Article**: Contextual relevance
- **Footer**: Additional monetization
- **Sidebar**: Complementary content

## 🔒 Security Features

- **Code Scanning**: Semgrep integration for vulnerability detection
- **Container Security**: Docker security best practices
- **Network Isolation**: Internal/external network separation
- **Access Control**: Role-based dashboard access
- **Audit Logging**: Comprehensive activity tracking

## 📚 API Documentation

### Content API
```http
POST /ingest
Content-Type: application/json

{
  "domain": "domain.com",
  "title": "Article Title",
  "body": "Article content...",
  "slug": "optional-slug"
}
```

### Pinterest Bot API
```http
POST /enqueue/keyword
Content-Type: application/json

{
  "keyword": "mortgage calculator guide"
}
```

### Analytics API
```http
GET /stats
GET /revenue
GET /traffic
```

## 🛠️ Development

### Adding New Services
1. Create service directory in `services/`
2. Add Dockerfile and requirements
3. Update `docker-compose.yml`
4. Add to service dependencies

### Custom Workflows
1. Create workflow in n8n
2. Export to `workflows/` directory
3. Configure triggers and nodes
4. Test automation pipeline

### Site Customization
1. Modify shared components in `packages/shared/`
2. Update domain configurations
3. Customize layouts and styling
4. Add new page types

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# System status
bash scripts/health.sh

# Service logs
docker compose logs -f [service-name]

# Resource usage
docker stats
```

### Backup & Recovery
```bash
# Create backup
bash scripts/quick-backup.sh

# Restore from backup
bash scripts/restore-backup.sh [backup-file]
```

### Performance Optimization
- **Redis Caching**: Optimize queue performance
- **Image Optimization**: Compress generated images
- **CDN Integration**: Cloudflare edge caching
- **Database Optimization**: Redis persistence and backup

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request
5. Follow coding standards

## 📄 License

This project is proprietary software. All rights reserved.

## 🆘 Support

- **Documentation**: Check this README and inline code comments
- **Issues**: Create GitHub issues for bugs or feature requests
- **Discussions**: Use GitHub discussions for questions
- **Security**: Report security issues privately

## 🎯 Roadmap

- [ ] **Multi-language Support**: International content generation
- [ ] **Advanced AI Models**: GPT-4, Claude-3 integration
- [ ] **Social Media Expansion**: Twitter, LinkedIn automation
- [ ] **Advanced Analytics**: Machine learning insights
- [ ] **Mobile App**: Dashboard mobile application
- [ ] **API Marketplace**: Third-party integrations

---

**Built with ❤️ for automated content generation and revenue optimization**

*Last updated: December 2024*
