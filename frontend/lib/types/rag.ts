export interface QueryRequest {
  query: string
  top_k_pre?: number
  top_k_post?: number
}

export interface SourceDocument {
  document_name: string
  page: number
  doc_type: string
  doc_url: string
  score: number
}

export interface QueryResponse {
  answer: string
  query: string
  sources: SourceDocument[]
  chunks?: RagChunk[]
}

export interface ChunkMetadata {
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

export interface RagChunk {
  chunk_id: string
  text: string
  score?: number
  metadata: ChunkMetadata
}

export interface DocumentChunk {
  id: string
  text: string
  score: number
  source_doc_name: string
  source_doc_id: string
  doc_type: string
  source_page: number
  chunk_index: number
  is_pi: boolean
  uid?: string
  created_at: string
  doc_url: string
}