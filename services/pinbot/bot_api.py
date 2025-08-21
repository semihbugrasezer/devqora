import os, json, redis
from flask import Flask, request, jsonify

r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), port=int(os.getenv("REDIS_PORT","6379")), decode_responses=True)
app = Flask(__name__)

@app.get("/health")
def health(): 
    return {"ok": True}

@app.post("/enqueue/keyword")
def enqueue_keyword():
    kw = request.get_json(force=True).get("keyword")
    if not kw: 
        return {"ok": False, "error":"keyword required"}, 400
    r.lpush("keyword_queue", kw)
    return {"ok": True, "queued": kw}

@app.get("/stats")
def stats():
    return {
        "keyword_queue": r.llen("keyword_queue"), 
        "pin_jobs": r.llen("pin_jobs"), 
        "reports": r.llen("reports")
    }

if __name__ == "__main__": 
    app.run(host="0.0.0.0", port=5001)
