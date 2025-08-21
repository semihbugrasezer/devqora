#!/bin/bash

# Auto-Adsense Automation System Monitor
# Monitors all components and provides status overview

set -e

echo "🤖 Auto-Adsense Automation System Monitor"
echo "=========================================="
echo ""

# Check Docker services
echo "📊 Docker Services Status:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Check Content API
echo "🌐 Content API Status:"
CONTENT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:7055/health 2>/dev/null || echo "000")
if [ "$CONTENT_STATUS" = "200" ]; then
    echo "✅ Content API: Running (Port 7055)"
else
    echo "❌ Content API: Not responding (Port 7055)"
fi

# Check Bot API
echo "🤖 Bot API Status:"
BOT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:7001/health 2>/dev/null || echo "000")
if [ "$BOT_STATUS" = "200" ]; then
    echo "✅ Bot API: Running (Port 7001)"
else
    echo "❌ Bot API: Not responding (Port 7001)"
fi

# Check N8N
echo "⚙️ N8N Status:"
N8N_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:7056 2>/dev/null || echo "000")
if [ "$N8N_STATUS" = "200" ]; then
    echo "✅ N8N: Running (Port 7056)"
else
    echo "❌ N8N: Not responding (Port 7056)"
fi

echo ""

# Check Redis queues
echo "📋 Redis Queue Status:"
if command -v redis-cli >/dev/null 2>&1; then
    KEYWORD_QUEUE=$(redis-cli -h localhost -p 6379 llen keyword_queue 2>/dev/null || echo "0")
    PIN_JOBS=$(redis-cli -h localhost -p 6379 llen pin_jobs 2>/dev/null || echo "0")
    AUTOMATION_LOGS=$(redis-cli -h localhost -p 6379 llen automation_logs 2>/dev/null || echo "0")
    
    echo "📝 Keywords in queue: $KEYWORD_QUEUE"
    echo "📌 Pin jobs waiting: $PIN_JOBS"
    echo "📊 Automation logs: $AUTOMATION_LOGS"
else
    echo "ℹ️ Redis CLI not available - queue status unavailable"
fi

echo ""

# Check recent automation logs
echo "📈 Recent Automation Activity:"
if command -v redis-cli >/dev/null 2>&1; then
    RECENT_LOGS=$(redis-cli -h localhost -p 6379 lrange automation_logs 0 4 2>/dev/null || echo "[]")
    if [ "$RECENT_LOGS" != "[]" ]; then
        echo "$RECENT_LOGS" | jq -r '.timestamp + " - " + .event + ": " + (.keyword // .error // "N/A")' 2>/dev/null || echo "Logs available but jq not installed"
    else
        echo "No recent automation logs found"
    fi
else
    echo "ℹ️ Redis CLI not available - logs unavailable"
fi

echo ""

# Check site build status
echo "🏗️ Site Build Status:"
if [ -d "/srv/auto-adsense/multidomain_site_kit" ]; then
    cd /srv/auto-adsense/multidomain_site_kit
    
    for d in sites/*; do
        if [ -d "$d" ]; then
            DOMAIN=$(basename "$d")
            if [ -d "$d/dist" ]; then
                BUILD_TIME=$(stat -c %Y "$d/dist" 2>/dev/null || echo "0")
                CURRENT_TIME=$(date +%s)
                AGE_HOURS=$(( (CURRENT_TIME - BUILD_TIME) / 3600 ))
                
                if [ $AGE_HOURS -lt 24 ]; then
                    echo "✅ $DOMAIN: Built $AGE_HOURS hours ago"
                else
                    echo "⚠️ $DOMAIN: Built $AGE_HOURS hours ago (may need rebuild)"
                fi
            else
                echo "❌ $DOMAIN: Not built (no dist directory)"
            fi
        fi
    done
else
    echo "❌ Site directory not found"
fi

echo ""

# Check daily targets
echo "🎯 Daily Automation Targets:"
if command -v redis-cli >/dev/null 2>&1; then
    TODAY=$(date +%Y-%m-%d)
    DAILY_STATS=$(redis-cli -h localhost -p 6379 hgetall "daily_stats:$TODAY" 2>/dev/null || echo "")
    
    if [ -n "$DAILY_STATS" ]; then
        echo "📅 $TODAY Progress:"
        echo "$DAILY_STATS" | xargs -n 2 | while read -r key value; do
            case $key in
                "pins") echo "📌 Pins: $value/6" ;;
                "repins") echo "🔄 Repins: $value/3" ;;
                "comments") echo "💬 Comments: $value/2" ;;
                "follows") echo "👥 Follows: $value/2" ;;
            esac
        done
    else
        echo "📅 $TODAY: No activity recorded yet"
    fi
else
    echo "ℹ️ Redis CLI not available - daily stats unavailable"
fi

echo ""

# System health summary
echo "🏥 System Health Summary:"
if [ "$CONTENT_STATUS" = "200" ] && [ "$BOT_STATUS" = "200" ] && [ "$N8N_STATUS" = "200" ]; then
    echo "✅ All core services are running"
    echo "✅ Automation system is operational"
    echo "✅ Ready for daily content generation"
else
    echo "❌ Some services are not responding"
    echo "❌ Automation system may be impaired"
    echo "⚠️ Check service logs for issues"
fi

echo ""
echo "🔄 Next scheduled run: Tomorrow at 9:00 AM"
echo "📊 Monitor logs: docker compose logs -f"
echo "🔧 Restart services: docker compose restart"
