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

  useEffect(() => {
    if (token) {
      loadShareLink()
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

  const handleDownload = async () => {
    if (!shareData?.file || !token) return

    try {
      await shareService.downloadSharedFile(
        token, 
        password || undefined,
        shareData.file.original_filename
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
            <button onClick={() => navigate('/login')} className="btn-primary">
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
                <button onClick={() => setPreviewFile({
                  id: shareData!.file!.id,
                  filename: shareData!.file!.original_filename,
                  contentType: shareData!.file!.content_type,
                })} className="btn-primary">
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
              <div className="share-info">
                <div className="info-icon">ℹ️</div>
                <h3>Accès au dossier partagé</h3>
                <p>Pour accéder au contenu de ce dossier partagé, vous devez vous connecter à votre compte SUPFile.</p>
                <p className="info-hint">Une fois connecté, vous pourrez voir et télécharger tous les fichiers contenus dans ce dossier.</p>
                <button onClick={() => navigate('/login')} className="btn-primary">
                  Se connecter pour accéder
                </button>
              </div>
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

      {previewFile && (
        <FileViewer
          fileId={previewFile.id}
          filename={previewFile.filename}
          contentType={previewFile.contentType}
          onClose={() => setPreviewFile(null)}
          shareToken={token}
          sharePassword={password || undefined}
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

