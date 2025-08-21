import os, json, time, random, datetime, redis
from generate_text import draft_description, pick_hashtags

print("=== Simple Pin Worker Started ===", flush=True)

r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), port=int(os.getenv("REDIS_PORT","6379")), decode_responses=True)
print("Redis connected successfully", flush=True)

DOMAIN_ROTATION = [d.strip() for d in os.getenv("DOMAIN_ROTATION","").split(",") if d.strip()]
print(f"Domain rotation: {DOMAIN_ROTATION}", flush=True)

def build_job(keyword: str):
    desc = draft_description(keyword)
    tags = pick_hashtags(keyword)
    link = random.choice(DOMAIN_ROTATION) if DOMAIN_ROTATION else "https://example.com"
    
    return {
        "keyword": keyword, 
        "description": desc, 
        "hashtags": tags, 
        "target_url": link,
        "image_generated": False  # Skip image generation for now
    }

iteration = 0
while True:
    try:
        iteration += 1
        print(f"=== Iteration {iteration} ===", flush=True)
        
        kw = r.rpop("keyword_queue") 
        if not kw: 
            print("No keywords in queue, waiting...", flush=True)
            time.sleep(10)
            continue
        
        print(f"Processing keyword: {kw}", flush=True)
        job = build_job(kw)
        r.lpush("pin_jobs", json.dumps(job))
        r.lpush("reports", json.dumps({"ts": time.time(), "event": "processed", "kw": kw}))
        print(f"Job created for keyword: {kw}", flush=True)
        
        time.sleep(5)  # Short delay for testing
        
    except Exception as e:
        print(f"Error: {e}", flush=True)
        r.lpush("reports", json.dumps({"ts": time.time(), "event": "error", "error": str(e)}))
        time.sleep(5)

    # Break after 5 iterations for testing
    if iteration >= 5:
        print("Test complete, stopping worker", flush=True)
        break