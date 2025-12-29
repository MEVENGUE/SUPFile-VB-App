# Guide de démarrage rapide Azure

Ce guide vous accompagne étape par étape pour déployer SUPFile sur Azure.

## Prérequis

1. **Azure CLI installé**
   ```bash
   # Windows (PowerShell)
   winget install -e --id Microsoft.AzureCLI

   # macOS
   brew install azure-cli

   # Linux
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   ```

2. **Docker installé** (pour builder les images)

3. **Compte Azure** avec abonnement actif

## Étape 1: Connexion à Azure

```bash
# Se connecter à Azure
az login

# Vérifier votre compte
az account show

# Lister vos abonnements
az account list --output table

# Sélectionner un abonnement si nécessaire
az account set --subscription "VOTRE_SUBSCRIPTION_ID"
```

## Étape 2: Créer les Resource Groups

```bash
# East US (New York)
az group create --name supfile-rg-eastus --location eastus

# France Central (Paris)
az group create --name supfile-rg-francecentral --location francecentral

# Canada Central (Toronto) - Pour backups
az group create --name supfile-rg-canadacentral --location canadacentral
```

## Étape 3: Créer Azure Container Registry (ACR)

```bash
# Créer ACR
az acr create \
  --resource-group supfile-rg-eastus \
  --name supfileregistry \
  --sku Basic \
  --admin-enabled true

# Se connecter à ACR
az acr login --name supfileregistry

# Récupérer les credentials
az acr credential show --name supfileregistry
```

## Étape 4: Build et Push des images Docker

```bash
# Backend
cd backend
docker build -t supfileregistry.azurecr.io/supfile-backend:latest .
docker push supfileregistry.azurecr.io/supfile-backend:latest

# Frontend
cd ../frontend
docker build -t supfileregistry.azurecr.io/supfile-frontend:latest .
docker push supfileregistry.azurecr.io/supfile-frontend:latest
```

## Étape 5: Créer PostgreSQL Database

```bash
# Créer le serveur PostgreSQL (Primary - East US)
az postgres flexible-server create \
  --resource-group supfile-rg-eastus \
  --name supfile-db-primary \
  --location eastus \
  --admin-user supfileadmin \
  --admin-password "VOTRE_MOT_DE_PASSE_FORT" \
  --sku-name Standard_B2s \
  --tier Burstable \
  --storage-size 100 \
  --version 15

# Créer la base de données
az postgres flexible-server db create \
  --resource-group supfile-rg-eastus \
  --server-name supfile-db-primary \
  --database-name supfile

# Autoriser Azure services
az postgres flexible-server firewall-rule create \
  --resource-group supfile-rg-eastus \
  --name supfile-db-primary \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

**Note**: Récupérez la connection string:
```bash
# Format: postgresql://supfileadmin:VOTRE_MOT_DE_PASSE@supfile-db-primary.postgres.database.azure.com:5432/supfile?sslmode=require
```

## Étape 6: Créer Azure Blob Storage

```bash
# Créer Storage Account
az storage account create \
  --resource-group supfile-rg-eastus \
  --name supfilestorage \
  --location eastus \
  --sku Standard_GRS \
  --kind StorageV2 \
  --access-tier Hot

# Créer le container
az storage container create \
  --account-name supfilestorage \
  --name supfile-files \
  --auth-mode login \
  --public-access off

# Récupérer les clés d'accès
az storage account keys list \
  --resource-group supfile-rg-eastus \
  --account-name supfilestorage
```

## Étape 7: Créer Azure Key Vault (pour les secrets)

```bash
# Créer Key Vault
az keyvault create \
  --name supfile-keyvault \
  --resource-group supfile-rg-eastus \
  --location eastus

# Stocker les secrets
az keyvault secret set \
  --vault-name supfile-keyvault \
  --name database-password \
  --value "VOTRE_MOT_DE_PASSE_DB"

az keyvault secret set \
  --vault-name supfile-keyvault \
  --name jwt-secret \
  --value "VOTRE_JWT_SECRET_MIN_32_CHARS"
```

## Étape 8: Déployer App Services

### Option A: Utiliser le script automatisé

```bash
chmod +x scripts/azure-deploy.sh
./scripts/azure-deploy.sh supfile-rg-eastus eastus
```

### Option B: Déploiement manuel

```bash
# Créer App Service Plan
az appservice plan create \
  --name supfile-plan-eastus \
  --resource-group supfile-rg-eastus \
  --location eastus \
  --is-linux \
  --sku B1

# Créer Backend App Service
az webapp create \
  --resource-group supfile-rg-eastus \
  --plan supfile-plan-eastus \
  --name supfile-backend-eastus \
  --deployment-container-image-name supfileregistry.azurecr.io/supfile-backend:latest

# Configurer les variables d'environnement
az webapp config appsettings set \
  --resource-group supfile-rg-eastus \
  --name supfile-backend-eastus \
  --settings \
    DATABASE_URL="postgresql://supfileadmin:PASSWORD@supfile-db-primary.postgres.database.azure.com:5432/supfile?sslmode=require" \
    SECRET_KEY="VOTRE_SECRET_KEY_32_CHARS_MIN" \
    JWT_SECRET_KEY="VOTRE_JWT_SECRET_32_CHARS_MIN" \
    AZURE_STORAGE_ACCOUNT_NAME="supfilestorage" \
    AZURE_STORAGE_ACCOUNT_KEY="VOTRE_STORAGE_KEY" \
    AZURE_STORAGE_CONTAINER_NAME="supfile-files" \
    CORS_ORIGINS="https://supfile-frontend-eastus.azurewebsites.net" \
    DEBUG="False"

# Configurer ACR authentication
ACR_PASSWORD=$(az acr credential show --name supfileregistry --query passwords[0].value -o tsv)
az webapp config container set \
  --resource-group supfile-rg-eastus \
  --name supfile-backend-eastus \
  --docker-custom-image-name supfileregistry.azurecr.io/supfile-backend:latest \
  --docker-registry-server-url https://supfileregistry.azurecr.io \
  --docker-registry-server-user supfileregistry \
  --docker-registry-server-password "$ACR_PASSWORD"

# Créer Frontend App Service
az webapp create \
  --resource-group supfile-rg-eastus \
  --plan supfile-plan-eastus \
  --name supfile-frontend-eastus \
  --deployment-container-image-name supfileregistry.azurecr.io/supfile-frontend:latest

az webapp config appsettings set \
  --resource-group supfile-rg-eastus \
  --name supfile-frontend-eastus \
  --settings \
    VITE_API_URL="https://supfile-backend-eastus.azurewebsites.net/api/v1"

az webapp config container set \
  --resource-group supfile-rg-eastus \
  --name supfile-frontend-eastus \
  --docker-custom-image-name supfileregistry.azurecr.io/supfile-frontend:latest \
  --docker-registry-server-url https://supfileregistry.azurecr.io \
  --docker-registry-server-user supfileregistry \
  --docker-registry-server-password "$ACR_PASSWORD"
```

## Étape 9: Vérifier le déploiement

```bash
# Tester le backend
curl https://supfile-backend-eastus.azurewebsites.net/health

# Voir les logs
az webapp log tail --name supfile-backend-eastus --resource-group supfile-rg-eastus
```

## Étape 10: (Optionnel) Azure Front Door

Pour le déploiement multi-régions avec Front Door, consultez `docs/DEPLOYMENT.md`.

## Dépannage

### Vérifier les logs

```bash
# Logs en temps réel
az webapp log tail --name supfile-backend-eastus --resource-group supfile-rg-eastus

# Télécharger les logs
az webapp log download --name supfile-backend-eastus --resource-group supfile-rg-eastus
```

### Vérifier les variables d'environnement

```bash
az webapp config appsettings list \
  --name supfile-backend-eastus \
  --resource-group supfile-rg-eastus
```

### Redémarrer l'application

```bash
az webapp restart --name supfile-backend-eastus --resource-group supfile-rg-eastus
```

## Coûts

Consultez `docs/ARCHITECTURE.md` pour une estimation des coûts mensuels.

## Support

Pour plus de détails, consultez:
- `docs/DEPLOYMENT.md` - Guide complet
- `docs/ARCHITECTURE.md` - Architecture détaillée
- `docs/SECURITY.md` - Sécurité

