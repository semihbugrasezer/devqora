#!/usr/bin/env bash
# /srv/auto-adsense/scripts/backup-system.sh
# Automated backup system for workflows, configs and data

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_ROOT="$PROJECT_ROOT/backups"
DATE_STAMP=$(date +%Y%m%d_%H%M%S)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Load environment
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

N8N_URL="${N8N_URL:-http://localhost:7056/api/v1}"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

create_backup_structure() {
    local backup_dir="$BACKUP_ROOT/$DATE_STAMP"
    
    log "Creating backup structure: $backup_dir"
    
    mkdir -p "$backup_dir"/{workflows,configs,data,docker,logs}
    echo "$backup_dir"
}

backup_workflows() {
    local backup_dir="$1"
    
    log "Backing up n8n workflows..."
    
    if [[ -z "$N8N_KEY" ]]; then
        warn "N8N_KEY not set, skipping workflow backup"
        return 1
    fi
    
    # Backup all workflows via API
    local workflows_response
    workflows_response=$(curl -s -H "X-N8N-API-KEY: $N8N_KEY" "$N8N_URL/workflows" 2>/dev/null)
    
    if [[ $? -eq 0 ]] && echo "$workflows_response" | jq . >/dev/null 2>&1; then
        echo "$workflows_response" | jq '.' > "$backup_dir/workflows/all_workflows_${DATE_STAMP}.json"
        
        # Individual workflow backups
        echo "$workflows_response" | jq -r '.data[] | "\(.id)|\(.name)"' | while IFS='|' read -r id name; do
            local safe_name=$(echo "$name" | sed 's/[^a-zA-Z0-9_-]/_/g')
            local workflow_data
            workflow_data=$(curl -s -H "X-N8N-API-KEY: $N8N_KEY" "$N8N_URL/workflows/$id" 2>/dev/null)
            
            if [[ $? -eq 0 ]]; then
                echo "$workflow_data" > "$backup_dir/workflows/${safe_name}_${id}.json"
            fi
        done
        
        log "✅ Workflows backed up successfully"
    else
        error "Failed to backup workflows"
        return 1
    fi
}

backup_configs() {
    local backup_dir="$1"
    
    log "Backing up configuration files..."
    
    # Docker compose and environment
    cp "$PROJECT_ROOT/docker-compose.yml" "$backup_dir/configs/" 2>/dev/null || true
    cp "$PROJECT_ROOT/.env" "$backup_dir/configs/.env.backup" 2>/dev/null || true
    
    # Scripts
    cp -r "$PROJECT_ROOT/scripts" "$backup_dir/configs/" 2>/dev/null || true
    
    # Local workflow definitions
    if [[ -d "$PROJECT_ROOT/workflows" ]]; then
        cp -r "$PROJECT_ROOT/workflows" "$backup_dir/configs/" 2>/dev/null || true
    fi
    
    log "✅ Configuration files backed up"
}

backup_data() {
    local backup_dir="$1"
    
    log "Backing up data volumes..."
    
    # Redis data
    if docker compose ps redis | grep -q "running"; then
        log "Backing up Redis data..."
        docker compose exec -T redis redis-cli BGSAVE >/dev/null 2>&1 || true
        sleep 2
        docker cp "auto-adsense-redis-1:/data/dump.rdb" "$backup_dir/data/redis_${DATE_STAMP}.rdb" 2>/dev/null || true
    fi
    
    # n8n data
    if docker compose ps n8n | grep -q "running"; then
        log "Backing up n8n data..."
        docker cp "auto-adsense-n8n-1:/home/node/.n8n" "$backup_dir/data/n8n_data_${DATE_STAMP}" 2>/dev/null || true
    fi
    
    log "✅ Data volumes backed up"
}

backup_docker_state() {
    local backup_dir="$1"
    
    log "Backing up Docker state..."
    
    # Container status
    docker compose ps > "$backup_dir/docker/container_status_${DATE_STAMP}.txt"
    
    # Images info
    docker compose images > "$backup_dir/docker/images_${DATE_STAMP}.txt"
    
    # Network info
    docker network ls | grep auto-adsense > "$backup_dir/docker/networks_${DATE_STAMP}.txt" 2>/dev/null || true
    
    log "✅ Docker state backed up"
}

backup_logs() {
    local backup_dir="$1"
    
    log "Backing up recent logs..."
    
    # Get logs from all services
    for service in n8n redis content-api bot-api pin-worker poster-worker; do
        if docker compose ps "$service" | grep -q "running\|Up"; then
            docker compose logs --tail=1000 "$service" > "$backup_dir/logs/${service}_${DATE_STAMP}.log" 2>/dev/null || true
        fi
    done
    
    log "✅ Logs backed up"
}

create_manifest() {
    local backup_dir="$1"
    
    log "Creating backup manifest..."
    
    cat > "$backup_dir/MANIFEST.txt" << EOF
AUTO-ADSENSE BACKUP MANIFEST
============================
Date: $(date)
Backup ID: $DATE_STAMP
System: $(uname -a)
Docker Version: $(docker --version)

CONTENTS:
- workflows/     n8n workflow definitions and exports
- configs/       Configuration files and scripts
- data/          Redis and n8n data volumes
- docker/        Docker container and network state
- logs/          Recent service logs

RESTORATION:
1. Stop system: docker compose down
2. Restore configs: cp configs/* /srv/auto-adsense/
3. Restore data volumes (if needed)
4. Start system: docker compose up -d
5. Restore workflows via n8n UI or API

VERIFICATION:
- Check workflow count: $(curl -s -H "X-N8N-API-KEY: $N8N_KEY" "$N8N_URL/workflows" 2>/dev/null | jq -r '.data | length // "API_ERROR"')
- System status: docker compose ps

Created by: auto-adsense backup system
EOF
    
    # Calculate sizes
    echo >> "$backup_dir/MANIFEST.txt"
    echo "BACKUP SIZES:" >> "$backup_dir/MANIFEST.txt"
    du -sh "$backup_dir"/* >> "$backup_dir/MANIFEST.txt" 2>/dev/null || true
    
    log "✅ Manifest created"
}

compress_backup() {
    local backup_dir="$1"
    local archive_name="auto_adsense_backup_${DATE_STAMP}.tar.gz"
    local archive_path="$BACKUP_ROOT/$archive_name"
    
    log "Compressing backup to: $archive_name"
    
    cd "$BACKUP_ROOT"
    tar -czf "$archive_name" "$(basename "$backup_dir")" 2>/dev/null
    
    if [[ -f "$archive_path" ]]; then
        local size=$(du -sh "$archive_path" | cut -f1)
        log "✅ Backup compressed: $size"
        
        # Remove uncompressed directory
        rm -rf "$backup_dir"
        
        echo "$archive_path"
    else
        error "Failed to create compressed backup"
        return 1
    fi
}

cleanup_old_backups() {
    local keep_days="${1:-7}"
    
    log "Cleaning up backups older than $keep_days days..."
    
    find "$BACKUP_ROOT" -name "auto_adsense_backup_*.tar.gz" -mtime +$keep_days -delete 2>/dev/null || true
    find "$BACKUP_ROOT" -name "20*" -type d -mtime +$keep_days -exec rm -rf {} + 2>/dev/null || true
    
    log "✅ Old backups cleaned up"
}

list_backups() {
    log "Available backups:"
    
    if [[ -d "$BACKUP_ROOT" ]]; then
        find "$BACKUP_ROOT" -name "auto_adsense_backup_*.tar.gz" -printf "%T@ %Tc %p\n" | sort -n | while read -r timestamp date_str path; do
            local size=$(du -sh "$path" 2>/dev/null | cut -f1)
            local basename=$(basename "$path" .tar.gz)
            local date_only=$(echo "$basename" | grep -o '[0-9]\{8\}_[0-9]\{6\}')
            echo "  📦 $date_only - $size - $path"
        done
    else
        warn "No backup directory found"
    fi
}

restore_backup() {
    local backup_file="$1"
    
    if [[ ! -f "$backup_file" ]]; then
        error "Backup file not found: $backup_file"
        return 1
    fi
    
    log "Restoring from: $(basename "$backup_file")"
    
    # Extract backup
    local temp_dir=$(mktemp -d)
    tar -xzf "$backup_file" -C "$temp_dir"
    
    local extracted_dir=$(find "$temp_dir" -maxdepth 1 -type d -name "20*" | head -1)
    
    if [[ -z "$extracted_dir" ]]; then
        error "Invalid backup structure"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Show manifest
    if [[ -f "$extracted_dir/MANIFEST.txt" ]]; then
        echo "📋 Backup Manifest:"
        cat "$extracted_dir/MANIFEST.txt"
        echo
    fi
    
    read -p "Continue with restoration? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Stopping system..."
        docker compose down
        
        log "Restoring configuration files..."
        if [[ -d "$extracted_dir/configs" ]]; then
            cp -r "$extracted_dir/configs"/* "$PROJECT_ROOT/" 2>/dev/null || true
        fi
        
        log "Starting system..."
        docker compose up -d
        
        log "✅ Backup restored successfully"
        log "Manually restore workflows via n8n UI if needed"
    else
        log "Restoration cancelled"
    fi
    
    rm -rf "$temp_dir"
}

show_help() {
    cat << EOF
Auto-AdSense Backup System

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    backup [days]   Create full system backup (default: keep 7 days)
    list           List available backups
    restore FILE   Restore from backup file
    cleanup [days] Clean old backups (default: 7 days)
    help           Show this help

Examples:
    $0 backup
    $0 backup 14          # Keep 14 days of backups
    $0 list
    $0 restore /srv/auto-adsense/backups/auto_adsense_backup_20241221_120000.tar.gz
    $0 cleanup 3          # Keep only 3 days

Backup includes:
- n8n workflows and configurations
- Docker compose and environment files
- Redis and n8n data volumes
- Recent service logs
- System state information
EOF
}

main() {
    case "${1:-backup}" in
        backup)
            local keep_days="${2:-7}"
            
            mkdir -p "$BACKUP_ROOT"
            
            local backup_dir
            backup_dir=$(create_backup_structure)
            
            backup_workflows "$backup_dir"
            backup_configs "$backup_dir"
            backup_data "$backup_dir"
            backup_docker_state "$backup_dir"
            backup_logs "$backup_dir"
            create_manifest "$backup_dir"
            
            local archive
            archive=$(compress_backup "$backup_dir")
            
            cleanup_old_backups "$keep_days"
            
            log "🎉 Backup completed: $(basename "$archive")"
            ;;
        list)
            list_backups
            ;;
        restore)
            if [[ -z "$2" ]]; then
                error "Backup file path required"
                show_help
                exit 1
            fi
            restore_backup "$2"
            ;;
        cleanup)
            cleanup_old_backups "${2:-7}"
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
