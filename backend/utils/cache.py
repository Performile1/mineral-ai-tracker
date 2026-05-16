"""
Mineral AI Tracker - Redis Cache Decorator (PRD v10.0 Phase 10.4)
Version: 10.0
Description: Redis caching decorator for expensive external API calls
"""

import os
import json
import hashlib
import asyncio
from functools import wraps
from typing import Any, Callable, Optional
import redis
from loguru import logger

# Redis client for caching
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)


def redis_cache(ttl_seconds: int = 86400):
    """
    Redis cache decorator for expensive function calls (supports both sync and async)
    
    Args:
        ttl_seconds: Time to live for cached data in seconds (default: 24 hours)
    
    Usage:
        @redis_cache(ttl_seconds=3600)
        async def fetch_fundamentals(ticker: str):
            # Expensive API call
            return data
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            
            # Add arguments to key (excluding self for methods)
            for arg in args:
                if hasattr(arg, '__class__') and arg.__class__.__name__ == 'object':
                    # Skip self parameter
                    continue
                key_parts.append(str(arg))
            
            # Add keyword arguments
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            
            # Create hash of key parts
            key_string = ":".join(key_parts)
            cache_key = f"cache:{hashlib.md5(key_string.encode()).hexdigest()}"
            
            # Try to get from cache
            try:
                cached_value = redis_client.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                    return json.loads(cached_value)
            except Exception as e:
                logger.warning(f"Redis cache get failed: {e}")
            
            # Call the async function
            result = await func(*args, **kwargs)
            
            # Save to cache
            try:
                redis_client.setex(
                    cache_key,
                    ttl_seconds,
                    json.dumps(result, default=str)
                )
                logger.debug(f"Cache set for {func.__name__}: {cache_key}")
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            
            # Add arguments to key (excluding self for methods)
            for arg in args:
                if hasattr(arg, '__class__') and arg.__class__.__name__ == 'object':
                    # Skip self parameter
                    continue
                key_parts.append(str(arg))
            
            # Add keyword arguments
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            
            # Create hash of key parts
            key_string = ":".join(key_parts)
            cache_key = f"cache:{hashlib.md5(key_string.encode()).hexdigest()}"
            
            # Try to get from cache
            try:
                cached_value = redis_client.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                    return json.loads(cached_value)
            except Exception as e:
                logger.warning(f"Redis cache get failed: {e}")
            
            # Call the function
            result = func(*args, **kwargs)
            
            # Save to cache
            try:
                redis_client.setex(
                    cache_key,
                    ttl_seconds,
                    json.dumps(result, default=str)
                )
                logger.debug(f"Cache set for {func.__name__}: {cache_key}")
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")
            
            return result
        
        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


def cache_invalidate(pattern: str):
    """
    Invalidate cache entries matching a pattern
    
    Args:
        pattern: Redis key pattern to match (e.g., "cache:*")
    """
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache entries matching {pattern}")
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
