import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User, ApiError } from '@/lib/types/auth'
import { authApi } from '@/lib/api/auth'
import toast from 'react-hot-toast'

interface AuthState {
  user: User | null
  accessToken: string | null
  isLoading: boolean
  error: string | null
  
  // Actions
  signup: (
    firstName: string,
    lastName: string,
    email: string,
    company: string,
    password: string,
    confirmPassword: string
  ) => Promise<boolean>
  
  login: (email: string, password: string) => Promise<boolean>
  
  googleLogin: (idToken: string) => Promise<boolean>
  
  logout: () => Promise<void>
  
  checkAuth: () => Promise<void>
  
  clearError: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
        user: null,
        accessToken: null,
        isLoading: false,
        error: null,

        signup: async (firstName, lastName, email, company, password, confirmPassword) => {
          set({ isLoading: true, error: null })
          
          try {
            const response = await authApi.signup(
              firstName,
              lastName,
              email,
              company,
              password,
              confirmPassword
            )
            
            set({ user: response.user, accessToken: response.access_token, isLoading: false })
            toast.success('Account created successfully!')
            return true
          } catch (error) {
            const apiError = error as ApiError
            let errorMessage = 'Signup failed'
            
            if (apiError.status === 409) {
              errorMessage = 'Email already registered'
            } else if (apiError.status === 422) {
              if (typeof apiError.detail === 'string') {
                errorMessage = apiError.detail
              } else if (typeof apiError.detail === 'object') {
                errorMessage = Object.values(apiError.detail).join(', ')
              }
            } else if (typeof apiError.detail === 'string') {
              errorMessage = apiError.detail
            }
            
            set({ error: errorMessage, isLoading: false })
            toast.error(errorMessage)
            return false
          }
        },

        login: async (email, password) => {
          set({ isLoading: true, error: null })
          
          try {
            const response = await authApi.login(email, password)
            set({ user: response.user, accessToken: response.access_token, isLoading: false })
            toast.success('Welcome back!')
            return true
          } catch (error) {
            const apiError = error as ApiError
            let errorMessage = 'Login failed'
            
            if (apiError.status === 401) {
              errorMessage = 'Invalid email or password'
            } else if (typeof apiError.detail === 'string') {
              errorMessage = apiError.detail
            }
            
            set({ error: errorMessage, isLoading: false })
            toast.error(errorMessage)
            return false
          }
        },

        googleLogin: async (idToken) => {
          set({ isLoading: true, error: null })
          
          try {
            const response = await authApi.googleAuth(idToken)
            set({ user: response.user, accessToken: response.access_token, isLoading: false })
            toast.success('Signed in with Google!')
            return true
          } catch (error) {
            const apiError = error as ApiError
            const errorMessage = typeof apiError.detail === 'string' 
              ? apiError.detail 
              : 'Google sign-in failed'
            
            set({ error: errorMessage, isLoading: false })
            toast.error(errorMessage)
            return false
          }
        },

        logout: async () => {
          set({ isLoading: true })
          
          try {
            await authApi.logout()
            set({ user: null, accessToken: null, isLoading: false })
            localStorage.removeItem('user_company')
            toast.success('Logged out successfully')
          } catch (error) {
            set({ isLoading: false })
            toast.error('Logout failed')
          }
        },

        checkAuth: async () => {
          try {
            const user = await authApi.getCurrentUser()
            set({ user, error: null })
          } catch (error) {
            // Try to refresh token if getCurrentUser fails
            try {
              const response = await authApi.refreshToken()
              set({ user: response.user, accessToken: response.access_token, error: null })
            } catch {
              // Both getCurrentUser and refresh failed - user is not authenticated
              set({ user: null, accessToken: null, error: null })
            }
          }
        },

        clearError: () => {
          set({ error: null })
        }
      }),
    {
      name: 'auth-storage',
      partialize: (state: AuthState) => ({ user: state.user, accessToken: state.accessToken })
    }
  )
)