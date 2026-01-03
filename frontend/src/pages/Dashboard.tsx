import { useState } from 'react'
import { fileService, FileMetadata } from '../services/fileService'
import { folderService } from '../services/folderService'
import { dashboardService } from '../services/dashboardService'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-toastify'
import { useDropzone } from 'react-dropzone'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { getFileIcon, getFileTypeLabel } from '../utils/fileIcons'
import Breadcrumbs from '../components/Breadcrumbs'
import FileViewer from '../components/FileViewer'
import ShareModal from '../components/ShareModal'
import SearchBar from '../components/SearchBar'
import RenameModal from '../components/RenameModal'
import MoveModal from '../components/MoveModal'
import Sidebar from '../components/Sidebar'
import Pagination from '../components/Pagination'
import { FolderMetadata } from '../services/folderService'
import './Dashboard.css'

const Dashboard = () => {
  const queryClient = useQueryClient()
  const [uploading, setUploading] = useState(false)
  const [currentFolderId, setCurrentFolderId] = useState<number | null>(null)
  const [showCreateFolder, setShowCreateFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [previewFile, setPreviewFile] = useState<FileMetadata | null>(null)
  const [shareTarget, setShareTarget] = useState<{ fileId?: number; folderId?: number; name: string } | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchContentType, setSearchContentType] = useState<string | undefined>(undefined)
  const [showStats, setShowStats] = useState(true)
  const [renameTarget, setRenameTarget] = useState<{ id: number; name: string; type: 'file' | 'folder' } | null>(null)
  const [moveTarget, setMoveTarget] = useState<{ id: number; currentFolderId: number | null; type: 'file' | 'folder' } | null>(null)
  const [expandedFolders, setExpandedFolders] = useState<Set<number>>(new Set())
  const [filesPage, setFilesPage] = useState(1)
  const [foldersPage, setFoldersPage] = useState(1)
  const itemsPerPage = 20

  // Search or list files with pagination
  const { data: filesData, isLoading: filesLoading } = useQuery({
    queryKey: ['files', currentFolderId, searchQuery, searchContentType, filesPage],
    queryFn: () => {
      if (searchQuery.trim()) {
        return fileService.searchFiles(searchQuery, searchContentType, currentFolderId, (filesPage - 1) * itemsPerPage, itemsPerPage)
      }
      return fileService.listFiles(currentFolderId, (filesPage - 1) * itemsPerPage, itemsPerPage)
    },
    enabled: true,
  })


  const { data: foldersData, isLoading: foldersLoading } = useQuery({
    queryKey: ['folders', currentFolderId, foldersPage],
    queryFn: () => folderService.listFolders(currentFolderId, (foldersPage - 1) * itemsPerPage, itemsPerPage),
  })

  // Get all folders for tree structure
  const { data: allFoldersData } = useQuery({
    queryKey: ['all-folders'],
    queryFn: () => folderService.listFolders(null, 0, 1000),
  })

  // Get root files count
  const { data: rootFilesData } = useQuery({
    queryKey: ['root-files'],
    queryFn: () => fileService.listFiles(null, 0, 1000),
  })

  // Get dashboard statistics for storage info
  const { data: statsData } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardService.getStats(),
    refetchInterval: 60000, // Refresh every minute
  })

  // Get current folder info for display
  const { data: currentFolderData } = useQuery({
    queryKey: ['folder', currentFolderId],
    queryFn: () => folderService.getFolder(currentFolderId!),
    enabled: !!currentFolderId,
  })

  const deleteMutation = useMutation({
    mutationFn: fileService.deleteFile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files'] })
      toast.success('Fichier supprimé avec succès')
    },
    onError: () => {
      toast.error('Erreur lors de la suppression')
    },
  })

  const onDrop = async (acceptedFiles: File[]) => {
    setUploading(true)
    try {
      for (const file of acceptedFiles) {
        await fileService.uploadFile(file, currentFolderId)
      }
      queryClient.invalidateQueries({ queryKey: ['files'] })
      queryClient.invalidateQueries({ queryKey: ['root-files'] })
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      toast.success('Fichier(s) téléversé(s) avec succès!')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erreur lors du téléversement')
    } finally {
      setUploading(false)
    }
  }

  const createFolderMutation = useMutation({
    mutationFn: (name: string) => folderService.createFolder({ name, parent_id: currentFolderId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      queryClient.invalidateQueries({ queryKey: ['all-folders'] })
      setShowCreateFolder(false)
      setNewFolderName('')
      toast.success('Dossier créé avec succès')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de la création du dossier')
    },
  })

  const deleteFolderMutation = useMutation({
    mutationFn: (folderId: number) => folderService.deleteFolder(folderId, false),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      queryClient.invalidateQueries({ queryKey: ['all-folders'] })
      queryClient.invalidateQueries({ queryKey: ['files'] })
      toast.success('Dossier supprimé avec succès')
    },
    onError: () => {
      toast.error('Erreur lors de la suppression du dossier')
    },
  })

  const renameFileMutation = useMutation({
    mutationFn: ({ fileId, newName }: { fileId: number; newName: string }) =>
      fileService.renameFile(fileId, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files'] })
    },
  })

  const moveFileMutation = useMutation({
    mutationFn: ({ fileId, folderId }: { fileId: number; folderId?: number | null }) =>
      fileService.moveFile(fileId, folderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files'] })
    },
  })

  const renameFolderMutation = useMutation({
    mutationFn: ({ folderId, newName }: { folderId: number; newName: string }) =>
      folderService.renameFolder(folderId, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      queryClient.invalidateQueries({ queryKey: ['all-folders'] })
    },
  })

  const moveFolderMutation = useMutation({
    mutationFn: ({ folderId, parentId }: { folderId: number; parentId?: number | null }) =>
      folderService.moveFolder(folderId, parentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      queryClient.invalidateQueries({ queryKey: ['all-folders'] })
    },
  })

  const handleCreateFolder = () => {
    if (newFolderName.trim()) {
      createFolderMutation.mutate(newFolderName.trim())
    }
  }

  const handleDeleteFolder = (folderId: number) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce dossier?')) {
      deleteFolderMutation.mutate(folderId)
    }
  }

  const handleFolderClick = (folderId: number | null) => {
    setCurrentFolderId(folderId)
    setFilesPage(1)
    setFoldersPage(1)
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled: uploading,
  })

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const handleDownload = async (file: FileMetadata) => {
    try {
      await fileService.downloadFile(file.id, file.original_filename)
      toast.success('Téléchargement démarré')
    } catch (error: any) {
      toast.error('Erreur lors du téléchargement')
    }
  }

  const handlePreview = (file: FileMetadata) => {
    setPreviewFile(file)
  }

  const handleDelete = (fileId: number) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce fichier?')) {
      deleteMutation.mutate(fileId)
    }
  }

  const handleRenameFile = (file: FileMetadata) => {
    setRenameTarget({ id: file.id, name: file.original_filename, type: 'file' })
  }

  const handleRenameFolder = (folder: any) => {
    setRenameTarget({ id: folder.id, name: folder.name, type: 'folder' })
  }

  const handleMoveFile = (file: FileMetadata) => {
    setMoveTarget({ id: file.id, currentFolderId: file.folder_id || null, type: 'file' })
  }

  const handleMoveFolder = (folder: any) => {
    setMoveTarget({ id: folder.id, currentFolderId: folder.parent_id, type: 'folder' })
  }

  const handleDownloadFolder = async (folder: any) => {
    try {
      await folderService.downloadFolder(folder.id, folder.name)
      toast.success('Téléchargement du dossier démarré')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erreur lors du téléchargement du dossier')
    }
  }

  const handleRenameConfirm = async (newName: string) => {
    if (!renameTarget) return
    if (renameTarget.type === 'file') {
      await renameFileMutation.mutateAsync({ fileId: renameTarget.id, newName })
    } else {
      await renameFolderMutation.mutateAsync({ folderId: renameTarget.id, newName })
    }
  }

  const handleMoveConfirm = async (targetFolderId: number | null) => {
    if (!moveTarget) return
    if (moveTarget.type === 'file') {
      await moveFileMutation.mutateAsync({ fileId: moveTarget.id, folderId: targetFolderId })
    } else {
      await moveFolderMutation.mutateAsync({ folderId: moveTarget.id, parentId: targetFolderId })
    }
  }

  const toggleFolder = (folderId: number) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev)
      if (newSet.has(folderId)) {
        newSet.delete(folderId)
      } else {
        newSet.add(folderId)
      }
      return newSet
    })
  }

  const renderFolderTree = (folders: FolderMetadata[], parentId: number | null = null, level = 0): JSX.Element[] => {
    const children = folders.filter(f => f.parent_id === parentId)
    return children.flatMap(folder => [
      <div key={folder.id} className="folder-tree-item" style={{ paddingLeft: `${level * 24}px` }}>
        <div className="folder-tree-row" onClick={() => toggleFolder(folder.id)}>
          <div className="folder-tree-icon">
            {expandedFolders.has(folder.id) ? '📂' : '📁'}
          </div>
          <div className="folder-tree-info">
            <span className="folder-tree-name">{folder.name}</span>
            <span className="folder-tree-meta">
              {folder.files_count} fichier{folder.files_count !== 1 ? 's' : ''} • {folder.children_count} sous-dossier{folder.children_count !== 1 ? 's' : ''}
            </span>
          </div>
          <button
            className="folder-tree-action"
            onClick={(e) => {
              e.stopPropagation()
              handleFolderClick(folder.id)
            }}
          >
            Ouvrir
          </button>
        </div>
        {expandedFolders.has(folder.id) && renderFolderTree(folders, folder.id, level + 1)}
      </div>
    ])
  }

  return (
    <div className="dashboard">
      <Sidebar />
      <main className="dashboard-main">
        {showStats && (
          <div className="dashboard-stats">
            <div className="stats-section">
              <h3>Statistiques</h3>
              <div className="stats-card">
                <div className="stat-card">
                  <div className="stat-icon">📁</div>
                  <div className="stat-info">
                    <div className="stat-value">{allFoldersData?.folders.length || 0}</div>
                    <div className="stat-label">Dossiers</div>
                  </div>
                </div>
                <div className="stat-card">
                  <div className="stat-icon">📄</div>
                  <div className="stat-info">
                    <div className="stat-value">{rootFilesData?.files.length || 0}</div>
                    <div className="stat-label">Fichiers à la racine</div>
                  </div>
                </div>
                <div className="stat-card">
                  <div className="stat-icon">📊</div>
                  <div className="stat-info">
                    <div className="stat-value">{filesData?.total || 0}</div>
                    <div className="stat-label">Fichiers totaux</div>
                  </div>
                </div>
              </div>
            </div>

            {statsData && (
              <div className="storage-stats-section">
                <h3>Espace de stockage</h3>
                <div className="storage-stats-grid">
                  <div className="storage-stat-card">
                    <div className="storage-stat-icon">💾</div>
                    <div className="storage-stat-info">
                      <div className="storage-stat-value">
                        {statsData.total_size_mb < 1024 
                          ? `${statsData.total_size_mb.toFixed(2)} MB`
                          : `${(statsData.total_size_mb / 1024).toFixed(2)} GB`}
                      </div>
                      <div className="storage-stat-label">Espace occupé</div>
                    </div>
                  </div>
                  <div className="storage-stat-card">
                    <div className="storage-stat-icon">📦</div>
                    <div className="storage-stat-info">
                      <div className="storage-stat-value">
                        {(() => {
                          const quotaGB = 100
                          const usedGB = statsData.total_size_mb / 1024
                          const availableGB = quotaGB - usedGB
                          return availableGB < 0 ? '0 GB' : availableGB < 1 
                            ? `${(availableGB * 1024).toFixed(2)} MB`
                            : `${availableGB.toFixed(2)} GB`
                        })()}
                      </div>
                      <div className="storage-stat-label">Espace disponible</div>
                    </div>
                  </div>
                  <div className="storage-stat-card">
                    <div className="storage-stat-icon">📈</div>
                    <div className="storage-stat-info">
                      <div className="storage-stat-value">{statsData.storage_usage_percentage.toFixed(1)}%</div>
                      <div className="storage-stat-label">Quota utilisé</div>
                      <div className="storage-progress">
                        <div 
                          className="storage-progress-bar" 
                          style={{ 
                            width: `${Math.min(statsData.storage_usage_percentage, 100)}%`,
                            backgroundColor: statsData.storage_usage_percentage > 90 ? '#f44336' : 
                                           statsData.storage_usage_percentage > 75 ? '#ff9800' : '#1a73e8'
                          }}
                        ></div>
                      </div>
                    </div>
                  </div>
                  <div className="storage-stat-card">
                    <div className="storage-stat-icon">📋</div>
                    <div className="storage-stat-info">
                      <div className="storage-stat-value">100 GB</div>
                      <div className="storage-stat-label">Quota total</div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="folder-structure-section">
              <h3>Structure des dossiers</h3>
              {allFoldersData && allFoldersData.folders.length > 0 ? (
                <div className="folder-tree">
                  {renderFolderTree(allFoldersData.folders)}
                </div>
              ) : (
                <div className="empty-state">Aucun dossier</div>
              )}
            </div>

            <button className="toggle-stats-btn" onClick={() => setShowStats(false)}>
              Masquer les statistiques
            </button>
          </div>
        )}

        {!showStats && (
          <button className="toggle-stats-btn" onClick={() => setShowStats(true)}>
            Afficher les statistiques
          </button>
        )}

        <Breadcrumbs currentFolderId={currentFolderId} onFolderClick={handleFolderClick} />

        <SearchBar
          onSearch={(query, contentType) => {
            setSearchQuery(query)
            setSearchContentType(contentType)
            setFilesPage(1)
            setFoldersPage(1)
          }}
          placeholder={searchQuery ? `Recherche: ${searchQuery}` : "Rechercher des fichiers..."}
        />

        <div className="current-location">
          <span className="location-label">
            📍 Emplacement actuel:
          </span>
          <span className="location-name">
            {currentFolderId ? (
              currentFolderData?.name || foldersData?.folders.find(f => f.id === currentFolderId)?.name || 'Dossier'
            ) : (
              'Racine'
            )}
          </span>
        </div>

        <div
          {...getRootProps()}
          className={`upload-zone ${isDragActive ? 'active' : ''} ${uploading ? 'uploading' : ''}`}
        >
          <input {...getInputProps()} />
          {uploading ? (
            <div>
              <img src="/Espace de Stockage.jpg" alt="Upload" className="upload-icon-image" />
              <p>Téléversement en cours...</p>
              <p className="upload-location-hint">
                Dans: {currentFolderId ? (
                  currentFolderData?.name || foldersData?.folders.find(f => f.id === currentFolderId)?.name || 'Dossier'
                ) : (
                  'Racine'
                )}
              </p>
            </div>
          ) : isDragActive ? (
            <div>
              <img src="/Espace de Stockage.jpg" alt="Upload" className="upload-icon-image" />
              <p>Déposez les fichiers ici...</p>
              <p className="upload-location-hint">
                Les fichiers seront placés dans: {currentFolderId ? (
                  currentFolderData?.name || foldersData?.folders.find(f => f.id === currentFolderId)?.name || 'ce dossier'
                ) : (
                  'la racine'
                )}
              </p>
            </div>
          ) : (
            <div>
              <img src="/Espace de Stockage.jpg" alt="Upload" className="upload-icon-image" />
              <p>Glissez-déposez des fichiers ici ou cliquez pour sélectionner</p>
              <p className="upload-hint">Taille max: 100MB</p>
              <p className="upload-location-hint">
                📁 Destination: {currentFolderId ? (
                  currentFolderData?.name || foldersData?.folders.find(f => f.id === currentFolderId)?.name || 'Dossier courant'
                ) : (
                  'Racine'
                )}
              </p>
            </div>
          )}
        </div>

        <div className="files-section">
          <div className="files-header">
            <h2>Mes fichiers</h2>
            <div className="files-header-actions">
              <button
                onClick={() => setShowCreateFolder(!showCreateFolder)}
                className="create-folder-btn smooth-transition hover-lift"
                title="Créer un dossier"
                aria-label="Créer un nouveau dossier"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    setShowCreateFolder(!showCreateFolder)
                  }
                }}
              >
                📁 Nouveau dossier
              </button>
              <span className="files-count">
                {filesData?.total || 0} fichier{filesData?.total !== 1 ? 's' : ''}
              </span>
            </div>
          </div>

          {showCreateFolder && (
            <div className="create-folder-form">
              <input
                type="text"
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                placeholder="Nom du dossier"
                className="folder-name-input"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleCreateFolder()
                  }
                }}
                autoFocus
              />
              <div className="folder-form-actions">
                <button onClick={handleCreateFolder} className="confirm-btn" disabled={!newFolderName.trim()}>
                  Créer
                </button>
                <button onClick={() => { setShowCreateFolder(false); setNewFolderName('') }} className="cancel-btn">
                  Annuler
                </button>
              </div>
            </div>
          )}

          {(foldersLoading || filesLoading) ? (
            <div className="loading">
              <div className="loading-spinner"></div>
              <p>Chargement...</p>
            </div>
          ) : (
            <>
              {/* Dossiers */}
              {foldersData && foldersData.folders.length > 0 && (
                <>
                <div className="folders-grid">
                  {foldersData.folders.map((folder, index) => (
                    <div 
                      key={folder.id} 
                      className="folder-card animate-fade-in smooth-transition hover-lift" 
                      onClick={() => handleFolderClick(folder.id)}
                      role="button"
                      tabIndex={0}
                      aria-label={`Ouvrir le dossier ${folder.name}`}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          handleFolderClick(folder.id)
                        }
                      }}
                      style={{ animationDelay: `${index * 0.05}s` }}
                    >
                      <div className="folder-preview">
                        <div className="folder-icon">📁</div>
                        <div className="folder-overlay">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDownloadFolder(folder)
                            }}
                            className="folder-action-btn download-btn"
                            title="Télécharger (ZIP)"
                          >
                            ⬇️
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleRenameFolder(folder)
                            }}
                            className="folder-action-btn rename-btn"
                            title="Renommer"
                          >
                            ✏️
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleMoveFolder(folder)
                            }}
                            className="folder-action-btn move-btn"
                            title="Déplacer"
                          >
                            📦
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setShareTarget({ folderId: folder.id, name: folder.name })
                            }}
                            className="folder-action-btn share-btn"
                            title="Partager"
                          >
                            🔗
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDeleteFolder(folder.id)
                            }}
                            className="folder-action-btn delete-btn"
                            title="Supprimer"
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                      <div className="folder-info">
                        <h3 className="folder-name" title={folder.name}>
                          {folder.name}
                        </h3>
                        <div className="folder-details">
                          <span>{folder.children_count} dossier{folder.children_count !== 1 ? 's' : ''}</span>
                          <span>{folder.files_count} fichier{folder.files_count !== 1 ? 's' : ''}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                {foldersData.total > itemsPerPage && (
                  <Pagination
                    currentPage={foldersPage}
                    totalPages={Math.ceil(foldersData.total / itemsPerPage)}
                    onPageChange={(page) => {
                      setFoldersPage(page)
                      window.scrollTo({ top: 0, behavior: 'smooth' })
                    }}
                    itemsPerPage={itemsPerPage}
                    totalItems={foldersData.total}
                  />
                )}
                </>
              )}

              {/* Fichiers */}
              {filesData && filesData.files.length > 0 && (
                <>
                <div className="files-grid">
                  {filesData.files.map((file) => (
                    <div key={file.id} className="file-card">
                      <div className="file-preview">
                        <img 
                          src={getFileIcon(file.original_filename, file.content_type)} 
                          alt={getFileTypeLabel(file.original_filename, file.content_type)}
                          className="file-icon-image"
                          loading="lazy"
                          onError={(e) => {
                            e.currentTarget.src = '/Fichier.jpg'
                          }}
                        />
                        <div className="file-overlay">
                          <button
                            onClick={() => handlePreview(file)}
                            className="file-action-btn preview-btn"
                            title="Prévisualiser"
                          >
                            👁️
                          </button>
                          <button
                            onClick={() => handleDownload(file)}
                            className="file-action-btn download-btn"
                            title="Télécharger"
                          >
                            ⬇️
                          </button>
                          <button
                            onClick={() => handleRenameFile(file)}
                            className="file-action-btn rename-btn"
                            title="Renommer"
                          >
                            ✏️
                          </button>
                          <button
                            onClick={() => handleMoveFile(file)}
                            className="file-action-btn move-btn"
                            title="Déplacer"
                          >
                            📦
                          </button>
                          <button
                            onClick={() => setShareTarget({ fileId: file.id, name: file.original_filename })}
                            className="file-action-btn share-btn"
                            title="Partager"
                          >
                            🔗
                          </button>
                          <button
                            onClick={() => handleDelete(file.id)}
                            className="file-action-btn delete-btn"
                            title="Supprimer"
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                      <div className="file-info">
                        <h3 className="file-name" title={file.original_filename}>
                          {file.original_filename}
                        </h3>
                        <div className="file-details">
                          <span className="file-size">{formatFileSize(file.file_size)}</span>
                          <span className="file-date">
                            {format(new Date(file.created_at), 'dd MMM yyyy', { locale: fr })}
                          </span>
                        </div>
                        {file.upload_region && (
                          <span className="file-region">📍 {file.upload_region}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                {filesData.total > itemsPerPage && (
                  <Pagination
                    currentPage={filesPage}
                    totalPages={Math.ceil(filesData.total / itemsPerPage)}
                    onPageChange={(page) => {
                      setFilesPage(page)
                      window.scrollTo({ top: 0, behavior: 'smooth' })
                    }}
                    itemsPerPage={itemsPerPage}
                    totalItems={filesData.total}
                  />
                )}
                </>
              )}

              {/* Fichiers */}
              {filesData && filesData.files.length > 0 && (
                <>
                <div className="files-grid">
                  {filesData.files.map((file) => (
                    <div key={file.id} className="file-card">
                      <div className="file-preview">
                        <img 
                          src={getFileIcon(file.original_filename, file.content_type)} 
                          alt={getFileTypeLabel(file.original_filename, file.content_type)}
                          className="file-icon-image"
                          onError={(e) => {
                            e.currentTarget.src = '/Fichier.jpg'
                          }}
                        />
                        <div className="file-overlay">
                          <button
                            onClick={() => handlePreview(file)}
                            className="file-action-btn preview-btn"
                            title="Prévisualiser"
                          >
                            👁️
                          </button>
                          <button
                            onClick={() => handleDownload(file)}
                            className="file-action-btn download-btn"
                            title="Télécharger"
                          >
                            ⬇️
                          </button>
                          <button
                            onClick={() => handleRenameFile(file)}
                            className="file-action-btn rename-btn"
                            title="Renommer"
                          >
                            ✏️
                          </button>
                          <button
                            onClick={() => handleMoveFile(file)}
                            className="file-action-btn move-btn"
                            title="Déplacer"
                          >
                            📦
                          </button>
                          <button
                            onClick={() => setShareTarget({ fileId: file.id, name: file.original_filename })}
                            className="file-action-btn share-btn"
                            title="Partager"
                          >
                            🔗
                          </button>
                          <button
                            onClick={() => handleDelete(file.id)}
                            className="file-action-btn delete-btn"
                            title="Supprimer"
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                      <div className="file-info">
                        <h3 className="file-name" title={file.original_filename}>
                          {file.original_filename}
                        </h3>
                        <div className="file-details">
                          <span className="file-size">{formatFileSize(file.file_size)}</span>
                          <span className="file-date">
                            {format(new Date(file.created_at), 'dd MMM yyyy', { locale: fr })}
                          </span>
                        </div>
                        {file.upload_region && (
                          <span className="file-region">📍 {file.upload_region}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                {filesData.total > itemsPerPage && (
                  <Pagination
                    currentPage={filesPage}
                    totalPages={Math.ceil(filesData.total / itemsPerPage)}
                    onPageChange={(page) => {
                      setFilesPage(page)
                      window.scrollTo({ top: 0, behavior: 'smooth' })
                    }}
                    itemsPerPage={itemsPerPage}
                    totalItems={filesData.total}
                  />
                )}
                </>
              )}

              {/* État vide */}
              {(!foldersData || foldersData.folders.length === 0) && 
               (!filesData || filesData.files.length === 0) && (
                <div className="empty-state">
                  <div className="empty-icon">📁</div>
                  <h3>Aucun fichier ni dossier</h3>
                  <p>Téléversez votre premier fichier ou créez un dossier pour commencer</p>
                </div>
              )}
            </>
          )}

        </div>
      </main>

      {previewFile && (
        <FileViewer
          fileId={previewFile.id}
          filename={previewFile.original_filename}
          contentType={previewFile.content_type}
          onClose={() => setPreviewFile(null)}
        />
      )}

      {shareTarget && (
        <ShareModal
          fileId={shareTarget.fileId}
          folderId={shareTarget.folderId}
          filename={shareTarget.name}
          onClose={() => setShareTarget(null)}
        />
      )}

      {renameTarget && (
        <RenameModal
          type={renameTarget.type}
          currentName={renameTarget.name}
          onConfirm={handleRenameConfirm}
          onClose={() => setRenameTarget(null)}
        />
      )}

      {moveTarget && (
        <MoveModal
          type={moveTarget.type}
          currentFolderId={moveTarget.currentFolderId}
          onConfirm={handleMoveConfirm}
          onClose={() => setMoveTarget(null)}
        />
      )}
    </div>
  )
}

export default Dashboard

