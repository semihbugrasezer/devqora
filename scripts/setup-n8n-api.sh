#!/usr/bin/env bash
# /srv/auto-adsense/scripts/setup-n8n-api.sh
# n8n API Setup and Configuration Script

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

check_dependencies() {
    log "Checking dependencies..."
    
    for cmd in curl jq docker; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            error "$cmd is required but not installed"
            exit 1
        fi
    done
    
    log "✅ All dependencies found"
}

check_n8n_running() {
    log "Checking if n8n is running..."
    
    if ! docker compose -f "$PROJECT_ROOT/docker-compose.yml" ps n8n | grep -q "running"; then
        error "n8n container is not running"
        log "Start with: cd $PROJECT_ROOT && docker compose up -d"
        exit 1
    fi
    
    log "✅ n8n container is running"
}

wait_for_n8n() {
    log "Waiting for n8n to be ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:7056/api/v1/workflows" >/dev/null 2>&1; then
            log "✅ n8n API is responding"
            return 0
        fi
        
        log "Attempt $attempt/$max_attempts - waiting for n8n..."
        sleep 5
        ((attempt++))
    done
    
    error "n8n API did not become available within timeout"
    exit 1
}

generate_api_key() {
    log "Generating n8n API key..."
    
    # Note: This is a simplified approach
    # In a real setup, you would create the API key through n8n UI or database
    local api_key="n8n_api_$(openssl rand -hex 16)"
    
    log "Generated API key: $api_key"
    log "⚠️  You need to manually create this API key in n8n UI:"
    log "   1. Open https://n8n.your-domain.com"
    log "   2. Go to Settings → API Keys"
    log "   3. Create new API key: $api_key"
    
    echo "$api_key"
}

setup_environment() {
    log "Setting up environment variables..."
    
    # Source existing .env if it exists
    if [[ -f "$ENV_FILE" ]]; then
        set -a
        source "$ENV_FILE"
        set +a
    fi
    
    # Set default values
    local n8n_url="${N8N_URL:-http://localhost:7056/api/v1}"
    local n8n_key="${N8N_KEY:-}"
    
    if [[ -z "$n8n_key" ]]; then
        error "N8N_KEY not found. Please export your existing n8n API key: export N8N_KEY=your_key_here"
        exit 1
    fi
    
    # Export for current session
    export N8N_URL="$n8n_url"
    export N8N_KEY="$n8n_key"
    
    log "Environment variables configured:"
    log "  N8N_URL: $N8N_URL"
    log "  N8N_KEY: ${N8N_KEY:0:10}..."
}

test_api_connection() {
    log "Testing n8n API connection..."
    
    if [[ -z "$N8N_KEY" ]]; then
        warn "Cannot test API - N8N_KEY not set"
        return 1
    fi
    
    local response
    response=$(curl -s -w "%{http_code}" -H "X-N8N-API-KEY: $N8N_KEY" "$N8N_URL/workflows" -o /tmp/n8n_test.json)
    
    if [[ "$response" == "200" ]]; then
        log "✅ n8n API connection successful"
        local workflow_count
        workflow_count=$(jq -r '.data | length' /tmp/n8n_test.json 2>/dev/null || echo "0")
        log "Found $workflow_count existing workflows"
        rm -f /tmp/n8n_test.json
        return 0
    elif [[ "$response" == "401" ]]; then
        error "API key authentication failed (401)"
        log "Please verify your API key in n8n UI"
        return 1
    else
        error "API connection failed (HTTP $response)"
        return 1
    fi
}

deploy_workflows() {
    log "Deploying workflows..."
    
    local workflow_dir="$PROJECT_ROOT/workflows"
    
    if [[ ! -d "$workflow_dir" ]]; then
        error "Workflow directory not found: $workflow_dir"
        return 1
    fi
    
    # Use the n8n-manager script
    local manager_script="$SCRIPT_DIR/n8n-manager.sh"
    
    if [[ ! -x "$manager_script" ]]; then
        error "n8n-manager.sh not found or not executable"
        return 1
    fi
    
    log "Deploying all workflows..."
    "$manager_script" deploy
}

create_backup() {
    log "Creating workflow backup..."
    
    local backup_dir="$PROJECT_ROOT/backups/workflows"
    local backup_file="$backup_dir/workflows_$(date +%Y%m%d_%H%M%S).json"
    
    mkdir -p "$backup_dir"
    
    if curl -s -H "X-N8N-API-KEY: $N8N_KEY" "$N8N_URL/workflows" | jq '.' > "$backup_file"; then
        log "✅ Backup created: $backup_file"
    else
        warn "Failed to create backup"
    fi
}

show_status() {
    log "n8n System Status"
    echo "===================="
    
    # Docker status
    echo "Docker Status:"
    docker compose -f "$PROJECT_ROOT/docker-compose.yml" ps n8n
    echo
    
    # API status
    echo "API Status:"
    if test_api_connection; then
        echo "✅ API Connection: OK"
    else
        echo "❌ API Connection: Failed"
    fi
    echo
    
    # Workflow count
    if [[ -n "$N8N_KEY" ]]; then
        echo "Workflows:"
        "$SCRIPT_DIR/n8n-manager.sh" list | head -10
    fi
}

show_help() {
    cat << EOF
n8n API Setup and Management

Usage: $0 [COMMAND]

Commands:
    setup       Full setup (check deps, start services, configure)
    deploy      Deploy all workflows from workflows/ directory
    test        Test API connection
    status      Show system status
    backup      Create workflow backup
    help        Show this help

Environment Variables:
    N8N_URL     n8n API base URL
    N8N_KEY     n8n API key

Examples:
    $0 setup
    $0 deploy
    $0 status
EOF
}

main() {
    case "${1:-setup}" in
        setup)
            check_dependencies
            check_n8n_running
            wait_for_n8n
            setup_environment
            if test_api_connection; then
                deploy_workflows
                create_backup
                show_status
            fi
            ;;
        deploy)
            check_dependencies
            setup_environment
            deploy_workflows
            ;;
        test)
            setup_environment
            test_api_connection
            ;;
        status)
            setup_environment
            show_status
            ;;
        backup)
            setup_environment
            create_backup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
