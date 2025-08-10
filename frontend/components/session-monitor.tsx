'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuthStore } from '@/lib/stores/auth'
import { TokenValidator } from '@/lib/utils/token-validator'
import toast from 'react-hot-toast'

interface SessionMonitorProps {
  children: React.ReactNode
}

export function SessionMonitor({ children }: SessionMonitorProps) {
  const { accessToken, logout } = useAuthStore()
  const [hasShownWarning, setHasShownWarning] = useState(false)
  const [warningToastId, setWarningToastId] = useState<string | null>(null)

  const handleTokenExpiration = useCallback(async () => {
    try {
      // Store current page for redirect
      const redirectUrl = TokenValidator.getSecureRedirectUrl()
      if (redirectUrl) {
        TokenValidator.storeSecureRedirectUrl(redirectUrl)
      }

      // Perform logout
      await logout()
      
      // Show logout notification
      toast.error('Your session has expired. Please log in again.')
      
      // Redirect to login page
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    } catch (error) {
      console.error('Error during automatic logout:', error)
      // Force redirect even if logout fails
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    }
  }, [logout])

  const checkTokenValidity = useCallback(async () => {
    if (!accessToken) return

    const validation = TokenValidator.validateToken(accessToken)

    // Handle expired token
    if (validation.shouldLogout) {
      await handleTokenExpiration()
      return
    }

    // Show expiration warning
    if (TokenValidator.shouldShowExpirationWarning(validation) && !hasShownWarning) {
      if (validation.timeUntilExpiry) {
        const message = TokenValidator.getExpirationWarningMessage(validation.timeUntilExpiry)
        
        // Clear any existing warning toast
        if (warningToastId) {
          toast.dismiss(warningToastId)
        }
        
        const toastId = toast(message, {
          icon: '⚠️',
          duration: 10000, // 10 seconds
          position: 'top-center',
          style: {
            background: '#FEF3C7',
            color: '#92400E',
            border: '1px solid #F59E0B'
          }
        })
        
        setWarningToastId(toastId)
        setHasShownWarning(true)
      }
    }

    // Reset warning flag when token is refreshed or has more time
    if (validation.timeUntilExpiry && validation.timeUntilExpiry > 3 * 60 * 1000) { // 3 minutes
      if (hasShownWarning) {
        setHasShownWarning(false)
        if (warningToastId) {
          toast.dismiss(warningToastId)
          setWarningToastId(null)
        }
      }
    }
  }, [accessToken, hasShownWarning, warningToastId, handleTokenExpiration])

  useEffect(() => {
    // Only monitor if user is authenticated
    if (!accessToken) {
      // Clear any existing warnings
      if (warningToastId) {
        toast.dismiss(warningToastId)
        setWarningToastId(null)
      }
      setHasShownWarning(false)
      return
    }

    // Initial check
    checkTokenValidity()

    // Set up interval to check token every 30 seconds
    const interval = setInterval(checkTokenValidity, 30 * 1000)

    // Also check on focus (when user returns to tab)
    const handleFocus = () => {
      checkTokenValidity()
    }

    // Check when user becomes active (mouse/keyboard activity)
    const handleActivity = () => {
      checkTokenValidity()
    }

    window.addEventListener('focus', handleFocus)
    window.addEventListener('mousedown', handleActivity)
    window.addEventListener('keydown', handleActivity)
    window.addEventListener('touchstart', handleActivity)

    return () => {
      clearInterval(interval)
      window.removeEventListener('focus', handleFocus)
      window.removeEventListener('mousedown', handleActivity)
      window.removeEventListener('keydown', handleActivity)
      window.removeEventListener('touchstart', handleActivity)
      
      // Clean up warning toast
      if (warningToastId) {
        toast.dismiss(warningToastId)
      }
    }
  }, [accessToken, checkTokenValidity, warningToastId])

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (warningToastId) {
        toast.dismiss(warningToastId)
      }
    }
  }, [warningToastId])

  return <>{children}</>
}