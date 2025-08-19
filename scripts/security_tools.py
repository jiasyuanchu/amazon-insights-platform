#!/usr/bin/env python3
"""
Security management tools for Amazon Insights Platform
"""
import asyncio
import argparse
import sys
import secrets
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import structlog

# Add src to path for imports
sys.path.append("src")

from src.app.core.config import settings
from src.app.core.database import get_db
from src.app.core.security import security_manager
from src.app.core.redis import get_redis_client
from src.app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = structlog.get_logger()


class SecurityManager:
    """Security management utilities"""
    
    def __init__(self):
        self.redis = None
        self.db = None
    
    async def init_connections(self):
        """Initialize database and Redis connections"""
        self.redis = await get_redis_client()
        
    async def close_connections(self):
        """Close connections"""
        if self.redis:
            await self.redis.close()
    
    async def generate_api_key(self, username: str) -> Optional[str]:
        """Generate API key for a user"""
        try:
            async for db in get_db():
                result = await db.execute(
                    select(User).where(User.username == username)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    print(f"❌ User '{username}' not found")
                    return None
                
                api_key = security_manager.generate_api_key(user.id)
                
                print(f"✅ API key generated for user '{username}':")
                print(f"   API Key: {api_key}")
                print(f"   User ID: {user.id}")
                print(f"   Generated: {datetime.utcnow().isoformat()}Z")
                print()
                print("⚠️  IMPORTANT: Store this API key securely. It cannot be retrieved again.")
                print("   Use it in requests with header: X-API-Key: <api_key>")
                
                return api_key
                
        except Exception as e:
            print(f"❌ Error generating API key: {str(e)}")
            return None
    
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate an API key format"""
        if not api_key.startswith("aip_"):
            print("❌ Invalid API key format - must start with 'aip_'")
            return False
        
        parts = api_key.split("_")
        if len(parts) != 3:
            print("❌ Invalid API key structure")
            return False
        
        if len(parts[1]) != 8:
            print("❌ Invalid user hash length")
            return False
        
        if len(parts[2]) < 20:
            print("❌ Invalid random part length")
            return False
        
        print("✅ API key format is valid")
        return True
    
    async def check_rate_limits(self, identifier: str = None) -> Dict[str, Any]:
        """Check current rate limits"""
        try:
            if not self.redis:
                await self.init_connections()
            
            if identifier:
                pattern = f"ratelimit:*:*:{identifier}"
            else:
                pattern = "ratelimit:*"
            
            keys = await self.redis.keys(pattern)
            
            if not keys:
                print("📊 No active rate limits found")
                return {}
            
            print(f"📊 Found {len(keys)} active rate limit entries")
            
            # Group by rule and identifier
            stats = {}
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 4:
                    rule = parts[1]
                    window = parts[2]
                    ident = ":".join(parts[3:])
                    
                    if rule not in stats:
                        stats[rule] = {}
                    if ident not in stats[rule]:
                        stats[rule][ident] = {}
                    
                    count = await self.redis.zcard(key)
                    ttl = await self.redis.ttl(key)
                    
                    stats[rule][ident][window] = {
                        "count": count,
                        "ttl": ttl
                    }
            
            # Display stats
            for rule, identifiers in stats.items():
                print(f"\n🔒 Rule: {rule}")
                for ident, windows in identifiers.items():
                    print(f"  👤 {ident}:")
                    for window, data in windows.items():
                        print(f"    📅 {window}: {data['count']} requests (TTL: {data['ttl']}s)")
            
            return stats
            
        except Exception as e:
            print(f"❌ Error checking rate limits: {str(e)}")
            return {}
    
    async def clear_rate_limits(self, identifier: str = None, rule: str = None) -> bool:
        """Clear rate limits"""
        try:
            if not self.redis:
                await self.init_connections()
            
            if identifier and rule:
                pattern = f"ratelimit:{rule}:*:{identifier}"
            elif identifier:
                pattern = f"ratelimit:*:*:{identifier}"
            elif rule:
                pattern = f"ratelimit:{rule}:*"
            else:
                pattern = "ratelimit:*"
            
            keys = await self.redis.keys(pattern)
            
            if not keys:
                print("📊 No rate limit entries found to clear")
                return True
            
            await self.redis.delete(*keys)
            print(f"✅ Cleared {len(keys)} rate limit entries")
            
            # Also clear burst limits
            if identifier and rule:
                burst_pattern = f"burst:{rule}:{identifier}"
            elif identifier:
                burst_pattern = f"burst:*:{identifier}"
            elif rule:
                burst_pattern = f"burst:{rule}:*"
            else:
                burst_pattern = "burst:*"
            
            burst_keys = await self.redis.keys(burst_pattern)
            if burst_keys:
                await self.redis.delete(*burst_keys)
                print(f"✅ Cleared {len(burst_keys)} burst limit entries")
            
            return True
            
        except Exception as e:
            print(f"❌ Error clearing rate limits: {str(e)}")
            return False
    
    async def generate_secret_key(self) -> str:
        """Generate a secure secret key"""
        key = secrets.token_urlsafe(64)
        print("🔐 Generated secure secret key:")
        print(f"   SECRET_KEY={key}")
        print()
        print("⚠️  IMPORTANT: Update your .env file with this key")
        print("   Never commit secret keys to version control")
        return key
    
    async def hash_password(self, password: str) -> str:
        """Hash a password"""
        hashed = security_manager.hash_password(password)
        print("🔐 Password hashed successfully:")
        print(f"   Original: {password}")
        print(f"   Hashed: {hashed}")
        return hashed
    
    async def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        is_valid = security_manager.verify_password(password, hashed)
        if is_valid:
            print("✅ Password verification successful")
        else:
            print("❌ Password verification failed")
        return is_valid
    
    async def test_jwt_token(self, username: str) -> Optional[str]:
        """Generate and test a JWT token"""
        try:
            # Generate token
            data = {"sub": username}
            token = security_manager.create_access_token(data)
            
            print(f"🎫 JWT token generated for '{username}':")
            print(f"   Token: {token}")
            
            # Verify token
            payload = security_manager.verify_token(token)
            print(f"✅ Token verification successful:")
            print(f"   Subject: {payload.get('sub')}")
            print(f"   Expires: {datetime.fromtimestamp(payload.get('exp')).isoformat()}")
            
            return token
            
        except Exception as e:
            print(f"❌ JWT token test failed: {str(e)}")
            return None
    
    async def security_audit(self) -> Dict[str, Any]:
        """Perform basic security audit"""
        print("🔍 Starting security audit...")
        
        audit_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Check secret key strength
        secret_key = settings.SECRET_KEY
        if len(secret_key) < 32:
            audit_results["checks"]["secret_key"] = {
                "status": "FAIL",
                "message": "Secret key is too short (< 32 characters)"
            }
            print("❌ Secret key is too short")
        else:
            audit_results["checks"]["secret_key"] = {
                "status": "PASS",
                "message": "Secret key has adequate length"
            }
            print("✅ Secret key length is adequate")
        
        # Check Redis connection
        try:
            if not self.redis:
                await self.init_connections()
            
            await self.redis.ping()
            audit_results["checks"]["redis"] = {
                "status": "PASS",
                "message": "Redis connection is working"
            }
            print("✅ Redis connection is working")
        except Exception as e:
            audit_results["checks"]["redis"] = {
                "status": "FAIL",
                "message": f"Redis connection failed: {str(e)}"
            }
            print(f"❌ Redis connection failed: {str(e)}")
        
        # Check environment
        if settings.is_production:
            if settings.DEBUG:
                audit_results["checks"]["debug_mode"] = {
                    "status": "FAIL",
                    "message": "Debug mode is enabled in production"
                }
                print("❌ Debug mode enabled in production")
            else:
                audit_results["checks"]["debug_mode"] = {
                    "status": "PASS", 
                    "message": "Debug mode is disabled in production"
                }
                print("✅ Debug mode is disabled")
        
        # Check CORS settings
        if "*" in settings.BACKEND_CORS_ORIGINS:
            audit_results["checks"]["cors"] = {
                "status": "WARN",
                "message": "CORS allows all origins (*)"
            }
            print("⚠️  CORS allows all origins")
        else:
            audit_results["checks"]["cors"] = {
                "status": "PASS",
                "message": "CORS is properly configured"
            }
            print("✅ CORS is properly configured")
        
        print("\n📋 Security audit completed")
        return audit_results


async def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Security management tools for Amazon Insights Platform"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # API Key commands
    api_parser = subparsers.add_parser("api-key", help="API key management")
    api_subparsers = api_parser.add_subparsers(dest="api_action")
    
    generate_parser = api_subparsers.add_parser("generate", help="Generate API key for user")
    generate_parser.add_argument("username", help="Username to generate API key for")
    
    validate_parser = api_subparsers.add_parser("validate", help="Validate API key format")
    validate_parser.add_argument("api_key", help="API key to validate")
    
    # Rate limit commands
    rate_parser = subparsers.add_parser("rate-limit", help="Rate limit management")
    rate_subparsers = rate_parser.add_subparsers(dest="rate_action")
    
    check_parser = rate_subparsers.add_parser("check", help="Check current rate limits")
    check_parser.add_argument("--identifier", help="Check specific identifier")
    
    clear_parser = rate_subparsers.add_parser("clear", help="Clear rate limits")
    clear_parser.add_argument("--identifier", help="Clear for specific identifier")
    clear_parser.add_argument("--rule", help="Clear for specific rule")
    
    # Password commands
    pwd_parser = subparsers.add_parser("password", help="Password utilities")
    pwd_subparsers = pwd_parser.add_subparsers(dest="pwd_action")
    
    hash_parser = pwd_subparsers.add_parser("hash", help="Hash a password")
    hash_parser.add_argument("password", help="Password to hash")
    
    verify_parser = pwd_subparsers.add_parser("verify", help="Verify password against hash")
    verify_parser.add_argument("password", help="Plain password")
    verify_parser.add_argument("hashed", help="Hashed password")
    
    # Secret key command
    subparsers.add_parser("secret-key", help="Generate secure secret key")
    
    # JWT token command
    jwt_parser = subparsers.add_parser("jwt-test", help="Test JWT token generation")
    jwt_parser.add_argument("username", help="Username for token")
    
    # Security audit command
    subparsers.add_parser("audit", help="Perform security audit")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize security manager
    sec_mgr = SecurityManager()
    
    try:
        await sec_mgr.init_connections()
        
        # Route commands
        if args.command == "api-key":
            if args.api_action == "generate":
                await sec_mgr.generate_api_key(args.username)
            elif args.api_action == "validate":
                await sec_mgr.validate_api_key(args.api_key)
            else:
                api_parser.print_help()
        
        elif args.command == "rate-limit":
            if args.rate_action == "check":
                await sec_mgr.check_rate_limits(args.identifier)
            elif args.rate_action == "clear":
                await sec_mgr.clear_rate_limits(args.identifier, args.rule)
            else:
                rate_parser.print_help()
        
        elif args.command == "password":
            if args.pwd_action == "hash":
                await sec_mgr.hash_password(args.password)
            elif args.pwd_action == "verify":
                await sec_mgr.verify_password(args.password, args.hashed)
            else:
                pwd_parser.print_help()
        
        elif args.command == "secret-key":
            await sec_mgr.generate_secret_key()
        
        elif args.command == "jwt-test":
            await sec_mgr.test_jwt_token(args.username)
        
        elif args.command == "audit":
            await sec_mgr.security_audit()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        await sec_mgr.close_connections()


if __name__ == "__main__":
    asyncio.run(main())