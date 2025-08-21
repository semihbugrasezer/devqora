import os, json, time, random, datetime, redis
from generate_text import draft_description, pick_hashtags
from generate_image import make_pin_image

r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), port=int(os.getenv("REDIS_PORT","6379")), decode_responses=True)

DOMAIN_ROTATION = [d.strip() for d in os.getenv("DOMAIN_ROTATION","").split(",") if d.strip()]
WINDOW_START = os.getenv("WINDOW_START","08:00")
WINDOW_END = os.getenv("WINDOW_END","22:30")

def in_window():
    now = datetime.datetime.now().time()
    s_h,s_m = map(int, WINDOW_START.split(":"))
    e_h,e_m = map(int, WINDOW_END.split(":"))
    start_t = datetime.time(s_h,s_m)
    end_t = datetime.time(e_h,e_m)
    return (start_t <= now <= end_t) if start_t <= end_t else (now >= start_t or now <= end_t)

def schedule_delay(): 
    return random.randint(600, 2400)

def build_job(keyword: str):
    desc = draft_description(keyword)
    tags = pick_hashtags(keyword)
    link = random.choice(DOMAIN_ROTATION) if DOMAIN_ROTATION else "https://example.com"
    out_img = f"/tmp/pin_{int(time.time())}.jpg"
    make_pin_image(keyword, out_img)
    
    return {
        "keyword": keyword, 
        "description": desc, 
        "hashtags": tags, 
        "image_path": out_img, 
        "target_url": link
    }

print("Pin worker started...")

while True:
    try:
        print(f"Checking window... Current time: {datetime.datetime.now().time()}")
        
        if not in_window(): 
            print("Outside time window, sleeping...")
            time.sleep(60)
            continue
        
        print("Inside time window, processing...")    
        
        if random.random() < 0.3: 
            print("Random sleep activated")
            time.sleep(60)
            continue
            
        kw = r.rpop("keyword_queue") 
        if not kw: 
            print("No keywords in queue")
            time.sleep(30)
            continue
        
        print(f"Processing keyword: {kw}")
        job = build_job(kw)
        r.lpush("pin_jobs", json.dumps(job))
        r.lpush("reports", json.dumps({"ts": time.time(), "event": "enqueued", "kw": kw}))
        print(f"Job created for keyword: {kw}")
        
    except Exception as e:
        print(f"Error: {e}")
        r.lpush("reports", json.dumps({"ts": time.time(), "event": "error", "error": str(e)}))
        
    delay = schedule_delay()
    print(f"Sleeping for {delay} seconds...")
    time.sleep(delay)
