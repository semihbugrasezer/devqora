#!/bin/bash

# Deploy all sites to Cloudflare Pages
echo "Deploying all sites to Cloudflare Pages..."

for d in sites/*; do
  if [ -d "$d" ]; then
    DOMAIN=$(basename "$d")
    PROJECT=${DOMAIN//./-}
    echo "Deploying $DOMAIN to project $PROJECT..."
    
    # Check if dist directory exists
    if [ ! -d "$d/dist" ]; then
      echo "❌ $DOMAIN not built. Building first..."
      (cd "$d" && pnpm install && pnpm build)
    fi
    
    # Deploy to Cloudflare Pages
    npx wrangler pages deploy "$d/dist" --project-name "$PROJECT"
    echo "✅ $DOMAIN deployed successfully"
  fi
done

echo "All sites deployed successfully!"
