import React, { useState, useEffect } from 'react'
import './UpdateNotification.css'

interface UpdateNotificationProps {
  onUpdate: () => void
  onDismiss?: () => void
}

const UpdateNotification: React.FC<UpdateNotificationProps> = ({ onUpdate, onDismiss }) => {
  const [showNotification, setShowNotification] = useState(false)
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null)

  useEffect(() => {
    // Vérifier si le service worker est supporté
    if ('serviceWorker' in navigator) {
      let reg: ServiceWorkerRegistration | null = null

      navigator.serviceWorker.ready.then((registration) => {
        reg = registration
        setRegistration(registration)

        // Écouter les mises à jour du service worker
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // Nouvelle version disponible
                setShowNotification(true)
              }
            })
          }
        })

        // Vérifier immédiatement s'il y a une mise à jour
        registration.update()
      })

      // Écouter les messages du service worker
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        // Le service worker a été mis à jour, recharger la page
        window.location.reload()
      })

      // Vérifier périodiquement les mises à jour (toutes les 30 minutes)
      const checkInterval = setInterval(() => {
        if (reg) {
          reg.update()
        }
      }, 30 * 60 * 1000)

      return () => clearInterval(checkInterval)
    }
  }, [])

  const handleUpdate = () => {
    if (registration?.waiting) {
      // Envoyer un message au service worker pour qu'il active la nouvelle version
      registration.waiting.postMessage({ type: 'SKIP_WAITING' })
      setShowNotification(false)
      onUpdate()
    }
  }

  const handleDismiss = () => {
    setShowNotification(false)
    // Ne pas afficher pendant 24h
    localStorage.setItem('update-notification-dismissed', Date.now().toString())
    if (onDismiss) {
      onDismiss()
    }
  }

  // Vérifier si l'utilisateur a déjà ignoré la notification récemment
  useEffect(() => {
    const dismissed = localStorage.getItem('update-notification-dismissed')
    if (dismissed) {
      const dismissedTime = parseInt(dismissed, 10)
      const hoursSinceDismissed = (Date.now() - dismissedTime) / (1000 * 60 * 60)
      if (hoursSinceDismissed < 24) {
        setShowNotification(false)
      }
    }
  }, [])

  if (!showNotification || !registration?.waiting) {
    return null
  }

  return (
    <div className="update-notification">
      <div className="update-notification-content">
        <div className="update-notification-icon">🔄</div>
        <div className="update-notification-text">
          <h3>Nouvelle version disponible</h3>
          <p>Une mise à jour de SUPFile est disponible. Téléchargez-la pour bénéficier des dernières améliorations.</p>
        </div>
        <div className="update-notification-actions">
          <button
            onClick={handleUpdate}
            className="update-btn"
            aria-label="Mettre à jour"
          >
            Mettre à jour
          </button>
          <button
            onClick={handleDismiss}
            className="dismiss-btn"
            aria-label="Plus tard"
          >
            Plus tard
          </button>
        </div>
      </div>
    </div>
  )
}

export default UpdateNotification

