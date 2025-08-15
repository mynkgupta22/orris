import { useAuthStore } from '@/lib/stores/auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const state = useAuthStore.getState?.() as { accessToken?: string } | undefined
  const token = state?.accessToken
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!res.ok) {
    const msg = await res.text().catch(() => '')
    const err: any = new Error(`HTTP ${res.status}`)
    err.status = res.status
    err.body = msg
    throw err
  }
  return res.json() as Promise<T>
}

export interface UserProfile {
  id: number
  name: string
  email: string
  role: 'signed_up' | 'non_pi_access' | 'pi_access' | 'admin'
  status: 'active' | 'inactive' | 'suspended'
  email_verified: boolean
  created_at: string
}

export const userApi = {
  me(): Promise<UserProfile> {
    return request<UserProfile>('/users/me', { method: 'GET' })
  },
}


