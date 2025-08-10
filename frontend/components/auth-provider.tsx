'use client'

import { useEffect, ReactNode } from 'react'
import { useAuthStore } from '@/lib/stores/auth'

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { checkAuth } = useAuthStore()

  useEffect(() => {
    // Check authentication status when the app loads
    checkAuth()
  }, [])

  return <>{children}</>
}