"""Redis client for streaming data"""
import redis
from typing import Optional
from app.core.config import settings


class RedisClient:
    """Redis client singleton for accessing streaming data"""

    _instance: Optional['RedisClient'] = None
    _client: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password if settings.redis_password else None,
                decode_responses=True
            )

    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance"""
        if self._client is None:
            raise RuntimeError("Redis client not initialized")
        return self._client

    def ping(self) -> bool:
        """Test Redis connection"""
        try:
            return self._client.ping()
        except Exception:
            return False

    def close(self):
        """Close Redis connection"""
        if self._client:
            self._client.close()
            self._client = None


def get_redis() -> redis.Redis:
    """Dependency for getting Redis client"""
    client = RedisClient()
    return client.client
