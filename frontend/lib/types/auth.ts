export interface User {
  id: number
  name: string
  email: string
  role: 'signed_up' | 'non_pi_access' | 'pi_access'
  status: 'active' | 'inactive' | 'suspended'
  email_verified: boolean
  created_at: string
}

export interface SignupRequest {
  name: string
  email: string
  password: string
  confirm_password: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface GoogleAuthRequest {
  id_token: string
}

export interface ApiError {
  detail: string | Record<string, string>
  status?: number
}