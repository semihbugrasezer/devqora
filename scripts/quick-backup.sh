#!/usr/bin/env bash
# /srv/auto-adsense/scripts/quick-backup.sh
# Quick backup for essential components

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATE_STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$PROJECT_ROOT/backups/quick_$DATE_STAMP"

# Load environment
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

N8N_URL="${N8N_URL:-http://localhost:7056/api/v1}"

log() {
    echo -e "\033[0;32m[$(date +'%Y-%m-%d %H:%M:%S')]\033[0m $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"/{workflows,configs,logs}

log "🔄 Starting quick backup to: $BACKUP_DIR"

# Backup workflows via API
if [[ -n "$N8N_KEY" ]]; then
    log "📋 Backing up workflows..."
    curl -s -H "X-N8N-API-KEY: $N8N_KEY" "$N8N_URL/workflows" > "$BACKUP_DIR/workflows/all_workflows.json" 2>/dev/null
    log "✅ Workflows backed up"
else
    log "⚠️  N8N_KEY not set, skipping workflows"
fi

# Backup configs
log "📁 Backing up configs..."
cp "$PROJECT_ROOT/docker-compose.yml" "$BACKUP_DIR/configs/" 2>/dev/null || true
cp "$PROJECT_ROOT/.env" "$BACKUP_DIR/configs/.env.backup" 2>/dev/null || true
cp -r "$PROJECT_ROOT/workflows" "$BACKUP_DIR/configs/" 2>/dev/null || true
cp -r "$PROJECT_ROOT/scripts" "$BACKUP_DIR/configs/" 2>/dev/null || true

# Backup recent logs
log "📄 Backing up logs..."
for service in n8n pin-worker content-api bot-api; do
    docker compose logs --tail=100 "$service" > "$BACKUP_DIR/logs/${service}.log" 2>/dev/null || true
done

# Create manifest
cat > "$BACKUP_DIR/MANIFEST.txt" << EOF
Quick Backup - $(date)
======================
System: Auto-AdSense
Backup ID: $DATE_STAMP

Contents:
- workflows/all_workflows.json - n8n workflows
- configs/ - Docker compose, .env, scripts
- logs/ - Recent service logs

Status Check:
$(docker compose ps 2>/dev/null | head -10)

Created: $(date)
EOF

# Compress
cd "$PROJECT_ROOT/backups"
tar -czf "quick_backup_${DATE_STAMP}.tar.gz" "quick_$DATE_STAMP"
rm -rf "quick_$DATE_STAMP"

log "🎉 Quick backup completed: quick_backup_${DATE_STAMP}.tar.gz"
log "📦 Size: $(du -sh "quick_backup_${DATE_STAMP}.tar.gz" | cut -f1)"
