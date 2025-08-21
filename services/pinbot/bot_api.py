import os, json, redis
from flask import Flask, request, jsonify

app = Flask(__name__)

# Try to connect to Redis; if unavailable, fall back to a simple in-memory queue
_memory_queues = {"keyword_queue": [], "pin_jobs": [], "reports": []}

def get_redis_client():
    try:
        client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", "6379")), decode_responses=True)
        # Ping to verify connectivity
        client.ping()
        return client
    except Exception:
        return None

r = get_redis_client()

@app.get("/health")
def health(): 
    return {"ok": True}

@app.post("/enqueue/keyword")
def enqueue_keyword():
    kw = request.get_json(force=True).get("keyword")
    if not kw: 
        return {"ok": False, "error":"keyword required"}, 400
    if r:
        r.lpush("keyword_queue", kw)
    else:
        _memory_queues["keyword_queue"].insert(0, kw)
    return {"ok": True, "queued": kw}

@app.get("/stats")
def stats():
    if r:
        return {
            "keyword_queue": r.llen("keyword_queue"), 
            "pin_jobs": r.llen("pin_jobs"), 
            "reports": r.llen("reports")
        }
    return {
        "keyword_queue": len(_memory_queues["keyword_queue"]),
        "pin_jobs": len(_memory_queues["pin_jobs"]),
        "reports": len(_memory_queues["reports"]) 
    }

if __name__ == "__main__": 
    # Run on port 5001 inside Docker and local for consistency
    app.run(host="0.0.0.0", port=5001)
