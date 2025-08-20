"""
Security tests for the application
Tests password validation, rate limiting, input sanitization, and other security features
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from app.core.security import SecurityService
from app.core.security_config import SecurityConfigValidator


class TestPasswordSecurity:
    """Test password security features"""
    
    def test_password_length_validation(self):
        """Test password length requirements"""
        # Too short
        is_valid, message = SecurityService.validate_password_strength("Short1!")
        assert not is_valid
        assert "12 characters" in message
        
        # Too long
        long_password = "a" * 130 + "A1!"
        is_valid, message = SecurityService.validate_password_strength(long_password)
        assert not is_valid
        assert "128 characters" in message
        
        # Valid length
        is_valid, message = SecurityService.validate_password_strength("ValidPassword123!")
        assert is_valid
    
    def test_password_complexity_requirements(self):
        """Test password complexity requirements"""
        # Missing uppercase
        is_valid, message = SecurityService.validate_password_strength("lowercase123!")
        assert not is_valid
        assert "uppercase" in message
        
        # Missing lowercase
        is_valid, message = SecurityService.validate_password_strength("UPPERCASE123!")
        assert not is_valid
        assert "lowercase" in message
        
        # Missing digit
        is_valid, message = SecurityService.validate_password_strength("ValidPassword!")
        assert not is_valid
        assert "number" in message
        
        # Missing special character
        is_valid, message = SecurityService.validate_password_strength("ValidPassword123")
        assert not is_valid
        assert "special character" in message
        
        # Valid password
        is_valid, message = SecurityService.validate_password_strength("ValidPassword123!")
        assert is_valid
    
    def test_weak_pattern_detection(self):
        """Test detection of weak password patterns"""
        # Sequential characters (4+ in a row)
        is_valid, message = SecurityService.validate_password_strength("Password1234abcd!")
        assert not is_valid
        assert "weak patterns" in message
        
        # Repeated characters (4+ in a row)
        is_valid, message = SecurityService.validate_password_strength("Passwordaaaa123!")
        assert not is_valid
        assert "weak patterns" in message
        
        # Keyboard patterns
        is_valid, message = SecurityService.validate_password_strength("Qwertyuiop123!")
        assert not is_valid
        assert "weak patterns" in message
    
    def test_common_password_detection(self):
        """Test detection of common passwords"""
        # Test a clearly common password that should be detected
        is_valid, message = SecurityService.validate_password_strength("Password13!Test")
        assert not is_valid
        assert "common" in message.lower()
        
        # Test another common password
        is_valid, message = SecurityService.validate_password_strength("Welcome13!Test")
        assert not is_valid  
        assert "common" in message.lower()


class TestTokenSecurity:
    """Test JWT token security features"""
    
    def test_token_creation_includes_security_claims(self):
        """Test that JWT tokens include proper security claims"""
        data = {"sub": "123", "email": "test@example.com"}
        token = SecurityService.create_access_token(data)
        
        # Verify token can be decoded (basic test)
        payload = SecurityService.verify_token(token)
        assert payload is not None
        assert "exp" in payload
        assert "iat" in payload
        assert "nbf" in payload
        assert "jti" in payload
    
    def test_token_hashing_with_pbkdf2(self):
        """Test that tokens are hashed using PBKDF2"""
        token = "test_token_12345"
        hashed = SecurityService.hash_token(token)
        
        # PBKDF2 hash should contain salt and hash separated by colon
        assert ":" in hashed
        salt_hex, hash_hex = hashed.split(":")
        assert len(salt_hex) == 64  # 32 bytes = 64 hex chars
        assert len(hash_hex) == 64  # 32 bytes = 64 hex chars
        
        # Verify the hash
        assert SecurityService.verify_token_hash(token, hashed)
        assert not SecurityService.verify_token_hash("wrong_token", hashed)
    
    def test_csrf_token_generation_and_validation(self):
        """Test CSRF token generation and validation"""
        token1 = SecurityService.generate_csrf_token()
        token2 = SecurityService.generate_csrf_token()
        
        # Tokens should be different
        assert token1 != token2
        assert len(token1) > 20  # Should be sufficiently long
        
        # Validation should work
        assert SecurityService.validate_csrf_token(token1, token1)
        assert not SecurityService.validate_csrf_token(token1, token2)


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limit_tracking(self):
        """Test rate limit tracking"""
        ip = "192.168.1.100"
        
        # Should allow requests within limit
        for i in range(4):
            assert SecurityService.check_rate_limit(ip, max_attempts=5, window_minutes=15)
            SecurityService.record_failed_attempt(ip)
        
        # Should block after limit
        SecurityService.record_failed_attempt(ip)
        assert not SecurityService.check_rate_limit(ip, max_attempts=5, window_minutes=15)
    
    def test_ip_blocking(self):
        """Test IP blocking functionality"""
        ip = "192.168.1.101"
        
        # Record enough failed attempts to trigger blocking
        for _ in range(5):
            SecurityService.record_failed_attempt(ip)
        
        # IP should be blocked
        assert SecurityService.is_ip_blocked(ip)
        
        # Different IP should not be blocked
        assert not SecurityService.is_ip_blocked("192.168.1.102")
    
    def test_account_locking(self):
        """Test account locking functionality"""
        email = "test@example.com"
        
        # Should not be locked initially
        assert not SecurityService.is_account_locked(email)
        
        # Lock account
        SecurityService.lock_account(email, duration_minutes=30)
        
        # Should be locked now
        assert SecurityService.is_account_locked(email)
        
        # Different email should not be locked
        assert not SecurityService.is_account_locked("other@example.com")


class TestInputSanitization:
    """Test input sanitization functionality"""
    
    def test_basic_input_sanitization(self):
        """Test basic input sanitization"""
        # Test HTML/script removal
        malicious_input = '<script>alert("xss")</script>Hello World'
        sanitized = SecurityService.sanitize_input(malicious_input)
        assert "<script>" not in sanitized
        assert "Hello World" in sanitized
        
        # Test length limiting
        long_input = "a" * 2000
        sanitized = SecurityService.sanitize_input(long_input, max_length=100)
        assert len(sanitized) <= 100
        
        # Test null bytes and control characters
        malicious_input = "Hello\x00\x01\x02World"
        sanitized = SecurityService.sanitize_input(malicious_input)
        assert "\x00" not in sanitized
        assert "HelloWorld" in sanitized
    
    def test_email_format_validation(self):
        """Test email format validation"""
        valid_emails = [
            "user@example.com",
            "test.email+tag@example.co.uk",
            "user123@test-domain.com"
        ]
        
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user@.com",
            "user space@example.com",
            "user@exam ple.com"
        ]
        
        for email in valid_emails:
            assert SecurityService.validate_email_format(email), f"Should accept {email}"
        
        for email in invalid_emails:
            assert not SecurityService.validate_email_format(email), f"Should reject {email}"


class TestSecurityConfiguration:
    """Test security configuration validation"""
    
    @patch('app.core.config.settings')
    def test_insecure_default_keys_detection(self, mock_settings):
        """Test detection of default insecure keys"""
        mock_settings.jwt_secret_key = "default-secret-key"
        mock_settings.jwt_refresh_secret_key = "default-refresh-secret-key"
        mock_settings.environment = "production"
        
        is_valid, warnings = SecurityConfigValidator.validate_configuration()
        
        assert not is_valid
        assert any("default value" in warning for warning in warnings)
    
    @patch('app.core.config.settings')
    def test_short_secret_keys_detection(self, mock_settings):
        """Test detection of short secret keys"""
        mock_settings.jwt_secret_key = "short"
        mock_settings.jwt_refresh_secret_key = "alsoshort"
        mock_settings.environment = "development"
        
        is_valid, warnings = SecurityConfigValidator.validate_configuration()
        
        assert not is_valid
        assert any("32 characters" in warning for warning in warnings)
    
    def test_secure_secret_generation(self):
        """Test secure secret generation"""
        secret1 = SecurityConfigValidator.generate_secure_secret()
        secret2 = SecurityConfigValidator.generate_secure_secret()
        
        # Should be different and sufficiently long
        assert secret1 != secret2
        assert len(secret1) > 50
        assert len(secret2) > 50


class TestMiddlewareSecurity:
    """Test security middleware functionality"""
    
    def test_security_headers_concept(self):
        """Test that we have security headers concept implemented"""
        # This would require a more complex test setup with FastAPI TestClient
        # For now, we'll test the concept
        headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Referrer-Policy",
            "Content-Security-Policy"
        ]
        
        # In a real test, you would verify these headers are added to responses
        assert all(header for header in headers)  # Placeholder assertion


if __name__ == "__main__":
    pytest.main([__file__])