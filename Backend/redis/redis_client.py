import os
import redis

from config import env_flag


_redis_enabled = env_flag('REDIS_ENABLED', True)
_redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# Existing imports can continue using `r`; disabled deployments receive None
# and never construct a Redis client.
r = redis.from_url(_redis_url, decode_responses=True) if _redis_enabled else None
