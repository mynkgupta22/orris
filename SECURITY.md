# Security Documentation

This document outlines the security features implemented in the ORRIS application and provides guidelines for maintaining security.

## Enhanced Security Features

### 1. Password Security

#### Enhanced Password Requirements
- **Minimum length**: 12 characters (increased from 8)
- **Maximum length**: 128 characters (to prevent DoS attacks)
- **Complexity requirements**:
  - At least one lowercase letter
  - At least one uppercase letter  
  - At least one digit
  - At least one special character

#### Advanced Password Validation
- **Weak pattern detection**: Detects sequential characters (abcd, 1234), repeated characters (aaaa), and keyboard patterns (qwertyuiop)
- **Common password detection**: Blocks common passwords like "Password123", "Welcome123", etc.
- **Timing-safe validation**: Uses secure comparison methods to prevent timing attacks

### 2. JWT Token Security

#### Enhanced Token Features
- **Strong hashing**: Uses PBKDF2 instead of plain SHA256 for token storage
- **Additional claims**: Includes `jti` (JWT ID), `nbf` (not before), and proper `iat` (issued at) timestamps
- **CSRF protection**: Implements CSRF token generation and validation
- **Secure comparison**: Uses timing-safe comparison for token validation

### 3. Rate Limiting & Account Protection

#### Brute Force Protection
- **Rate limiting**: Tracks failed login attempts per IP address
- **Account lockout**: Locks accounts after 5 failed attempts for 30 minutes
- **IP blocking**: Temporarily blocks IPs with excessive failed attempts
- **Progressive delays**: Implements exponential backoff for repeated failures

#### Implementation Details
```python
# Check rate limit
if not SecurityService.check_rate_limit(ip_address, max_attempts=5, window_minutes=15):
    raise HTTPException(status_code=429, detail="Too many attempts")

# Record failed attempt
SecurityService.record_failed_attempt(ip_address)

# Check if account is locked
if SecurityService.is_account_locked(email):
    raise HTTPException(status_code=423, detail="Account locked")
```

### 4. Input Validation & Sanitization

#### Enhanced Input Sanitization
- **Length limiting**: Prevents buffer overflow attacks
- **Character filtering**: Removes dangerous characters including null bytes and control characters
- **HTML/Script removal**: Strips potentially malicious HTML and JavaScript
- **Email validation**: Comprehensive email format validation with regex

#### RAG Query Sanitization
- **Prompt injection protection**: Advanced regex patterns to detect and block prompt injection attempts
- **Dangerous command filtering**: Blocks system commands and code execution attempts
- **Content normalization**: Normalizes whitespace and removes excessive formatting

### 5. Security Headers & Middleware

#### Security Headers
All responses include the following security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy: [comprehensive policy]`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (HTTPS only)

#### Rate Limiting Middleware
- Global rate limiting (60 requests/minute by default)
- Rate limit headers in responses
- Configurable limits per endpoint

### 6. Configuration Security

#### Security Configuration Validation
- **Default key detection**: Warns about default JWT secret keys
- **Key strength validation**: Ensures secret keys are at least 32 characters
- **Environment checks**: Validates security settings for production
- **Automatic recommendations**: Provides security best practice recommendations

### 7. Logging & Monitoring

#### Security Event Logging
- Login attempts (successful and failed)
- Account lockouts and IP blocks
- Rate limit violations
- Suspicious activity detection
- Audit trails for sensitive operations

## Security Best Practices

### For Developers

1. **Never commit secrets**: Use environment variables for all sensitive configuration
2. **Validate all inputs**: Always sanitize and validate user inputs
3. **Use HTTPS**: Enforce HTTPS in production environments
4. **Regular updates**: Keep dependencies updated and monitor for security vulnerabilities
5. **Security testing**: Run security tests as part of CI/CD pipeline

### For Deployment

1. **Environment variables**: Store secrets in secure environment variables or secret management systems
2. **Network security**: Use firewalls and network segmentation
3. **Database security**: Enable encryption in transit and at rest
4. **Monitoring**: Implement comprehensive logging and monitoring
5. **Backup security**: Secure backup storage and test recovery procedures

### For Operations

1. **Regular audits**: Conduct regular security audits and penetration testing
2. **Access control**: Implement principle of least privilege
3. **Incident response**: Have a security incident response plan
4. **Staff training**: Regular security awareness training
5. **Vulnerability management**: Process for handling security vulnerabilities

## Configuration Examples

### Environment Variables for Production
```bash
# JWT Configuration
JWT_SECRET_KEY="your-very-long-and-secure-secret-key-at-least-32-chars"
JWT_REFRESH_SECRET_KEY="another-very-long-and-secure-refresh-key"
JWT_ALGORITHM="HS512"
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database (use connection string without embedded credentials)
DATABASE_URL="postgresql://user@host:5432/dbname"

# Security Settings
DEBUG=False
ENVIRONMENT=production
ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

### Security Headers Configuration
```python
# Add to your FastAPI app
from app.middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, calls_per_minute=60)
```

## Testing Security Features

Run the comprehensive security test suite:
```bash
python -m pytest tests/test_security.py -v
```

Test categories:
- Password strength validation
- Token security features  
- Rate limiting functionality
- Input sanitization
- Configuration validation

## Security Checklist

### Before Production Deployment

- [ ] All default secrets changed
- [ ] HTTPS enforced
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Input validation implemented
- [ ] Logging configured
- [ ] Security tests passing
- [ ] Dependencies updated
- [ ] Configuration validated
- [ ] Monitoring setup

### Regular Security Maintenance

- [ ] Review access logs weekly
- [ ] Update dependencies monthly
- [ ] Security configuration audit quarterly
- [ ] Penetration testing annually
- [ ] Staff security training annually

## Incident Response

In case of a security incident:

1. **Immediate response**: Isolate affected systems
2. **Assessment**: Determine scope and impact
3. **Containment**: Stop the attack and prevent spread
4. **Eradication**: Remove malicious code/access
5. **Recovery**: Restore systems and services
6. **Lessons learned**: Document and improve security

## Contact

For security issues or questions, contact the security team or create a security-related issue in the repository.

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)