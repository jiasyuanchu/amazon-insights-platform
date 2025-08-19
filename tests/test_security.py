"""
Tests for security functionality
"""
import pytest
from fastapi import Request
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from src.app.core.security import (
    security_manager,
    sanitize_input,
    validate_asin,
    generate_csrf_token,
    verify_csrf_token
)
from src.app.core.rate_limiter import rate_limiter, RateLimitResult


class TestSecurityManager:
    """Test security manager functionality"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "test_password_123!"
        
        # Hash password
        hashed = security_manager.hash_password(password)
        assert hashed != password
        assert len(hashed) > 20  # bcrypt hashes are long
        
        # Verify correct password
        assert security_manager.verify_password(password, hashed)
        
        # Verify incorrect password
        assert not security_manager.verify_password("wrong_password", hashed)
    
    def test_jwt_token_creation_and_verification(self):
        """Test JWT token creation and verification"""
        data = {"sub": "test_user", "role": "user"}
        
        # Create token
        token = security_manager.create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long
        
        # Verify token
        payload = security_manager.verify_token(token)
        assert payload["sub"] == "test_user"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_jwt_token_expiry(self):
        """Test JWT token expiry"""
        data = {"sub": "test_user"}
        short_expiry = timedelta(seconds=-1)  # Already expired
        
        # Create expired token
        expired_token = security_manager.create_access_token(data, short_expiry)
        
        # Verify token should fail
        with pytest.raises(Exception):  # HTTPException in real usage
            security_manager.verify_token(expired_token)
    
    def test_refresh_token_creation(self):
        """Test refresh token creation"""
        data = {"sub": "test_user"}
        
        refresh_token = security_manager.create_refresh_token(data)
        assert isinstance(refresh_token, str)
        
        # Verify as refresh token
        payload = security_manager.verify_token(refresh_token, "refresh")
        assert payload["sub"] == "test_user"
        assert payload["type"] == "refresh"
    
    def test_api_key_generation(self):
        """Test API key generation"""
        user_id = 123
        
        api_key = security_manager.generate_api_key(user_id)
        
        assert api_key.startswith("aip_")
        assert len(api_key.split("_")) == 3
        assert len(api_key) > 40  # Should be reasonably long
    
    def test_password_strength_validation(self):
        """Test password strength validation"""
        # Strong password
        strong_password = "StrongP@ssw0rd123!"
        issues = security_manager.validate_password_strength(strong_password)
        assert len(issues) == 0
        
        # Weak passwords
        weak_passwords = [
            "123",  # Too short
            "password",  # No uppercase, numbers, special chars
            "PASSWORD",  # No lowercase, numbers, special chars  
            "Password",  # No numbers, special chars
            "Password123",  # No special chars
            "letmein123!"  # Common weak pattern
        ]
        
        for weak_pwd in weak_passwords:
            issues = security_manager.validate_password_strength(weak_pwd)
            assert len(issues) > 0


class TestInputValidation:
    """Test input validation functions"""
    
    def test_input_sanitization(self):
        """Test input sanitization"""
        # Basic sanitization
        clean_input = "Hello World"
        assert sanitize_input(clean_input) == "Hello World"
        
        # Remove script tags
        malicious_input = "<script>alert('xss')</script>Hello"
        sanitized = sanitize_input(malicious_input)
        assert "<script>" not in sanitized
        assert "Hello" in sanitized
        
        # Remove iframe
        iframe_input = "<iframe src='evil.com'></iframe>Safe text"
        sanitized = sanitize_input(iframe_input)
        assert "<iframe>" not in sanitized
        assert "Safe text" in sanitized
        
        # Length limiting
        long_input = "x" * 1000
        sanitized = sanitize_input(long_input, max_length=100)
        assert len(sanitized) <= 100
        
        # Remove null bytes
        null_input = "test\x00malicious"
        sanitized = sanitize_input(null_input)
        assert "\x00" not in sanitized
        assert sanitized == "testmalicious"
    
    def test_asin_validation(self):
        """Test ASIN validation"""
        # Valid ASINs
        valid_asins = [
            "B08N5WRWNW",
            "B0123456789", 
            "A123456789"
        ]
        
        for asin in valid_asins:
            assert validate_asin(asin)
        
        # Invalid ASINs
        invalid_asins = [
            "B08N5WRWN",  # Too short
            "B08N5WRWNWA",  # Too long
            "B08N5WRW W",  # Contains space
            "b08n5wrwnw",  # Wrong case
            "B08N5WRW-W",  # Contains dash
            "",  # Empty
            None,  # None
            123  # Not string
        ]
        
        for asin in invalid_asins:
            assert not validate_asin(asin)


class TestCSRFProtection:
    """Test CSRF protection"""
    
    def test_csrf_token_generation(self):
        """Test CSRF token generation"""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        
        assert isinstance(token1, str)
        assert isinstance(token2, str)
        assert len(token1) > 20
        assert token1 != token2  # Should be unique
    
    def test_csrf_token_verification(self):
        """Test CSRF token verification"""
        token = generate_csrf_token()
        
        # Valid verification
        assert verify_csrf_token(token, token)
        
        # Invalid verification
        other_token = generate_csrf_token()
        assert not verify_csrf_token(token, other_token)
        assert not verify_csrf_token(token, "invalid")
        assert not verify_csrf_token(token, "")


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def setup_method(self):
        """Setup test method"""
        self.mock_request = Mock(spec=Request)
        self.mock_request.client = Mock()
        self.mock_request.client.host = "127.0.0.1"
        self.mock_request.headers = {"user-agent": "test"}
        self.mock_request.state = Mock()
        self.mock_request.state.user_id = None
    
    @pytest.mark.asyncio
    async def test_client_identification(self):
        """Test client identification"""
        # IP-based identification
        identifier = rate_limiter._get_client_identifier(self.mock_request)
        assert identifier.startswith("ip:")
        
        # User-based identification
        self.mock_request.state.user_id = 123
        identifier = rate_limiter._get_client_identifier(self.mock_request)
        assert identifier == "user:123"
    
    def test_key_generation(self):
        """Test Redis key generation"""
        key = rate_limiter._generate_key("user:123", "default", "minute")
        assert key == "ratelimit:default:minute:user:123"
    
    def test_client_ip_extraction(self):
        """Test client IP extraction"""
        # Direct IP
        self.mock_request.headers = {}
        ip = rate_limiter._get_client_ip(self.mock_request)
        assert ip == "127.0.0.1"
        
        # X-Forwarded-For header
        self.mock_request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        ip = rate_limiter._get_client_ip(self.mock_request)
        assert ip == "192.168.1.1"
        
        # X-Real-IP header
        self.mock_request.headers = {"x-real-ip": "192.168.1.2"}
        ip = rate_limiter._get_client_ip(self.mock_request)
        assert ip == "192.168.1.2"
    
    def test_rate_limit_result(self):
        """Test rate limit result structure"""
        result = RateLimitResult(
            allowed=True,
            remaining=50,
            reset_time=1234567890
        )
        
        assert result.allowed is True
        assert result.remaining == 50
        assert result.reset_time == 1234567890
        assert result.retry_after is None
        
        # Test with retry_after
        blocked_result = RateLimitResult(
            allowed=False,
            remaining=0,
            reset_time=1234567890,
            retry_after=60
        )
        
        assert blocked_result.allowed is False
        assert blocked_result.retry_after == 60


@pytest.mark.asyncio
async def test_rate_limit_decorator_integration():
    """Test rate limit decorator integration"""
    from src.app.core.rate_limiter import create_rate_limit_decorator
    
    # Create a mock rate limit decorator
    rate_limit_test = create_rate_limit_decorator("default")
    
    # Mock function
    @rate_limit_test
    async def test_endpoint(request: Request):
        return {"message": "success"}
    
    # Mock request
    mock_request = Mock(spec=Request)
    mock_request.client = Mock()
    mock_request.client.host = "127.0.0.1"
    mock_request.headers = {"user-agent": "test"}
    mock_request.state = Mock()
    mock_request.state.user_id = None
    
    # This test would need a real Redis instance to work fully
    # For now, we just verify the decorator structure
    assert callable(test_endpoint)


class TestSecurityIntegration:
    """Integration tests for security components"""
    
    def test_security_headers_application(self):
        """Test security headers are properly applied"""
        from src.app.core.security import SecurityHeaders
        from fastapi import Response
        
        response = Response()
        secured_response = SecurityHeaders.add_security_headers(response)
        
        # Check required security headers
        assert secured_response.headers["X-Content-Type-Options"] == "nosniff"
        assert secured_response.headers["X-Frame-Options"] == "DENY"
        assert secured_response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Strict-Transport-Security" in secured_response.headers
        assert "Referrer-Policy" in secured_response.headers
        assert "Permissions-Policy" in secured_response.headers
    
    def test_middleware_request_processing(self):
        """Test middleware request processing flow"""
        # This would require more complex setup with FastAPI test client
        # For now, we verify the middleware classes exist and are importable
        from src.app.core.middleware import (
            SecurityMiddleware,
            RequestLoggingMiddleware,
            CSRFProtectionMiddleware
        )
        
        assert SecurityMiddleware is not None
        assert RequestLoggingMiddleware is not None
        assert CSRFProtectionMiddleware is not None