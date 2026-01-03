import React, { useState, useEffect } from 'react'
import { toast } from 'react-toastify'
import { folderService, FolderMetadata } from '../services/folderService'
import { useQuery } from '@tanstack/react-query'
import './MoveModal.css'

interface MoveModalProps {
  currentFolderId: number | null
  type: 'file' | 'folder'
  onConfirm: (targetFolderId: number | null) => Promise<void>
  onClose: () => void
}

const MoveModal: React.FC<MoveModalProps> = ({ currentFolderId, type, onConfirm, onClose }) => {
  const [selectedFolderId, setSelectedFolderId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [folderPath, setFolderPath] = useState<number[]>([]) // Stack for navigation

  // Get folders for current level
  const { data: foldersData } = useQuery({
    queryKey: ['folders', folderPath.length > 0 ? folderPath[folderPath.length - 1] : null],
    queryFn: () => folderService.listFolders(folderPath.length > 0 ? folderPath[folderPath.length - 1] : null),
  })

  // Get breadcrumbs for current level
  const { data: breadcrumbsData } = useQuery({
    queryKey: ['folder', folderPath.length > 0 ? folderPath[folderPath.length - 1] : null],
    queryFn: () => {
      if (folderPath.length > 0) {
        return folderService.getFolder(folderPath[folderPath.length - 1]!)
      }
      return null
    },
    enabled: folderPath.length > 0,
  })

  const handleFolderClick = (folderId: number) => {
    setFolderPath([...folderPath, folderId])
    setSelectedFolderId(folderId)
  }

  const handleBreadcrumbClick = (index: number) => {
    setFolderPath(folderPath.slice(0, index + 1))
    if (index === -1) {
      setSelectedFolderId(null)
    } else {
      setSelectedFolderId(folderPath[index])
    }
  }

  const handleSelectRoot = () => {
    setSelectedFolderId(null)
    setFolderPath([])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (selectedFolderId === currentFolderId) {
      toast.info('Le fichier/dossier est déjà dans ce dossier')
      onClose()
      return
    }

    setLoading(true)
    try {
      await onConfirm(selectedFolderId)
      toast.success(`${type === 'file' ? 'Fichier' : 'Dossier'} déplacé avec succès`)
      onClose()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || `Erreur lors du déplacement du ${type}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="move-modal-overlay" onClick={onClose}>
      <div className="move-modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="move-modal-header">
          <h3>Déplacer {type === 'file' ? 'le fichier' : 'le dossier'}</h3>
          <button onClick={onClose} className="move-modal-close">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="move-modal-content">
          <div className="move-modal-breadcrumbs">
            <button
              type="button"
              onClick={handleSelectRoot}
              className={`breadcrumb-item ${selectedFolderId === null ? 'active' : ''}`}
            >
              📁 Racine
            </button>
            {folderPath.map((folderId, index) => (
              <React.Fragment key={folderId}>
                <span className="breadcrumb-separator">/</span>
                <button
                  type="button"
                  onClick={() => handleBreadcrumbClick(index)}
                  className={`breadcrumb-item ${index === folderPath.length - 1 ? 'active' : ''}`}
                >
                  {breadcrumbsData?.name || '...'}
                </button>
              </React.Fragment>
            ))}
          </div>

          <div className="move-modal-folders">
            {foldersData && foldersData.folders.length > 0 ? (
              <div className="folders-list">
                {foldersData.folders.map((folder) => (
                  <div
                    key={folder.id}
                    className={`folder-item ${selectedFolderId === folder.id ? 'selected' : ''}`}
                    onClick={() => handleFolderClick(folder.id)}
                  >
                    <span className="folder-icon">📁</span>
                    <span className="folder-name">{folder.name}</span>
                    <span className="folder-count">
                      {folder.files_count} fichier{folder.files_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-folders">
                <p>Aucun dossier disponible</p>
              </div>
            )}
          </div>

          <div className="move-modal-actions">
            <button type="button" onClick={onClose} className="cancel-btn" disabled={loading}>
              Annuler
            </button>
            <button type="submit" className="confirm-btn" disabled={loading}>
              {loading ? 'Déplacement...' : 'Déplacer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default MoveModal

