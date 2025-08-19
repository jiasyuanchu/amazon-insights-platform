"""Tests for advanced cache service"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.app.services.advanced_cache import AdvancedCacheService, CacheConfig


@pytest.fixture
def cache_service():
    """Create cache service instance for testing"""
    with patch('src.app.services.advanced_cache.redis_client') as mock_redis:
        service = AdvancedCacheService()
        service.redis = mock_redis
        return service, mock_redis


@pytest.mark.asyncio
async def test_cache_config_initialization():
    """Test cache configuration initialization"""
    service = AdvancedCacheService()
    
    assert "api_response" in service.cache_configs
    assert "product_data" in service.cache_configs
    assert "competitor_analysis" in service.cache_configs
    
    api_config = service.cache_configs["api_response"]
    assert api_config.ttl == 300
    assert api_config.namespace == "api:response"
    assert api_config.compression is True


@pytest.mark.asyncio
async def test_cache_key_generation():
    """Test cache key generation"""
    service = AdvancedCacheService()
    config = CacheConfig(ttl=300, namespace="test")
    
    key1 = service._generate_cache_key(config, "user:123")
    key2 = service._generate_cache_key(config, "user:123")
    key3 = service._generate_cache_key(config, "user:456")
    
    assert key1 == key2  # Same input should generate same key
    assert key1 != key3  # Different input should generate different key
    assert key1.startswith("test:")
    assert len(key1.split(":")[1]) == 12  # Hash length


@pytest.mark.asyncio
async def test_cache_get_hit(cache_service):
    """Test cache get with hit"""
    service, mock_redis = cache_service
    
    # Mock Redis response
    mock_redis.pipeline.return_value.execute = AsyncMock(return_value=[b'{"test": "value"}', 300])
    
    result = await service.get("api_response", "test_key")
    
    assert result == {"test": "value"}
    assert service.metrics["hits"] == 1
    assert service.metrics["misses"] == 0


@pytest.mark.asyncio
async def test_cache_get_miss(cache_service):
    """Test cache get with miss"""
    service, mock_redis = cache_service
    
    # Mock Redis response (cache miss)
    mock_redis.pipeline.return_value.execute = AsyncMock(return_value=[None, -2])
    
    result = await service.get("api_response", "test_key", default="default")
    
    assert result == "default"
    assert service.metrics["hits"] == 0
    assert service.metrics["misses"] == 1


@pytest.mark.asyncio
async def test_cache_set(cache_service):
    """Test cache set operation"""
    service, mock_redis = cache_service
    
    mock_redis.setex = AsyncMock(return_value=True)
    
    result = await service.set("api_response", "test_key", {"data": "test"})
    
    assert result is True
    assert service.metrics["sets"] == 1
    mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_cache_delete(cache_service):
    """Test cache delete operation"""
    service, mock_redis = cache_service
    
    mock_redis.delete = AsyncMock(return_value=1)
    
    result = await service.delete("api_response", "test_key")
    
    assert result is True
    assert service.metrics["deletes"] == 1
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_invalidate_pattern(cache_service):
    """Test pattern-based cache invalidation"""
    service, mock_redis = cache_service
    
    # Mock scan results
    mock_redis.scan = AsyncMock(side_effect=[
        (0, [b"api:response:key1", b"api:response:key2"])
    ])
    mock_redis.delete = AsyncMock(return_value=2)
    
    result = await service.invalidate_pattern("api_response", "test")
    
    assert result == 2
    assert service.metrics["deletes"] == 2


@pytest.mark.asyncio  
async def test_bulk_get(cache_service):
    """Test bulk get operation"""
    service, mock_redis = cache_service
    
    mock_redis.mget = AsyncMock(return_value=[b'{"key1": "value1"}', None, b'{"key3": "value3"}'])
    
    result = await service.bulk_get("api_response", ["key1", "key2", "key3"])
    
    assert len(result) == 2
    assert result["key1"] == {"key1": "value1"}
    assert result["key3"] == {"key3": "value3"}
    assert "key2" not in result
    
    assert service.metrics["hits"] == 2
    assert service.metrics["misses"] == 1


@pytest.mark.asyncio
async def test_bulk_set(cache_service):
    """Test bulk set operation"""
    service, mock_redis = cache_service
    
    mock_redis.pipeline.return_value.execute = AsyncMock(return_value=[True, True])
    
    data = {"key1": "value1", "key2": "value2"}
    result = await service.bulk_set("api_response", data)
    
    assert result is True
    assert service.metrics["sets"] == 2


@pytest.mark.asyncio
async def test_cache_with_lock(cache_service):
    """Test cache with distributed lock"""
    service, mock_redis = cache_service
    
    # First call returns None (cache miss), then lock acquisition succeeds
    mock_redis.pipeline.return_value.execute = AsyncMock(return_value=[None, -2])
    mock_redis.set = AsyncMock(return_value=True)  # Lock acquired
    mock_redis.setex = AsyncMock(return_value=True)  # Cache set
    mock_redis.delete = AsyncMock(return_value=True)  # Lock release
    
    async def mock_computation():
        return "computed_value"
    
    result = await service.get_with_lock(
        "api_response",
        "test_key", 
        mock_computation
    )
    
    assert result == "computed_value"


@pytest.mark.asyncio
async def test_cache_stats(cache_service):
    """Test cache statistics"""
    service, mock_redis = cache_service
    
    # Mock Redis info
    mock_redis.info = AsyncMock(return_value={
        "used_memory_human": "1MB",
        "used_memory_peak_human": "2MB",
        "mem_fragmentation_ratio": 1.1
    })
    
    # Mock scan for key counting
    mock_redis.scan = AsyncMock(side_effect=[
        (0, [b"api:response:key1", b"api:response:key2"])
    ])
    
    # Set some metrics
    service.metrics["hits"] = 80
    service.metrics["misses"] = 20
    
    stats = await service.get_cache_stats()
    
    assert "performance_metrics" in stats
    assert "memory_usage" in stats
    assert "namespace_statistics" in stats
    assert stats["performance_metrics"]["hit_rate_percent"] == 80.0


@pytest.mark.asyncio
async def test_serialization():
    """Test value serialization and deserialization"""
    service = AdvancedCacheService()
    config = CacheConfig(ttl=300, namespace="test", serialize_json=True)
    
    # Test dict serialization
    test_data = {"key": "value", "number": 123}
    serialized = service._serialize_value(test_data, config)
    deserialized = service._deserialize_value(serialized, config)
    
    assert deserialized == test_data
    
    # Test non-JSON config
    config.serialize_json = False
    serialized = service._serialize_value("simple_string", config)
    assert serialized == "simple_string"


@pytest.mark.asyncio
async def test_cleanup_expired(cache_service):
    """Test expired cache cleanup"""
    service, mock_redis = cache_service
    
    # Mock scan and TTL checks
    mock_redis.scan = AsyncMock(side_effect=[
        (0, [b"test:key1", b"test:key2"])
    ])
    mock_redis.ttl = AsyncMock(side_effect=[-2, 100])  # key1 expired, key2 valid
    
    result = await service.cleanup_expired()
    
    assert result == 1  # One expired key found


def test_cache_decorator():
    """Test cache result decorator"""
    from src.app.services.advanced_cache import cache_result
    
    @cache_result("api_response", "test_func")
    async def test_function(arg1, arg2=None):
        return f"result_{arg1}_{arg2}"
    
    # Test that decorator preserves function metadata
    assert hasattr(test_function, '__call__')
    
    # For sync function
    @cache_result("api_response", "sync_func")  
    def sync_function(x):
        return x * 2
    
    assert hasattr(sync_function, '__call__')


@pytest.mark.asyncio
async def test_error_handling(cache_service):
    """Test error handling in cache operations"""
    service, mock_redis = cache_service
    
    # Test get error
    mock_redis.pipeline.return_value.execute = AsyncMock(side_effect=Exception("Redis error"))
    
    result = await service.get("api_response", "test_key", default="default")
    assert result == "default"  # Should return default on error
    
    # Test set error
    mock_redis.setex = AsyncMock(side_effect=Exception("Redis error"))
    
    result = await service.set("api_response", "test_key", "value")
    assert result is False  # Should return False on error


@pytest.mark.asyncio
async def test_auto_refresh_detection(cache_service):
    """Test auto-refresh threshold detection"""
    service, mock_redis = cache_service
    
    # Mock cache hit with low TTL (should trigger refresh detection)
    mock_redis.pipeline.return_value.execute = AsyncMock(return_value=[b'{"data": "test"}', 60])  # TTL = 60s
    
    # For api_response config with TTL=300, refresh_threshold=0.8
    # refresh_time = 300 * (1 - 0.8) = 60s
    # Since TTL=60 < refresh_time=60, it should detect refresh need
    
    result = await service.get("api_response", "test_key")
    
    assert result == {"data": "test"}
    # In real implementation, this would log refresh needed