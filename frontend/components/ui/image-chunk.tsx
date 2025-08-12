'use client'

import { FileText, Image, Maximize2, Minimize2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { useState } from 'react'

interface ChunkMetadata {
  source_doc_name: string
  is_table?: boolean
  is_pi?: boolean
  uid?: string
  doc_type?: string
  source_page?: number
  chunk_index?: number
}

interface RagChunk {
  chunk_id: string
  text: string
  score?: number
  metadata: ChunkMetadata
}

interface ChunkDisplayProps {
  chunk: RagChunk
  imageBase64?: string  // Add support for base64 image
}

export function ImageChunk({ chunk, imageBase64 }: ChunkDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  // Debug logging
  console.log('ImageChunk render:', {
    chunkId: chunk.chunk_id,
    hasImageBase64: !!imageBase64,
    imageBase64Length: imageBase64?.length,
    imageBase64Preview: imageBase64?.substring(0, 50) + '...'
  })
  
  // Convert base64 to data URL if provided
  // Try to detect image format or default to webp
  const imageDataUrl = imageBase64 ? (() => {
    // Check if base64 starts with format indicators
    if (imageBase64.startsWith('/9j/')) return `data:image/jpeg;base64,${imageBase64}`
    if (imageBase64.startsWith('iVBORw0K')) return `data:image/png;base64,${imageBase64}`
    if (imageBase64.startsWith('UklGR')) return `data:image/webp;base64,${imageBase64}`
    if (imageBase64.startsWith('R0lGOD')) return `data:image/gif;base64,${imageBase64}`
    // Default to webp
    return `data:image/webp;base64,${imageBase64}`
  })() : null
  
  console.log('imageDataUrl created:', !!imageDataUrl)
  return (
    <div className="rag-chunk border-l-2 border-blue-200 pl-4 py-2 space-y-3">
      {/* Chunk Content Text */}
      <p className="text-sm text-gray-900">{chunk.text}</p>
      
      {/* Debug info - remove this after debugging */}
      {imageBase64 && (
        <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
          DEBUG: Image base64 received (length: {imageBase64.length})
          {!imageDataUrl && " - but imageDataUrl is null!"}
        </div>
      )}
      
      {/* Base64 Image Display - Only shows if imageBase64 is provided */}
      {imageDataUrl && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Image className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-gray-700">Related Image</span>
            </div>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center space-x-1 text-xs text-blue-600 hover:text-blue-800 transition-colors"
            >
              {isExpanded ? (
                <>
                  <Minimize2 className="w-3 h-3" />
                  <span>Minimize</span>
                </>
              ) : (
                <>
                  <Maximize2 className="w-3 h-3" />
                  <span>Expand</span>
                </>
              )}
            </button>
          </div>
          
          <div className="border rounded-lg overflow-hidden bg-gray-50">
            <img
              src={imageDataUrl}
              alt={`Image from ${chunk.metadata.source_doc_name}`}
              className={`w-full object-contain transition-all duration-200 cursor-pointer ${
                isExpanded ? 'max-h-none' : 'max-h-64'
              }`}
              onClick={() => setIsExpanded(!isExpanded)}
              onError={(e) => {
                console.error('Image load error:', e)
                console.error('Image src length:', imageDataUrl?.length)
              }}
              onLoad={() => {
                console.log('Image loaded successfully!')
              }}
            />
          </div>
        </div>
      )}
      
      {/* Source and Metadata */}
      <div className="flex items-center space-x-2">
        <Badge variant="outline" className="text-xs">
          <FileText className="w-3 h-3 mr-1" />
          {chunk.metadata.source_doc_name}
        </Badge>
        {chunk.metadata.source_page && (
          <Badge variant="secondary" className="text-xs">
            Page {chunk.metadata.source_page}
          </Badge>
        )}
        {chunk.metadata.is_table && (
          <Badge variant="secondary" className="text-xs bg-green-100 text-green-800">
            Table
          </Badge>
        )}
        {imageDataUrl && (
          <Badge variant="secondary" className="text-xs bg-purple-100 text-purple-800">
            <Image className="w-3 h-3 mr-1" />
            Image
          </Badge>
        )}
      </div>
    </div>
  )
}