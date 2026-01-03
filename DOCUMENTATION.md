# SUPFile - Documentation Complète

> Documentation technique complète du projet SUPFile

## Table des Matières

1. [Architecture](#architecture)
2. [Fonctionnalités Implémentées](#fonctionnalités-implémentées)
3. [Modifications et Évolutions](#modifications-et-évolutions)
4. [Guide de Déploiement](#guide-de-déploiement)
5. [Sécurité](#sécurité)
6. [API Reference](#api-reference)
7. [Roadmap](#roadmap)

---

## Architecture

### Architecture Globale

SUPFile est une application web de stockage de fichiers cloud avec une architecture moderne séparée en frontend et backend.

```
┌─────────────────┐
│   Frontend      │  React + TypeScript + Vite
│   (React)       │  Port: 3000
└────────┬────────┘
         │ HTTP/REST
         │
┌────────▼────────┐
│   Backend       │  FastAPI + Python
│   (FastAPI)     │  Port: 8000
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│PostgreSQL│ │Azure Blob│
│Database │ │ Storage  │
└─────────┘ └──────────┘
```

### Structure du Projet

```
SUPFile/
├── frontend/              # Application React
│   ├── src/
│   │   ├── components/    # Composants réutilisables
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Breadcrumbs.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   ├── FileViewer.tsx
│   │   │   ├── ShareModal.tsx
│   │   │   ├── RenameModal.tsx
│   │   │   ├── MoveModal.tsx
│   │   │   ├── Pagination.tsx
│   │   │   ├── ThemeToggle.tsx
│   │   │   └── LoadingSpinner.tsx
│   │   ├── pages/         # Pages de l'application
│   │   │   ├── HomePage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── MyFilesPage.tsx
│   │   │   ├── SharedFilesPage.tsx
│   │   │   └── AboutPage.tsx
│   │   ├── services/      # Services API
│   │   │   ├── authService.ts
│   │   │   ├── fileService.ts
│   │   │   └── folderService.ts
│   │   ├── contexts/       # Contextes React
│   │   │   ├── AuthContext.tsx
│   │   │   └── ThemeContext.tsx
│   │   ├── hooks/         # Hooks personnalisés
│   │   │   └── useWebSocket.ts
│   │   └── utils/          # Utilitaires
│   │       └── fileIcons.ts
│   ├── public/            # Fichiers statiques
│   └── package.json
│
├── backend/               # API FastAPI
│   ├── app/
│   │   ├── api/v1/        # Routes API version 1
│   │   │   ├── auth.py
│   │   │   ├── files.py
│   │   │   ├── folders.py
│   │   │   ├── share.py
│   │   │   ├── dashboard.py
│   │   │   ├── file_history.py
│   │   │   ├── file_comments.py
│   │   │   └── websocket.py
│   │   ├── core/          # Configuration
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   └── middleware.py
│   │   ├── models/        # Modèles SQLAlchemy
│   │   │   ├── user.py
│   │   │   ├── file.py
│   │   │   ├── folder.py
│   │   │   ├── share_link.py
│   │   │   ├── file_history.py
│   │   │   └── file_comment.py
│   │   └── services/      # Services métier
│   │       └── azure_blob.py
│   ├── alembic/           # Migrations base de données
│   └── requirements.txt
```

### Technologies Utilisées

**Frontend :**
- React 18.2.0
- TypeScript 5.3.3
- Vite 5.0.8 (build tool)
- React Router 6.20.0 (navigation)
- React Query 5.12.2 (gestion d'état serveur)
- Axios 1.6.2 (requêtes HTTP)
- React Dropzone 14.2.3 (upload drag & drop)
- React Toastify 9.1.3 (notifications)
- Date-fns 2.30.0 (formatage dates)

**Backend :**
- FastAPI 0.104.1
- Python 3.11
- SQLAlchemy 2.0.23 (ORM)
- Alembic 1.12.1 (migrations)
- PostgreSQL 15 (base de données)
- Azure Blob Storage 12.19.0 (stockage fichiers)
- Python-JOSE 3.3.0 (JWT)
- Passlib 1.7.4 + Bcrypt 4.0.0 (hachage mots de passe)
- Pydantic 2.5.0 (validation)

**Infrastructure :**
- Docker & Docker Compose
- PostgreSQL (base de données)
- Azure Blob Storage (stockage cloud)

### Architecture de Fonctionnement

#### Flux d'Authentification

1. Utilisateur saisit email/mot de passe
2. Frontend envoie requête POST `/api/v1/auth/login`
3. Backend vérifie credentials et génère JWT
4. Frontend stocke token dans localStorage
5. Token inclus dans header `Authorization` pour requêtes suivantes

#### Flux d'Upload de Fichier

1. Utilisateur glisse-dépose fichier
2. Frontend envoie fichier via FormData à `/api/v1/files/upload`
3. Backend valide fichier (taille, extension)
4. Backend upload fichier vers Azure Blob Storage
5. Backend sauvegarde métadonnées dans PostgreSQL
6. Backend retourne métadonnées fichier
7. Frontend met à jour la liste des fichiers

#### Flux de Navigation

1. Utilisateur clique sur dossier
2. Frontend met à jour `currentFolderId`
3. Frontend requête `/api/v1/files?folder_id={id}`
4. Backend retourne fichiers du dossier
5. Frontend affiche fichiers avec breadcrumbs

---

## Fonctionnalités Implémentées

### ✅ Authentification

- **Inscription** : Création de compte avec email/mot de passe
- **Connexion** : Authentification JWT sécurisée
- **Sessions** : Gestion des tokens (access + refresh)
- **Sécurité** : Hachage bcrypt (12 rounds)

### ✅ Gestion des Fichiers

- **Upload** : Drag & drop, barre de progression
- **Téléchargement** : Téléchargement individuel
- **Suppression** : Suppression sécurisée
- **Renommage** : Modification du nom
- **Déplacement** : Déplacement entre dossiers
- **Recherche** : Recherche par nom et type
- **Prévisualisation** : Images, PDF, texte
- **Métadonnées** : Affichage taille, date, type

### ✅ Gestion des Dossiers

- **Création** : Création de dossiers
- **Navigation** : Arborescence avec breadcrumbs
- **Renommage** : Modification du nom
- **Déplacement** : Déplacement dans l'arborescence
- **Suppression** : Suppression récursive

### ✅ Partage

- **Liens publics** : Génération de liens de partage
- **Accès public** : Accès sans authentification
- **Expiration** : Liens avec date d'expiration
- **Mot de passe** : Protection par mot de passe (optionnel)

### ✅ Dashboard

- **Statistiques** : Nombre de fichiers, espace utilisé
- **Fichiers récents** : Liste des derniers fichiers
- **Graphiques** : Visualisation de l'espace de stockage
- **Activité** : Vue d'ensemble de l'activité

### ✅ Interface Utilisateur

- **Thème** : Thème clair/sombre
- **Responsive** : Design adaptatif mobile/desktop
- **Animations** : Transitions et animations fluides
- **Accessibilité** : Support clavier et ARIA
- **Notifications** : Toast notifications

### ✅ Fonctionnalités Avancées

- **Historique** : Historique des modifications
- **Commentaires** : Commentaires sur fichiers/dossiers
- **WebSocket** : Synchronisation temps réel (en développement)
- **Pagination** : Pagination des listes
- **Lazy Loading** : Chargement différé des images

---

## Modifications et Évolutions

### Historique des Modifications

#### Version 1.0 - Décembre 2024

**Fonctionnalités Initiales :**
- Authentification JWT
- Upload/téléchargement fichiers
- Liste des fichiers
- Dashboard basique

#### Version 1.1 - Janvier 2025

**Améliorations UX :**
- Thème blanc avec accents bleu clair
- Animations et transitions
- Design responsive
- Accessibilité améliorée

**Nouvelles Fonctionnalités :**
- Gestion des dossiers (création, navigation, breadcrumbs)
- Recherche de fichiers
- Prévisualisation (images, PDF, texte)
- Partage de fichiers (liens publics)
- Renommage et déplacement
- Pagination

#### Version 1.2 - Février 2025

**Fonctionnalités Avancées :**
- Historique des modifications
- Commentaires sur fichiers
- WebSocket pour synchronisation temps réel
- Thème clair/sombre
- Statistiques détaillées (espace utilisé, disponible, pourcentage)

**Optimisations :**
- Lazy loading des composants React
- Lazy loading des images
- Pagination optimisée
- Performance améliorée

### Évolutions Futures

- OAuth2 (Google, GitHub, Microsoft)
- Application mobile (React Native)
- Chiffrement fichiers
- Versioning fichiers
- Synchronisation temps réel complète

---

## Guide de Déploiement

### Déploiement Local avec Docker

1. **Cloner le projet**
```bash
git clone <repository-url>
cd SUPFile
```

2. **Configurer les variables d'environnement**

Créer `.env` à la racine :
```env
DATABASE_URL=postgresql://supfile_user:supfile_password@postgres:5432/supfile
SECRET_KEY=votre-secret-key-minimum-32-caracteres
JWT_SECRET_KEY=votre-jwt-secret-key-minimum-32-caracteres
AZURE_STORAGE_ACCOUNT_NAME=
AZURE_STORAGE_ACCOUNT_KEY=
AZURE_STORAGE_CONTAINER_NAME=supfile-files
VITE_API_URL=http://localhost:8000/api/v1
```

3. **Démarrer les services**
```bash
docker-compose up -d
```

4. **Initialiser la base de données**
```bash
docker exec -it supfile-backend bash
alembic upgrade head
```

5. **Accéder à l'application**
- Frontend : http://localhost:3000
- Backend API : http://localhost:8000
- API Docs : http://localhost:8000/docs

### Déploiement sur Vercel (Frontend)

1. **Installer Vercel CLI**
```bash
npm i -g vercel
```

2. **Se connecter**
```bash
vercel login
```

3. **Déployer**
```bash
cd frontend
vercel
```

4. **Configurer les variables d'environnement**
- Dans le dashboard Vercel, ajouter `VITE_API_URL` pointant vers votre backend

### Déploiement Backend (Cloud)

Le backend peut être déployé sur :
- Azure App Service
- Heroku
- Railway
- Render
- AWS Elastic Beanstalk

**Variables d'environnement requises :**
- `DATABASE_URL`
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `AZURE_STORAGE_ACCOUNT_NAME`
- `AZURE_STORAGE_ACCOUNT_KEY`
- `AZURE_STORAGE_CONTAINER_NAME`
- `CORS_ORIGINS`

---

## Sécurité

### Mesures de Sécurité Implémentées

1. **Authentification**
   - JWT tokens sécurisés
   - Hachage bcrypt (12 rounds)
   - Tokens avec expiration
   - Refresh tokens

2. **Autorisation**
   - Contrôle d'accès par utilisateur
   - Vérification des permissions
   - Middleware d'authentification

3. **Validation**
   - Validation des entrées (Pydantic)
   - Validation des fichiers (taille, extension)
   - Protection injection SQL (SQLAlchemy)

4. **Réseau**
   - HTTPS (en production)
   - CORS configuré
   - Headers de sécurité

5. **Stockage**
   - Secrets dans variables d'environnement
   - Pas de secrets en clair
   - Azure Blob Storage sécurisé

### Bonnes Pratiques

- ✅ Aucun secret en clair dans le code
- ✅ Validation de toutes les entrées
- ✅ Protection contre injection SQL
- ✅ HTTPS partout
- ✅ CORS restreint
- ✅ Rate limiting (à implémenter)

---

## API Reference

### Authentification

#### POST `/api/v1/auth/register`
Inscription d'un nouvel utilisateur

**Body :**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "John Doe"
}
```

**Response :**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe"
}
```

#### POST `/api/v1/auth/login`
Connexion utilisateur

**Body :**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response :**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

### Fichiers

#### GET `/api/v1/files`
Liste des fichiers

**Query Parameters :**
- `folder_id` (optional) : ID du dossier parent
- `skip` (optional) : Nombre de résultats à sauter
- `limit` (optional) : Nombre de résultats à retourner

#### POST `/api/v1/files/upload`
Upload d'un fichier

**Body :** FormData avec champ `file`

**Response :**
```json
{
  "id": 1,
  "filename": "document.pdf",
  "size": 1024,
  "content_type": "application/pdf",
  "created_at": "2024-01-01T00:00:00"
}
```

#### GET `/api/v1/files/{id}/download`
Téléchargement d'un fichier

#### DELETE `/api/v1/files/{id}`
Suppression d'un fichier

#### PATCH `/api/v1/files/{id}/rename`
Renommage d'un fichier

**Body :**
```json
{
  "name": "nouveau_nom.pdf"
}
```

#### PATCH `/api/v1/files/{id}/move`
Déplacement d'un fichier

**Body :**
```json
{
  "folder_id": 2
}
```

### Dossiers

#### GET `/api/v1/folders`
Liste des dossiers

#### POST `/api/v1/folders`
Création d'un dossier

**Body :**
```json
{
  "name": "Mon Dossier",
  "parent_id": null
}
```

#### PATCH `/api/v1/folders/{id}/rename`
Renommage d'un dossier

#### PATCH `/api/v1/folders/{id}/move`
Déplacement d'un dossier

#### DELETE `/api/v1/folders/{id}`
Suppression d'un dossier

### Partage

#### POST `/api/v1/share`
Création d'un lien de partage

**Body :**
```json
{
  "file_id": 1,
  "expires_at": "2024-12-31T23:59:59",
  "password": "optional_password"
}
```

**Response :**
```json
{
  "token": "uuid-token",
  "url": "https://app.com/share/uuid-token"
}
```

#### GET `/api/v1/share/{token}`
Accès à un fichier partagé

### Dashboard

#### GET `/api/v1/dashboard/stats`
Statistiques du dashboard

**Response :**
```json
{
  "total_files": 100,
  "total_size": 1073741824,
  "storage_used": 536870912,
  "storage_available": 107374182400,
  "storage_percentage": 0.5
}
```

---

## Roadmap

### Phase 1 : Fondations ✅
- Authentification JWT
- Upload/téléchargement
- Gestion fichiers de base

### Phase 2 : Organisation ✅
- Gestion dossiers
- Navigation breadcrumbs
- Recherche

### Phase 3 : Partage ✅
- Liens publics
- Partage sécurisé

### Phase 4 : Améliorations UX ✅
- Thème clair/sombre
- Animations
- Responsive design

### Phase 5 : Fonctionnalités Avancées ✅
- Historique modifications
- Commentaires
- WebSocket

### Phase 6 : À Venir
- OAuth2
- Application mobile
- Chiffrement fichiers
- Versioning

---

**Dernière mise à jour** : Février 2025

