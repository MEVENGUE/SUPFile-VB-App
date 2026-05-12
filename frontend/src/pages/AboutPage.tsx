import { Link } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import './AboutPage.css'

const AboutPage = () => {

  return (
    <div className="about-page">
      <Sidebar />
      <div className="about-content">
        <div className="about-hero">
          <h2>À propos de SUPFile</h2>
          <p className="about-subtitle">Système de stockage cloud sécurisé</p>
        </div>

        <div className="about-section">
          <div className="about-logo-section">
            <img 
              src="/Images app/SUPINFO Paris Logo.png" 
              alt="SUPINFO Logo" 
              className="supinfo-logo"
            />
            <h3>École SUPINFO</h3>
            <p>Projet réalisé dans le cadre de la formation SUPINFO</p>
          </div>

          <div className="about-info-grid">
            <div className="info-card">
              <h4>👤 Auteurs</h4>
              <p>MEVENGUE Franck</p>
              <p>Nadia Loukdache</p>
              <p>Ayman El-Karroussi</p>
              <p className="info-subtitle">Étudiants SUPINFO</p>
            </div>

            <div className="info-card">
              <h4>🛠️ Technologies</h4>
              <ul>
                <li>Frontend: React + TypeScript</li>
                <li>Backend: FastAPI + Python</li>
                <li>Base de données: PostgreSQL</li>
                <li>Stockage: Azure Blob Storage</li>
                <li>Authentification: JWT + OAuth2</li>
              </ul>
            </div>

            <div className="info-card">
              <h4>📦 Outils utilisés</h4>
              <ul>
                <li>React Query</li>
                <li>React Router</li>
                <li>SQLAlchemy</li>
                <li>Alembic</li>
                <li>Azure SDK</li>
                <li>Authlib</li>
              </ul>
            </div>

            <div className="info-card">
              <h4>📄 Licence</h4>
              <p className="license-text">
                <strong>Licence SUPINFO</strong>
              </p>
              <p className="license-details">
                Ce projet est réalisé dans le cadre académique de SUPINFO.
                Tous droits réservés.
              </p>
            </div>
          </div>

          <div className="about-features">
            <h3>Fonctionnalités</h3>
            <div className="features-list">
              <div className="feature-item">☁️ Stockage cloud sécurisé</div>
              <div className="feature-item">📁 Gestion de dossiers</div>
              <div className="feature-item">🔗 Partage de fichiers</div>
              <div className="feature-item">🔐 Authentification OAuth2</div>
              <div className="feature-item">📱 Application PWA</div>
              <div className="feature-item">🗑️ Corbeille</div>
              <div className="feature-item">📊 Statistiques</div>
              <div className="feature-item">🔍 Recherche avancée</div>
            </div>
          </div>

          <div className="about-footer">
            <Link to="/dashboard" className="back-button">
              ← Retour au Dashboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AboutPage

