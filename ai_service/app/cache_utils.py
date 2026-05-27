import os
import json
import redis

# Use REDIS_URL from env or default to localhost for local testing outside docker
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    redis_client = None
    print(f"Failed to connect to Redis: {e}")

def get_cached_summaries(patient_id: str):
    if not redis_client:
        return None
    try:
        data = redis_client.get(f"patient_summaries:{patient_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        print(f"Redis get error: {e}")
    return None

def set_cached_summaries(patient_id: str, summaries: list):
    if not redis_client:
        return
    try:
        # Cache for 1 hour
        redis_client.setex(f"patient_summaries:{patient_id}", 3600, json.dumps(summaries))
    except Exception as e:
        print(f"Redis set error: {e}")

def invalidate_cached_summaries(patient_id: str):
    if not redis_client:
        return
    try:
        redis_client.delete(f"patient_summaries:{patient_id}")
    except Exception as e:
        print(f"Redis delete error: {e}")
