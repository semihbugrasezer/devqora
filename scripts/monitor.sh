#!/usr/bin/env bash
# /srv/auto-adsense/scripts/monitor.sh
# Real-time monitoring and analytics dashboard

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

N8N_URL="${N8N_URL:-http://localhost:7056/api/v1}"
BOT_API_URL="${BOT_API_URL:-http://localhost:7001}"
CONTENT_API_URL="${CONTENT_API_URL:-http://localhost:7055}"

print_header() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}                 ${YELLOW}AUTO-ADSENSE SYSTEM MONITOR${NC}                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                    ${GREEN}Live Dashboard v1.0${NC}                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo -e "${BLUE}$(date '+%Y-%m-%d %H:%M:%S')${NC} | Refresh: 10s | Press Ctrl+C to exit"
    echo
}

get_system_stats() {
    # Docker containers
    local containers_running=$(docker compose ps --services --filter "status=running" | wc -l)
    local containers_total=$(docker compose ps --services | wc -l)
    
    # Bot stats
    local bot_stats=$(curl -s "$BOT_API_URL/stats" 2>/dev/null || echo '{"keyword_queue":0,"pin_jobs":0,"reports":0}')
    local keyword_queue=$(echo "$bot_stats" | jq -r '.keyword_queue // 0')
    local pin_jobs=$(echo "$bot_stats" | jq -r '.pin_jobs // 0')
    local reports=$(echo "$bot_stats" | jq -r '.reports // 0')
    
    # Content API health
    local content_health=$(curl -s "$CONTENT_API_URL/health" 2>/dev/null | jq -r '.ok // false')
    
    # n8n workflows
    local workflow_stats=""
    if [[ -n "$N8N_KEY" ]]; then
        workflow_stats=$(curl -s -H "X-N8N-API-KEY: $N8N_KEY" "$N8N_URL/workflows" 2>/dev/null || echo '{"data":[]}')
    fi
    local total_workflows=$(echo "$workflow_stats" | jq -r '.data | length // 0')
    local active_workflows=$(echo "$workflow_stats" | jq -r '.data | map(select(.active == true)) | length // 0')
    
    echo "$containers_running,$containers_total,$keyword_queue,$pin_jobs,$reports,$content_health,$total_workflows,$active_workflows"
}

display_container_status() {
    echo -e "${PURPLE}📦 CONTAINER STATUS${NC}"
    echo -e "${PURPLE}═══════════════════${NC}"
    
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" | while read -r line; do
        if [[ "$line" == *"NAME"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        elif [[ "$line" == *"Up"* ]] || [[ "$line" == *"running"* ]]; then
            echo -e "${GREEN}$line${NC}"
        elif [[ "$line" == *"Restarting"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        else
            echo -e "${RED}$line${NC}"
        fi
    done
    echo
}

display_bot_metrics() {
    local stats=$(curl -s "$BOT_API_URL/stats" 2>/dev/null || echo '{"keyword_queue":0,"pin_jobs":0,"reports":0}')
    
    echo -e "${PURPLE}🤖 PINTEREST BOT METRICS${NC}"
    echo -e "${PURPLE}═══════════════════════════${NC}"
    
    local keyword_queue=$(echo "$stats" | jq -r '.keyword_queue // 0')
    local pin_jobs=$(echo "$stats" | jq -r '.pin_jobs // 0')
    local reports=$(echo "$stats" | jq -r '.reports // 0')
    
    # Color coding based on values
    local kq_color=$GREEN
    [[ $keyword_queue -lt 5 ]] && kq_color=$YELLOW
    [[ $keyword_queue -eq 0 ]] && kq_color=$RED
    
    local pj_color=$GREEN
    [[ $pin_jobs -gt 20 ]] && pj_color=$YELLOW
    [[ $pin_jobs -gt 50 ]] && pj_color=$RED
    
    echo -e "Keyword Queue:  ${kq_color}${keyword_queue}${NC} items"
    echo -e "Pin Jobs:       ${pj_color}${pin_jobs}${NC} pending"
    echo -e "Reports:        ${CYAN}${reports}${NC} total"
    
    # Activity indicator
    local activity_level="🟢 Active"
    [[ $keyword_queue -eq 0 && $pin_jobs -eq 0 ]] && activity_level="🟡 Idle"
    [[ $pin_jobs -gt 30 ]] && activity_level="🔴 Overloaded"
    
    echo -e "Status:         $activity_level"
    echo
}

display_workflow_status() {
    echo -e "${PURPLE}⚡ N8N WORKFLOWS${NC}"
    echo -e "${PURPLE}═══════════════════${NC}"
    
    if [[ -z "$N8N_KEY" ]]; then
        echo -e "${RED}❌ N8N_KEY not configured${NC}"
        echo
        return
    fi
    
    local workflow_data=$(curl -s -H "X-N8N-API-KEY: $N8N_KEY" "$N8N_URL/workflows" 2>/dev/null)
    
    if [[ $? -ne 0 ]] || [[ -z "$workflow_data" ]]; then
        echo -e "${RED}❌ Unable to connect to n8n API${NC}"
        echo
        return
    fi
    
    echo "$workflow_data" | jq -r '.data[] | "\(.name)|\(.active)|\(.id)"' | while IFS='|' read -r name active id; do
        local status_icon="🟢"
        local status_color=$GREEN
        
        if [[ "$active" == "false" ]]; then
            status_icon="🔴"
            status_color=$RED
        fi
        
        printf "%-40s %s %s\n" "$name" "$status_icon" "${status_color}${active}${NC}"
    done
    echo
}

display_content_api_status() {
    echo -e "${PURPLE}📝 CONTENT API${NC}"
    echo -e "${PURPLE}═══════════════${NC}"
    
    local health=$(curl -s "$CONTENT_API_URL/health" 2>/dev/null)
    
    if [[ $? -eq 0 ]] && echo "$health" | jq -e '.ok' >/dev/null 2>&1; then
        echo -e "Status:     ${GREEN}🟢 Healthy${NC}"
        echo -e "Endpoint:   ${CYAN}$CONTENT_API_URL${NC}"
    else
        echo -e "Status:     ${RED}🔴 Unhealthy${NC}"
        echo -e "Endpoint:   ${RED}$CONTENT_API_URL${NC}"
    fi
    echo
}

display_recent_activity() {
    echo -e "${PURPLE}📊 RECENT ACTIVITY${NC}"
    echo -e "${PURPLE}═══════════════════${NC}"
    
    # Check docker logs for recent activity
    echo -e "${YELLOW}Last 5 Pinterest Bot Events:${NC}"
    docker compose logs --tail=5 pin-worker 2>/dev/null | grep -E "(enqueued|posted|error)" | tail -5 | while read -r line; do
        if [[ "$line" == *"error"* ]]; then
            echo -e "${RED}  $line${NC}"
        elif [[ "$line" == *"enqueued"* ]]; then
            echo -e "${GREEN}  $line${NC}"
        else
            echo -e "${CYAN}  $line${NC}"
        fi
    done
    
    echo
    echo -e "${YELLOW}Last 3 Content API Events:${NC}"
    docker compose logs --tail=3 content-api 2>/dev/null | tail -3 | while read -r line; do
        echo -e "${CYAN}  $line${NC}"
    done
    echo
}

display_performance_metrics() {
    echo -e "${PURPLE}⚡ PERFORMANCE METRICS${NC}"
    echo -e "${PURPLE}═══════════════════════════${NC}"
    
    # Memory usage
    local memory_usage=$(docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}" | grep auto-adsense | head -5)
    echo -e "${YELLOW}Memory Usage (Top 5):${NC}"
    echo "$memory_usage" | while read -r line; do
        echo -e "${CYAN}  $line${NC}"
    done
    echo
    
    # CPU usage
    local cpu_usage=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}" | grep auto-adsense | head -5)
    echo -e "${YELLOW}CPU Usage (Top 5):${NC}"
    echo "$cpu_usage" | while read -r line; do
        echo -e "${CYAN}  $line${NC}"
    done
    echo
}

show_help() {
    echo -e "${YELLOW}Usage: $0 [COMMAND]${NC}"
    echo
    echo -e "${CYAN}Commands:${NC}"
    echo -e "  ${GREEN}live${NC}      Real-time monitoring dashboard (default)"
    echo -e "  ${GREEN}status${NC}    One-time status check"
    echo -e "  ${GREEN}stats${NC}     Detailed statistics"
    echo -e "  ${GREEN}logs${NC}      Show recent logs"
    echo -e "  ${GREEN}help${NC}      Show this help"
    echo
    echo -e "${CYAN}Examples:${NC}"
    echo -e "  $0"
    echo -e "  $0 live"
    echo -e "  $0 status"
}

monitor_live() {
    echo -e "${GREEN}Starting live monitoring... Press Ctrl+C to exit${NC}"
    echo
    
    while true; do
        print_header
        display_container_status
        display_bot_metrics
        display_workflow_status
        display_content_api_status
        display_recent_activity
        
        sleep 10
    done
}

show_status() {
    print_header
    display_container_status
    display_bot_metrics
    display_workflow_status
    display_content_api_status
}

show_stats() {
    print_header
    display_container_status
    display_bot_metrics
    display_workflow_status
    display_content_api_status
    display_performance_metrics
}

show_logs() {
    echo -e "${PURPLE}📋 RECENT LOGS${NC}"
    echo -e "${PURPLE}═══════════════${NC}"
    
    echo -e "${YELLOW}n8n logs:${NC}"
    docker compose logs --tail=10 n8n
    echo
    
    echo -e "${YELLOW}Pinterest Bot logs:${NC}"
    docker compose logs --tail=10 pin-worker
    echo
    
    echo -e "${YELLOW}Content API logs:${NC}"
    docker compose logs --tail=10 content-api
    echo
}

main() {
    case "${1:-live}" in
        live|monitor)
            monitor_live
            ;;
        status)
            show_status
            ;;
        stats)
            show_stats
            ;;
        logs)
            show_logs
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown command: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Monitoring stopped.${NC}"; exit 0' INT

main "$@"
