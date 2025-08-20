"""
Security middleware for FastAPI application
Implements security headers, rate limiting, and other security measures
"""

from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from typing import Callable
import time
from collections import defaultdict, deque

from app.core.security import SecurityService


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy - adjust based on your needs
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # HSTS (HTTP Strict Transport Security) - only for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests"""
    
    def __init__(self, app, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.requests: defaultdict = defaultdict(lambda: deque())
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old requests
        request_times = self.requests[client_ip]
        while request_times and current_time - request_times[0] > 60:
            request_times.popleft()
        
        # Check rate limit
        if len(request_times) >= self.calls_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Record this request
        request_times.append(current_time)
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(self.calls_per_minute - len(request_times))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for forwarded headers (from reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"


class LoginProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware to protect against brute force login attempts"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only apply to auth endpoints
        if request.url.path in ["/auth/login", "/auth/signup"]:
            client_ip = self._get_client_ip(request)
            
            # Check if IP is blocked
            if SecurityService.is_ip_blocked(client_ip):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="IP temporarily blocked due to suspicious activity"
                )
            
            # Check rate limit for login attempts
            if not SecurityService.check_rate_limit(client_ip, max_attempts=5, window_minutes=15):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Please try again later."
                )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"