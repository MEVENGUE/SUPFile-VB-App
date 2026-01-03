import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import ThemeToggle from './ThemeToggle'
import './Sidebar.css'

const Sidebar = () => {
  const location = useLocation()
  const { user, logout } = useAuth()

  const menuItems = [
    {
      path: '/dashboard',
      icon: '📁',
      label: 'Accéder à mes fichiers',
      exact: true
    },
    {
      path: '/my-files',
      icon: '📂',
      label: 'Mes fichiers'
    },
    {
      path: '/shared',
      icon: '🔗',
      label: 'Fichiers partagés'
    },
    {
      path: '/chat',
      icon: '💬',
      label: 'Aide & Commentaires'
    },
    {
      path: '/trash',
      icon: '🗑️',
      label: 'Corbeille'
    },
    {
      path: '/about',
      icon: 'ℹ️',
      label: 'À propos'
    }
  ]

  const isActive = (path: string, exact?: boolean) => {
    if (exact) {
      return location.pathname === path
    }
    return location.pathname.startsWith(path)
  }

  return (
    <aside className="sidebar" role="complementary" aria-label="Navigation principale">
      <div className="sidebar-header">
        <Link to="/home" className="sidebar-logo" aria-label="Retour à l'accueil SUPFile">
          <img src="/logo.jpg" alt="SUPFile Logo" className="sidebar-logo-image" />
          <span className="sidebar-logo-text">SUPFile</span>
        </Link>
      </div>

      <nav className="sidebar-nav" role="navigation" aria-label="Menu de navigation">
        <ul className="sidebar-menu">
          {menuItems.map((item) => (
            <li key={item.path}>
              <Link
                to={item.path}
                className={`sidebar-menu-item ${isActive(item.path, item.exact) ? 'active' : ''} animate-fade-in`}
                aria-current={isActive(item.path, item.exact) ? 'page' : undefined}
                aria-label={item.label}
              >
                <span className="sidebar-menu-icon" aria-hidden="true">{item.icon}</span>
                <span className="sidebar-menu-label">{item.label}</span>
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <div className="sidebar-footer">
        <ThemeToggle />
        <div className="sidebar-user">
          <img src="/Utulisateur_profile.jpg" alt="User" className="sidebar-user-avatar" />
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user?.username || 'Utilisateur'}</div>
            <div className="sidebar-user-email">{user?.email || ''}</div>
          </div>
        </div>
        <button 
          onClick={logout} 
          className="sidebar-logout" 
          title="Déconnexion"
          aria-label="Se déconnecter"
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              logout()
            }
          }}
        >
          <span className="sidebar-logout-icon" aria-hidden="true">🚪</span>
          <span className="sidebar-logout-text">Déconnexion</span>
        </button>
      </div>
    </aside>
  )
}

export default Sidebar

