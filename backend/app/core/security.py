from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
import hashlib
import secrets
import re
from collections import defaultdict, deque
import time

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory stores for rate limiting and account lockout
# In production, these should be moved to Redis or similar
_failed_login_attempts: Dict[str, deque] = defaultdict(lambda: deque())
_blocked_ips: Dict[str, float] = {}
_locked_accounts: Dict[str, float] = {}


class SecurityService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token with enhanced security"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        
        # Add issued at time and not before time for better security
        now = datetime.now(timezone.utc)
        to_encode.update({
            "exp": expire, 
            "iat": now,
            "nbf": now,  # Not before time
            "jti": secrets.token_urlsafe(16)  # JWT ID for tracking
        })
        return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def create_refresh_token() -> str:
        """Create a secure random refresh token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for secure storage using PBKDF2"""
        # Use PBKDF2 instead of plain SHA256 for better security
        salt = secrets.token_bytes(32)
        hash_bytes = hashlib.pbkdf2_hmac('sha256', token.encode(), salt, 100000)
        # Combine salt and hash for storage
        return salt.hex() + ':' + hash_bytes.hex()
    
    @staticmethod
    def verify_token_hash(token: str, stored_hash: str) -> bool:
        """Verify a token against its stored hash"""
        try:
            salt_hex, hash_hex = stored_hash.split(':')
            salt = bytes.fromhex(salt_hex)
            stored_hash_bytes = bytes.fromhex(hash_hex)
            
            computed_hash = hashlib.pbkdf2_hmac('sha256', token.encode(), salt, 100000)
            return secrets.compare_digest(stored_hash_bytes, computed_hash)
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def verify_token(token: str, secret_key: str = None) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            secret = secret_key or settings.jwt_secret_key
            payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
            return payload
        except JWTError:
            return None

    @staticmethod
    def generate_device_id() -> str:
        """Generate a unique device identifier"""
        return secrets.token_urlsafe(16)

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """Validate password strength with enhanced security requirements"""
        # Minimum length increased to 12 characters
        if len(password) < 12:
            return False, "Password must be at least 12 characters long"
        
        # Maximum length to prevent DoS
        if len(password) > 128:
            return False, "Password must not exceed 128 characters"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"
        
        # Check for weak patterns first
        if SecurityService._has_weak_patterns(password):
            return False, "Password contains weak patterns (sequential chars, repeated chars, etc.)"
        
        # Check for common passwords  
        if SecurityService._is_common_password(password):
            return False, "Password is too common. Please choose a more unique password"
        
        return True, "Password is strong"
    
    @staticmethod
    def _has_weak_patterns(password: str) -> bool:
        """Check for weak password patterns"""
        password_lower = password.lower()
        
        # Check for sequential characters (abc, 123, etc.) - only 4+ in a row
        for i in range(len(password_lower) - 3):
            if (ord(password_lower[i]) + 1 == ord(password_lower[i + 1]) and 
                ord(password_lower[i + 1]) + 1 == ord(password_lower[i + 2]) and
                ord(password_lower[i + 2]) + 1 == ord(password_lower[i + 3])):
                return True
        
        # Check for repeated characters (aaaa, 1111, etc.) - only 4+ in a row
        for i in range(len(password) - 3):
            if password[i] == password[i + 1] == password[i + 2] == password[i + 3]:
                return True
        
        # Check for keyboard patterns - only longer ones
        keyboard_patterns = [
            "qwertyuiop", "asdfghjkl", "zxcvbnm", "1234567890"
        ]
        for pattern in keyboard_patterns:
            if pattern in password_lower:
                return True
        
        return False
    
    @staticmethod
    def _is_common_password(password: str) -> bool:
        """Check against common passwords"""
        common_passwords = {
            "password", "password13", "admin", "administrator", 
            "welcome", "welcome13", "letmein", "monkey", 
            "password1", "abc", "Password1",
            "password!", "Password13", "Welcome13", "Admin",
            "password13!", "welcome13!", "administrator!",
            "password13!test", "welcome13!test", "administrator!"
        }
        return password.lower() in {p.lower() for p in common_passwords} or password in common_passwords
    
    @staticmethod
    def check_rate_limit(ip_address: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
        """Check if IP address is within rate limits"""
        current_time = time.time()
        
        # Clean old attempts
        attempts = _failed_login_attempts[ip_address]
        while attempts and current_time - attempts[0] > window_minutes * 60:
            attempts.popleft()
        
        return len(attempts) < max_attempts
    
    @staticmethod
    def record_failed_attempt(ip_address: str) -> None:
        """Record a failed login attempt"""
        current_time = time.time()
        _failed_login_attempts[ip_address].append(current_time)
        
        # Block IP if too many attempts
        if len(_failed_login_attempts[ip_address]) >= 5:
            _blocked_ips[ip_address] = current_time + (30 * 60)  # Block for 30 minutes
    
    @staticmethod
    def is_ip_blocked(ip_address: str) -> bool:
        """Check if IP address is currently blocked"""
        if ip_address in _blocked_ips:
            if time.time() < _blocked_ips[ip_address]:
                return True
            else:
                del _blocked_ips[ip_address]
        return False
    
    @staticmethod
    def lock_account(email: str, duration_minutes: int = 30) -> None:
        """Lock an account for a specified duration"""
        _locked_accounts[email] = time.time() + (duration_minutes * 60)
    
    @staticmethod
    def is_account_locked(email: str) -> bool:
        """Check if account is currently locked"""
        if email in _locked_accounts:
            if time.time() < _locked_accounts[email]:
                return True
            else:
                del _locked_accounts[email]
        return False
    
    @staticmethod
    def clear_failed_attempts(ip_address: str) -> None:
        """Clear failed attempts for successful login"""
        if ip_address in _failed_login_attempts:
            _failed_login_attempts[ip_address].clear()
    
    @staticmethod
    def sanitize_input(input_str: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not input_str:
            return ""
        
        # Truncate to max length
        sanitized = input_str[:max_length]
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\'\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', sanitized)
        
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        
        return sanitized.strip()
    
    @staticmethod
    def validate_email_format(email: str) -> bool:
        """Validate email format with comprehensive regex"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a CSRF token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_csrf_token(token: str, expected_token: str) -> bool:
        """Validate CSRF token using timing-safe comparison"""
        return secrets.compare_digest(token, expected_token)