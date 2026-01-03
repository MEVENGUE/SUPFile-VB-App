# SUPFile-Vercel-App

# SUPFile - Secure Cloud File Storage System

> **Projet académique SUPINFO** - Système de stockage de fichiers cloud sécurisé (type Dropbox)

## 📋 Vue d'ensemble

SUPFile est une application web de stockage de fichiers cloud sécurisée permettant aux utilisateurs de :
- 📤 Téléverser des fichiers de manière sécurisée
- 📥 Télécharger leurs fichiers
- 🔐 S'authentifier via JWT
- 📁 Organiser leurs fichiers dans des dossiers
- 🔍 Rechercher leurs fichiers
- 👁️ Prévisualiser leurs fichiers
- 🔗 Partager leurs fichiers
- 📊 Visualiser leurs statistiques
- 🌍 Bénéficier d'une haute disponibilité multi-régions

## 🏗️ Architecture

### Structure du Projet

```
SUPFile/
├── frontend/          # Application React + TypeScript
│   ├── src/
│   │   ├── components/    # Composants React
│   │   ├── pages/         # Pages de l'application
│   │   ├── services/      # Services API
│   │   ├── contexts/      # Contextes React
│   │   ├── hooks/         # Hooks personnalisés
│   │   └── utils/         # Utilitaires
│   ├── public/            # Fichiers statiques
│   ├── package.json
│   └── vite.config.ts
│
├── backend/           # API FastAPI + Python
│   ├── app/
│   │   ├── api/v1/        # Routes API
│   │   ├── core/          # Configuration, sécurité
│   │   ├── models/        # Modèles SQLAlchemy
│   │   └── services/      # Services Azure Blob Storage
│   ├── alembic/           # Migrations base de données
│   ├── requirements.txt
│   └── Dockerfile
│
└── docker-compose.yml # Configuration Docker pour développement local
```

### Technologies Utilisées

**Frontend :**
- React 18 + TypeScript
- Vite (build tool)
- React Router (navigation)
- React Query (gestion d'état)
- Axios (requêtes HTTP)
- React Dropzone (upload drag & drop)
- React Toastify (notifications)

**Backend :**
- FastAPI (framework Python)
- SQLAlchemy (ORM)
- PostgreSQL (base de données)
- Alembic (migrations)
- Azure Blob Storage (stockage fichiers)
- JWT (authentification)
- Bcrypt (hachage mots de passe)

**Infrastructure :**
- Docker & Docker Compose
- PostgreSQL (base de données)
- Azure Blob Storage (stockage cloud)

## 🚀 Installation et Démarrage Local

### Prérequis

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL (si installation manuelle)

### Installation avec Docker (Recommandé)

1. **Cloner le projet**
```bash
git clone <repository-url>
cd SUPFile
```

2. **Configurer les variables d'environnement**

Créez un fichier `.env` à la racine :
```env
# Backend
DATABASE_URL=postgresql://supfile_user:supfile_password@postgres:5432/supfile
SECRET_KEY=votre-secret-key-minimum-32-caracteres
JWT_SECRET_KEY=votre-jwt-secret-key-minimum-32-caracteres

# Azure (optionnel pour développement local)
AZURE_STORAGE_ACCOUNT_NAME=
AZURE_STORAGE_ACCOUNT_KEY=
AZURE_STORAGE_CONTAINER_NAME=supfile-files

# Frontend
VITE_API_URL=http://localhost:8000/api/v1
```

3. **Démarrer les services**
```bash
docker-compose up -d
```

4. **Initialiser la base de données**
```bash
# Entrer dans le container backend
docker exec -it supfile-backend bash

# Exécuter les migrations
alembic upgrade head
```

5. **Accéder à l'application**
- Frontend : http://localhost:3000
- Backend API : http://localhost:8000
- Documentation API : http://localhost:8000/docs

### Installation Manuelle

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Créer un fichier .env avec les variables d'environnement
cp .env.example .env

# Configurer PostgreSQL localement
# Puis exécuter les migrations
alembic upgrade head

# Démarrer le serveur
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install

# Créer un fichier .env
echo "VITE_API_URL=http://localhost:8000/api/v1" > .env

# Démarrer le serveur de développement
npm run dev
```

## 📚 Fonctionnalités

### Authentification
- ✅ Inscription et connexion avec email/mot de passe
- ✅ Authentification JWT sécurisée
- ✅ Hachage des mots de passe avec bcrypt
- ⚠️ OAuth2 (Google, GitHub, Microsoft) - En développement

### Gestion des Fichiers
- ✅ Upload de fichiers (drag & drop)
- ✅ Téléchargement de fichiers
- ✅ Suppression de fichiers
- ✅ Renommage de fichiers
- ✅ Déplacement de fichiers
- ✅ Recherche de fichiers
- ✅ Prévisualisation (images, PDF, texte)
- ✅ Partage de fichiers (liens publics)
- ✅ Métadonnées des fichiers

### Gestion des Dossiers
- ✅ Création de dossiers
- ✅ Navigation dans les dossiers (breadcrumbs)
- ✅ Renommage de dossiers
- ✅ Déplacement de dossiers
- ✅ Suppression de dossiers
- ✅ Arborescence de dossiers

### Dashboard
- ✅ Statistiques des fichiers
- ✅ Espace de stockage utilisé
- ✅ Liste des fichiers récents
- ✅ Vue d'ensemble de l'activité

### Autres Fonctionnalités
- ✅ Thème clair/sombre
- ✅ Interface responsive
- ✅ Notifications toast
- ✅ Pagination
- ✅ Historique des modifications
- ✅ Commentaires sur les fichiers
- ⚠️ Synchronisation temps réel (WebSocket) - En développement

## 🔐 Sécurité

- ✅ Authentification JWT sécurisée
- ✅ Hachage des mots de passe (bcrypt)
- ✅ Validation des entrées
- ✅ Protection CORS
- ✅ HTTPS (en production)
- ✅ Secrets via variables d'environnement
- ✅ Contrôle d'accès basé sur les utilisateurs

## 📖 Documentation Complète

Consultez [DOCUMENTATION.md](./DOCUMENTATION.md) pour :
- Architecture détaillée
- Guide de déploiement
- Sécurité et bonnes pratiques
- API Reference
- Historique des modifications
- Roadmap

## 🧪 Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## 📝 Scripts Disponibles

### Backend
```bash
# Démarrer le serveur
uvicorn app.main:app --reload

# Migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head
alembic downgrade -1
```

### Frontend
```bash
# Développement
npm run dev

# Build production
npm run build

# Preview build
npm run preview

# Linter
npm run lint
```

## 🤝 Contribution

Ce projet est un projet académique SUPINFO. Pour toute question, contactez l'équipe projet.

## 👥 Auteurs

- MEVENGUE Franck
- Nadia Loukdache

## 📄 Licence

Projet académique - Tous droits réservés

---

**Note :** Ce projet est optimisé pour un déploiement sur Vercel (frontend) et une infrastructure cloud (backend).
