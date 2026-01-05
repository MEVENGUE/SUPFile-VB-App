import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { shareService, type ShareAccessResponse } from '../services/shareService'
import { toast } from 'react-toastify'
import FileViewer from '../components/FileViewer'
import './SharePage.css'

const SharePage: React.FC = () => {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [passwordRequired, setPasswordRequired] = useState(false)
  const [password, setPassword] = useState('')
  const [shareData, setShareData] = useState<ShareAccessResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [previewFile, setPreviewFile] = useState<{ id: number; filename: string; contentType?: string } | null>(null)
  const [folderContent, setFolderContent] = useState<{
    folder: { id: number; name: string; created_at: string | null }
    files: Array<{
      id: number
      filename: string
      original_filename: string
      file_size: number
      content_type: string
      created_at: string | null
    }>
    subfolders: Array<{
      id: number
      name: string
      created_at: string | null
    }>
    files_total: number
    subfolders_total: number
  } | null>(null)
  const [loadingFolderContent, setLoadingFolderContent] = useState(false)

  useEffect(() => {
    console.log('SharePage mounted, token from URL:', token)
    if (token) {
      console.log('Token found, loading share link...')
      loadShareLink()
    } else {
      console.error('No token found in URL params')
      setError('Token de partage manquant dans l\'URL')
      setLoading(false)
    }
  }, [token])

  const loadShareLink = async (providedPassword?: string) => {
    try {
      setLoading(true)
      setError(null)
      
      console.log('Loading share link with token:', token)
      const data = await shareService.getShareLink(token!, providedPassword || password)
      console.log('Share link data received:', data)
      setShareData(data)
      setPasswordRequired(false)

      // If it's a file, prepare for preview
      if (data.file) {
        setPreviewFile({
          id: data.file.id,
          filename: data.file.original_filename,
          contentType: data.file.content_type,
        })
      }

      // If it's a folder, load its content
      if (data.folder && token) {
        loadFolderContent(token, providedPassword || password)
      }
    } catch (err: any) {
      console.error('Error loading share link:', err)
      if (err.response?.status === 401) {
        setPasswordRequired(true)
        setError('Mot de passe requis pour accéder à ce lien')
      } else if (err.response?.status === 404) {
        setError('Lien de partage introuvable. Le lien peut avoir expiré ou avoir été supprimé.')
      } else if (err.response?.status === 403) {
        setError(err.response?.data?.detail || 'Ce lien de partage a été désactivé ou a expiré.')
      } else if (err.response?.status === 500) {
        setError('Erreur serveur. Veuillez réessayer plus tard.')
      } else if (!err.response) {
        setError('Erreur de connexion. Vérifiez votre connexion internet.')
      } else {
        setError(err.response?.data?.detail || 'Erreur lors du chargement du lien de partage')
      }
    } finally {
      setLoading(false)
    }
  }

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    loadShareLink(password)
  }

  const loadFolderContent = async (shareToken: string, sharePassword?: string) => {
    try {
      setLoadingFolderContent(true)
      const content = await shareService.getSharedFolderContent(shareToken, sharePassword)
      setFolderContent(content)
    } catch (err: any) {
      console.error('Error loading folder content:', err)
      if (err.response?.status === 401) {
        setPasswordRequired(true)
        setError('Mot de passe requis pour accéder à ce dossier')
      } else {
        setError(err.response?.data?.detail || 'Erreur lors du chargement du contenu du dossier')
      }
    } finally {
      setLoadingFolderContent(false)
    }
  }

  const handleDownload = async () => {
    if (!token) return

    try {
      if (shareData?.file) {
        // Download single file
        await shareService.downloadSharedFile(
          token, 
          password || undefined,
          shareData.file.original_filename
        )
        toast.success('Téléchargement démarré')
      } else if (shareData?.folder) {
        // Download folder as ZIP (downloadSharedFile handles both files and folders)
        await shareService.downloadSharedFile(
          token,
          password || undefined,
          `${shareData.folder.name}.zip`
        )
        toast.success('Téléchargement du dossier en cours...')
      }
    } catch (error: any) {
      if (error.response?.status === 401) {
        setPasswordRequired(true)
        setError('Mot de passe requis pour télécharger')
      } else {
        toast.error(error.response?.data?.detail || 'Erreur lors du téléchargement')
      }
    }
  }

  const handleDownloadFileFromFolder = async (file: {
    id: number
    filename: string
    original_filename: string
    file_size: number
    content_type: string
    created_at: string | null
  }) => {
    if (!token) return

    try {
      await shareService.downloadFileFromSharedFolder(
        token,
        file.id,
        password || undefined
      )
      toast.success('Téléchargement démarré')
    } catch (error: any) {
      if (error.response?.status === 401) {
        setPasswordRequired(true)
        setError('Mot de passe requis pour télécharger ce fichier')
      } else {
        toast.error(error.response?.data?.detail || 'Erreur lors du téléchargement')
      }
    }
  }

  const handlePreviewFileFromFolder = (file: {
    id: number
    filename: string
    original_filename: string
    file_size: number
    content_type: string
    created_at: string | null
  }) => {
    // For files in shared folders, we need to use the folder share token
    // The FileViewer will need to handle this case
    setPreviewFile({
      id: file.id,
      filename: file.original_filename,
      contentType: file.content_type,
    })
  }

  if (loading) {
    return (
      <div className="share-page">
        <div className="share-page-container">
          <div className="share-loading">
            <div className="spinner"></div>
            <p>Chargement du lien de partage...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error && !passwordRequired) {
    return (
      <div className="share-page">
        <div className="share-page-container">
          <div className="share-error">
            <span className="error-icon">⚠️</span>
            <h2>Lien de partage invalide</h2>
            <p>{error}</p>
                <button onClick={() => {
                  // Store the share URL in sessionStorage for redirect after login
                  sessionStorage.setItem('redirectAfterLogin', `/share/${token}`)
                  navigate('/login')
                }} className="btn-primary">
                  Se connecter
                </button>
          </div>
        </div>
      </div>
    )
  }

  if (passwordRequired) {
    return (
      <div className="share-page">
        <div className="share-page-container">
          <div className="share-password-form">
            <div className="password-header">
              <span className="lock-icon">🔒</span>
              <h2>Lien protégé par mot de passe</h2>
              <p>Ce lien de partage est protégé. Veuillez entrer le mot de passe.</p>
            </div>
            <form onSubmit={handlePasswordSubmit} className="password-form">
              <div className="form-group">
                <label htmlFor="password">Mot de passe</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Entrez le mot de passe"
                  className="form-input"
                  required
                  autoFocus
                />
              </div>
              {error && <p className="error-message">{error}</p>}
              <div className="form-actions">
                <button type="submit" className="btn-primary">
                  Accéder
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    )
  }

  if (!shareData) {
    return null
  }

  return (
    <div className="share-page">
      <div className="share-page-container">
        <div className="share-content">
          <div className="share-header">
            <h1>Fichier partagé</h1>
            <p className="share-subtitle">
              {shareData.file ? 'Fichier partagé avec vous' : 'Dossier partagé avec vous'}
            </p>
          </div>

          {shareData.file && (
            <div className="share-file-info">
              <div className="file-details-card">
                <div className="file-icon-large">📄</div>
                <div className="file-details">
                  <h2>{shareData.file.original_filename}</h2>
                  <div className="file-meta">
                    <span>Taille: {formatFileSize(shareData.file.file_size || shareData.file.size)}</span>
                    <span>Type: {shareData.file.content_type || 'Inconnu'}</span>
                    <span>
                      {shareData.file.created_at && (
                        <>Créé le: {new Date(shareData.file.created_at).toLocaleDateString('fr-FR')}</>
                      )}
                    </span>
                  </div>
                </div>
              </div>

              <div className="share-actions">
                <button onClick={() => {
                  console.log('Preview button clicked, token:', token)
                  setPreviewFile({
                    id: shareData!.file!.id,
                    filename: shareData!.file!.original_filename,
                    contentType: shareData!.file!.content_type,
                  })
                }} className="btn-primary">
                  👁️ Prévisualiser
                </button>
                <button onClick={handleDownload} className="btn-secondary">
                  ⬇️ Télécharger
                </button>
              </div>
            </div>
          )}

          {shareData.folder && (
            <div className="share-folder-info">
              <div className="folder-details-card">
                <div className="folder-icon-large">📁</div>
                <div className="folder-details">
                  <h2>{shareData.folder.name}</h2>
                  <div className="folder-meta">
                    <span>
                      {shareData.folder.created_at && (
                        <>Créé le: {new Date(shareData.folder.created_at).toLocaleDateString('fr-FR')}</>
                      )}
                    </span>
                  </div>
                </div>
              </div>

              <div className="share-actions">
                <button onClick={handleDownload} className="btn-primary">
                  📦 Télécharger le dossier (ZIP)
                </button>
              </div>

              {loadingFolderContent ? (
                <div className="share-loading">
                  <div className="spinner"></div>
                  <p>Chargement du contenu du dossier...</p>
                </div>
              ) : folderContent ? (
                <div className="folder-content">
                  {folderContent.files_total > 0 && (
                    <div className="folder-section">
                      <h3>Fichiers ({folderContent.files_total})</h3>
                      <div className="file-list">
                        {folderContent.files.map((file) => (
                          <div key={file.id} className="file-item">
                            <div className="file-icon">📄</div>
                            <div className="file-info">
                              <span className="file-name">{file.original_filename}</span>
                              <span className="file-size">{formatFileSize(file.file_size)}</span>
                            </div>
                            <div className="file-actions">
                              <button
                                onClick={() => handlePreviewFileFromFolder(file)}
                                className="btn-icon"
                                title="Prévisualiser"
                              >
                                👁️
                              </button>
                              <button
                                onClick={() => handleDownloadFileFromFolder(file)}
                                className="btn-icon"
                                title="Télécharger"
                              >
                                ⬇️
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {folderContent.subfolders_total > 0 && (
                    <div className="folder-section">
                      <h3>Dossiers ({folderContent.subfolders_total})</h3>
                      <div className="folder-list">
                        {folderContent.subfolders.map((subfolder) => (
                          <div key={subfolder.id} className="folder-item">
                            <div className="folder-icon">📁</div>
                            <div className="folder-info">
                              <span className="folder-name">{subfolder.name}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {folderContent.files_total === 0 && folderContent.subfolders_total === 0 && (
                    <div className="empty-folder">
                      <p>Ce dossier est vide</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="share-info">
                  <div className="info-icon">ℹ️</div>
                  <p>Chargement du contenu du dossier...</p>
                </div>
              )}
            </div>
          )}

          <div className="share-footer">
            <p className="share-info-text">
              Partage créé le {new Date(shareData.share_link.created_at).toLocaleDateString('fr-FR')}
              {shareData.share_link.expires_at && (
                <> • Expire le {new Date(shareData.share_link.expires_at).toLocaleDateString('fr-FR')}</>
              )}
            </p>
          </div>
        </div>
      </div>

      {previewFile && token && (
        <FileViewer
          key={`${token}-${previewFile.id}`}
          fileId={previewFile.id}
          filename={previewFile.filename}
          contentType={previewFile.contentType}
          onClose={() => setPreviewFile(null)}
          shareToken={token}
          sharePassword={password || undefined}
          isFromSharedFolder={!!shareData?.folder && !!folderContent}
        />
      )}
    </div>
  )
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

export default SharePage

