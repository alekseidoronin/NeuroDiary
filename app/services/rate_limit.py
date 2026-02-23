from fastapi import Request, HTTPException
from app.config import settings
from redis.asyncio import Redis

# Using a single redis connection pool
redis = Redis.from_url(settings.REDIS_URL, decode_responses=True, encoding="utf-8")

async def check_admin_rate_limit(request: Request):
    """
    Check if the IP is rate-limited for admin login attempts.
    Raises 429 if limit exceeded.
    """
    # Get real IP behind proxy (Traefik/Cloudflare)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"

    key = f"admin_login_fails:{ip}"
    
    # Check if blocked
    fails = await redis.get(key)
    if fails and int(fails) >= 5:
        raise HTTPException(status_code=429, detail="Слишком много попыток входа. Попробуйте через 15 минут.")

async def record_failed_login(request: Request):
    """
    Increment failed login attempt counter for the IP.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
        
    key = f"admin_login_fails:{ip}"
    
    async with redis.pipeline() as pipe:
        await pipe.incr(key)
        await pipe.expire(key, 900) # 15 minutes TTL
        await pipe.execute()

async def reset_failed_login(request: Request):
    """
    Reset failed login counter on successful login.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    
    key = f"admin_login_fails:{ip}"
    await redis.delete(key)
