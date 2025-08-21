import os, json, time, random, redis

print("=== Simple Poster Worker Started ===", flush=True)

r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), port=int(os.getenv("REDIS_PORT","6379")), decode_responses=True)
print("Redis connected successfully", flush=True)

def post_to_tailwind(job): 
    print(f"Posting to Tailwind: {job['keyword']}", flush=True)
    time.sleep(2)
    return {"status":"ok","id":f"tw_{int(time.time())}","platform":"tailwind"}

def post_to_pinterest(job): 
    print(f"Posting to Pinterest: {job['keyword']}", flush=True)
    time.sleep(2)
    return {"status":"ok","id":f"pin_{int(time.time())}","platform":"pinterest"}

USE_TAILWIND = bool(os.getenv("TAILWIND_API_KEY"))
print(f"Using Tailwind: {USE_TAILWIND}", flush=True)

iteration = 0
while True:
    try:
        iteration += 1
        print(f"=== Poster Iteration {iteration} ===", flush=True)
        
        job_raw = r.rpop("pin_jobs")
        if not job_raw: 
            print("No pin jobs, waiting...", flush=True)
            time.sleep(5)
            continue
            
        job = json.loads(job_raw)
        print(f"Processing job: {job['keyword']}", flush=True)
        
        res = post_to_tailwind(job) if USE_TAILWIND else post_to_pinterest(job)
        r.lpush("reports", json.dumps({"event":"posted","res":res,"job":job,"ts":time.time()}))
        print(f"Posted successfully: {res}", flush=True)
        
        time.sleep(5)  # Short delay for testing
        
    except Exception as e:
        print(f"Poster error: {e}", flush=True)
        r.lpush("reports", json.dumps({"event":"poster_error","error":str(e),"ts":time.time()}))
        time.sleep(5)

    # Break after 3 posts for testing
    if iteration >= 3:
        print("Poster test complete, stopping", flush=True)
        break