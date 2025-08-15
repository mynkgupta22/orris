'use client'

import { ReactNode } from 'react'

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  // Auth state is managed by individual components as needed
  // 401 responses from API calls will handle automatic logout
  return <>{children}</>
}