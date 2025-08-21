import os, json, time, random, redis

r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), port=int(os.getenv("REDIS_PORT","6379")), decode_responses=True)

def post_to_tailwind(job): 
    time.sleep(random.randint(2,5))
    return {"status":"ok","id":f"tw_{int(time.time())}"}

def post_to_pinterest(job): 
    time.sleep(random.randint(2,5))
    return {"status":"ok","id":f"pin_{int(time.time())}"}

USE_TAILWIND = bool(os.getenv("TAILWIND_API_KEY"))

while True:
    job_raw = r.rpop("pin_jobs")
    if not job_raw: 
        time.sleep(10)
        continue
        
    job = json.loads(job_raw)
    res = post_to_tailwind(job) if USE_TAILWIND else post_to_pinterest(job)
    r.lpush("reports", json.dumps({"event":"posted","res":res,"job":job,"ts":time.time()}))
    # Best-effort cleanup of temporary image files to prevent disk leaks
    image_path = job.get("image_path")
    if image_path and os.path.exists(image_path):
        try:
            os.remove(image_path)
        except Exception:
            pass
    time.sleep(random.randint(20,80))
