/**
 * Secure Token Validation Utility
 * Handles token expiration detection and validation without exposing sensitive data
 */

export interface TokenValidationResult {
  isValid: boolean
  expiresAt: number | null
  timeUntilExpiry: number | null
  shouldRefresh: boolean
  shouldLogout: boolean
}

export class TokenValidator {
  private static readonly REFRESH_THRESHOLD_MS = 5 * 60 * 1000 // 5 minutes before expiry
  private static readonly WARNING_THRESHOLD_MS = 2 * 60 * 1000 // 2 minutes before expiry

  /**
   * Safely decode JWT token without exposing payload
   * Only extracts expiration time for validation
   */
  static validateToken(token: string | null): TokenValidationResult {
    const defaultResult: TokenValidationResult = {
      isValid: false,
      expiresAt: null,
      timeUntilExpiry: null,
      shouldRefresh: false,
      shouldLogout: true
    }

    if (!token) {
      return defaultResult
    }

    try {
      // Split JWT token (header.payload.signature)
      const parts = token.split('.')
      if (parts.length !== 3) {
        return defaultResult
      }

      // Decode payload (base64url)
      const payload = JSON.parse(
        atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'))
      )

      const exp = payload.exp
      if (!exp || typeof exp !== 'number') {
        return defaultResult
      }

      const expiresAt = exp * 1000 // Convert to milliseconds
      const currentTime = Date.now()
      const timeUntilExpiry = expiresAt - currentTime

      // Token is expired
      if (timeUntilExpiry <= 0) {
        return {
          isValid: false,
          expiresAt,
          timeUntilExpiry: 0,
          shouldRefresh: true,
          shouldLogout: true
        }
      }

      // Token is valid
      return {
        isValid: true,
        expiresAt,
        timeUntilExpiry,
        shouldRefresh: timeUntilExpiry <= this.REFRESH_THRESHOLD_MS,
        shouldLogout: false
      }
    } catch (error) {
      // Invalid token format or decode error
      console.error('Token validation error:', error)
      return defaultResult
    }
  }

  /**
   * Check if user should be warned about session expiration
   */
  static shouldShowExpirationWarning(validationResult: TokenValidationResult): boolean {
    if (!validationResult.isValid || !validationResult.timeUntilExpiry) {
      return false
    }

    return validationResult.timeUntilExpiry <= this.WARNING_THRESHOLD_MS &&
           validationResult.timeUntilExpiry > 0
  }

  /**
   * Get human-readable time until expiration
   */
  static getExpirationWarningMessage(timeUntilExpiry: number): string {
    const minutes = Math.ceil(timeUntilExpiry / (60 * 1000))
    if (minutes <= 1) {
      return 'Your session will expire in less than 1 minute'
    }
    return `Your session will expire in ${minutes} minute${minutes > 1 ? 's' : ''}`
  }

  /**
   * Safely get current page URL for post-login redirect
   * Validates URL to prevent open redirect attacks
   */
  static getSecureRedirectUrl(): string | null {
    if (typeof window === 'undefined') return null

    try {
      const currentUrl = window.location.pathname + window.location.search
      
      // Security checks for safe redirect
      if (
        currentUrl.includes('//') || // No protocol-relative URLs
        currentUrl.includes('javascript:') || // No javascript URLs
        currentUrl.includes('data:') || // No data URLs
        currentUrl.startsWith('http') || // No absolute URLs
        currentUrl.includes('<') || // No HTML injection
        currentUrl.includes('>') ||
        currentUrl.length > 500 // Reasonable URL length limit
      ) {
        return null
      }

      // Don't redirect to auth pages
      if (
        currentUrl.includes('/login') ||
        currentUrl.includes('/signup') ||
        currentUrl.includes('/auth')
      ) {
        return null
      }

      return currentUrl
    } catch (error) {
      console.error('Error getting redirect URL:', error)
      return null
    }
  }

  /**
   * Clear any stored redirect URL (for security)
   */
  static clearStoredRedirectUrl(): void {
    try {
      localStorage.removeItem('auth-redirect-url')
      sessionStorage.removeItem('auth-redirect-url')
    } catch (error) {
      // Ignore localStorage errors
    }
  }

  /**
   * Securely store redirect URL
   */
  static storeSecureRedirectUrl(url: string | null): void {
    if (!url) return

    try {
      // Use sessionStorage for security (cleared when tab closes)
      sessionStorage.setItem('auth-redirect-url', url)
    } catch (error) {
      // Ignore storage errors
    }
  }

  /**
   * Get and clear stored redirect URL
   */
  static getAndClearStoredRedirectUrl(): string | null {
    try {
      const url = sessionStorage.getItem('auth-redirect-url')
      if (url) {
        sessionStorage.removeItem('auth-redirect-url')
        
        // Re-validate the stored URL for security
        if (this.isSecureRedirectUrl(url)) {
          return url
        }
      }
    } catch (error) {
      // Ignore storage errors
    }
    
    return null
  }

  /**
   * Validate if a URL is safe for redirect
   */
  private static isSecureRedirectUrl(url: string): boolean {
    return !(
      url.includes('//') ||
      url.includes('javascript:') ||
      url.includes('data:') ||
      url.startsWith('http') ||
      url.includes('<') ||
      url.includes('>') ||
      url.length > 500 ||
      url.includes('/login') ||
      url.includes('/signup') ||
      url.includes('/auth')
    )
  }
}