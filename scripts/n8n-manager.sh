#!/usr/bin/env bash
# /srv/auto-adsense/scripts/n8n-manager.sh
# n8n Workflow API Management Script

set -e

# Configuration
N8N_URL="${N8N_URL:-http://n8n.your-domain.com/api/v1}"
N8N_KEY="${N8N_KEY:-}"
WORKFLOW_DIR="${WORKFLOW_DIR:-$(dirname "$0")/../workflows}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

check_requirements() {
    if [[ -z "$N8N_KEY" ]]; then
        error "N8N_KEY environment variable required"
        exit 1
    fi
    
    if ! command -v curl >/dev/null 2>&1; then
        error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq >/dev/null 2>&1; then
        error "jq is required but not installed"
        exit 1
    fi
}

api_call() {
    local method="$1"
    local endpoint="$2"
    local data_file="$3"
    
    local cmd=(curl -sS -X "$method" "$N8N_URL$endpoint")
    cmd+=(-H 'accept: application/json')
    cmd+=(-H "X-N8N-API-KEY: $N8N_KEY")
    
    if [[ -n "$data_file" ]]; then
        cmd+=(-H 'Content-Type: application/json')
        cmd+=(--data-binary "@$data_file")
    fi
    
    "${cmd[@]}"
}

list_workflows() {
    log "Fetching workflow list..."
    api_call GET "/workflows" | jq -r '.data[] | "\(.id)\t\(.name)\t\(.active)"'
}

create_workflow() {
    local workflow_file="$1"
    
    if [[ ! -f "$workflow_file" ]]; then
        error "Workflow file not found: $workflow_file"
        return 1
    fi
    
    log "Creating workflow from: $workflow_file"
    local response
    response=$(api_call POST "/workflows" "$workflow_file")
    
    local workflow_id
    workflow_id=$(echo "$response" | jq -r '.id')
    
    if [[ "$workflow_id" != "null" ]]; then
        log "✅ Workflow created with ID: $workflow_id"
        echo "$workflow_id"
    else
        error "Failed to create workflow"
        echo "$response" | jq .
        return 1
    fi
}

activate_workflow() {
    local workflow_id="$1"
    
    log "Activating workflow: $workflow_id"
    local response
    response=$(api_call POST "/workflows/$workflow_id/activate")
    
    if echo "$response" | jq -e '.active' >/dev/null 2>&1; then
        log "✅ Workflow activated successfully"
    else
        error "Failed to activate workflow"
        echo "$response" | jq .
        return 1
    fi
}

deactivate_workflow() {
    local workflow_id="$1"
    
    log "Deactivating workflow: $workflow_id"
    local response
    response=$(api_call POST "/workflows/$workflow_id/deactivate")
    
    if echo "$response" | jq -e '.active == false' >/dev/null 2>&1; then
        log "✅ Workflow deactivated successfully"
    else
        error "Failed to deactivate workflow"
        echo "$response" | jq .
        return 1
    fi
}

update_workflow() {
    local workflow_id="$1"
    local workflow_file="$2"
    
    if [[ ! -f "$workflow_file" ]]; then
        error "Workflow file not found: $workflow_file"
        return 1
    fi
    
    log "Updating workflow: $workflow_id"
    local response
    response=$(api_call PUT "/workflows/$workflow_id" "$workflow_file")
    
    if echo "$response" | jq -e '.id' >/dev/null 2>&1; then
        log "✅ Workflow updated successfully"
    else
        error "Failed to update workflow"
        echo "$response" | jq .
        return 1
    fi
}

delete_workflow() {
    local workflow_id="$1"
    
    warn "Deleting workflow: $workflow_id"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        local response
        response=$(api_call DELETE "/workflows/$workflow_id")
        log "✅ Workflow deleted"
    else
        log "Delete cancelled"
    fi
}

deploy_all_workflows() {
    log "Deploying all workflows from: $WORKFLOW_DIR"
    
    if [[ ! -d "$WORKFLOW_DIR" ]]; then
        error "Workflow directory not found: $WORKFLOW_DIR"
        return 1
    fi
    
    for workflow_file in "$WORKFLOW_DIR"/*.json; do
        if [[ -f "$workflow_file" ]]; then
            local filename
            filename=$(basename "$workflow_file" .json)
            
            log "Processing: $filename"
            
            local workflow_id
            workflow_id=$(create_workflow "$workflow_file")
            
            if [[ -n "$workflow_id" && "$workflow_id" != "null" ]]; then
                activate_workflow "$workflow_id"
                echo "$workflow_id" > "$WORKFLOW_DIR/${filename}.id"
            fi
        fi
    done
}

get_workflow_status() {
    local workflow_id="$1"
    
    local response
    response=$(api_call GET "/workflows/$workflow_id")
    
    echo "$response" | jq -r '"ID: \(.id) | Name: \(.name) | Active: \(.active) | Created: \(.createdAt)"'
}

show_help() {
    cat << EOF
n8n Workflow Manager

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    list                    List all workflows
    create FILE             Create workflow from JSON file
    activate ID             Activate workflow by ID
    deactivate ID           Deactivate workflow by ID  
    update ID FILE          Update workflow with new JSON
    delete ID               Delete workflow by ID
    deploy                  Deploy all workflows from directory
    status ID               Show workflow status
    help                    Show this help

Environment Variables:
    N8N_URL                 n8n API base URL (default: http://n8n.your-domain.com/api/v1)
    N8N_KEY                 n8n API key (required)
    WORKFLOW_DIR            Directory containing workflow JSON files

Examples:
    $0 list
    $0 create workflows/daily-content.json
    $0 activate 12345
    $0 deploy
EOF
}

main() {
    check_requirements
    
    case "${1:-help}" in
        list)
            list_workflows
            ;;
        create)
            create_workflow "$2"
            ;;
        activate)
            activate_workflow "$2"
            ;;
        deactivate)
            deactivate_workflow "$2"
            ;;
        update)
            update_workflow "$2" "$3"
            ;;
        delete)
            delete_workflow "$2"
            ;;
        deploy)
            deploy_all_workflows
            ;;
        status)
            get_workflow_status "$2"
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
