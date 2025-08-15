import { apiClient } from './client'
import { 
  User, 
  SignupRequest, 
  LoginRequest, 
  TokenResponse,
  GoogleAuthRequest 
} from '@/lib/types/auth'

export const authApi = {
  async signup(
    firstName: string,
    lastName: string,
    email: string,
    company: string,
    password: string,
    confirmPassword: string
  ): Promise<TokenResponse> {
    const signupData: SignupRequest = {
      name: `${firstName} ${lastName}`.trim(),
      email,
      password,
      confirm_password: confirmPassword
    }
    
    // Store company info locally if needed
    if (company) {
      localStorage.setItem('user_company', company)
    }
    
    return apiClient.post<TokenResponse>('/auth/signup', signupData)
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    const loginData: LoginRequest = {
      email,
      password
    }
    
    return apiClient.post<TokenResponse>('/auth/login', loginData)
  },

  async googleAuth(idToken: string): Promise<TokenResponse> {
    const googleData: GoogleAuthRequest = {
      id_token: idToken
    }
    
    return apiClient.post<TokenResponse>('/auth/google', googleData)
  },

  async logout(): Promise<{ message: string }> {
    return apiClient.post('/auth/logout')
  },

  async refreshToken(): Promise<TokenResponse> {
    return apiClient.post<TokenResponse>('/auth/refresh')
  },

  async getCurrentUser(): Promise<User> {
    return apiClient.get<User>('/users/me')
  }
}