'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Brain, Eye, EyeOff, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { useAuthStore } from '@/lib/stores/auth'
import { TokenValidator } from '@/lib/utils/token-validator'
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google'

export default function LoginPage() {
  const router = useRouter()
  const { user, login, googleLogin, isLoading } = useAuthStore()

  // Check for stored redirect URL and redirect authenticated users
  useEffect(() => {
    if (user) {
      // Check if there's a stored redirect URL
      const redirectUrl = TokenValidator.getAndClearStoredRedirectUrl()
      if (redirectUrl) {
        router.push(redirectUrl)
      } else {
        router.push('/chat')
      }
    }
  }, [user, router])
  const [showPassword, setShowPassword] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const validateForm = () => {
    const errors: Record<string, string> = {}
    
    if (!email.trim()) errors.email = 'Email is required'
    if (!password) errors.password = 'Password is required'
    
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) return
    
    const success = await login(email, password)
    
    if (success) {
      // Check for stored redirect URL
      const redirectUrl = TokenValidator.getAndClearStoredRedirectUrl()
      if (redirectUrl) {
        router.push(redirectUrl)
      } else {
        router.push('/chat')
      }
    }
  }

  const handleGoogleSuccess = async (credentialResponse: any) => {
    if (credentialResponse.credential) {
      const success = await googleLogin(credentialResponse.credential)
      if (success) {
        // Check for stored redirect URL
        const redirectUrl = TokenValidator.getAndClearStoredRedirectUrl()
        if (redirectUrl) {
          router.push(redirectUrl)
        } else {
          router.push('/chat')
        }
      }
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      {/* Floating Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-20 w-16 h-16 bg-blue-100 rounded-2xl opacity-60 rotate-12"></div>
        <div className="absolute top-40 right-32 w-12 h-12 bg-green-100 rounded-xl opacity-40 -rotate-6"></div>
        <div className="absolute bottom-32 left-16 w-20 h-20 bg-purple-100 rounded-3xl opacity-50 rotate-45"></div>
        <div className="absolute bottom-20 right-20 w-14 h-14 bg-orange-100 rounded-2xl opacity-60 -rotate-12"></div>
        <div className="absolute top-1/2 left-8 w-10 h-10 bg-pink-100 rounded-xl opacity-40 rotate-30"></div>
        <div className="absolute top-1/3 right-8 w-18 h-18 bg-indigo-100 rounded-2xl opacity-50 -rotate-15"></div>
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center space-x-2">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-gray-900">Orris</span>
          </Link>
        </div>

        <Card className="border-0 shadow-2xl bg-white/95 backdrop-blur-sm ring-1 ring-gray-100">
          <CardHeader className="text-center pb-6">
            <CardTitle className="text-2xl font-bold text-gray-900">Welcome back</CardTitle>
            <CardDescription className="text-gray-600">
              Sign in to access your company's AI assistant
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium text-gray-700">
                  Email address
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={`h-12 border-gray-200 focus:border-blue-500 focus:ring-blue-500 ${fieldErrors.email ? 'border-red-500' : ''}`}
                  disabled={isLoading}
                />
                {fieldErrors.email && (
                  <p className="text-xs text-red-500">{fieldErrors.email}</p>
                )}
              </div>
              
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-sm font-medium text-gray-700">
                    Password
                  </Label>
                  <Link href="/forgot-password" className="text-sm text-blue-600 hover:text-blue-700">
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={`h-12 border-gray-200 focus:border-blue-500 focus:ring-blue-500 pr-12 ${fieldErrors.password ? 'border-red-500' : ''}`}
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    disabled={isLoading}
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {fieldErrors.password && (
                  <p className="text-xs text-red-500">{fieldErrors.password}</p>
                )}
              </div>

              <Button 
                type="submit"
                disabled={isLoading}
                className="w-full h-14 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold shadow-lg hover:shadow-xl transition-all duration-300"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing In...
                  </>
                ) : (
                  'Sign In'
                )}
              </Button>
            </form>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white text-gray-500">Or continue with</span>
              </div>
            </div>

            <GoogleOAuthProvider clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || ''}>
              <div className="w-full flex justify-center">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => {
                    console.error('Google Login Failed')
                  }}
                  useOneTap={false}
                  theme="outline"
                  size="large"
                  text="continue_with"
                  width="100%"
                />
              </div>
            </GoogleOAuthProvider>

            <div className="text-center text-sm text-gray-600">
              Don't have an account?{' '}
              <Link href="/signup" className="text-blue-600 hover:text-blue-700 font-medium">
                Create an account
              </Link>
            </div>
          </CardContent>
        </Card>

        <div className="mt-8 text-center text-xs text-gray-500">
          Protected by enterprise-grade security
        </div>
      </div>
    </div>
  )
}
