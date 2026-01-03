# Guide de Déploiement - SUPFile

Ce guide vous explique comment déployer SUPFile sur Vercel (frontend) et Railway (backend).

## 📋 Architecture de Déploiement

- **Frontend (React + Vite)** : Déployé sur Vercel
- **Backend (FastAPI)** : Déployé sur Railway
- **Base de données PostgreSQL** : Provisionnée via Railway
- **Stockage de fichiers** : Azure Blob Storage

---

## 🚀 Déploiement sur Vercel (Frontend)

### Étape 1 : Préparer le projet

1. Assurez-vous que votre code est poussé sur GitHub
2. Vérifiez que le fichier `frontend/vercel.json` existe

### Étape 2 : Créer un projet sur Vercel

1. Allez sur [vercel.com](https://vercel.com) et connectez-vous avec GitHub
2. Cliquez sur **"Add New Project"**
3. Importez le dépôt `SUPFile-Vercel-App`
4. Configurez le projet :
   - **Framework Preset** : Vite
   - **Root Directory** : `frontend`
   - **Build Command** : `npm run build`
   - **Output Directory** : `dist`
   - **Install Command** : `npm install`

### Étape 3 : Configurer les variables d'environnement

Dans les paramètres du projet Vercel, ajoutez ces variables d'environnement :

```
VITE_API_URL=https://votre-backend-railway.railway.app/api/v1
```

**Important** : Remplacez `votre-backend-railway.railway.app` par l'URL réelle de votre backend Railway (vous l'obtiendrez après le déploiement du backend).

### Étape 4 : Déployer

1. Cliquez sur **"Deploy"**
2. Vercel va automatiquement :
   - Installer les dépendances
   - Builder le projet
   - Déployer l'application
3. Une fois terminé, vous obtiendrez une URL (ex: `https://supfile.vercel.app`)

### Étape 5 : Configurer le domaine personnalisé (optionnel)

1. Allez dans **Settings** > **Domains**
2. Ajoutez votre domaine personnalisé si vous en avez un

---

## 🚂 Déploiement sur Railway (Backend)

### Étape 1 : Créer un compte Railway

1. Allez sur [railway.app](https://railway.app)
2. Connectez-vous avec GitHub
3. Créez un nouveau projet

### Étape 2 : Ajouter PostgreSQL

1. Dans votre projet Railway, cliquez sur **"+ New"**
2. Sélectionnez **"Database"** > **"Add PostgreSQL"**
3. Railway va créer une base de données PostgreSQL
4. Notez les variables d'environnement générées (notamment `DATABASE_URL`)

### Étape 3 : Déployer le Backend

1. Dans votre projet Railway, cliquez sur **"+ New"**
2. Sélectionnez **"GitHub Repo"**
3. Choisissez le dépôt `SUPFile-Vercel-App`
4. Railway détectera automatiquement le Dockerfile dans `backend/`
5. Configurez les paramètres :
   - **Root Directory** : `backend`
   - **Dockerfile Path** : `backend/Dockerfile`

### Étape 4 : Configurer les variables d'environnement

Dans les paramètres du service backend, ajoutez toutes ces variables :

#### Variables obligatoires :

```env
# Base de données (générée automatiquement par Railway PostgreSQL)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Clés secrètes (générez des valeurs aléatoires sécurisées)
SECRET_KEY=votre-secret-key-minimum-32-caracteres-aleatoires
JWT_SECRET_KEY=votre-jwt-secret-key-minimum-32-caracteres-aleatoires

# Azure Blob Storage
AZURE_STORAGE_ACCOUNT_NAME=votre-compte-azure
AZURE_STORAGE_ACCOUNT_KEY=votre-cle-azure
AZURE_STORAGE_CONTAINER_NAME=supfile-files
AZURE_STORAGE_CONNECTION_STRING=votre-connection-string-azure

# CORS (URL de votre frontend Vercel)
CORS_ORIGINS=https://votre-frontend.vercel.app,https://votre-frontend.vercel.app

# Configuration serveur
HOST=0.0.0.0
PORT=${{PORT}}
DEBUG=False
APP_ENV=production
```

#### Variables optionnelles (OAuth) :

```env
OAUTH_GOOGLE_CLIENT_ID=
OAUTH_GOOGLE_CLIENT_SECRET=
OAUTH_GITHUB_CLIENT_ID=
OAUTH_GITHUB_CLIENT_SECRET=
OAUTH_MICROSOFT_CLIENT_ID=
OAUTH_MICROSOFT_CLIENT_SECRET=
OAUTH_REDIRECT_BASE_URL=https://votre-frontend.vercel.app
```

**Note** : Pour générer des clés secrètes sécurisées, vous pouvez utiliser :
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Étape 5 : Exécuter les migrations de base de données

1. Une fois le backend déployé, vous devez exécuter les migrations Alembic
2. Dans Railway, allez dans votre service backend
3. Ouvrez la console (terminal)
4. Exécutez :
```bash
alembic upgrade head
```

### Étape 6 : Obtenir l'URL du backend

1. Dans Railway, allez dans votre service backend
2. Cliquez sur **"Settings"**
3. Activez **"Generate Domain"** pour obtenir une URL publique
4. Notez cette URL (ex: `https://supfile-backend-production.up.railway.app`)

### Étape 7 : Mettre à jour le frontend

1. Retournez sur Vercel
2. Mettez à jour la variable d'environnement `VITE_API_URL` avec l'URL réelle de votre backend Railway
3. Redéployez le frontend (Vercel le fera automatiquement si vous avez activé les déploiements automatiques)

---

## 🔧 Configuration Azure Blob Storage

### Étape 1 : Créer un compte de stockage Azure

1. Allez sur [portal.azure.com](https://portal.azure.com)
2. Créez un nouveau **Storage Account**
3. Notez le nom du compte et générez une clé d'accès

### Étape 2 : Créer un conteneur

1. Dans votre Storage Account, créez un conteneur nommé `supfile-files`
2. Configurez le niveau d'accès (Private recommandé)

### Étape 3 : Obtenir la connection string

1. Dans les paramètres du Storage Account, allez dans **"Access keys"**
2. Copiez la **Connection string**
3. Ajoutez-la dans les variables d'environnement Railway

---

## ✅ Vérification du déploiement

### Vérifier le Backend

1. Visitez `https://votre-backend.railway.app/health`
2. Vous devriez voir : `{"status": "healthy", "database": "connected", "storage": "azure_blob"}`
3. Visitez `https://votre-backend.railway.app/api/docs` pour voir la documentation API

### Vérifier le Frontend

1. Visitez votre URL Vercel
2. Essayez de vous inscrire et de vous connecter
3. Testez l'upload d'un fichier

---

## 🔄 Déploiements automatiques

### Vercel

- Les déploiements automatiques sont activés par défaut
- Chaque push sur la branche `main` déclenche un nouveau déploiement

### Railway

- Les déploiements automatiques sont activés par défaut
- Chaque push sur la branche `main` déclenche un nouveau déploiement

---

## 🐛 Dépannage

### Problème : Le frontend ne peut pas se connecter au backend

- Vérifiez que `VITE_API_URL` dans Vercel pointe vers la bonne URL Railway
- Vérifiez que `CORS_ORIGINS` dans Railway inclut l'URL de votre frontend Vercel
- Vérifiez que le backend Railway est bien déployé et accessible

### Problème : Erreur de base de données

- Vérifiez que `DATABASE_URL` est correctement configuré dans Railway
- Vérifiez que les migrations Alembic ont été exécutées
- Vérifiez les logs Railway pour plus de détails

### Problème : Erreur Azure Blob Storage

- Vérifiez que toutes les variables Azure sont correctement configurées
- Vérifiez que le conteneur `supfile-files` existe dans Azure
- Vérifiez les permissions du Storage Account

### Problème : Build échoue sur Vercel

- Vérifiez que `Root Directory` est bien configuré sur `frontend`
- Vérifiez les logs de build dans Vercel
- Assurez-vous que toutes les dépendances sont dans `package.json`

---

## 📝 Notes importantes

1. **Sécurité** : Ne commitez jamais les fichiers `.env` ou les clés secrètes dans Git
2. **Variables d'environnement** : Utilisez toujours les variables d'environnement pour les secrets
3. **CORS** : Assurez-vous que les URLs CORS correspondent exactement (avec/sans trailing slash)
4. **HTTPS** : Vercel et Railway fournissent HTTPS automatiquement
5. **Monitoring** : Utilisez les logs de Vercel et Railway pour surveiller votre application

---

## 🔗 Liens utiles

- [Documentation Vercel](https://vercel.com/docs)
- [Documentation Railway](https://docs.railway.app)
- [Documentation Azure Blob Storage](https://docs.microsoft.com/en-us/azure/storage/blobs/)
- [Documentation FastAPI](https://fastapi.tiangolo.com)
- [Documentation React](https://react.dev)

---

**Bon déploiement ! 🚀**

