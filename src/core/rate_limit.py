import os
from fastapi import Request
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def init_rate_limiter():
    r = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(r)

def rl_general():
    return RateLimiter(times=None, seconds=0, limit_value=os.getenv("RATE_LIMIT_GENERAL", "100/minute"))

def rl_auth():
    return RateLimiter(times=None, seconds=0, limit_value=os.getenv("RATE_LIMIT_AUTH", "10/minute"))

def rl_upload():
    return RateLimiter(times=None, seconds=0, limit_value=os.getenv("RATE_LIMIT_UPLOAD", "10/hour"))
