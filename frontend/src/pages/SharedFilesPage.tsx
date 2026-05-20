import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-toastify'
import { shareService } from '../services/shareService'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import axios from 'axios'
import { API_URL } from '../config/api'
import Sidebar from '../components/Sidebar'
import './SharedFilesPage.css'

const SharedFilesPage = () => {
  const queryClient = useQueryClient()

  const { data: shareLinksData, isLoading } = useQuery({
    queryKey: ['share-links'],
    queryFn: () => shareService.listShareLinks(),
  })

  const deleteShareLinkMutation = useMutation({
    mutationFn: async (shareId: number) => {
      const token = localStorage.getItem('token')
      await axios.delete(
        `${API_URL}/share/${shareId}`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['share-links'] })
      toast.success('Lien de partage supprimé')
    },
    onError: () => {
      toast.error('Erreur lors de la suppression')
    },
  })

  const toggleShareLinkMutation = useMutation({
    mutationFn: async ({ shareId, isActive }: { shareId: number; isActive: boolean }) => {
      const token = localStorage.getItem('token')
      await axios.patch(
        `${API_URL}/share/${shareId}/toggle`,
        { is_active: !isActive },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['share-links'] })
      toast.success('Lien de partage mis à jour')
    },
    onError: () => {
      toast.error('Erreur lors de la mise à jour')
    },
  })

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(`${window.location.origin}${text}`)
    toast.success('Lien copié dans le presse-papiers')
  }

  const shareLinks = shareLinksData?.share_links || []

  return (
    <div className="shared-files-page">
      <Sidebar />
      <div className="shared-files-content">
        <div className="shared-files-title-section">
          <img src="/Images app/Partagés.jpg" alt="Partagés" className="shared-files-icon" />
          <h2>Fichiers partagés</h2>
          <p>Gérez tous vos liens de partage</p>
        </div>

        {isLoading ? (
          <div className="loading">
            <div className="loading-spinner"></div>
            <p>Chargement...</p>
          </div>
        ) : shareLinks.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🔗</div>
            <h3>Aucun fichier partagé</h3>
            <p>Vous n'avez pas encore créé de lien de partage</p>
            <Link to="/dashboard" className="empty-action-btn">
              Aller au Dashboard
            </Link>
          </div>
        ) : (
          <div className="share-links-grid">
            {shareLinks.map(link => (
              <div key={link.id} className="share-link-card">
                <div className="share-link-header">
                  <div className="share-link-type">
                    {link.file_id ? '📄 Fichier' : '📁 Dossier'}
                  </div>
                  <div className={`share-link-status ${link.is_active ? 'active' : 'inactive'}`}>
                    {link.is_active ? 'Actif' : 'Inactif'}
                  </div>
                </div>
                <div className="share-link-info">
                  <div className="share-link-url">
                    <input
                      type="text"
                      value={`${window.location.origin}${link.share_url}`}
                      readOnly
                      className="share-url-input"
                    />
                    <button
                      className="copy-btn"
                      onClick={() => copyToClipboard(link.share_url)}
                      title="Copier le lien"
                    >
                      📋
                    </button>
                  </div>
                  <div className="share-link-stats">
                    <span>👁️ {link.access_count} accès</span>
                    {link.has_password && <span>🔒 Protégé</span>}
                    {link.expires_at && (
                      <span>
                        ⏰ Expire le {format(new Date(link.expires_at), 'dd MMM yyyy', { locale: fr })}
                      </span>
                    )}
                  </div>
                  <div className="share-link-date">
                    Créé le {format(new Date(link.created_at), 'dd MMM yyyy à HH:mm', { locale: fr })}
                  </div>
                </div>
                <div className="share-link-actions">
                  <button
                    className="toggle-btn"
                    onClick={() => toggleShareLinkMutation.mutate({ shareId: link.id, isActive: link.is_active })}
                  >
                    {link.is_active ? 'Désactiver' : 'Activer'}
                  </button>
                  <a
                    href={link.share_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="view-btn"
                  >
                    Voir
                  </a>
                  <button
                    className="delete-btn"
                    onClick={() => {
                      if (window.confirm('Êtes-vous sûr de vouloir supprimer ce lien de partage ?')) {
                        deleteShareLinkMutation.mutate(link.id)
                      }
                    }}
                  >
                    Supprimer
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default SharedFilesPage

