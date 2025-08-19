"""
Security middleware for Amazon Insights Platform
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import structlog

from src.app.core.config import settings
from src.app.core.security import SecurityHeaders
from src.app.core.rate_limiter import rate_limit_middleware

logger = structlog.get_logger()


class SecurityMiddleware:
    """Comprehensive security middleware"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request through security layers"""
        
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        try:
            # Security checks
            await self._validate_request(request)
            
            # Add security context to request
            await self._add_security_context(request)
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            response = SecurityHeaders.add_security_headers(response)
            
            # Add request tracking headers
            response.headers["X-Request-ID"] = request_id
            
            # Log successful request
            process_time = time.time() - start_time
            logger.info(
                "Request processed successfully",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time=process_time,
                user_agent=request.headers.get("user-agent", "unknown")
            )
            
            return response
            
        except HTTPException as e:
            # Handle HTTP exceptions
            process_time = time.time() - start_time
            logger.warning(
                "Request failed with HTTP exception",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=e.status_code,
                detail=e.detail,
                process_time=process_time
            )
            
            # Return error response with security headers
            response = JSONResponse(
                status_code=e.status_code,
                content={
                    "detail": e.detail,
                    "request_id": request_id,
                    "timestamp": time.time()
                }
            )
            response = SecurityHeaders.add_security_headers(response)
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Handle unexpected exceptions
            process_time = time.time() - start_time
            logger.error(
                "Request failed with unexpected error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                process_time=process_time
            )
            
            # Return generic error response
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id,
                    "timestamp": time.time()
                }
            )
            response = SecurityHeaders.add_security_headers(response)
            response.headers["X-Request-ID"] = request_id
            
            return response
    
    async def _validate_request(self, request: Request):
        """Validate request for security issues"""
        
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
        
        # Validate User-Agent header
        user_agent = request.headers.get("user-agent", "")
        if len(user_agent) > 512:  # Limit User-Agent length
            logger.warning(
                "Suspicious User-Agent header",
                user_agent=user_agent[:100],
                client_ip=self._get_client_ip(request)
            )
        
        # Check for suspicious patterns in URL
        suspicious_patterns = [
            "admin", "wp-admin", "phpmyadmin", ".env", "config",
            "backup", "db_", "database", "sql", "passwd"
        ]
        
        path_lower = request.url.path.lower()
        for pattern in suspicious_patterns:
            if pattern in path_lower:
                logger.warning(
                    "Suspicious URL pattern detected",
                    pattern=pattern,
                    path=request.url.path,
                    client_ip=self._get_client_ip(request)
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Not found"
                )
        
        # Validate query parameters
        if request.query_params:
            for key, value in request.query_params.items():
                if len(key) > 100 or len(str(value)) > 1000:
                    logger.warning(
                        "Oversized query parameter",
                        key=key[:50],
                        value_length=len(str(value)),
                        client_ip=self._get_client_ip(request)
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid request parameters"
                    )
    
    async def _add_security_context(self, request: Request):
        """Add security context to request"""
        
        # Store client IP
        request.state.client_ip = self._get_client_ip(request)
        
        # Store request timestamp
        request.state.request_timestamp = time.time()
        
        # Extract and validate headers
        request.state.user_agent = request.headers.get("user-agent", "unknown")
        request.state.referer = request.headers.get("referer", "")
        
        # Check for proxy headers
        request.state.via_proxy = any([
            request.headers.get("x-forwarded-for"),
            request.headers.get("x-real-ip"),
            request.headers.get("x-forwarded-proto")
        ])
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"


class RequestLoggingMiddleware:
    """Request logging middleware"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Log request details"""
        
        # Skip logging for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            "Incoming request",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params) if request.query_params else None,
            client_ip=getattr(request.state, 'client_ip', 'unknown'),
            user_agent=request.headers.get("user-agent", "unknown")[:100],
            request_id=getattr(request.state, 'request_id', 'unknown')
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=round(process_time, 4),
            request_id=getattr(request.state, 'request_id', 'unknown')
        )
        
        return response


class CSRFProtectionMiddleware:
    """CSRF protection middleware"""
    
    def __init__(self, app):
        self.app = app
        self.csrf_exempt_paths = [
            "/api/v1/auth/token",  # Login endpoint
            "/api/v1/health/",     # Health check
            "/metrics",            # Metrics endpoint
            "/docs",               # API docs
            "/openapi.json",       # OpenAPI spec
        ]
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Validate CSRF tokens for state-changing requests"""
        
        # Skip CSRF check for safe methods and exempt paths
        if (request.method in ["GET", "HEAD", "OPTIONS"] or
            any(request.url.path.startswith(path) for path in self.csrf_exempt_paths)):
            return await call_next(request)
        
        # Skip CSRF check for API key authentication
        if request.headers.get("x-api-key"):
            return await call_next(request)
        
        # Check CSRF token for authenticated requests
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            csrf_token = request.headers.get("x-csrf-token")
            
            if not csrf_token:
                logger.warning(
                    "Missing CSRF token",
                    path=request.url.path,
                    method=request.method,
                    client_ip=getattr(request.state, 'client_ip', 'unknown')
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token required"
                )
            
            # In a real implementation, you would validate the CSRF token
            # against a stored value or generate it from session data
            # For now, we just check that it's present and has reasonable format
            if len(csrf_token) < 16:
                logger.warning(
                    "Invalid CSRF token format",
                    path=request.url.path,
                    method=request.method,
                    client_ip=getattr(request.state, 'client_ip', 'unknown')
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid CSRF token"
                )
        
        return await call_next(request)


def setup_cors_middleware(app):
    """Setup CORS middleware"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-API-Key",
            "X-CSRF-Token",
            "X-Request-ID",
            "User-Agent",
            "Accept",
            "Accept-Language",
            "Content-Language",
            "DNT",
            "Cache-Control"
        ],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining", 
            "X-RateLimit-Reset",
            "Retry-After"
        ]
    )


def setup_security_middleware(app):
    """Setup all security middleware"""
    
    # Add middleware in reverse order (last added = first executed)
    
    # CORS (should be first)
    setup_cors_middleware(app)
    
    # Rate limiting
    app.middleware("http")(rate_limit_middleware)
    
    # CSRF Protection
    app.add_middleware(CSRFProtectionMiddleware)
    
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # Main security middleware (should be last)
    app.add_middleware(SecurityMiddleware)


__all__ = [
    "SecurityMiddleware",
    "RequestLoggingMiddleware",
    "CSRFProtectionMiddleware",
    "setup_cors_middleware",
    "setup_security_middleware"
]