'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Brain, Send, Shield, Clock, FileText, User, Bot, Menu, Search, LogOut, Lock } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'
import { ragApi } from '@/lib/api/rag'
import { authApi } from '@/lib/api/auth'

interface Message {
  id: string
  content: string
  sender: 'user' | 'ai'
  timestamp: Date
  isProtected?: boolean
  sources?: string[]
}

interface ChatHistory {
  id: string
  title: string
  timestamp: Date
}

export default function ChatInterface() {
  const router = useRouter()
  const { logout } = useAuthStore()
  
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: 'Hello! I\'m your company\'s AI assistant. I can help you find information from your company documents, policies, and knowledge base. What would you like to know?',
      sender: 'ai',
      timestamp: new Date(),
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const chatHistory: ChatHistory[] = [
    { id: '1', title: 'Remote work policy questions', timestamp: new Date(Date.now() - 86400000) },
    { id: '2', title: 'Employee benefits overview', timestamp: new Date(Date.now() - 172800000) },
    { id: '3', title: 'IT security guidelines', timestamp: new Date(Date.now() - 259200000) },
    { id: '4', title: 'Vacation request process', timestamp: new Date(Date.now() - 345600000) },
  ]

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const testAuth = async () => {
    try {
      const user = await authApi.getCurrentUser()
      console.log('Current user:', user)
      alert('Authentication working! User: ' + user.email)
    } catch (error) {
      console.error('Auth test error:', error)
      alert('Authentication failed: ' + JSON.stringify(error))
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return

    const userQuery = inputValue
    const userMessage: Message = {
      id: Date.now().toString(),
      content: userQuery,
      sender: 'user',
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      // Call the actual RAG API
      console.log('Sending RAG query:', userQuery)
      const response = await ragApi.query({
        query: userQuery,
        top_k_pre: 30,
        top_k_post: 7
      })

      console.log('RAG API response:', response)
      console.log('Response type:', typeof response)
      console.log('Response keys:', Object.keys(response))
      console.log('Sources received:', response.sources)
      console.log('Sources type:', typeof response.sources)
      console.log('Sources length:', response.sources?.length)

      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: response.answer,
        sender: 'ai',
        timestamp: new Date(),
        sources: response.sources?.map(source => {
          console.log('Processing source:', source)
          return typeof source === 'string' ? source : 
            source.document_name || 'Unknown Document'
        }) || []
      }

      console.log('Parsed AI response:', aiResponse)
      setMessages(prev => [...prev, aiResponse])
    } catch (error) {
      console.error('RAG API error:', error)
      console.error('Error details:', JSON.stringify(error, null, 2))
      
      let errorMessage = 'I apologize, but I encountered an error while processing your request. Please try again later or contact support if the issue persists.'
      let isProtected = false
      
      // Check if it's an authentication error
      if (error && typeof error === 'object' && 'status' in error) {
        if (error.status === 401) {
          errorMessage = 'You need to be logged in to access the company knowledge base. Please log in and try again.'
        } else if (error.status === 403) {
          errorMessage = 'You don\'t have permission to access this information. Please contact your administrator for access.'
        }
      }
      
      // Check if it's a privacy/access control issue
      const isPrivacyRestricted = userQuery.toLowerCase().includes('salary') || 
                                  userQuery.toLowerCase().includes('personal') || 
                                  userQuery.toLowerCase().includes('phone')
      
      if (isPrivacyRestricted) {
        errorMessage = 'I cannot access personal or sensitive information like salaries, personal contact details, or confidential employee data. This information is protected by our privacy policies. Is there something else I can help you with?'
        isProtected = true
      }

      const errorResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: errorMessage,
        sender: 'ai',
        timestamp: new Date(),
        isProtected: isProtected,
      }

      setMessages(prev => [...prev, errorResponse])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-80' : 'w-0'} transition-all duration-300 bg-white/95 backdrop-blur-sm border-r border-gray-200 flex flex-col overflow-hidden shadow-lg`}>
        <div className="p-4 border-b border-gray-100">
          <Link href="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-semibold text-gray-900">Orris</span>
          </Link>
        </div>

        <div className="p-4 border-b border-gray-100 space-y-2">
          <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white">
            New Chat
          </Button>
          <Button onClick={testAuth} className="w-full bg-gray-600 hover:bg-gray-700 text-white text-xs">
            Test Auth
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Recent Chats</h3>
            {chatHistory.map((chat) => (
              <Card key={chat.id} className="cursor-pointer hover:bg-gray-50 transition-colors">
                <CardContent className="p-3">
                  <div className="flex items-start space-x-3">
                    <Clock className="w-4 h-4 text-gray-400 mt-1 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 truncate">{chat.title}</p>
                      <p className="text-xs text-gray-500">
                        {chat.timestamp.toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        <div className="p-4 border-t border-gray-100 space-y-4">
          {/* User Profile Section */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900">John Smith</p>
                <p className="text-xs text-gray-500 truncate">john.smith@company.com</p>
                <div className="flex items-center space-x-1 mt-1">
                  <Badge variant="secondary" className="text-xs">Manager</Badge>
                  <Badge variant="outline" className="text-xs">
                    <Shield className="w-3 h-3 mr-1 text-green-600" />
                    Verified
                  </Badge>
                </div>
              </div>
            </div>
          </div>
          
          <Button 
            variant="ghost" 
            className="w-full justify-start text-gray-600"
            onClick={async () => {
              await logout();
              router.push('/login');
            }}
          >
            <LogOut className="w-4 h-4 mr-3" />
            Sign Out
          </Button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white/95 backdrop-blur-sm border-b border-gray-200 p-6 flex items-center justify-between shadow-sm">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-gray-600"
            >
              <Menu className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Company AI Assistant</h1>
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <Shield className="w-4 h-4 text-green-600" />
                <span>Privacy protection active</span>
                <Badge variant="secondary" className="text-xs">Manager Access</Badge>
              </div>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex space-x-3 max-w-3xl ${message.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  message.sender === 'user' 
                    ? 'bg-blue-600' 
                    : message.isProtected 
                      ? 'bg-red-100' 
                      : 'bg-gray-100'
                }`}>
                  {message.sender === 'user' ? (
                    <User className="w-4 h-4 text-white" />
                  ) : message.isProtected ? (
                    <Lock className="w-4 h-4 text-red-600" />
                  ) : (
                    <Bot className="w-4 h-4 text-gray-600" />
                  )}
                </div>
                <div className={`rounded-2xl px-6 py-4 shadow-sm ${
                  message.sender === 'user'
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg'
                    : message.isProtected
                      ? 'bg-gradient-to-r from-red-50 to-red-100 border border-red-200 shadow-sm'
                      : 'bg-white border border-gray-200 shadow-sm'
                }`}>
                  <p className={`text-sm ${
                    message.sender === 'user' 
                      ? 'text-white' 
                      : message.isProtected 
                        ? 'text-red-800' 
                        : 'text-gray-900'
                  }`}>
                    {message.content}
                  </p>
                  {message.sources && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <p className="text-xs text-gray-500 mb-2">Sources:</p>
                      <div className="flex flex-wrap gap-1">
                        {message.sources.map((source, index) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            <FileText className="w-3 h-3 mr-1" />
                            {source}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  <p className="text-xs opacity-70 mt-2">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="flex space-x-3 max-w-3xl">
                <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-gray-600" />
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-gray-200 p-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex space-x-4">
              <div className="flex-1 relative">
                <Input
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask about company policies, procedures, or any work-related questions..."
                  className="pr-12 h-12 border-gray-200 focus:border-blue-500 focus:ring-blue-500"
                  disabled={isLoading}
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isLoading}
                  className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 p-0 bg-blue-600 hover:bg-blue-700"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
            <div className="flex items-center justify-center space-x-4 mt-3 text-xs text-gray-500">
              <div className="flex items-center space-x-1">
                <Shield className="w-3 h-3 text-green-600" />
                <span>Privacy protected</span>
              </div>
              <div className="flex items-center space-x-1">
                <Lock className="w-3 h-3 text-blue-600" />
                <span>Enterprise secure</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
