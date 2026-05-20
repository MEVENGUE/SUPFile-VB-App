# 🚀 SUPFile - Secure Hybrid Cloud File Storage

<div align="center">

![Version](https://img.shields.io/badge/version-2.0-blue.svg)
![License](https://img.shields.io/badge/license-Academic-red.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![React](https://img.shields.io/badge/react-18.2+-61dafb.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.104+-009688.svg)

**SUPFile** est une solution de stockage de fichiers sécurisée et hybride pour un projet académique SUPINFO.

[📚 Documentation Complète](./DOCUMENTATION.md) • [📊 Diagrammes](./DIAGRAMS.md)

</div>

---

## 📋 Table des Matières

- [Vue d'ensemble](#-vue-doverview)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture hybride](#-architecture-hybride)
- [Installation locale](#-installation-locale)
- [Déploiement](#-déploiement)
- [Documentation](#-documentation)
- [Technologies](#-technologies)
- [Contribuer](#-contribuer)

---

## 🎯 Vue d'ensemble

SUPFile est une application web de stockage de fichiers moderne qui combine :

- un frontend React déployé sur Vercel,
- un backend FastAPI exécuté sur des machines privées,
- un stockage partagé GlusterFS sur plusieurs nœuds,
- un fallback Azure Blob Storage pour la résilience cloud.

Cette architecture hybride est conçue pour un déploiement souple en production tout en restant compatible avec un environnement local de développement.

---

## ✨ Fonctionnalités principales

- 🔐 Authentification OAuth2 et JWT
- 📁 Uploads / téléchargements de fichiers
- 📂 Gestion de dossiers et arborescence
- 🔄 Versioning et historique des fichiers
- 🔗 Partage de liens publics avec expiration et mot de passe
- 🗑️ Corbeille et restauration
- 📊 Statistiques d’utilisation
- 🌍 Stockage hybride local + cloud

---

## 🏗️ Architecture hybride

### Vue d’ensemble

```
Frontend (Vercel)
  └─ HTTPS/WSS
      ┌────────────────────────────────────────────┐
      │      Ingress Hybride (Tailscale / HAProxy) │
      │  Nginx reverse proxy + tunnel sécurisé     │
      └────────────────────────────────────────────┘
                    │
                    ▼
      ┌─────────────────────────────────────────┐
      │  Backend FastAPI / Uvicorn              │
      │  + MySQL Galera / ProxySQL              │
      │  + GlusterFS shared storage              │
      │  + Azure Blob Storage fallback           │
      └─────────────────────────────────────────┘
```

### Composants clés

- `frontend/` : application React + Vite.
- `backend/` : API FastAPI, SQLAlchemy, services de stockage.
- `docker-compose.yml` : environnement local complet.
- `deploy/` : exemples Nginx, HAProxy, service systemd.
- `DOCUMENTATION.md` : guide de déploiement détaillé.

### Mode de déploiement

- `Frontend` sur Vercel pour rapidité et distribution globale.
- `Backend` sur VM/serveur privé avec Tailscale Funnel ou HAProxy.
- `MySQL Galera` et `ProxySQL` pour haute disponibilité et scalabilité.
- `GlusterFS` pour le partage des `UPLOAD_PATH` entre plusieurs instances.
- `Azure Blob Storage` pour la redondance cloud et le fallback lorsque le stockage local n’est pas disponible.

### Stockage hybride

1. Le backend enregistre les métadonnées dans la base MySQL.
2. Les fichiers sont d’abord stockés dans GlusterFS pour un accès local partagé.
3. Si le stockage local chute, une stratégie de fallback vers Azure Blob Storage prend le relais.
4. Les téléchargements et la preview reposent sur des flux HTTP sécurisés via FastAPI.

---

## ⚙️ Installation locale

### Prérequis

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### Démarrage rapide

```bash
git clone https://github.com/MEVENGUE/SUPFile-VB-App.git
cd SUPFile-Vercel-App

# Copier les exemples d'environnement
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env

# Installer les dépendances frontend
cd frontend
npm install

# Installer les dépendances backend
cd ..\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Lancer les services locaux
cd ..
docker-compose up -d

# Exécuter les migrations
cd backend
.venv\Scripts\Activate.ps1
alembic upgrade head
```

### Accès local

- Frontend : `http://localhost:3000`
- Backend : `http://localhost:8000`
- API docs : `http://localhost:8000/docs`

---

## 🚀 Déploiement

### Frontend (Vercel)

1. Connectez le dépôt GitHub à Vercel.
2. Indiquez `frontend` comme répertoire racine.
3. Ajoutez ces variables d’environnement :

```env
VITE_API_URL=https://<PUBLIC_HOST>/api/v1
VITE_WS_URL=wss://<PUBLIC_HOST>/api/v1/ws
```

4. Déployez la branche principale.

### Backend hybride (VM + Tailscale / HAProxy)

1. Déployez votre VM backend et installez Python 3.11.
2. Copiez `backend/.env.example` vers `backend/.env`.
3. Configurez :
   - `DATABASE_URL` connectant ProxySQL à Galera MySQL.
   - `UPLOAD_PATH` sur votre volume GlusterFS.
   - `SECRET_KEY`, `JWT_SECRET_KEY` et les secrets OAuth.
   - `AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_KEY` si Azure Blob est utilisé.
4. Configurez l’ingress :
   - `deploy/nginx-supfile.conf`
   - `deploy/haproxy.cfg.example`
5. Ouvrez l’accès public via Tailscale Funnel ou HAProxy.
6. Activez le service systemd / service manager.
7. Lancez les migrations :

```bash
cd backend
alembic upgrade head
```

### Conseils de production

- Surveillez la réplication Galera et la latence ProxySQL.
- Vérifiez la disponibilité du volume GlusterFS sur tous les nœuds.
- Testez le fallback Azure pour les uploads et téléchargements.
- Utilisez HTTPS et des en-têtes de sécurité stricts.

---

## 🔐 Sécurité et OAuth

- JWT pour l’authentification et la gestion des sessions.
- OAuth2 pour Google, GitHub et Microsoft.
- Infrastructure isolée via Tailscale et reverse proxy.
- Variables sensibles conservées dans `.env`.

---

## 📚 Documentation

- `DOCUMENTATION.md` : guide d’installation complet, architecture, API et sécurité.
- `deploy/` : exemples de configuration pour Nginx, HAProxy et systemd.
- `railway.json` : exemple de configuration de déploiement.

---

## 🧰 Technologies

### Frontend
- React 18
- TypeScript
- Vite
- Axios
- React Router

### Backend
- FastAPI
- Python 3.11
- SQLAlchemy
- Alembic
- MySQL / Galera
- Azure Blob Storage


---

## 👥 Contributeurs

- **MEVENGUE Franck** - Développeur principal
- **Nadia Loukdache** - Co-développeuse
- **Ayman El-Karroussi** - Co-développeur

---

## 🤝 Contribuer

1. Forkez le dépôt.
2. Créez une branche dédiée.
3. Commitez les changements avec un message clair.
4. Ouvrez une pull request.
5. Documentez les variables d’environnement et les opérations de déploiement.

---

## 📄 Licence

Projet académique SUPINFO.
