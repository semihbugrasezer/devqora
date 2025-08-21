# Setup Guide for Hing.me & Playu.co Domains

## Overview
This guide will help you set up your auto-adsense system with the real domains `hing.me` and `playu.co`.

## Current Status
✅ Docker services running  
✅ Domain configuration created  
✅ Site structure built  
✅ n8n workflow created  

## Next Steps

### 1. Install Dependencies & Build Sites
```bash
cd /srv/auto-adsense/multidomain_site_kit

# Install dependencies for all sites
for d in sites/*; do
  (cd "$d" && pnpm install)
done

# Build all sites
./scripts/build-all.sh
```

### 2. Set Up Cloudflare Pages
```bash
# Login to Cloudflare
wrangler login

# Deploy hing.me
cd sites/hing.me
pnpm build
npx wrangler pages deploy dist --project-name hing-me

# Deploy playu.co  
cd ../playu.co
pnpm build
npx wrangler pages deploy dist --project-name playu-co
```

### 3. Configure Custom Domains
- In Cloudflare Pages, add custom domain `hing.me` to the `hing-me` project
- Add custom domain `playu.co` to the `playu-co` project
- Update DNS records to point to Cloudflare Pages

### 4. Set Up AdSense
- Get your AdSense publisher ID
- Update `multidomain_site_kit/config/domains.json` with real AdSense IDs
- Create `ads.txt` files in each site's `public/` directory
- Redeploy sites after adding ads.txt

### 5. Import n8n Workflow
- Open `https://n8n.hing.me`
- Import the `n8n_workflow_hing_playu.json` file
- Activate the workflow
- The workflow will run daily at 9 AM and generate content for both domains

### 6. Test Content API
```bash
# Test content ingestion
curl -X POST http://localhost:5055/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "hing.me",
    "title": "Test Article",
    "body": "This is a test article content."
  }'
```

## Domain-Specific Content Strategy

### Hing.me (Finance Focus)
- **Target Audience**: Financial planners, investors, debt management
- **Content Types**: Calculators, investment guides, credit score tips
- **High-CPC Keywords**: mortgage, investment, credit, retirement
- **Ad Placement**: Header, in-article, footer

### Playu.co (Gaming Focus)  
- **Target Audience**: Gamers, streamers, tech enthusiasts
- **Content Types**: Setup guides, game reviews, streaming tips
- **High-CPC Keywords**: gaming setup, streaming equipment, PC parts
- **Ad Placement**: Header, in-article, footer

## Automation Features

### Daily Content Generation
- n8n workflow runs at 9 AM daily
- Fetches data from public APIs
- Generates relevant content for each domain
- Automatically builds and deploys sites

### Pinterest Integration
- Bot enqueues keywords from generated content
- Creates pin images and descriptions
- Posts to Pinterest with domain rotation
- Tracks performance metrics

## Monitoring & Analytics

### Health Checks
```bash
cd /srv/auto-adsense
bash scripts/health.sh
```

### Content API Status
```bash
curl http://localhost:5055/health
```

### Bot API Status
```bash
curl http://localhost:5001/health
```

## Revenue Optimization

### AdSense Setup
1. **Header Ads**: Above-the-fold placement for high visibility
2. **In-Article Ads**: Contextual placement within content
3. **Footer Ads**: Additional monetization without affecting UX

### Content Strategy
1. **High-CPC Topics**: Focus on finance and gaming keywords
2. **User Intent**: Create content that answers specific questions
3. **Internal Linking**: Guide users through your content funnel
4. **SEO Optimization**: Target long-tail keywords with high search volume

## Scaling Plan

### Phase 1 (Weeks 1-2)
- [ ] Deploy both domains to Cloudflare Pages
- [ ] Set up AdSense and ads.txt
- [ ] Test n8n workflow
- [ ] Monitor initial performance

### Phase 2 (Weeks 3-4)  
- [ ] Increase content generation to 5-7 articles/day
- [ ] Optimize ad placements based on CTR data
- [ ] Add more Pinterest boards and keywords
- [ ] A/B test different content formats

### Phase 3 (Weeks 5-8)
- [ ] Scale to 10+ articles/day per domain
- [ ] Add new high-CPC domains
- [ ] Implement advanced analytics
- [ ] Optimize for mobile performance

## Troubleshooting

### Common Issues
1. **Build Failures**: Check Node.js version and dependencies
2. **Deployment Issues**: Verify Cloudflare authentication
3. **Content API Errors**: Check Docker container logs
4. **AdSense Issues**: Verify ads.txt and domain verification

### Support Commands
```bash
# View all container logs
docker compose logs

# Restart specific service
docker compose restart content-api

# Check disk space
df -h

# Monitor system resources
htop
```

## Success Metrics

### Traffic Goals
- **Month 1**: 1,000+ visitors/month per domain
- **Month 3**: 5,000+ visitors/month per domain  
- **Month 6**: 15,000+ visitors/month per domain

### Revenue Targets
- **Month 1**: $50-100/month
- **Month 3**: $200-500/month
- **Month 6**: $500-1,000/month

### Content Goals
- **Month 1**: 50+ articles per domain
- **Month 3**: 150+ articles per domain
- **Month 6**: 300+ articles per domain

---

**Next Action**: Run the build script to test your site setup!
```bash
cd /srv/auto-adsense/multidomain_site_kit
./scripts/build-all.sh
```
