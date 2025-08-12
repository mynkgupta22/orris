import { ApiError } from '@/lib/types/auth'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

// Function to get access token from auth store
const getAccessToken = (): string | null => {
  if (typeof window === 'undefined') return null
  try {
    const authStorage = localStorage.getItem('auth-storage')
    if (authStorage) {
      const parsed = JSON.parse(authStorage)
      return parsed.state?.accessToken || null
    }
  } catch (error) {
    console.error('Error getting access token:', error)
  }
  return null
}

class ApiClient {
  private baseURL: string
  private isRefreshing = false
  private refreshPromise: Promise<void> | null = null

  constructor() {
    this.baseURL = API_BASE_URL
  }

  private async handleResponse<T>(response: Response, originalRequest?: () => Promise<Response>, endpoint?: string): Promise<T> {
    if (!response.ok) {
      let errorMessage = 'An error occurred'
      let errorDetail: any = errorMessage
      
      try {
        const errorData = await response.json()
        errorDetail = errorData.detail || errorMessage
      } catch {
        errorDetail = response.statusText || errorMessage
      }

      // Handle 401 errors with automatic token refresh
      // But skip retry for auth endpoints to prevent infinite loops
      const skipRetryEndpoints = ['/auth/login', '/auth/signup', '/auth/refresh', '/auth/logout', '/auth/google']
      const isAuthEndpoint = endpoint && skipRetryEndpoints.includes(endpoint)
      
      if (response.status === 401 && originalRequest && !this.isRefreshing && !isAuthEndpoint) {
        try {
          await this.refreshTokens()
          // Retry the original request
          const retryResponse = await originalRequest()
          return this.handleResponse<T>(retryResponse, undefined, endpoint)
        } catch (refreshError) {
          // Refresh failed - this means tokens are invalid/expired
          this.handleAuthenticationFailure()
          
          const authError: ApiError = {
            detail: 'Session expired. Please log in again.',
            status: 401
          }
          throw authError
        }
      }

      // Handle 401 on auth endpoints (login/refresh failures)
      if (response.status === 401 && isAuthEndpoint && endpoint === '/auth/refresh') {
        this.handleAuthenticationFailure()
      }

      const error: ApiError = {
        detail: errorDetail,
        status: response.status
      }
      
      throw error
    }

    try {
      return await response.json()
    } catch {
      return {} as T
    }
  }

  private async refreshTokens(): Promise<void> {
    if (this.isRefreshing) {
      // Wait for ongoing refresh
      if (this.refreshPromise) {
        await this.refreshPromise
      }
      return
    }

    this.isRefreshing = true
    this.refreshPromise = this.performRefresh()
    
    try {
      await this.refreshPromise
    } finally {
      this.isRefreshing = false
      this.refreshPromise = null
    }
  }

  private async performRefresh(): Promise<void> {
    const response = await fetch(`${this.baseURL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    })

    if (!response.ok) {
      throw new Error('Token refresh failed')
    }
    
    // The refresh endpoint sets new cookies automatically
    return
  }

  private handleAuthenticationFailure(): void {
    // Clear any stored authentication data
    if (typeof window !== 'undefined') {
      try {
        // Clear localStorage auth data completely
        localStorage.removeItem('auth-storage')
        localStorage.removeItem('user_company')
      } catch (error) {
        console.error('Error clearing auth data:', error)
      }

      // Simple redirect to login page
      console.log('Authentication failed, redirecting to login')
      window.location.href = '/login'
    }
  }

  async get<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const token = getAccessToken()
    const makeRequest = () => fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options?.headers,
      },
      credentials: 'include',
    })

    const response = await makeRequest()
    return this.handleResponse<T>(response, makeRequest, endpoint)
  }

  async post<T>(endpoint: string, data?: any, options?: RequestInit): Promise<T> {
    const token = getAccessToken()
    const makeRequest = () => fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options?.headers,
      },
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include',
    })

    const response = await makeRequest()
    return this.handleResponse<T>(response, makeRequest, endpoint)
  }

  async put<T>(endpoint: string, data?: any, options?: RequestInit): Promise<T> {
    const token = getAccessToken()
    const makeRequest = () => fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options?.headers,
      },
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include',
    })

    const response = await makeRequest()
    return this.handleResponse<T>(response, makeRequest, endpoint)
  }

  async delete<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const token = getAccessToken()
    const makeRequest = () => fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options?.headers,
      },
      credentials: 'include',
    })

    const response = await makeRequest()
    return this.handleResponse<T>(response, makeRequest, endpoint)
  }
}

export const apiClient = new ApiClient()