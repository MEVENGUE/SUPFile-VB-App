import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-toastify'
import { fileService, FileMetadata } from '../services/fileService'
import { folderService, FolderMetadata } from '../services/folderService'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { getFileIcon } from '../utils/fileIcons'
import Sidebar from '../components/Sidebar'
import './TrashPage.css'

const TrashPage = () => {
  const queryClient = useQueryClient()
  const [selectedType, setSelectedType] = useState<'all' | 'files' | 'folders'>('all')

  // Fetch trash files
  const { data: trashFilesData, isLoading: filesLoading } = useQuery({
    queryKey: ['trash-files'],
    queryFn: () => fileService.listTrashFiles(),
  })

  // Fetch trash folders
  const { data: trashFoldersData, isLoading: foldersLoading } = useQuery({
    queryKey: ['trash-folders'],
    queryFn: () => folderService.listTrashFolders(),
  })

  // Restore file mutation
  const restoreFileMutation = useMutation({
    mutationFn: fileService.restoreFile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trash-files'] })
      queryClient.invalidateQueries({ queryKey: ['files'] })
      toast.success('Fichier restauré avec succès')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de la restauration')
    },
  })

  // Restore folder mutation
  const restoreFolderMutation = useMutation({
    mutationFn: folderService.restoreFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trash-folders'] })
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      toast.success('Dossier restauré avec succès')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de la restauration')
    },
  })

  // Permanent delete file mutation
  const deleteFilePermanentMutation = useMutation({
    mutationFn: fileService.deleteFilePermanent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trash-files'] })
      toast.success('Fichier supprimé définitivement')
    },
    onError: () => {
      toast.error('Erreur lors de la suppression définitive')
    },
  })

  // Permanent delete folder mutation
  const deleteFolderPermanentMutation = useMutation({
    mutationFn: (folderId: number) => folderService.deleteFolder(folderId, true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trash-folders'] })
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      toast.success('Dossier supprimé définitivement')
    },
    onError: () => {
      toast.error('Erreur lors de la suppression définitive')
    },
  })

  const handleRestoreFile = (fileId: number) => {
    restoreFileMutation.mutate(fileId)
  }

  const handleRestoreFolder = (folderId: number) => {
    restoreFolderMutation.mutate(folderId)
  }

  const handleDeletePermanent = (itemId: number, type: 'file' | 'folder') => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer définitivement cet élément ? Cette action est irréversible.')) {
      if (type === 'file') {
        deleteFilePermanentMutation.mutate(itemId)
      } else {
        deleteFolderPermanentMutation.mutate(itemId)
      }
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const files = trashFilesData?.files || []
  const folders = trashFoldersData?.folders || []

  const filteredItems = selectedType === 'all' 
    ? [...files.map(f => ({ ...f, type: 'file' as const })), ...folders.map(f => ({ ...f, type: 'folder' as const }))]
    : selectedType === 'files'
    ? files.map(f => ({ ...f, type: 'file' as const }))
    : folders.map(f => ({ ...f, type: 'folder' as const }))

  return (
    <div className="trash-page">
      <Sidebar />
      <div className="trash-content">
        <div className="trash-header">
          <div className="trash-header-left">
            <h1>🗑️ Corbeille</h1>
            <p className="trash-subtitle">Fichiers et dossiers supprimés</p>
          </div>
          <div className="trash-filters">
            <button
              className={`filter-btn ${selectedType === 'all' ? 'active' : ''}`}
              onClick={() => setSelectedType('all')}
            >
              Tout ({files.length + folders.length})
            </button>
            <button
              className={`filter-btn ${selectedType === 'files' ? 'active' : ''}`}
              onClick={() => setSelectedType('files')}
            >
              Fichiers ({files.length})
            </button>
            <button
              className={`filter-btn ${selectedType === 'folders' ? 'active' : ''}`}
              onClick={() => setSelectedType('folders')}
            >
              Dossiers ({folders.length})
            </button>
          </div>
        </div>

      {(filesLoading || foldersLoading) ? (
        <div className="loading">
          <div className="loading-spinner"></div>
          <p>Chargement de la corbeille...</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="empty-trash">
          <div className="empty-icon">🗑️</div>
          <h3>Corbeille vide</h3>
          <p>Aucun fichier ou dossier supprimé</p>
        </div>
      ) : (
        <div className="trash-items-grid">
          {filteredItems.map((item) => (
            <div key={`${item.type}-${item.id}`} className="trash-item-card">
              <div className="trash-item-preview">
                <div className="trash-item-icon">
                  {item.type === 'file' ? (
                    <img src={getFileIcon((item as FileMetadata).content_type)} alt="File" className="file-icon-image" />
                  ) : (
                    <span className="folder-icon">📁</span>
                  )}
                </div>
                <div className="trash-item-overlay">
                  <button
                    onClick={() => item.type === 'file' ? handleRestoreFile(item.id) : handleRestoreFolder(item.id)}
                    className="trash-action-btn restore-btn"
                    title="Restaurer"
                  >
                    ♻️
                  </button>
                  <button
                    onClick={() => handleDeletePermanent(item.id, item.type)}
                    className="trash-action-btn delete-permanent-btn"
                    title="Supprimer définitivement"
                  >
                    🗑️
                  </button>
                </div>
              </div>
              <div className="trash-item-info">
                <h3 className="trash-item-name" title={item.type === 'file' ? (item as FileMetadata).original_filename : (item as FolderMetadata).name}>
                  {item.type === 'file' ? (item as FileMetadata).original_filename : (item as FolderMetadata).name}
                </h3>
                <div className="trash-item-details">
                  {item.type === 'file' && (
                    <span className="trash-item-size">{formatFileSize((item as FileMetadata).file_size)}</span>
                  )}
                  {item.type === 'folder' && (
                    <span className="trash-item-count">
                      {(item as FolderMetadata).files_count || 0} fichier{((item as FolderMetadata).files_count || 0) !== 1 ? 's' : ''}
                    </span>
                  )}
                </div>
                <div className="trash-item-date">
                  Supprimé le {format(new Date((item as any).deleted_at || (item as any).created_at), 'dd MMM yyyy à HH:mm', { locale: fr })}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      </div>
    </div>
  )
}

export default TrashPage

