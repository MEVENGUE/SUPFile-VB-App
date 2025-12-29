# SUPFile - Secure Cloud File Storage System

> **Projet académique SUPINFO** - Système de stockage de fichiers cloud sécurisé (type Dropbox)  
> Déployé sur **Microsoft Azure** avec architecture multi-régions

---

## 📋 Vue d'ensemble

SUPFile est une application web de stockage de fichiers cloud sécurisée permettant aux utilisateurs de :
- 📤 Téléverser des fichiers de manière sécurisée
- 📥 Télécharger leurs fichiers
- 🔐 S'authentifier via JWT
- 📊 Visualiser leurs métadonnées de fichiers
- 🌍 Bénéficier d'une haute disponibilité multi-régions

---

## 🏗️ Architecture Azure Multi-Régions

### Régions déployées

- **DC1 (Actif)** : New York → **Azure East US**
- **DC2 (Actif)** : Paris → **Azure France Central**
- **DC3 (Backup/PRA)** : Toronto → **Azure Canada Central**

### Services Azure utilisés

- **Frontend/API** : Azure App Service (ou AKS) avec Nginx
- **Base de données** : Azure Database for PostgreSQL
  - Primary : East US
  - Read Replica : France Central
  - Backups : Canada Central
- **Stockage** : Azure Blob Storage (geo-réplication activée)
- **Réseau** : Azure Front Door (distribution globale)
- **Sécurité** : Azure NSG, Firewall, HTTPS partout
- **Monitoring** : Azure Monitor, Application Insights
- **Backup/PRA** : Azure Backup Vault (Canada Central)

Voir [ARCHITECTURE.md](./docs/ARCHITECTURE.md) pour plus de détails.

---

## 🚀 Démarrage rapide

### Prérequis

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Azure CLI (pour le déploiement)

### Installation locale avec Docker

```bash
# Cloner le projet
git clone <repository-url>
cd SUPFile

# Copier les fichiers d'environnement
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Démarrer les services
docker-compose up -d

# L'application sera accessible sur http://localhost:3000
```

### Installation manuelle

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

#### Frontend

```bash
cd frontend
npm install
npm start
```

---

## 📁 Structure du projet

```
SUPFile/
├── backend/                 # API FastAPI
│   ├── app/
│   │   ├── api/            # Routes API
│   │   ├── core/           # Configuration, sécurité
│   │   ├── models/         # Modèles SQLAlchemy
│   │   ├── services/       # Services Azure Blob Storage
│   │   └── utils/          # Utilitaires
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # Application React
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── utils/
│   ├── Dockerfile
│   ├── package.json
│   └── .env.example
├── docker-compose.yml       # Développement local
├── azure/                   # Configurations Azure
│   ├── app-service/
│   ├── aks/
│   └── front-door/
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   └── SECURITY.md
└── README.md
```

---

## 🔐 Sécurité

- ✅ Authentification JWT
- ✅ HTTPS partout (TLS 1.2+)
- ✅ Validation des entrées
- ✅ Contrôle d'accès basé sur les rôles
- ✅ Secrets via variables d'environnement
- ✅ Protection contre les attaques (rate limiting, CORS)

Voir [docs/SECURITY.md](./docs/SECURITY.md) pour plus de détails.

---

## 📊 Plan de Reprise d'Activité (PRA)

- **RPO** : 1 heure (Recovery Point Objective)
- **RTO** : 4 heures (Recovery Time Objective)
- **Backups** : Quotidiennes automatiques vers Canada Central
- **Geo-réplication** : Blob Storage répliqué entre East US et France Central

Voir [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) pour le plan complet.

---

## 🧪 Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

---

## 📚 Documentation

- [Architecture détaillée](./docs/ARCHITECTURE.md)
- [Guide de déploiement Azure](./docs/DEPLOYMENT.md)
- [Sécurité et bonnes pratiques](./docs/SECURITY.md)

---

## 🤝 Contribution

Ce projet est un projet académique SUPINFO. Pour toute question, contactez l'équipe projet.

---

## 📄 Licence

Projet académique - Tous droits réservés

---

## 👥 Auteurs

Équipe SUPFile - SUPINFO 2024

