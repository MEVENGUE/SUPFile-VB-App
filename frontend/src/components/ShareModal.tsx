import React, { useState } from 'react'
import { shareService, type ShareLinkMetadata } from '../services/shareService'
import { toast } from 'react-toastify'
import './ShareModal.css'

interface ShareModalProps {
  fileId?: number
  folderId?: number
  filename: string
  onClose: () => void
  onShareCreated?: (shareLink: ShareLinkMetadata) => void
}

const ShareModal: React.FC<ShareModalProps> = ({
  fileId,
  folderId,
  filename,
  onClose,
  onShareCreated,
}) => {
  const [password, setPassword] = useState('')
  const [expiresInDays, setExpiresInDays] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [shareLink, setShareLink] = useState<ShareLinkMetadata | null>(null)

  const handleCreateShare = async () => {
    try {
      setLoading(true)
      const data = {
        file_id: fileId || null,
        folder_id: folderId || null,
        password: password || null,
        expires_in_days: expiresInDays || null,
      }

      const createdLink = await shareService.createShareLink(data)
      setShareLink(createdLink)
      
      if (onShareCreated) {
        onShareCreated(createdLink)
      }

      toast.success('Lien de partage créé avec succès!')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erreur lors de la création du lien')
    } finally {
      setLoading(false)
    }
  }

  const handleCopyLink = () => {
    if (shareLink) {
      const fullUrl = shareService.getFullShareUrl(shareLink.token)
      navigator.clipboard.writeText(fullUrl)
      toast.success('Lien copié dans le presse-papiers!')
    }
  }

  const handleCopyToken = () => {
    if (shareLink) {
      navigator.clipboard.writeText(shareLink.token)
      toast.success('Token copié dans le presse-papiers!')
    }
  }

  return (
    <div className="share-modal-overlay" onClick={onClose}>
      <div className="share-modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="share-modal-header">
          <h2>Partager "{filename}"</h2>
          <button onClick={onClose} className="share-modal-close" aria-label="Fermer">
            ✕
          </button>
        </div>

        <div className="share-modal-content">
          {!shareLink ? (
            <div className="share-form">
              <div className="form-group">
                <label htmlFor="password">Mot de passe (optionnel)</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Laissez vide pour un accès libre"
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label htmlFor="expires">Expiration (optionnel)</label>
                <select
                  id="expires"
                  value={expiresInDays || ''}
                  onChange={(e) => setExpiresInDays(e.target.value ? parseInt(e.target.value) : null)}
                  className="form-select"
                >
                  <option value="">Aucune expiration</option>
                  <option value="1">1 jour</option>
                  <option value="7">7 jours</option>
                  <option value="30">30 jours</option>
                  <option value="90">90 jours</option>
                </select>
              </div>

              <div className="share-modal-actions">
                <button
                  onClick={handleCreateShare}
                  disabled={loading}
                  className="btn-primary"
                >
                  {loading ? 'Création...' : 'Créer le lien'}
                </button>
                <button onClick={onClose} className="btn-secondary">
                  Annuler
                </button>
              </div>
            </div>
          ) : (
            <div className="share-result">
              <div className="share-success-icon">✅</div>
              <p className="share-success-message">Lien de partage créé avec succès!</p>

              <div className="share-link-display">
                <label>Lien de partage:</label>
                <div className="share-link-input-group">
                  <input
                    type="text"
                    value={shareService.getFullShareUrl(shareLink.token)}
                    readOnly
                    className="share-link-input"
                  />
                  <button onClick={handleCopyLink} className="btn-copy" title="Copier le lien">
                    📋
                  </button>
                </div>
              </div>

              <div className="share-link-info">
                <div className="info-item">
                  <span className="info-label">Token:</span>
                  <span className="info-value">{shareLink.token}</span>
                  <button onClick={handleCopyToken} className="btn-copy-small" title="Copier le token">
                    📋
                  </button>
                </div>
                {shareLink.expires_at && (
                  <div className="info-item">
                    <span className="info-label">Expire le:</span>
                    <span className="info-value">
                      {new Date(shareLink.expires_at).toLocaleDateString('fr-FR')}
                    </span>
                  </div>
                )}
                {shareLink.has_password && (
                  <div className="info-item">
                    <span className="info-label">Protection:</span>
                    <span className="info-value">🔒 Mot de passe requis</span>
                  </div>
                )}
                <div className="info-item">
                  <span className="info-label">Accès:</span>
                  <span className="info-value">{shareLink.access_count} fois</span>
                </div>
              </div>

              <div className="share-modal-actions">
                <button onClick={onClose} className="btn-primary">
                  Fermer
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ShareModal

