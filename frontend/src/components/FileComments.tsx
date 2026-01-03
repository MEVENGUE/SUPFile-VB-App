import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import axios from 'axios'
import { toast } from 'react-toastify'
import { getAuthHeaders } from '../services/authService'
import { useAuth } from '../contexts/AuthContext'
import './FileComments.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

interface Comment {
  id: number
  file_id?: number
  folder_id?: number
  user_id: number
  username?: string
  comment: string
  parent_comment_id?: number
  replies: Comment[]
  created_at: string
  updated_at: string
}

interface FileCommentsProps {
  fileId?: number
  folderId?: number
  onClose: () => void
}

const FileComments = ({ fileId, folderId, onClose }: FileCommentsProps) => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [newComment, setNewComment] = useState('')
  const [replyingTo, setReplyingTo] = useState<number | null>(null)
  const [replyText, setReplyText] = useState('')

  const endpoint = fileId 
    ? `${API_URL}/comments/files/${fileId}/comments`
    : `${API_URL}/comments/folders/${folderId}/comments`

  const { data: comments, isLoading } = useQuery({
    queryKey: ['comments', fileId, folderId],
    queryFn: async () => {
      const response = await axios.get(endpoint, {
        headers: getAuthHeaders()
      })
      return response.data as Comment[]
    },
    enabled: !!(fileId || folderId)
  })

  const createCommentMutation = useMutation({
    mutationFn: async (data: { comment: string; parent_comment_id?: number }) => {
      const response = await axios.post(endpoint, data, {
        headers: getAuthHeaders()
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments', fileId, folderId] })
      setNewComment('')
      setReplyingTo(null)
      setReplyText('')
      toast.success('Commentaire ajouté')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'ajout du commentaire')
    }
  })

  const handleSubmit = (e: React.FormEvent, parentId?: number) => {
    e.preventDefault()
    const text = parentId ? replyText : newComment
    if (!text.trim()) return

    createCommentMutation.mutate({
      comment: text.trim(),
      parent_comment_id: parentId
    })
  }

  const renderComment = (comment: Comment, level = 0) => (
    <div key={comment.id} className={`comment-item ${level > 0 ? 'comment-reply' : ''}`}>
      <div className="comment-header">
        <div className="comment-author">
          <span className="comment-avatar">{comment.username?.[0]?.toUpperCase() || 'U'}</span>
          <div>
            <div className="comment-username">{comment.username || 'Utilisateur'}</div>
            <div className="comment-date">
              {format(new Date(comment.created_at), 'dd MMM yyyy à HH:mm', { locale: fr })}
            </div>
          </div>
        </div>
        {comment.user_id === user?.id && (
          <span className="comment-badge">Vous</span>
        )}
      </div>
      <div className="comment-content">{comment.comment}</div>
      {level === 0 && (
        <button
          className="comment-reply-btn"
          onClick={() => setReplyingTo(replyingTo === comment.id ? null : comment.id)}
        >
          Répondre
        </button>
      )}
      {replyingTo === comment.id && (
        <form className="comment-reply-form" onSubmit={(e) => handleSubmit(e, comment.id)}>
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Écrivez votre réponse..."
            className="comment-input"
            rows={3}
          />
          <div className="comment-form-actions">
            <button
              type="button"
              onClick={() => {
                setReplyingTo(null)
                setReplyText('')
              }}
              className="comment-cancel-btn"
            >
              Annuler
            </button>
            <button
              type="submit"
              className="comment-submit-btn"
              disabled={!replyText.trim() || createCommentMutation.isPending}
            >
              {createCommentMutation.isPending ? 'Envoi...' : 'Répondre'}
            </button>
          </div>
        </form>
      )}
      {comment.replies && comment.replies.length > 0 && (
        <div className="comment-replies">
          {comment.replies.map((reply) => renderComment(reply, level + 1))}
        </div>
      )}
    </div>
  )

  return (
    <div className="comments-modal-overlay animate-fade-in" onClick={onClose}>
      <div className="comments-modal-container animate-scale-in" onClick={(e) => e.stopPropagation()}>
        <div className="comments-modal-header">
          <h3>Commentaires {fileId ? 'du fichier' : 'du dossier'}</h3>
          <button 
            onClick={onClose} 
            className="comments-modal-close"
            aria-label="Fermer les commentaires"
          >
            <span aria-hidden="true">✕</span>
          </button>
        </div>
        
        <div className="comments-modal-content">
          {isLoading ? (
            <div className="comments-loading">Chargement...</div>
          ) : (
            <>
              <div className="comments-list">
                {comments && comments.length > 0 ? (
                  comments.map((comment) => renderComment(comment))
                ) : (
                  <div className="comments-empty">
                    <p>Aucun commentaire pour le moment</p>
                    <p className="comments-empty-hint">Soyez le premier à commenter !</p>
                  </div>
                )}
              </div>
              
              <form className="comments-form" onSubmit={(e) => handleSubmit(e)}>
                <textarea
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Ajouter un commentaire..."
                  className="comment-input"
                  rows={4}
                />
                <div className="comment-form-actions">
                  <button
                    type="submit"
                    className="comment-submit-btn"
                    disabled={!newComment.trim() || createCommentMutation.isPending}
                  >
                    {createCommentMutation.isPending ? 'Envoi...' : 'Commenter'}
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default FileComments

