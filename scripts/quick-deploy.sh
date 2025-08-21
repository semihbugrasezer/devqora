#!/usr/bin/env bash
# /srv/auto-adsense/scripts/quick-deploy.sh
# Quick deployment script for n8n workflows

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source environment
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Set defaults
N8N_URL="${N8N_URL:-http://localhost:7056/api/v1}"

log() {
    echo -e "\033[0;32m[$(date +'%Y-%m-%d %H:%M:%S')]\033[0m $1"
}

error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1" >&2
}

deploy_workflow() {
    local workflow_file="$1"
    local workflow_name="$2"
    
    if [[ ! -f "$workflow_file" ]]; then
        error "Workflow file not found: $workflow_file"
        return 1
    fi
    
    log "Deploying: $workflow_name"
    
    # Create workflow
    local response
    response=$(curl -sS -X POST "$N8N_URL/workflows" \
        -H 'accept: application/json' \
        -H "X-N8N-API-KEY: $N8N_KEY" \
        -H 'Content-Type: application/json' \
        --data-binary "@$workflow_file")
    
    local workflow_id
    workflow_id=$(echo "$response" | jq -r '.id')
    
    if [[ "$workflow_id" != "null" && -n "$workflow_id" ]]; then
        log "✅ Created workflow: $workflow_id"
        
        # Activate workflow
        curl -sS -X POST "$N8N_URL/workflows/$workflow_id/activate" \
            -H 'accept: application/json' \
            -H "X-N8N-API-KEY: $N8N_KEY" >/dev/null
        
        log "✅ Activated workflow: $workflow_name"
        echo "$workflow_id" > "$PROJECT_ROOT/workflows/.${workflow_name}.id"
    else
        error "Failed to create workflow: $workflow_name"
        echo "$response" | jq .
        return 1
    fi
}

main() {
    log "🚀 Quick Deploy - n8n Workflows"
    
    if [[ -z "$N8N_KEY" ]]; then
        error "N8N_KEY environment variable required"
        log "Run: export N8N_KEY='your-api-key'"
        exit 1
    fi
    
    # Deploy main workflows
    deploy_workflow "$PROJECT_ROOT/workflows/daily-content-generator.json" "daily-content-generator"
    deploy_workflow "$PROJECT_ROOT/workflows/pinterest-accelerator.json" "pinterest-accelerator"
    
    log "🎉 Deployment complete!"
    log "Check status with: ./scripts/n8n-manager.sh list"
}

main "$@"
