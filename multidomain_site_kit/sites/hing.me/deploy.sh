#!/bin/bash

# Hing.me Optimized Deployment Script
set -e

echo "🚀 Starting Hing.me deployment..."

# Build the site
echo "📦 Building site..."
pnpm build

# Deploy to Cloudflare Pages
echo "☁️ Deploying to Cloudflare Pages..."
npx wrangler pages deploy dist --project-name hing-me

# Get deployment URL
echo "✅ Deployment complete!"
echo "🌐 Live at: https://hing.me"
echo "🔗 Latest deployment: https://hing-me.pages.dev"

# Test the deployment
echo "🧪 Testing deployment..."
sleep 5
curl -I https://hing.me || echo "⚠️ Main domain not yet updated"
curl -I https://hing-me.pages.dev || echo "⚠️ Pages domain failed"

echo "🎉 Deployment pipeline complete!"