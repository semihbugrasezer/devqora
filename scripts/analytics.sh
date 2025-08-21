#!/usr/bin/env bash
# /srv/auto-adsense/scripts/analytics.sh
# Advanced analytics and performance tracking

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ANALYTICS_DIR="$PROJECT_ROOT/analytics"
DATE_STAMP=$(date +%Y%m%d_%H%M%S)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Load environment
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

BOT_API_URL="${BOT_API_URL:-http://localhost:7001}"
CONTENT_API_URL="${CONTENT_API_URL:-http://localhost:7055}"
N8N_URL="${N8N_URL:-http://localhost:7056/api/v1}"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

init_analytics() {
    mkdir -p "$ANALYTICS_DIR"/{daily,hourly,reports}
    
    # Create analytics database file if not exists
    if [[ ! -f "$ANALYTICS_DIR/analytics.csv" ]]; then
        echo "timestamp,keyword_queue,pin_jobs,reports,active_workflows,container_health,api_response_time" > "$ANALYTICS_DIR/analytics.csv"
        log "📊 Analytics database initialized"
    fi
}

collect_metrics() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Bot metrics
    local bot_stats=$(curl -s "$BOT_API_URL/stats" 2>/dev/null || echo '{"keyword_queue":0,"pin_jobs":0,"reports":0}')
    local keyword_queue=$(echo "$bot_stats" | jq -r '.keyword_queue // 0')
    local pin_jobs=$(echo "$bot_stats" | jq -r '.pin_jobs // 0')
    local reports=$(echo "$bot_stats" | jq -r '.reports // 0')
    
    # Workflow metrics
    local active_workflows=0
    if [[ -n "$N8N_KEY" ]]; then
        local workflow_stats=$(curl -s -H "X-N8N-API-KEY: $N8N_KEY" "$N8N_URL/workflows" 2>/dev/null || echo '{"data":[]}')
        active_workflows=$(echo "$workflow_stats" | jq -r '.data | map(select(.active == true)) | length // 0')
    fi
    
    # Container health
    local running_containers=$(docker compose ps --services --filter "status=running" | wc -l)
    local total_containers=$(docker compose ps --services | wc -l)
    local container_health=$(echo "scale=2; $running_containers * 100 / $total_containers" | bc -l 2>/dev/null || echo "0")
    
    # API response time
    local start_time=$(date +%s%N)
    curl -s "$CONTENT_API_URL/health" >/dev/null 2>&1
    local end_time=$(date +%s%N)
    local api_response_time=$(echo "scale=3; ($end_time - $start_time) / 1000000" | bc -l 2>/dev/null || echo "0")
    
    # Save to CSV
    echo "$timestamp,$keyword_queue,$pin_jobs,$reports,$active_workflows,$container_health,$api_response_time" >> "$ANALYTICS_DIR/analytics.csv"
    
    echo "$timestamp,$keyword_queue,$pin_jobs,$reports,$active_workflows,$container_health,$api_response_time"
}

generate_daily_report() {
    local date_filter="${1:-$(date +%Y-%m-%d)}"
    local report_file="$ANALYTICS_DIR/reports/daily_report_${date_filter//-/}.txt"
    
    log "📈 Generating daily report for: $date_filter"
    
    # Extract today's data
    local today_data=$(grep "^$date_filter" "$ANALYTICS_DIR/analytics.csv" 2>/dev/null || echo "")
    
    if [[ -z "$today_data" ]]; then
        log "❌ No data found for $date_filter"
        return 1
    fi
    
    # Calculate statistics
    local total_records=$(echo "$today_data" | wc -l)
    local avg_keyword_queue=$(echo "$today_data" | awk -F',' '{sum+=$2} END {printf "%.1f", sum/NR}' 2>/dev/null || echo "0")
    local max_pin_jobs=$(echo "$today_data" | awk -F',' 'BEGIN{max=0} {if($3>max) max=$3} END{print max}' 2>/dev/null || echo "0")
    local total_reports=$(echo "$today_data" | tail -1 | cut -d',' -f4)
    local avg_container_health=$(echo "$today_data" | awk -F',' '{sum+=$5} END {printf "%.1f", sum/NR}' 2>/dev/null || echo "0")
    local avg_response_time=$(echo "$today_data" | awk -F',' '{sum+=$6} END {printf "%.3f", sum/NR}' 2>/dev/null || echo "0")
    
    # Generate report
    cat > "$report_file" << EOF
AUTO-ADSENSE DAILY REPORT
========================
Date: $date_filter
Generated: $(date)

📊 SYSTEM METRICS
================
Total Data Points: $total_records
Average Keyword Queue: $avg_keyword_queue items
Peak Pin Jobs: $max_pin_jobs
Total Reports Generated: $total_reports
Average Container Health: $avg_container_health%
Average API Response Time: ${avg_response_time}ms

🎯 PERFORMANCE ANALYSIS
======================
$(analyze_performance "$today_data")

📈 HOURLY BREAKDOWN
==================
$(generate_hourly_breakdown "$today_data")

🔍 RECOMMENDATIONS
=================
$(generate_recommendations "$avg_keyword_queue" "$max_pin_jobs" "$avg_container_health")

EOF
    
    log "✅ Daily report saved: $report_file"
    echo "$report_file"
}

analyze_performance() {
    local data="$1"
    
    # Performance analysis
    local peak_hour=$(echo "$data" | awk -F'[, ]' '{print $2 " " $3}' | sort | uniq -c | sort -nr | head -1 | awk '{print $2 " " $3}')
    local low_queue_periods=$(echo "$data" | awk -F',' '$2 < 5 {count++} END {print count+0}')
    local high_load_periods=$(echo "$data" | awk -F',' '$3 > 20 {count++} END {print count+0}')
    
    cat << EOF
Peak Activity: $peak_hour
Low Queue Periods: $low_queue_periods times
High Load Periods: $high_load_periods times
System Stability: $(echo "$data" | awk -F',' '$5 > 80 {count++} END {printf "%.1f", (count/NR)*100}')% uptime
EOF
}

generate_hourly_breakdown() {
    local data="$1"
    
    echo "Hour | Avg Queue | Max Jobs | Health"
    echo "-----|-----------|----------|--------"
    
    for hour in {00..23}; do
        local hour_data=$(echo "$data" | grep " $hour:")
        if [[ -n "$hour_data" ]]; then
            local avg_queue=$(echo "$hour_data" | awk -F',' '{sum+=$2} END {printf "%.1f", sum/NR}')
            local max_jobs=$(echo "$hour_data" | awk -F',' 'BEGIN{max=0} {if($3>max) max=$3} END{print max}')
            local avg_health=$(echo "$hour_data" | awk -F',' '{sum+=$5} END {printf "%.0f", sum/NR}')
            printf "%2s   | %9s | %8s | %6s%%\n" "$hour" "$avg_queue" "$max_jobs" "$avg_health"
        fi
    done
}

generate_recommendations() {
    local avg_queue="$1"
    local max_jobs="$2"
    local avg_health="$3"
    
    local recommendations=""
    
    # Queue analysis
    if (( $(echo "$avg_queue < 5" | bc -l) )); then
        recommendations="🔄 Consider increasing keyword generation frequency\n"
    elif (( $(echo "$avg_queue > 50" | bc -l) )); then
        recommendations="⚠️  High keyword queue - consider scaling Pinterest workers\n"
    fi
    
    # Job analysis
    if (( max_jobs > 30 )); then
        recommendations="${recommendations}📈 Peak pin job load detected - monitor poster worker performance\n"
    fi
    
    # Health analysis
    if (( $(echo "$avg_health < 90" | bc -l) )); then
        recommendations="${recommendations}🏥 Container health below optimal - check for restarts/failures\n"
    fi
    
    # Default recommendation
    if [[ -z "$recommendations" ]]; then
        recommendations="✅ System performing optimally - no immediate actions required\n"
    fi
    
    echo -e "$recommendations"
}

show_live_analytics() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}               ${YELLOW}LIVE ANALYTICS DASHBOARD${NC}                ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo
    
    while true; do
        clear
        echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║${NC}               ${YELLOW}LIVE ANALYTICS DASHBOARD${NC}                ${CYAN}║${NC}"
        echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
        echo -e "${BLUE}$(date '+%Y-%m-%d %H:%M:%S')${NC} | Refresh: 30s | Press Ctrl+C to exit"
        echo
        
        # Collect and display current metrics
        local current_metrics=$(collect_metrics)
        echo -e "${PURPLE}📊 CURRENT METRICS${NC}"
        echo -e "${PURPLE}═══════════════════${NC}"
        echo "$current_metrics" | tail -1 | awk -F',' -v green="$GREEN" -v yellow="$YELLOW" -v cyan="$CYAN" -v nc="$NC" '
        {
            printf "Timestamp:         %s%s%s\n", cyan, $1, nc
            printf "Keyword Queue:     %s%s%s items\n", ($2<5?yellow:green), $2, nc
            printf "Pin Jobs:          %s%s%s pending\n", ($3>20?yellow:green), $3, nc
            printf "Total Reports:     %s%s%s\n", cyan, $4, nc
            printf "Active Workflows:  %s%s%s\n", green, $5, nc
            printf "Container Health:  %s%.1f%%%s\n", ($6<90?yellow:green), $6, nc
            printf "API Response:      %s%.1fms%s\n", ($7>100?yellow:green), $7, nc
        }'
        echo
        
        # Show trend for last hour
        local last_hour_data=$(tail -120 "$ANALYTICS_DIR/analytics.csv" 2>/dev/null | tail -n +2)
        if [[ -n "$last_hour_data" ]]; then
            echo -e "${PURPLE}📈 LAST HOUR TREND${NC}"
            echo -e "${PURPLE}═══════════════════${NC}"
            
            local trend_queue=$(echo "$last_hour_data" | awk -F',' 'NR==1{first=$2} END{trend=($2-first); if(trend>0) print "↗️ +"trend; else if(trend<0) print "↘️ "trend; else print "➡️ stable"}')
            local trend_jobs=$(echo "$last_hour_data" | awk -F',' 'NR==1{first=$3} END{trend=($3-first); if(trend>0) print "↗️ +"trend; else if(trend<0) print "↘️ "trend; else print "➡️ stable"}')
            
            echo -e "Queue Trend:    $trend_queue"
            echo -e "Jobs Trend:     $trend_jobs"
        fi
        
        echo
        echo -e "${PURPLE}💡 QUICK ACTIONS${NC}"
        echo -e "${PURPLE}════════════════${NC}"
        echo -e "${CYAN}  ./scripts/monitor.sh status${NC}    - System status"
        echo -e "${CYAN}  ./scripts/analytics.sh report${NC}  - Generate daily report" 
        echo -e "${CYAN}  ./scripts/quick-backup.sh${NC}      - Quick backup"
        
        sleep 30
    done
}

export_data() {
    local format="${1:-csv}"
    local days="${2:-7}"
    local output_file="$ANALYTICS_DIR/export_${DATE_STAMP}.${format}"
    
    log "📤 Exporting last $days days of data as $format"
    
    local cutoff_date=$(date -d "$days days ago" +%Y-%m-%d)
    
    case "$format" in
        csv)
            head -1 "$ANALYTICS_DIR/analytics.csv" > "$output_file"
            awk -F',' -v cutoff="$cutoff_date" '$1 >= cutoff' "$ANALYTICS_DIR/analytics.csv" >> "$output_file"
            ;;
        json)
            echo '{"data":[' > "$output_file"
            awk -F',' -v cutoff="$cutoff_date" '
            NR==1 {for(i=1;i<=NF;i++) headers[i]=$i; next}
            $1 >= cutoff {
                if(records > 0) printf ","
                printf "{"
                for(i=1;i<=NF;i++) {
                    if(i>1) printf ","
                    printf "\"%s\":\"%s\"", headers[i], $i
                }
                printf "}"
                records++
            }' "$ANALYTICS_DIR/analytics.csv" >> "$output_file"
            echo ']}' >> "$output_file"
            ;;
    esac
    
    log "✅ Data exported: $output_file"
    echo "$output_file"
}

show_help() {
    cat << EOF
Auto-AdSense Analytics System

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    collect              Collect current metrics (single point)
    live                 Live analytics dashboard
    report [date]        Generate daily report (default: today)
    export [format] [days] Export data (csv|json, default: csv, 7 days)
    init                 Initialize analytics system
    help                 Show this help

Examples:
    $0 collect
    $0 live
    $0 report 2024-12-21
    $0 export json 30
    $0 init

Data Collected:
- Keyword queue sizes
- Pin job volumes  
- Container health metrics
- API response times
- Workflow activity
- System performance
EOF
}

main() {
    case "${1:-collect}" in
        init)
            init_analytics
            ;;
        collect)
            init_analytics
            collect_metrics
            ;;
        live)
            init_analytics
            show_live_analytics
            ;;
        report)
            init_analytics
            generate_daily_report "${2:-$(date +%Y-%m-%d)}"
            ;;
        export)
            init_analytics
            export_data "${2:-csv}" "${3:-7}"
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
trap 'echo -e "\n${YELLOW}Analytics stopped.${NC}"; exit 0' INT

main "$@"
