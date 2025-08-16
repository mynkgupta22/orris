import { useAuthStore } from '@/lib/stores/auth'

type UUID = string

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const state = useAuthStore.getState?.() as { accessToken?: string } | undefined
  const token = state?.accessToken

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache',
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!res.ok) {
    // Handle 401 Unauthorized - automatic logout
    if (res.status === 401) {
      console.log('401 detected in RAG API, clearing auth and redirecting to login')
      
      // Clear auth data
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth-storage')
        localStorage.removeItem('user_company')
        
        // Redirect to login
        window.location.href = '/login'
      }
    }
    
    const errText = await res.text().catch(() => '')
    const error: any = new Error(`HTTP ${res.status}`)
    error.status = res.status
    error.body = errText
    throw error
  }

  return res.json() as Promise<T>
}

export interface QueryRequestBody {
  query: string
  session_id?: UUID
  top_k_pre?: number
  top_k_post?: number
  use_finllama?: boolean
}

export interface QueryResponseBody {
  answer: string
  query: string
  session_id: UUID
  image_base64?: string  // Add support for base64 image from backend
  chunks?: Array<{
    chunk_id: string
    text: string
    metadata: {
      is_image?: boolean
      image_summary?: string
      source_doc_name: string
      is_table?: boolean
      is_pi?: boolean
      uid?: string
      doc_type?: string
      source_page?: number
      chunk_index?: number
    }
  }>
}

export interface ChatSessionListItem {
  session_id: UUID
  title: string
  message_count: number
  created_at: string
  updated_at: string
  expires_at: string
}

export interface ChatSessionDetail {
  session_id: UUID
  title: string
  conversation: {
    messages: Array<{
      role: 'human' | 'assistant'
      content: string
      timestamp: string
      image_base64?: string  // Add support for base64 image in chat history
    }>
  }
  created_at: string
  updated_at: string
  expires_at: string
  message_count: number
}

export const ragApi = {
  async query(body: QueryRequestBody): Promise<QueryResponseBody> {
    return request<QueryResponseBody>('/rag/query', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  async listSessions(): Promise<ChatSessionListItem[]> {
    return request<ChatSessionListItem[]>('/rag/chat-sessions', {
      method: 'GET',
    })
  },

  async getSession(sessionId: UUID): Promise<ChatSessionDetail> {
    return request<ChatSessionDetail>(`/rag/chat-sessions/${sessionId}`, {
      method: 'GET',
    })
  },

  async deleteSession(sessionId: UUID): Promise<{ message: string }> {
    return request<{ message: string }>(`/rag/chat-sessions/${sessionId}`, {
      method: 'DELETE',
    })
  },
}

export type { UUID }
 