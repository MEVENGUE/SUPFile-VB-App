import { folderService, FolderMetadata } from '../services/folderService'
import { useEffect, useState } from 'react'
import './Breadcrumbs.css'

interface BreadcrumbsProps {
  currentFolderId: number | null
  onFolderClick: (folderId: number | null) => void
}

const Breadcrumbs = ({ currentFolderId, onFolderClick }: BreadcrumbsProps) => {
  const [breadcrumbs, setBreadcrumbs] = useState<FolderMetadata[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const loadBreadcrumbs = async () => {
      if (currentFolderId === null) {
        setBreadcrumbs([])
        return
      }

      setLoading(true)
      try {
        const crumbs = await folderService.getBreadcrumbs(currentFolderId)
        setBreadcrumbs(crumbs)
      } catch (error) {
        console.error('Error loading breadcrumbs:', error)
        setBreadcrumbs([])
      } finally {
        setLoading(false)
      }
    }

    loadBreadcrumbs()
  }, [currentFolderId])

  if (loading) {
    return <div className="breadcrumbs-loading">Chargement...</div>
  }

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <ol className="breadcrumbs-list">
        <li className="breadcrumb-item">
          <button
            onClick={() => onFolderClick(null)}
            className="breadcrumb-link"
            aria-label="Racine"
          >
            <span className="breadcrumb-icon">📁</span>
            <span>Racine</span>
          </button>
        </li>
        {breadcrumbs.map((folder) => (
          <li key={folder.id} className="breadcrumb-item">
            <span className="breadcrumb-separator">/</span>
            <button
              onClick={() => onFolderClick(folder.id)}
              className="breadcrumb-link"
              aria-label={folder.name}
            >
              {folder.name}
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}

export default Breadcrumbs

