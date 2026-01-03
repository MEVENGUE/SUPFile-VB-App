import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import Sidebar from '../components/Sidebar'
import './HomePage.css'

const HomePage = () => {
  const { user } = useAuth()

  if (!user) {
    return (
      <div className="home-page">
        <div className="home-header">
          <div className="header-content">
            <div className="header-logo-title">
              <img src="/logo.jpg" alt="SUPFile Logo" className="header-logo-icon" />
              <h1>SUPFile</h1>
            </div>
            <div className="header-user">
              <Link to="/login" className="login-link">
                Se connecter
              </Link>
            </div>
          </div>
        </div>
        <div className="home-content">
          <div className="home-hero">
            <h2 className="home-title">Bienvenue sur SUPFile</h2>
            <p className="home-subtitle">Votre solution de stockage cloud sécurisée</p>
            <div className="home-actions">
              <Link to="/login" className="home-action-btn primary">
                Se connecter
              </Link>
              <Link to="/register" className="home-action-btn">
                Créer un compte
              </Link>
            </div>
          </div>
          <div className="home-features">
            <div className="feature-card">
              <div className="feature-icon">☁️</div>
              <h3>Stockage Cloud</h3>
              <p>Stockez vos fichiers en toute sécurité dans le cloud</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🔒</div>
              <h3>Sécurisé</h3>
              <p>Vos données sont protégées et chiffrées</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🔗</div>
              <h3>Partage</h3>
              <p>Partagez facilement vos fichiers avec d'autres</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📱</div>
              <h3>Multi-plateforme</h3>
              <p>Accédez à vos fichiers depuis n'importe quel appareil</p>
            </div>
          </div>
          <div className="home-footer-links">
            <Link to="/about" className="footer-link">À propos</Link>
            <span className="footer-separator">•</span>
            <Link to="/chat" className="footer-link">💬 Aide & Commentaires</Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="home-page">
      <Sidebar />
      <div className="home-content">
        <div className="home-hero">
          <h2 className="home-title">Bienvenue sur SUPFile</h2>
          <p className="home-subtitle">Votre solution de stockage cloud sécurisée</p>
          
          {user ? (
            <div className="home-actions">
              <Link to="/dashboard" className="home-action-btn primary">
                📁 Accéder à mes fichiers
              </Link>
              <Link to="/my-files" className="home-action-btn">
                📂 Mes fichiers
              </Link>
              <Link to="/shared" className="home-action-btn">
                🔗 Fichiers partagés
              </Link>
            </div>
          ) : (
            <div className="home-actions">
              <Link to="/login" className="home-action-btn primary">
                Se connecter
              </Link>
              <Link to="/register" className="home-action-btn">
                Créer un compte
              </Link>
            </div>
          )}
        </div>

        <div className="home-features">
          <div className="feature-card">
            <div className="feature-icon">☁️</div>
            <h3>Stockage Cloud</h3>
            <p>Stockez vos fichiers en toute sécurité dans le cloud</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3>Sécurisé</h3>
            <p>Vos données sont protégées et chiffrées</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔗</div>
            <h3>Partage</h3>
            <p>Partagez facilement vos fichiers avec d'autres</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📱</div>
            <h3>Multi-plateforme</h3>
            <p>Accédez à vos fichiers depuis n'importe quel appareil</p>
          </div>
        </div>

        <div className="home-footer-links">
          <Link to="/about" className="footer-link">À propos</Link>
          <span className="footer-separator">•</span>
          <Link to="/chat" className="footer-link">💬 Aide & Commentaires</Link>
        </div>
      </div>
    </div>
  )
}

export default HomePage

