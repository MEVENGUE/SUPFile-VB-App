import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import axios from 'axios'
import { getAuthHeaders } from '../services/authService'
import './FileHistory.css'

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1'

interface HistoryItem {
  id: number
  file_id?: number
  folder_id?: number
  user_id: number
  action: string
  old_value?: string
  new_value?: string
  description?: string
  created_at: string
}

interface FileHistoryProps {
  fileId?: number
  folderId?: number
  onClose: () => void
}

const FileHistory = ({ fileId, folderId, onClose }: FileHistoryProps) => {
  const { data: history, isLoading } = useQuery({
    queryKey: ['history', fileId, folderId],
    queryFn: async () => {
      const endpoint = fileId 
        ? `${API_URL}/history/files/${fileId}/history`
        : `${API_URL}/history/folders/${folderId}/history`
      
      const response = await axios.get(endpoint, {
        headers: getAuthHeaders()
      })
      return response.data as HistoryItem[]
    },
    enabled: !!(fileId || folderId)
  })

  const getActionLabel = (action: string) => {
    const labels: Record<string, string> = {
      created: 'Créé',
      updated: 'Modifié',
      renamed: 'Renommé',
      moved: 'Déplacé',
      deleted: 'Supprimé',
      restored: 'Restauré',
      shared: 'Partagé',
      unshared: 'Partage retiré',
      downloaded: 'Téléchargé',
      viewed: 'Consulté'
    }
    return labels[action] || action
  }

  const getActionIcon = (action: string) => {
    const icons: Record<string, string> = {
      created: '➕',
      updated: '✏️',
      renamed: '🏷️',
      moved: '📦',
      deleted: '🗑️',
      restored: '♻️',
      shared: '🔗',
      unshared: '🔒',
      downloaded: '⬇️',
      viewed: '👁️'
    }
    return icons[action] || '📝'
  }

  return (
    <div className="history-modal-overlay animate-fade-in" onClick={onClose}>
      <div className="history-modal-container animate-scale-in" onClick={(e) => e.stopPropagation()}>
        <div className="history-modal-header">
          <h3>Historique {fileId ? 'du fichier' : 'du dossier'}</h3>
          <button 
            onClick={onClose} 
            className="history-modal-close"
            aria-label="Fermer l'historique"
          >
            <span aria-hidden="true">✕</span>
          </button>
        </div>
        
        <div className="history-modal-content">
          {isLoading ? (
            <div className="history-loading">Chargement...</div>
          ) : history && history.length > 0 ? (
            <div className="history-list">
              {history.map((item) => (
                <div key={item.id} className="history-item">
                  <div className="history-item-icon">
                    {getActionIcon(item.action)}
                  </div>
                  <div className="history-item-content">
                    <div className="history-item-action">
                      {getActionLabel(item.action)}
                    </div>
                    {item.description && (
                      <div className="history-item-description">
                        {item.description}
                      </div>
                    )}
                    {item.old_value && item.new_value && (
                      <div className="history-item-changes">
                        <span className="history-old">{item.old_value}</span>
                        <span className="history-arrow">→</span>
                        <span className="history-new">{item.new_value}</span>
                      </div>
                    )}
                    <div className="history-item-date">
                      {format(new Date(item.created_at), 'dd MMM yyyy à HH:mm', { locale: fr })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="history-empty">
              <p>Aucun historique disponible</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default FileHistory

