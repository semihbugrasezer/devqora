#!/bin/bash

# Build all sites in the multidomain_site_kit
echo "Building all sites..."

for d in sites/*; do
  if [ -d "$d" ]; then
    DOMAIN=$(basename "$d")
    echo "Building $DOMAIN..."
    (cd "$d" && pnpm install && pnpm build)
    echo "✅ $DOMAIN built successfully"
  fi
done

echo "All sites built successfully!"
