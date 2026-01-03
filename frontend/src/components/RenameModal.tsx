import React, { useState, useEffect } from 'react'
import { toast } from 'react-toastify'
import './RenameModal.css'

interface RenameModalProps {
  currentName: string
  type: 'file' | 'folder'
  onConfirm: (newName: string) => Promise<void>
  onClose: () => void
}

const RenameModal: React.FC<RenameModalProps> = ({ currentName, type, onConfirm, onClose }) => {
  const [newName, setNewName] = useState(currentName)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setNewName(currentName)
  }, [currentName])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!newName.trim()) {
      toast.error('Le nom ne peut pas être vide')
      return
    }

    if (newName.trim() === currentName) {
      onClose()
      return
    }

    setLoading(true)
    try {
      await onConfirm(newName.trim())
      toast.success(`${type === 'file' ? 'Fichier' : 'Dossier'} renommé avec succès`)
      onClose()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || `Erreur lors du renommage du ${type}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div 
      className="rename-modal-overlay animate-fade-in" 
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="rename-modal-title"
    >
      <div 
        className="rename-modal-container animate-scale-in" 
        onClick={(e) => e.stopPropagation()}
        role="document"
      >
        <div className="rename-modal-header">
          <h3 id="rename-modal-title">Renommer {type === 'file' ? 'le fichier' : 'le dossier'}</h3>
          <button 
            onClick={onClose} 
            className="rename-modal-close"
            aria-label="Fermer la fenêtre de renommage"
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                onClose()
              }
            }}
          >
            <span aria-hidden="true">✕</span>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="rename-modal-content">
          <div className="form-group">
            <label htmlFor="rename-input">Nouveau nom</label>
            <input
              id="rename-input"
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={`Nom du ${type}`}
              className="rename-input"
              autoFocus
              disabled={loading}
              aria-required="true"
              aria-invalid={!newName.trim()}
            />
          </div>
          <div className="rename-modal-actions">
            <button 
              type="button" 
              onClick={onClose} 
              className="cancel-btn" 
              disabled={loading}
              aria-label="Annuler le renommage"
            >
              Annuler
            </button>
            <button 
              type="submit" 
              className="confirm-btn" 
              disabled={loading || !newName.trim()}
              aria-label="Confirmer le renommage"
            >
              {loading ? 'Renommage...' : 'Renommer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default RenameModal

