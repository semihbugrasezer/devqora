#!/usr/bin/env python3
import requests
import json
import time

print("=== FULL SYSTEM TEST ===")

# Test 1: Content API
print("\n1. Testing Content API...")
try:
    health_response = requests.get("http://localhost:7055/health")
    print(f"Health check: {health_response.status_code} - {health_response.json()}")
    
    # Create test content
    content_data = {
        "domain": "hing.me",
        "title": "System Test Article - Auto Generated",
        "body": "This article was automatically generated during system testing. It demonstrates the full content creation pipeline working properly."
    }
    
    create_response = requests.post("http://localhost:7055/ingest", json=content_data)
    print(f"Content creation: {create_response.status_code} - {create_response.json()}")
    
except Exception as e:
    print(f"Content API error: {e}")

# Test 2: Pinterest Bot API
print("\n2. Testing Pinterest Bot API...")
try:
    bot_health = requests.get("http://localhost:7001/health")
    print(f"Bot health: {bot_health.status_code} - {bot_health.json()}")
    
    # Check stats before
    stats_before = requests.get("http://localhost:7001/stats").json()
    print(f"Stats before: {stats_before}")
    
    # Add keyword
    keyword_data = {"keyword": "system test automation"}
    enqueue_response = requests.post("http://localhost:7001/enqueue/keyword", json=keyword_data)
    print(f"Keyword enqueue: {enqueue_response.status_code} - {enqueue_response.json()}")
    
    # Check stats after
    stats_after = requests.get("http://localhost:7001/stats").json()
    print(f"Stats after: {stats_after}")
    
except Exception as e:
    print(f"Bot API error: {e}")

# Test 3: n8n availability
print("\n3. Testing n8n...")
try:
    n8n_health = requests.get("http://localhost:7056/healthz")
    print(f"n8n health: {n8n_health.status_code} - {n8n_health.json()}")
except Exception as e:
    print(f"n8n error: {e}")

print("\n=== SYSTEM TEST COMPLETE ===")
print("\nNext steps:")
print("1. Import workflow to n8n: http://localhost:7056")
print("2. Use: /srv/auto-adsense/n8n_simple_working_workflow.json")
print("3. Activate the workflow for automation")
print("4. Monitor with: bash /srv/auto-adsense/scripts/health.sh")