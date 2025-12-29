import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { fileService, FileMetadata } from '../services/fileService'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-toastify'
import { useDropzone } from 'react-dropzone'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import './Dashboard.css'

const Dashboard = () => {
  const { user, logout } = useAuth()
  const queryClient = useQueryClient()
  const [uploading, setUploading] = useState(false)

  const { data: filesData, isLoading } = useQuery({
    queryKey: ['files'],
    queryFn: () => fileService.listFiles(),
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
        await fileService.uploadFile(file)
      }
      queryClient.invalidateQueries({ queryKey: ['files'] })
      toast.success('Fichier(s) téléversé(s) avec succès!')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erreur lors du téléversement')
    } finally {
      setUploading(false)
    }
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

  const handleDelete = (fileId: number) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce fichier?')) {
      deleteMutation.mutate(fileId)
    }
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>SUPFile</h1>
          <div className="header-user">
            <span>Bonjour, {user?.username}</span>
            <button onClick={logout} className="logout-button">
              Déconnexion
            </button>
          </div>
        </div>
      </header>

      <main className="dashboard-main">
        <div
          {...getRootProps()}
          className={`upload-zone ${isDragActive ? 'active' : ''} ${uploading ? 'uploading' : ''}`}
        >
          <input {...getInputProps()} />
          {uploading ? (
            <p>Téléversement en cours...</p>
          ) : isDragActive ? (
            <p>Déposez les fichiers ici...</p>
          ) : (
            <div>
              <p className="upload-icon">📤</p>
              <p>Glissez-déposez des fichiers ici ou cliquez pour sélectionner</p>
              <p className="upload-hint">Taille max: 100MB</p>
            </div>
          )}
        </div>

        <div className="files-section">
          <h2>Mes fichiers ({filesData?.total || 0})</h2>

          {isLoading ? (
            <div className="loading">Chargement...</div>
          ) : filesData && filesData.files.length > 0 ? (
            <div className="files-grid">
              {filesData.files.map((file) => (
                <div key={file.id} className="file-card">
                  <div className="file-icon">
                    {file.content_type?.startsWith('image/') ? '🖼️' : '📄'}
                  </div>
                  <div className="file-info">
                    <h3 className="file-name" title={file.original_filename}>
                      {file.original_filename}
                    </h3>
                    <p className="file-meta">
                      {formatFileSize(file.file_size)} •{' '}
                      {format(new Date(file.created_at), 'dd MMM yyyy', { locale: fr })}
                    </p>
                    {file.upload_region && (
                      <p className="file-region">📍 {file.upload_region}</p>
                    )}
                  </div>
                  <div className="file-actions">
                    <button
                      onClick={() => handleDownload(file)}
                      className="action-button download"
                    >
                      ⬇️ Télécharger
                    </button>
                    <button
                      onClick={() => handleDelete(file.id)}
                      className="action-button delete"
                    >
                      🗑️ Supprimer
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>📁 Aucun fichier pour le moment</p>
              <p>Téléversez votre premier fichier ci-dessus</p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default Dashboard

