# 🚀 Guide de démarrage rapide SUPFile

Guide étape par étape pour déployer SUPFile sur Azure.

## ⚡ Démarrage rapide (5 minutes)

### 1. Prérequis

- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) installé
- [Docker](https://www.docker.com/get-started) installé
- Compte Azure avec abonnement actif

### 2. Connexion à Azure

```bash
# Se connecter
az login

# Vérifier votre compte
az account show
```

### 3. Exécuter le script de setup

**Windows (PowerShell):**
```powershell
.\scripts\azure-setup.ps1
```

**Linux/macOS:**
```bash
chmod +x scripts/azure-setup.sh
./scripts/azure-setup.sh
```

### 4. Suivre le guide complet

Consultez **[scripts/azure-quickstart.md](scripts/azure-quickstart.md)** pour les instructions détaillées.

## 📋 Checklist de déploiement

- [ ] Azure CLI installé et connecté
- [ ] Resource Groups créés (3 régions)
- [ ] Azure Container Registry (ACR) créé
- [ ] Images Docker buildées et pushées
- [ ] PostgreSQL Database créée
- [ ] Azure Blob Storage créé
- [ ] Azure Key Vault créé (pour secrets)
- [ ] App Services déployés
- [ ] Variables d'environnement configurées
- [ ] Tests de fonctionnement

## 🔍 Vérifier votre configuration

**Windows:**
```powershell
.\scripts\check-azure-setup.ps1
```

**Linux/macOS:**
```bash
./scripts/check-azure-setup.sh
```

## 📚 Documentation complète

- **[scripts/azure-quickstart.md](scripts/azure-quickstart.md)** - Guide détaillé étape par étape
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Guide de déploiement complet
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Architecture détaillée
- **[docs/SECURITY.md](docs/SECURITY.md)** - Sécurité et bonnes pratiques

## 🆘 Besoin d'aide?

1. Vérifiez les logs: `az webapp log tail --name supfile-backend-eastus --resource-group supfile-rg-eastus`
2. Consultez la documentation dans `docs/`
3. Vérifiez votre configuration avec les scripts de vérification

## ⚠️ Important

**Ne partagez JAMAIS vos credentials Azure!**
- Les secrets doivent être dans Azure Key Vault
- Utilisez Managed Identity quand possible
- Ne commitez jamais de fichiers `.env` avec des secrets

---

**Bon déploiement! 🎉**

