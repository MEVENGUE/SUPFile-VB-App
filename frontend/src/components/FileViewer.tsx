import React, { useState, useEffect, useRef } from 'react'
import { fileService } from '../services/fileService'
import './FileViewer.css'

interface FileViewerProps {
  fileId: number
  filename: string
  contentType?: string
  onClose: () => void
}

const FileViewer: React.FC<FileViewerProps> = ({ fileId, filename, contentType, onClose }) => {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [textContent, setTextContent] = useState<string | null>(null)
  const [imageZoom, setImageZoom] = useState(1)
  const [imagePosition, setImagePosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [isFullscreen, setIsFullscreen] = useState(false)
  const imageRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    const loadPreview = async () => {
      try {
        setLoading(true)
        const data = await fileService.getPreviewUrl(fileId)
        setPreviewUrl(data.preview_url)

        // For text files, fetch and display content directly
        if (isTextFile(data.content_type || contentType || '')) {
          try {
            const response = await fetch(data.preview_url)
            const text = await response.text()
            setTextContent(text)
          } catch (err) {
            console.error('Error loading text content:', err)
            setError('Impossible de charger le contenu du fichier texte')
          }
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Erreur lors du chargement de la prévisualisation')
      } finally {
        setLoading(false)
      }
    }

    loadPreview()
  }, [fileId, contentType])

  const isTextFile = (contentType: string): boolean => {
    return (
      contentType?.startsWith('text/') ||
      contentType === 'application/json' ||
      filename.endsWith('.txt') ||
      filename.endsWith('.md') ||
      filename.endsWith('.json') ||
      filename.endsWith('.csv') ||
      filename.endsWith('.log')
    )
  }

  const isImage = (contentType?: string): boolean => {
    return contentType?.startsWith('image/') || false
  }

  const isPDF = (contentType?: string): boolean => {
    return contentType === 'application/pdf' || filename.toLowerCase().endsWith('.pdf')
  }

  const isAudio = (contentType?: string): boolean => {
    return contentType?.startsWith('audio/') || false
  }

  const isVideo = (contentType?: string): boolean => {
    return contentType?.startsWith('video/') || false
  }

  const handleImageZoom = (delta: number) => {
    setImageZoom((prev) => {
      const newZoom = Math.max(0.5, Math.min(5, prev + delta))
      return newZoom
    })
  }

  const handleImageReset = () => {
    setImageZoom(1)
    setImagePosition({ x: 0, y: 0 })
  }

  const handleImageDragStart = (e: React.MouseEvent) => {
    if (imageZoom > 1) {
      setIsDragging(true)
      setDragStart({ x: e.clientX - imagePosition.x, y: e.clientY - imagePosition.y })
    }
  }

  const handleImageDrag = (e: React.MouseEvent) => {
    if (isDragging && imageZoom > 1) {
      setImagePosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      })
    }
  }

  const handleImageDragEnd = () => {
    setIsDragging(false)
  }

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
  }

  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      if (isImage(contentType) && imageRef.current) {
        e.preventDefault()
        const delta = e.deltaY > 0 ? -0.1 : 0.1
        handleImageZoom(delta)
      }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false)
      }
      if (e.key === '+' || e.key === '=') {
        handleImageZoom(0.1)
      }
      if (e.key === '-') {
        handleImageZoom(-0.1)
      }
      if (e.key === '0') {
        handleImageReset()
      }
    }

    if (isImage(contentType)) {
      window.addEventListener('wheel', handleWheel, { passive: false })
      window.addEventListener('keydown', handleKeyDown)
    }

    return () => {
      window.removeEventListener('wheel', handleWheel)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [contentType, imageZoom, isFullscreen])

  if (loading) {
    return (
      <div className="file-viewer-overlay" onClick={onClose}>
        <div className="file-viewer-container" onClick={(e) => e.stopPropagation()}>
          <div className="file-viewer-loading">
            <div className="spinner"></div>
            <p>Chargement de la prévisualisation...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="file-viewer-overlay" onClick={onClose}>
        <div className="file-viewer-container" onClick={(e) => e.stopPropagation()}>
          <div className="file-viewer-error">
            <span className="error-icon">⚠️</span>
            <p>{error}</p>
            <button onClick={onClose} className="close-button">
              Fermer
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="file-viewer-overlay" onClick={onClose}>
      <div className="file-viewer-container" onClick={(e) => e.stopPropagation()}>
        <div className="file-viewer-header">
          <h3 className="file-viewer-title">{filename}</h3>
          <button onClick={onClose} className="file-viewer-close" aria-label="Fermer">
            ✕
          </button>
        </div>

        <div className="file-viewer-content">
          {isImage(contentType) && previewUrl && (
            <div className={`image-viewer ${isFullscreen ? 'fullscreen' : ''}`}>
              <div className="image-controls">
                <button
                  onClick={() => handleImageZoom(0.1)}
                  className="zoom-btn"
                  title="Zoomer (molette ou +)"
                >
                  ➕
                </button>
                <button
                  onClick={() => handleImageZoom(-0.1)}
                  className="zoom-btn"
                  title="Dézoomer (molette ou -)"
                >
                  ➖
                </button>
                <button
                  onClick={handleImageReset}
                  className="zoom-btn"
                  title="Réinitialiser (0)"
                >
                  🔍
                </button>
                <button
                  onClick={toggleFullscreen}
                  className="zoom-btn"
                  title="Plein écran (F11)"
                >
                  {isFullscreen ? '🗗' : '🗖'}
                </button>
              </div>
              <div
                className="image-container"
                onMouseDown={handleImageDragStart}
                onMouseMove={handleImageDrag}
                onMouseUp={handleImageDragEnd}
                onMouseLeave={handleImageDragEnd}
                style={{ cursor: imageZoom > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default' }}
              >
                <img
                  ref={imageRef}
                  src={previewUrl}
                  alt={filename}
                  className="preview-image"
                  style={{
                    transform: `scale(${imageZoom}) translate(${imagePosition.x / imageZoom}px, ${imagePosition.y / imageZoom}px)`,
                    transition: isDragging ? 'none' : 'transform 0.1s ease-out',
                  }}
                  draggable={false}
                />
              </div>
              <div className="image-info">
                Zoom: {Math.round(imageZoom * 100)}% | Utilisez la molette pour zoomer, glissez pour déplacer
              </div>
            </div>
          )}

          {isPDF(contentType) && previewUrl && (
            <div className="pdf-viewer">
              <iframe
                src={previewUrl}
                title={filename}
                className="preview-iframe"
                frameBorder="0"
              />
            </div>
          )}

          {isTextFile(contentType || '') && (
            <div className="text-viewer">
              <pre className="text-content">
                {textContent || 'Chargement du contenu...'}
              </pre>
            </div>
          )}

          {isAudio(contentType) && previewUrl && (
            <div className="audio-viewer">
              <audio controls className="preview-audio" src={previewUrl}>
                Votre navigateur ne supporte pas la lecture audio.
              </audio>
            </div>
          )}

          {isVideo(contentType) && previewUrl && (
            <div className="video-viewer">
              <video controls className="preview-video" src={previewUrl}>
                Votre navigateur ne supporte pas la lecture vidéo.
              </video>
            </div>
          )}

          {!isImage(contentType) &&
            !isPDF(contentType) &&
            !isTextFile(contentType || '') &&
            !isAudio(contentType) &&
            !isVideo(contentType) && (
              <div className="unsupported-viewer">
                <span className="unsupported-icon">📄</span>
                <p>Prévisualisation non disponible pour ce type de fichier</p>
                <p className="unsupported-hint">
                  Type: {contentType || 'inconnu'}
                </p>
                {previewUrl && (
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="download-link"
                  >
                    Télécharger le fichier
                  </a>
                )}
              </div>
            )}
        </div>
      </div>
    </div>
  )
}

export default FileViewer

