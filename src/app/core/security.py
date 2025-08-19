"""
Security utilities and configurations for Amazon Insights Platform
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
import secrets
import re
import structlog

from src.app.core.config import settings
from src.app.core.database import get_db
from src.app.models.user import User

logger = structlog.get_logger()

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Security
security = HTTPBearer()


class SecurityManager:
    """Central security management class"""
    
    def __init__(self):
        self.pwd_context = pwd_context
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )
            
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Check token type
            if payload.get("type") != token_type:
                raise JWTError("Invalid token type")
                
            return payload
            
        except JWTError as e:
            logger.warning("Token verification failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def generate_api_key(self, user_id: int) -> str:
        """Generate a secure API key for a user"""
        random_part = secrets.token_urlsafe(32)
        user_part = hashlib.sha256(str(user_id).encode()).hexdigest()[:8]
        return f"aip_{user_part}_{random_part}"
    
    def validate_password_strength(self, password: str) -> List[str]:
        """Validate password strength and return list of issues"""
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
            
        if not re.search(r"[A-Z]", password):
            issues.append("Password must contain at least one uppercase letter")
            
        if not re.search(r"[a-z]", password):
            issues.append("Password must contain at least one lowercase letter")
            
        if not re.search(r"\d", password):
            issues.append("Password must contain at least one number")
            
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            issues.append("Password must contain at least one special character")
            
        # Check for common weak passwords
        weak_patterns = [
            r"password", r"123456", r"qwerty", r"admin", 
            r"letmein", r"welcome", r"monkey"
        ]
        
        password_lower = password.lower()
        for pattern in weak_patterns:
            if re.search(pattern, password_lower):
                issues.append("Password contains common weak patterns")
                break
        
        return issues


# Global security manager instance
security_manager = SecurityManager()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    
    try:
        # Verify token
        payload = security_manager.verify_token(credentials.credentials)
        username: str = payload.get("sub")
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload invalid"
            )
        
        # Get user from database
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        # Log successful authentication
        logger.info(
            "User authenticated",
            user_id=user.id,
            username=user.username
        )
        
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (additional check)"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


def require_permissions(required_permissions: List[str]):
    """Dependency to check user permissions"""
    def permission_dependency(
        current_user: User = Depends(get_current_active_user)
    ):
        # Basic implementation - extend based on your permission system
        if not current_user.is_superuser:
            # Check if user has required permissions
            # This is a placeholder - implement based on your needs
            pass
        return current_user
    
    return permission_dependency


class APIKeyAuth:
    """API Key authentication for programmatic access"""
    
    def __init__(self):
        self.api_key_header = "X-API-Key"
    
    async def __call__(
        self, 
        request: Request,
        db: AsyncSession = Depends(get_db)
    ) -> User:
        """Authenticate request using API key"""
        
        api_key = request.headers.get(self.api_key_header)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required"
            )
        
        # Validate API key format
        if not api_key.startswith("aip_"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key format"
            )
        
        # Extract user ID from API key
        try:
            parts = api_key.split("_")
            if len(parts) != 3:
                raise ValueError("Invalid API key structure")
            
            user_hash = parts[1]
            
            # Find user by API key hash match
            # Note: In production, store API keys hashed in database
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            for user in users:
                expected_hash = hashlib.sha256(str(user.id).encode()).hexdigest()[:8]
                if expected_hash == user_hash:
                    if not user.is_active:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="User account is disabled"
                        )
                    
                    logger.info(
                        "API key authentication successful",
                        user_id=user.id,
                        username=user.username
                    )
                    return user
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
            
        except Exception as e:
            logger.warning("API key authentication failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )


# API Key authentication instance
api_key_auth = APIKeyAuth()


def sanitize_input(input_str: str, max_length: int = 255) -> str:
    """Sanitize user input to prevent XSS and injection attacks"""
    if not isinstance(input_str, str):
        return str(input_str)
    
    # Remove null bytes
    cleaned = input_str.replace('\x00', '')
    
    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    # Remove dangerous HTML/script tags
    dangerous_patterns = [
        r'<script.*?</script>',
        r'<iframe.*?</iframe>',
        r'<object.*?</object>',
        r'<embed.*?>',
        r'<applet.*?</applet>',
        r'javascript:',
        r'vbscript:',
        r'on\w+\s*=',
    ]
    
    for pattern in dangerous_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    return cleaned.strip()


def validate_asin(asin: str) -> bool:
    """Validate Amazon ASIN format"""
    if not isinstance(asin, str):
        return False
    
    # ASIN should be 10 characters, alphanumeric, usually starts with B0
    if len(asin) != 10:
        return False
    
    if not asin.isalnum():
        return False
    
    # Most ASINs start with B0, but not all
    if not re.match(r'^[A-Z0-9]{10}$', asin):
        return False
    
    return True


def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, expected_token: str) -> bool:
    """Verify CSRF token"""
    return secrets.compare_digest(token, expected_token)


class SecurityHeaders:
    """Security headers middleware"""
    
    @staticmethod
    def add_security_headers(response):
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = \
            "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = \
            "geolocation=(), microphone=(), camera=()"
        
        if settings.is_production:
            response.headers["Content-Security-Policy"] = \
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        
        return response


# Export commonly used functions
__all__ = [
    "security_manager",
    "get_current_user", 
    "get_current_active_user",
    "require_permissions",
    "api_key_auth",
    "sanitize_input",
    "validate_asin",
    "generate_csrf_token",
    "verify_csrf_token",
    "SecurityHeaders"
]