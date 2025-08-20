"""
Example of how to integrate the security enhancements into your FastAPI application
"""

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from app.middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware, LoginProtectionMiddleware
from app.core.security import SecurityService
from app.core.security_config import SecurityConfigValidator

# Initialize FastAPI app
app = FastAPI(title="Secure ORRIS API")

# Add security middleware (order matters!)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, calls_per_minute=60)
app.add_middleware(LoginProtectionMiddleware)

# Initialize security on startup
@app.on_event("startup")
async def startup_event():
    """Initialize security settings on application startup"""
    try:
        SecurityConfigValidator.initialize_security()
        print("Security initialization completed successfully")
    except Exception as e:
        print(f"Security initialization failed: {e}")
        # In production, you might want to exit here
        raise

# Example of enhanced login endpoint
@app.post("/auth/login")
async def enhanced_login(request: Request, response: Response):
    """
    Example login endpoint using enhanced security features
    """
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    
    # Check if IP is blocked
    if SecurityService.is_ip_blocked(client_ip):
        raise HTTPException(status_code=429, detail="IP temporarily blocked")
    
    # Check rate limit
    if not SecurityService.check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many attempts")
    
    # Your existing login logic here...
    # On success: SecurityService.clear_failed_attempts(client_ip)
    # On failure: SecurityService.record_failed_attempt(client_ip)
    
    return {"message": "Login endpoint with enhanced security"}

# Example of password validation endpoint
@app.post("/auth/validate-password")
async def validate_password(password: str):
    """
    Example endpoint for password validation
    """
    is_valid, message = SecurityService.validate_password_strength(password)
    return {
        "valid": is_valid,
        "message": message,
        "requirements": {
            "min_length": 12,
            "max_length": 128,
            "requires_uppercase": True,
            "requires_lowercase": True,
            "requires_digit": True,
            "requires_special": True,
            "blocks_weak_patterns": True,
            "blocks_common_passwords": True
        }
    }

# Example of input sanitization
@app.post("/api/sanitize-input")
async def sanitize_input(user_input: str):
    """
    Example endpoint showing input sanitization
    """
    sanitized = SecurityService.sanitize_input(user_input, max_length=1000)
    return {
        "original": user_input,
        "sanitized": sanitized,
        "safe": sanitized == user_input
    }

# Security status endpoint
@app.get("/security/status")
async def security_status():
    """
    Endpoint to check security configuration status
    """
    is_valid, warnings = SecurityConfigValidator.validate_configuration()
    recommendations = SecurityConfigValidator.get_security_recommendations()
    
    return {
        "configuration_valid": is_valid,
        "warnings": warnings,
        "recommendations": recommendations,
        "features": {
            "enhanced_passwords": True,
            "rate_limiting": True,
            "security_headers": True,
            "input_sanitization": True,
            "account_lockout": True,
            "csrf_protection": True,
            "audit_logging": True
        }
    }

# CSRF token endpoint
@app.get("/security/csrf-token")
async def get_csrf_token():
    """
    Endpoint to get CSRF token for forms
    """
    token = SecurityService.generate_csrf_token()
    return {"csrf_token": token}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)