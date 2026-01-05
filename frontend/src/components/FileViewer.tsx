import React, { useState, useEffect, useRef } from 'react'
import { fileService } from '../services/fileService'
import { shareService } from '../services/shareService'
import './FileViewer.css'

interface FileViewerProps {
  fileId: number
  filename: string
  contentType?: string
  onClose: () => void
  shareToken?: string
  sharePassword?: string
  isFromSharedFolder?: boolean // Indicates if this file is from a shared folder
}

const FileViewer: React.FC<FileViewerProps> = ({ fileId, filename, contentType, onClose, shareToken, sharePassword, isFromSharedFolder }) => {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [textContent, setTextContent] = useState<string | null>(null)
  const [imageZoom, setImageZoom] = useState(1)
  const [imagePosition, setImagePosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [touchStart, setTouchStart] = useState<{ x: number; y: number; distance: number } | null>(null)
  const [isMobile, setIsMobile] = useState(false)
  const imageRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    // Détecter si on est sur mobile
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768 || 'ontouchstart' in window)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  useEffect(() => {
    const loadPreview = async () => {
      try {
        setLoading(true)
        let data: { preview_url: string; content_type: string; filename: string }
        
        console.log('FileViewer loadPreview:', { 
          shareToken, 
          shareTokenType: typeof shareToken,
          shareTokenLength: shareToken?.length,
          sharePassword, 
          fileId, 
          isFromSharedFolder 
        })
        
        // Use share service if shareToken is provided and not empty, otherwise use regular file service
        if (shareToken && shareToken.trim().length > 0) {
          console.log('Using share service for preview with token:', shareToken.substring(0, 8) + '...')
          // If file is from a shared folder, pass fileId to the preview endpoint
          data = await shareService.getSharedFilePreview(shareToken, sharePassword, isFromSharedFolder ? fileId : undefined)
        } else {
          console.warn('shareToken is missing or empty, using regular file service for preview')
          data = await fileService.getPreviewUrl(fileId)
        }
        
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
  }, [fileId, contentType, shareToken, sharePassword, isFromSharedFolder])

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

  const isOfficeDocument = (contentType?: string, filename?: string): boolean => {
    if (!contentType && !filename) return false
    const officeTypes = [
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
      'application/vnd.ms-powerpoint',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation', // .pptx
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
      'application/vnd.oasis.opendocument.text', // .odt
      'application/vnd.oasis.opendocument.presentation', // .odp
      'application/vnd.oasis.opendocument.spreadsheet', // .ods
    ]
    const officeExtensions = ['.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.odt', '.odp', '.ods']
    
    if (contentType && officeTypes.includes(contentType)) return true
    if (filename) {
      const lowerFilename = filename.toLowerCase()
      return officeExtensions.some(ext => lowerFilename.endsWith(ext))
    }
    return false
  }

  const getOfficePreviewUrl = (previewUrl: string, contentType?: string, filename?: string): string => {
    // Use Microsoft Office Online Viewer for Office documents
    // This requires the file to be publicly accessible or use a service that can access it
    const encodedUrl = encodeURIComponent(previewUrl)
    
    if (contentType?.includes('word') || filename?.match(/\.(doc|docx)$/i)) {
      return `https://view.officeapps.live.com/op/embed.aspx?src=${encodedUrl}`
    }
    if (contentType?.includes('powerpoint') || filename?.match(/\.(ppt|pptx)$/i)) {
      return `https://view.officeapps.live.com/op/embed.aspx?src=${encodedUrl}`
    }
    if (contentType?.includes('excel') || filename?.match(/\.(xls|xlsx)$/i)) {
      return `https://view.officeapps.live.com/op/embed.aspx?src=${encodedUrl}`
    }
    
    // Fallback: return original URL
    return previewUrl
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

  // Gestion tactile pour mobile
  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 2) {
      const touch1 = e.touches[0]
      const touch2 = e.touches[1]
      const distance = Math.hypot(
        touch2.clientX - touch1.clientX,
        touch2.clientY - touch1.clientY
      )
      setTouchStart({ x: (touch1.clientX + touch2.clientX) / 2, y: (touch1.clientY + touch2.clientY) / 2, distance })
    } else if (e.touches.length === 1 && imageZoom > 1) {
      const touch = e.touches[0]
      setIsDragging(true)
      setDragStart({ x: touch.clientX - imagePosition.x, y: touch.clientY - imagePosition.y })
    }
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    if (e.touches.length === 2 && touchStart) {
      const touch1 = e.touches[0]
      const touch2 = e.touches[1]
      const distance = Math.hypot(
        touch2.clientX - touch1.clientX,
        touch2.clientY - touch1.clientY
      )
      const scale = distance / touchStart.distance
      const newZoom = Math.max(0.5, Math.min(5, imageZoom * scale))
      setImageZoom(newZoom)
    } else if (e.touches.length === 1 && isDragging && imageZoom > 1) {
      const touch = e.touches[0]
      setImagePosition({
        x: touch.clientX - dragStart.x,
        y: touch.clientY - dragStart.y,
      })
    }
  }

  const handleTouchEnd = () => {
    setIsDragging(false)
    setTouchStart(null)
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
            <div className={`image-viewer ${isFullscreen ? 'fullscreen' : ''} ${isMobile ? 'mobile' : ''}`}>
              <div className="image-controls">
                <button
                  onClick={() => handleImageZoom(0.1)}
                  className="zoom-btn"
                  title="Zoomer"
                  aria-label="Zoomer"
                >
                  ➕
                </button>
                <button
                  onClick={() => handleImageZoom(-0.1)}
                  className="zoom-btn"
                  title="Dézoomer"
                  aria-label="Dézoomer"
                >
                  ➖
                </button>
                <button
                  onClick={handleImageReset}
                  className="zoom-btn"
                  title="Réinitialiser"
                  aria-label="Réinitialiser"
                >
                  🔍
                </button>
                <button
                  onClick={toggleFullscreen}
                  className="zoom-btn"
                  title="Plein écran"
                  aria-label="Plein écran"
                >
                  {isFullscreen ? '🗗' : '🗖'}
                </button>
              </div>
              {isMobile && (
                <div className="mobile-hints">
                  <p>📌 Pincez pour zoomer • Glissez pour déplacer</p>
                </div>
              )}
              <div
                className="image-container"
                onMouseDown={handleImageDragStart}
                onMouseMove={handleImageDrag}
                onMouseUp={handleImageDragEnd}
                onMouseLeave={handleImageDragEnd}
                onTouchStart={handleTouchStart}
                onTouchMove={handleTouchMove}
                onTouchEnd={handleTouchEnd}
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
                Zoom: {Math.round(imageZoom * 100)}% {!isMobile && '| Utilisez la molette pour zoomer, glissez pour déplacer'}
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

          {isOfficeDocument(contentType, filename) && previewUrl && (
            <div className="office-viewer">
              <div className="office-viewer-info">
                <p>📄 Document Office détecté</p>
                <p className="office-hint">Prévisualisation via Office Online</p>
              </div>
              <iframe
                src={getOfficePreviewUrl(previewUrl, contentType, filename)}
                title={filename}
                className="preview-iframe office-iframe"
                frameBorder="0"
                allow="fullscreen"
              />
              <div className="office-fallback">
                <p>Si la prévisualisation ne fonctionne pas, vous pouvez :</p>
                <a
                  href={previewUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="download-link"
                  download={filename}
                >
                  📥 Télécharger le fichier
                </a>
              </div>
            </div>
          )}

          {!isImage(contentType) &&
            !isPDF(contentType) &&
            !isTextFile(contentType || '') &&
            !isAudio(contentType) &&
            !isVideo(contentType) &&
            !isOfficeDocument(contentType, filename) && (
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
                    download={filename}
                  >
                    📥 Télécharger le fichier
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

