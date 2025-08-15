'use client'

import { useState, useEffect } from 'react'
import { useAuthStore } from '@/lib/stores/auth'

interface AuthenticatedImageProps {
  src: string
  alt: string
  className?: string
  onClick?: () => void
  onLoad?: () => void
  onError?: () => void
}

export function AuthenticatedImage({
  src,
  alt,
  className,
  onClick,
  onLoad,
  onError,
}: AuthenticatedImageProps) {
  const [imageSrc, setImageSrc] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const { accessToken } = useAuthStore()

  useEffect(() => {
    const loadImage = async () => {
      try {
        setLoading(true)
        setError(false)
        
        const response = await fetch(src, {
          headers: {
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          },
        })

        if (!response.ok) {
          throw new Error(`Failed to load image: ${response.status}`)
        }

        const blob = await response.blob()
        const imageUrl = URL.createObjectURL(blob)
        setImageSrc(imageUrl)
        onLoad?.()
      } catch (err) {
        console.error('Error loading authenticated image:', err)
        setError(true)
        onError?.()
      } finally {
        setLoading(false)
      }
    }

    if (src && accessToken) {
      loadImage()
    }

    // Cleanup function to revoke object URL
    return () => {
      if (imageSrc) {
        URL.revokeObjectURL(imageSrc)
      }
    }
  }, [src, accessToken, onLoad, onError])

  if (loading || !imageSrc) {
    return null // Parent component handles loading state
  }

  if (error) {
    return null // Parent component handles error state
  }

  return (
    <img
      src={imageSrc}
      alt={alt}
      className={className}
      onClick={onClick}
    />
  )
}