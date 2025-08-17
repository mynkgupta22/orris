'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ImageChunk } from '@/components/ui/image-chunk'
import { Brain, Send, Shield, Clock, FileText, User, Bot, Menu, Search, LogOut, Lock, Trash, X, ChevronDown } from 'lucide-react'
import toast from 'react-hot-toast'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth'
import { ragApi, type ChatSessionListItem, type UUID, type QueryResponseBody } from '@/lib/api/rag'
import { authApi } from '@/lib/api/auth'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'

interface Message {
  id: string
  content: string
  sender: 'user' | 'ai'
  timestamp: Date
  isProtected?: boolean
  sources?: string[]
  chunks?: QueryResponseBody['chunks']
  imageBase64?: string  // Add support for base64 image
}

interface ChatHistory {
  id: string
  title: string
  timestamp: Date
}

type ModelType = 'default' | 'gemini' | 'finllama'

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
  const [sessionId, setSessionId] = useState<UUID | null>(null)
  const [chatSessions, setChatSessions] = useState<ChatSessionListItem[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [selectedModel, setSelectedModel] = useState<ModelType>('default')
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const modelDropdownRef = useRef<HTMLDivElement>(null)
  const { accessToken } = useAuthStore()
  const [roleText, setRoleText] = useState<string>('Signed Up')
  const [isProfileOpen, setIsProfileOpen] = useState(false)
  const [profile, setProfile] = useState<any>(null)
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileError, setProfileError] = useState<string | null>(null)

  // Model options configuration
  const modelOptions = [
    { value: 'default' as ModelType, label: 'Default', description: 'Standard model', disabled: false },
    { value: 'gemini' as ModelType, label: 'Gemini', description: 'Google Gemini model', disabled: false },
    { value: 'finllama' as ModelType, label: 'Fin-Llama', description: 'Financial Llama model (Coming Soon)', disabled: true }
  ]

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(event.target as Node)) {
        setModelDropdownOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Reset selected model if it's finllama (disabled)
  useEffect(() => {
    if (selectedModel === 'finllama') {
      setSelectedModel('default')
    }
  }, [selectedModel])

  // Get use_finllama value based on selected model
  const getUseFinllama = (model: ModelType): boolean => {
    return model === 'finllama'
  }

  // Get selected model display info
  const selectedModelInfo = modelOptions.find(option => option.value === selectedModel)

  // Decode JWT to get role and keep it updated when token changes
  useEffect(() => {
    function parseJwt(token: string): any | null {
      try {
        const base64Url = token.split('.')[1]
        if (!base64Url) return null
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
        const jsonPayload = decodeURIComponent(
          atob(base64)
            .split('')
            .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
            .join('')
        )
        return JSON.parse(jsonPayload)
      } catch {
        return null
      }
    }

    function normalizeRole(raw: unknown): string | null {
      if (!raw) return null
      const s = String(raw).toLowerCase()
      if (['admin'].includes(s)) return 'ADMIN'
      if (['pi_access', 'pi-access', 'piaccess'].includes(s)) return 'PI_ACCESS'
      if (['non_pi_access', 'non-pi-access', 'nonpi', 'nonpi_access'].includes(s)) return 'NON_PI_ACCESS'
      if (['signed_up', 'signed-up', 'signedup', 'basic'].includes(s)) return 'SIGNED_UP'
      return null
    }

    function toLabel(role: string | null): string {
      switch (role) {
        case 'ADMIN':
          return 'Admin'
        case 'PI_ACCESS':
          return 'PI Access'
        case 'NON_PI_ACCESS':
          return 'Non-PI Access'
        case 'SIGNED_UP':
          return 'Signed Up'
        default:
          return 'Signed Up'
      }
    }

    if (accessToken) {
      const payload = parseJwt(accessToken)
      const candidate =
        normalizeRole(payload?.role) ||
        normalizeRole(payload?.user?.role) ||
        normalizeRole(payload?.permissions?.role) ||
        null
      setRoleText(toLabel(candidate))
    } else {
      setRoleText('Signed Up')
    }
  }, [accessToken])

  useEffect(() => {
    // Load user's chat sessions for sidebar
    const loadSessions = async () => {
      try {
        const sessions = await ragApi.listSessions()
        setChatSessions(sessions)
      } catch (err) {
        console.error('Failed to load chat sessions', err)
      }
    }
    loadSessions()
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
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
      // Call the RAG API, including session_id if continuing an existing session
      // and the use_finllama parameter based on selected model
      const response = await ragApi.query({
        query: userQuery,
        top_k_pre: 30,
        top_k_post: 7,
        use_finllama: getUseFinllama(selectedModel),
        ...(sessionId ? { session_id: sessionId } : {}),
      })

      // Ensure we store the active session id (created on first send if not provided)
      setSessionId(response.session_id)

      // Debug logging for base64 image
      console.log('RAG Response received:', {
        hasImageBase64: !!response.image_base64,
        imageBase64Length: response.image_base64?.length,
        responseKeys: Object.keys(response),
        chunksCount: response.chunks?.length
      })

      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: response.answer,
        sender: 'ai',
        timestamp: new Date(),
        chunks: response.chunks,
        imageBase64: response.image_base64, // Include base64 image if present
      }

      console.log('Message created with imageBase64:', !!aiResponse.imageBase64)

      setMessages(prev => [...prev, aiResponse])
      // Refresh sessions list to reflect updated timestamps/order
      ragApi.listSessions().then(setChatSessions).catch(() => {})
    } catch (error) {
      console.error('RAG API error:', error)
      console.error('Error details:', JSON.stringify(error, null, 2))
      
      let errorMessage = 'I apologize, but I encountered an error while processing your request. Please try again later or contact support if the issue persists.'
      let isProtected = false
      
      // Check if it's an authentication or permission error
      if (error && typeof error === 'object' && 'status' in error) {
        if (error.status === 401) {
          // 401 should trigger automatic logout in the RAG API, so this shouldn't be reached
          // But if it does, don't show error message since user will be redirected
          return
        } else if (error.status === 403) {
          errorMessage = 'You don\'t have permission to access this information. Please contact your administrator for access.'
        } else if (error.status === 404) {
          // Likely an invalid or expired session; reset and inform
          setSessionId(null)
          toast('This chat session is no longer available. Starting a new chat.', { icon: 'ℹ️' })
          // Also refresh sessions list
          try { const sessions = await ragApi.listSessions(); setChatSessions(sessions) } catch {}
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
          <Button 
            className="w-full bg-blue-600 hover:bg-blue-700 text-white"
            onClick={() => {
              setSessionId(null)
              setMessages([
                {
                  id: '1',
                  content: 'Hello! I\'m your company\'s AI assistant. I can help you find information from your company documents, policies, and knowledge base. What would you like to know?',
                  sender: 'ai',
                  timestamp: new Date(),
                }
              ])
            }}
          >
            New Chat
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Recent Chats</h3>
            {chatSessions.map((chat) => (
              <Card 
                key={chat.session_id} 
                className="cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={async () => {
                  try {
                    setIsLoading(true)
                    const session = await ragApi.getSession(chat.session_id)
                    setSessionId(session.session_id)
                    const conv = session.conversation?.messages || []
                    const loadedMessages: Message[] = conv.map((m, idx) => ({
                      id: `${session.session_id}-${idx}`,
                      content: m.content,
                      sender: m.role === 'human' ? 'user' : 'ai',
                      timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
                      imageBase64: m.image_base64, // Include image_base64 from chat history
                    }))
                    setMessages(
                      loadedMessages.length > 0
                        ? loadedMessages
                        : [
                            {
                              id: '1',
                              content:
                                "Hello! I'm your company's AI assistant. I can help you find information from your company documents, policies, and knowledge base. What would you like to know?",
                              sender: 'ai',
                              timestamp: new Date(),
                            },
                          ]
                    )
                  } catch (e: any) {
                    console.error('Failed to open chat session', e)
                    if (e && e.status === 404) {
                      toast('That chat was not found or has expired.', { icon: '⚠️' })
                    }
                    // Refresh sessions in case it was deleted/expired
                    try {
                      const sessions = await ragApi.listSessions()
                      setChatSessions(sessions)
                    } catch {}
                  } finally {
                    setIsLoading(false)
                  }
                }}
              >
                <CardContent className="p-3">
                  <div className="flex items-start space-x-3">
                    <Clock className="w-4 h-4 text-gray-400 mt-1 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 truncate">{chat.title}</p>
                      <p className="text-xs text-gray-500">
                        {new Date(chat.updated_at).toLocaleDateString()}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-gray-500 hover:text-red-600"
                      onClick={async (e) => {
                        e.stopPropagation()
                        try {
                          await ragApi.deleteSession(chat.session_id)
                          setChatSessions(prev => prev.filter(s => s.session_id !== chat.session_id))
                          if (sessionId === chat.session_id) {
                            setSessionId(null)
                            setMessages([
                              {
                                id: '1',
                                content:
                                  "Hello! I'm your company's AI assistant. I can help you find information from your company documents, policies, and knowledge base. What would you like to know?",
                                sender: 'ai',
                                timestamp: new Date(),
                              },
                            ])
                          }
                          toast.success('Chat deleted')
                        } catch (delErr) {
                          console.error('Failed to delete chat', delErr)
                          toast.error('Failed to delete chat')
                        }
                      }}
                    >
                      <Trash className="w-4 h-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        <div className="p-4 border-t border-gray-100 space-y-4">
          {/* User Profile Section */}
          <button
            className="bg-gray-50 rounded-lg p-4 w-full text-left hover:bg-gray-100"
            onClick={async () => {
              setIsProfileOpen(true)
              setProfileLoading(true)
              setProfileError(null)
              try {
                const me = await authApi.getCurrentUser()
                setProfile(me)
              } catch (e: any) {
                console.error('Failed to load profile', e)
                setProfile(null)
                setProfileError('Failed to load profile')
              } finally {
                setProfileLoading(false)
              }
            }}
          >
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900">Profile</p>
                <p className="text-xs text-gray-500 truncate">Click to view details</p>
              </div>
            </div>
          </button>
          
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
                <Badge variant="secondary" className="text-xs">{roleText}</Badge>
                <Badge variant="outline" className="text-xs">{selectedModelInfo?.label}</Badge>
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
                  <div className={`text-sm ${
                    message.sender === 'user' 
                      ? 'text-white' 
                      : message.isProtected 
                        ? 'text-red-800' 
                        : 'text-gray-900'
                  }`}>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeRaw]}
                      components={{
                        p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
                        ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-2 pl-2">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-2 pl-2">{children}</ol>,
                        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                        strong: ({ children }) => (
                          <strong className={`font-semibold ${
                            message.sender === 'user' ? 'text-white' : 'text-gray-900'
                          }`}>{children}</strong>
                        ),
                        em: ({ children }) => <em className="italic">{children}</em>,
                        h1: ({ children }) => (
                          <h1 className={`text-lg font-bold mb-3 mt-4 first:mt-0 ${
                            message.sender === 'user' ? 'text-white' : 'text-gray-900'
                          }`}>{children}</h1>
                        ),
                        h2: ({ children }) => (
                          <h2 className={`text-base font-bold mb-2 mt-3 first:mt-0 ${
                            message.sender === 'user' ? 'text-white' : 'text-gray-900'
                          }`}>{children}</h2>
                        ),
                        h3: ({ children }) => (
                          <h3 className={`text-sm font-bold mb-2 mt-2 first:mt-0 ${
                            message.sender === 'user' ? 'text-white' : 'text-gray-900'
                          }`}>{children}</h3>
                        ),
                        h4: ({ children }) => (
                          <h4 className={`text-sm font-semibold mb-1 mt-2 first:mt-0 ${
                            message.sender === 'user' ? 'text-white' : 'text-gray-800'
                          }`}>{children}</h4>
                        ),
                        code: ({ children, className }) => {
                          const isInline = !className;
                          if (isInline) {
                            return (
                              <code className={`px-1.5 py-0.5 rounded text-xs font-mono ${
                                message.sender === 'user' 
                                  ? 'bg-blue-500 bg-opacity-30 text-white' 
                                  : 'bg-gray-100 text-gray-800'
                              }`}>{children}</code>
                            );
                          }
                          return (
                            <pre className={`border p-3 rounded-md text-xs font-mono overflow-x-auto mb-3 ${
                              message.sender === 'user'
                                ? 'bg-blue-500 bg-opacity-20 border-blue-400 text-white'
                                : 'bg-gray-50 border-gray-200 text-gray-800'
                            }`}>
                              <code>{children}</code>
                            </pre>
                          );
                        },
                        blockquote: ({ children }) => (
                          <blockquote className={`border-l-4 pl-4 py-2 italic mb-3 rounded-r-md ${
                            message.sender === 'user'
                              ? 'border-blue-300 bg-blue-500 bg-opacity-20'
                              : 'border-blue-300 bg-blue-50'
                          }`}>{children}</blockquote>
                        ),
                        hr: () => (
                          <hr className={`my-4 ${
                            message.sender === 'user' ? 'border-blue-300' : 'border-gray-300'
                          }`} />
                        ),
                        table: ({ children }) => (
                          <div className="overflow-x-auto mb-3">
                            <table className={`min-w-full border rounded-md ${
                              message.sender === 'user' ? 'border-blue-300' : 'border-gray-200'
                            }`}>{children}</table>
                          </div>
                        ),
                        thead: ({ children }) => (
                          <thead className={message.sender === 'user' ? 'bg-blue-500 bg-opacity-20' : 'bg-gray-50'}>
                            {children}
                          </thead>
                        ),
                        th: ({ children }) => (
                          <th className={`border px-3 py-2 text-left font-semibold ${
                            message.sender === 'user' 
                              ? 'border-blue-300 text-white' 
                              : 'border-gray-200 text-gray-900'
                          }`}>{children}</th>
                        ),
                        td: ({ children }) => (
                          <td className={`border px-3 py-2 ${
                            message.sender === 'user' 
                              ? 'border-blue-300 text-white' 
                              : 'border-gray-200 text-gray-700'
                          }`}>{children}</td>
                        ),
                        a: ({ children, href }) => (
                          <a 
                            href={href} 
                            className={`underline ${
                              message.sender === 'user'
                                ? 'text-blue-200 hover:text-blue-100'
                                : 'text-blue-600 hover:text-blue-800'
                            }`}
                            target="_blank" 
                            rel="noopener noreferrer"
                          >
                            {children}
                          </a>
                        ),
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                  
                  {/* Display chunks if available (for AI responses) */}
                  {message.chunks && message.chunks.length > 0 && (
                    <div className="mt-4 space-y-3">
                      <div className="text-xs text-gray-500 border-t border-gray-100 pt-2">
                        Sources:
                      </div>
                      {message.chunks.map((chunk, index) => {
                        console.log(`Rendering chunk ${index}:`, {
                          chunkId: chunk.chunk_id,
                          messageHasImageBase64: !!message.imageBase64,
                          imageBase64Length: message.imageBase64?.length
                        })
                        return (
                          <ImageChunk 
                            key={`${message.id}-chunk-${index}`} 
                            chunk={chunk} 
                            imageBase64={message.imageBase64} 
                          />
                        )
                      })}
                    </div>
                  )}
                  
                  {/* Display image if available but no chunks (direct image response) */}
                  {message.imageBase64 && (!message.chunks || message.chunks.length === 0) && (
                    <div className="mt-4 space-y-3">
                      <div className="text-xs text-gray-500 border-t border-gray-100 pt-2">
                        Related Image:
                      </div>
                      <div className="border rounded-lg overflow-hidden bg-gray-50">
                        <img
                          src={(() => {
                            // Auto-detect image format
                            const base64 = message.imageBase64!
                            if (base64.startsWith('/9j/')) return `data:image/jpeg;base64,${base64}`
                            if (base64.startsWith('iVBORw0K')) return `data:image/png;base64,${base64}`
                            if (base64.startsWith('UklGR')) return `data:image/webp;base64,${base64}`
                            if (base64.startsWith('R0lGOD')) return `data:image/gif;base64,${base64}`
                            return `data:image/webp;base64,${base64}`
                          })()}
                          alt="Related image content"
                          className="w-full object-contain max-h-96 cursor-pointer"
                          onClick={(e) => {
                            const img = e.target as HTMLImageElement
                            if (img.style.maxHeight === 'none') {
                              img.style.maxHeight = '24rem'
                            } else {
                              img.style.maxHeight = 'none'
                            }
                          }}
                          onError={(e) => {
                            console.error('Image load error:', e)
                            console.error('Base64 length:', message.imageBase64?.length)
                          }}
                          onLoad={() => {
                            console.log('Image loaded successfully!')
                          }}
                        />
                      </div>
                    </div>
                  )}
                  
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
              {/* Model Selection Dropdown */}
              <div className="relative" ref={modelDropdownRef}>
                <button
                  onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
                  className="flex items-center space-x-2 px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors h-12"
                  disabled={isLoading}
                >
                  <Brain className="w-4 h-4 text-gray-600" />
                  <span className="text-sm text-gray-700">{selectedModelInfo?.label}</span>
                  <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${modelDropdownOpen ? 'rotate-180' : ''}`} />
                </button>
                
                {modelDropdownOpen && (
                  <div className="absolute bottom-full mb-2 left-0 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
                    <div className="p-2">
                      {modelOptions.map((option) => (
                        <button
                          key={option.value}
                          onClick={() => {
                            if (!option.disabled) {
                              setSelectedModel(option.value)
                              setModelDropdownOpen(false)
                            }
                          }}
                          disabled={option.disabled}
                          className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
                            option.disabled
                              ? 'cursor-not-allowed opacity-50 bg-gray-50 text-gray-400'
                              : selectedModel === option.value
                              ? 'bg-blue-50 text-blue-700 border border-blue-200'
                              : 'hover:bg-gray-50 text-gray-700'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="font-medium text-sm">{option.label}</div>
                              <div className="text-xs text-gray-500">{option.description}</div>
                            </div>
                            {option.disabled && (
                              <Lock className="w-4 h-4 text-gray-400" />
                            )}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

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
              <div className="flex items-center space-x-1">
                <Brain className="w-3 h-3 text-purple-600" />
                <span>Model: {selectedModelInfo?.label}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      {/* Profile Modal */}
      {isProfileOpen && (
        <div className="fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/40" onClick={() => setIsProfileOpen(false)} />
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[92vw] max-w-md bg-white rounded-xl shadow-xl border border-gray-200">
            <div className="flex items-center justify-between p-4 border-b border-gray-100">
              <h3 className="text-base font-semibold text-gray-900">Your Profile</h3>
              <button className="p-1 text-gray-500 hover:text-gray-700" onClick={() => setIsProfileOpen(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4">
              {profileLoading && (
                <p className="text-sm text-gray-500">Loading…</p>
              )}
              {!profileLoading && profileError && (
                <p className="text-sm text-red-600">{profileError}</p>
              )}
              {!profileLoading && !profileError && (
                <div className="space-y-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                      <User className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{(profile as any)?.name ?? '—'}</p>
                      <p className="text-xs text-gray-500">{(profile as any)?.email ?? '—'}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-xs text-gray-500">Role</p>
                      <p className="text-sm text-gray-900">{(profile as any)?.role ?? '—'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Status</p>
                      <p className="text-sm text-gray-900">{(profile as any)?.status ?? '—'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Email Verified</p>
                      <p className="text-sm text-gray-900">{((profile as any)?.email_verified ?? (profile as any)?.emailVerified) ? 'Yes' : 'No'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Joined</p>
                      <p className="text-sm text-gray-900">{(profile as any)?.created_at ? new Date((profile as any).created_at).toLocaleString() : ((profile as any)?.createdAt ? new Date((profile as any).createdAt).toLocaleString() : '—')}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="p-4 border-t border-gray-100 text-right">
              <Button onClick={() => setIsProfileOpen(false)} className="bg-gray-800 text-white hover:bg-gray-900">Close</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
