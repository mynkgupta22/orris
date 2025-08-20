"""
Security configuration validation and initialization
"""

import os
import secrets
import logging
from typing import List, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityConfigValidator:
    """Validates and ensures secure configuration settings"""
    
    @staticmethod
    def validate_configuration() -> Tuple[bool, List[str]]:
        """
        Validate security configuration and return validation status and warnings
        Returns: (is_valid, warnings)
        """
        warnings = []
        is_valid = True
        
        # Check JWT secret keys
        if settings.jwt_secret_key == "default-secret-key":
            warnings.append("JWT secret key is using default value - this is insecure for production")
            is_valid = False
        
        if settings.jwt_refresh_secret_key == "default-refresh-secret-key":
            warnings.append("JWT refresh secret key is using default value - this is insecure for production")
            is_valid = False
        
        # Check secret key strength
        if len(settings.jwt_secret_key) < 32:
            warnings.append("JWT secret key should be at least 32 characters long")
            is_valid = False
        
        if len(settings.jwt_refresh_secret_key) < 32:
            warnings.append("JWT refresh secret key should be at least 32 characters long")
            is_valid = False
        
        # Check token expiration times
        if settings.access_token_expire_minutes > 60:
            warnings.append("Access token expiration time is too long (>60 minutes) - consider shorter duration")
        
        if settings.refresh_token_expire_days > 30:
            warnings.append("Refresh token expiration time is too long (>30 days) - consider shorter duration")
        
        # Check database URL security
        if "password" in settings.database_url.lower() and settings.environment == "production":
            warnings.append("Database URL contains credentials in plaintext - consider using environment variables")
        
        # Check debug mode
        if settings.debug and settings.environment == "production":
            warnings.append("Debug mode is enabled in production - this should be disabled")
            is_valid = False
        
        # Check HTTPS enforcement
        if settings.environment == "production" and not any("https" in origin for origin in settings.get_allowed_origins()):
            warnings.append("No HTTPS origins configured for production - this is insecure")
        
        # Check if API keys are set for production
        if settings.environment == "production":
            if not settings.openai_api_key:
                warnings.append("OpenAI API key not set")
            
            if not settings.google_client_id or not settings.google_client_secret:
                warnings.append("Google OAuth credentials not properly configured")
        
        return is_valid, warnings
    
    @staticmethod
    def generate_secure_secret() -> str:
        """Generate a cryptographically secure secret key"""
        return secrets.token_urlsafe(64)
    
    @staticmethod
    def initialize_security() -> None:
        """Initialize security settings and log warnings"""
        is_valid, warnings = SecurityConfigValidator.validate_configuration()
        
        if warnings:
            logger.warning("Security configuration warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")
        
        if not is_valid:
            logger.error("Critical security configuration issues detected!")
            if settings.environment == "production":
                raise RuntimeError("Insecure configuration detected in production environment")
        
        logger.info("Security configuration validation completed")
    
    @staticmethod
    def get_security_recommendations() -> List[str]:
        """Get security recommendations for the current configuration"""
        recommendations = [
            "Use environment variables for all secret keys and credentials",
            "Enable HTTPS in production with proper SSL certificates",
            "Implement proper logging and monitoring for security events",
            "Regularly rotate JWT secret keys",
            "Use a dedicated secrets management service for production",
            "Implement IP whitelisting for admin endpoints",
            "Enable database connection encryption",
            "Set up proper backup and disaster recovery procedures",
            "Implement security scanning in CI/CD pipeline",
            "Regular security audits and penetration testing"
        ]
        return recommendations