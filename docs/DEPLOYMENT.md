# Guide de Déploiement SUPFile sur Azure

Ce guide détaille les étapes pour déployer SUPFile sur Microsoft Azure avec une architecture multi-régions.

## Prérequis

- Azure CLI installé et configuré
- Docker installé
- Accès à un compte Azure avec permissions suffisantes
- Azure Container Registry (ACR) ou Docker Hub pour stocker les images

## Architecture de déploiement

- **DC1** : East US (New York) - Actif
- **DC2** : France Central (Paris) - Actif
- **DC3** : Canada Central (Toronto) - Backup/PRA

## Étape 1 : Préparation de l'environnement Azure

### 1.1 Créer les Resource Groups

```bash
# Resource Group pour East US
az group create --name supfile-rg-eastus --location eastus

# Resource Group pour France Central
az group create --name supfile-rg-francecentral --location francecentral

# Resource Group pour Canada Central (Backups)
az group create --name supfile-rg-canadacentral --location canadacentral
```

### 1.2 Créer Azure Container Registry (ACR)

```bash
az acr create \
  --resource-group supfile-rg-eastus \
  --name supfileregistry \
  --sku Basic \
  --admin-enabled true
```

## Étape 2 : Base de données PostgreSQL

### 2.1 Créer PostgreSQL Primary (East US)

```bash
az postgres flexible-server create \
  --resource-group supfile-rg-eastus \
  --name supfile-db-primary \
  --location eastus \
  --admin-user supfileadmin \
  --admin-password <strong-password> \
  --sku-name Standard_B2s \
  --tier Burstable \
  --storage-size 100 \
  --version 15 \
  --public-access 0.0.0.0
```

### 2.2 Créer Read Replica (France Central)

```bash
az postgres flexible-server replica create \
  --resource-group supfile-rg-francecentral \
  --name supfile-db-replica \
  --replica-name supfile-db-primary \
  --location francecentral
```

### 2.3 Créer la base de données

```bash
az postgres flexible-server db create \
  --resource-group supfile-rg-eastus \
  --server-name supfile-db-primary \
  --database-name supfile
```

### 2.4 Configurer les règles de pare-feu

```bash
# Autoriser Azure services
az postgres flexible-server firewall-rule create \
  --resource-group supfile-rg-eastus \
  --name supfile-db-primary \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

## Étape 3 : Azure Blob Storage

### 3.1 Créer Storage Account (East US)

```bash
az storage account create \
  --resource-group supfile-rg-eastus \
  --name supfilestorage \
  --location eastus \
  --sku Standard_GRS \
  --kind StorageV2 \
  --access-tier Hot
```

### 3.2 Activer Geo-Replication

La géo-réplication est automatique avec `Standard_GRS`.

### 3.3 Créer le container

```bash
az storage container create \
  --account-name supfilestorage \
  --name supfile-files \
  --auth-mode login \
  --public-access off
```

### 3.4 Récupérer les clés d'accès

```bash
az storage account keys list \
  --resource-group supfile-rg-eastus \
  --account-name supfilestorage
```

## Étape 4 : Build et Push des images Docker

### 4.1 Se connecter à ACR

```bash
az acr login --name supfileregistry
```

### 4.2 Build et push Backend

```bash
cd backend
docker build -t supfileregistry.azurecr.io/supfile-backend:latest .
docker push supfileregistry.azurecr.io/supfile-backend:latest
```

### 4.3 Build et push Frontend

```bash
cd frontend
docker build -t supfileregistry.azurecr.io/supfile-frontend:latest .
docker push supfileregistry.azurecr.io/supfile-frontend:latest
```

## Étape 5 : Déploiement App Service

### 5.1 Créer App Service Plan (East US)

```bash
az appservice plan create \
  --name supfile-plan-eastus \
  --resource-group supfile-rg-eastus \
  --location eastus \
  --is-linux \
  --sku B1
```

### 5.2 Créer App Service Backend (East US)

```bash
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
    DATABASE_URL="postgresql://supfileadmin:<password>@supfile-db-primary.postgres.database.azure.com:5432/supfile?sslmode=require" \
    SECRET_KEY="<generate-strong-secret>" \
    JWT_SECRET_KEY="<generate-strong-secret>" \
    AZURE_STORAGE_ACCOUNT_NAME="supfilestorage" \
    AZURE_STORAGE_ACCOUNT_KEY="<storage-key>" \
    AZURE_STORAGE_CONTAINER_NAME="supfile-files" \
    CORS_ORIGINS="https://supfile-frontend-eastus.azurewebsites.net" \
    DEBUG="False"

# Configurer l'authentification ACR
az webapp config container set \
  --resource-group supfile-rg-eastus \
  --name supfile-backend-eastus \
  --docker-custom-image-name supfileregistry.azurecr.io/supfile-backend:latest \
  --docker-registry-server-url https://supfileregistry.azurecr.io \
  --docker-registry-server-user supfileregistry \
  --docker-registry-server-password <acr-password>
```

### 5.3 Répéter pour France Central

```bash
# App Service Plan
az appservice plan create \
  --name supfile-plan-francecentral \
  --resource-group supfile-rg-francecentral \
  --location francecentral \
  --is-linux \
  --sku B1

# Backend
az webapp create \
  --resource-group supfile-rg-francecentral \
  --plan supfile-plan-francecentral \
  --name supfile-backend-francecentral \
  --deployment-container-image-name supfileregistry.azurecr.io/supfile-backend:latest

# Configurer (utiliser DATABASE_URL vers le replica)
az webapp config appsettings set \
  --resource-group supfile-rg-francecentral \
  --name supfile-backend-francecentral \
  --settings \
    DATABASE_URL="postgresql://supfileadmin:<password>@supfile-db-replica.postgres.database.azure.com:5432/supfile?sslmode=require" \
    # ... autres variables similaires
```

### 5.4 Déployer Frontend (East US et France Central)

```bash
# East US
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
```

## Étape 6 : Azure Front Door

### 6.1 Créer Front Door Profile

```bash
az deployment group create \
  --resource-group supfile-rg-eastus \
  --template-file azure/front-door/front-door.bicep \
  --parameters \
    frontDoorName=supfile-frontdoor \
    backendEastUsUrl=supfile-backend-eastus.azurewebsites.net \
    backendFranceCentralUrl=supfile-backend-francecentral.azurewebsites.net \
    frontendEastUsUrl=supfile-frontend-eastus.azurewebsites.net \
    frontendFranceCentralUrl=supfile-frontend-francecentral.azurewebsites.net
```

### 6.2 Configurer le domaine personnalisé (optionnel)

```bash
az network front-door frontend-endpoint custom-domain https-enable \
  --resource-group supfile-rg-eastus \
  --front-door-name supfile-frontdoor \
  --name supfile.com \
  --certificate-type FrontDoorManagedCertificate
```

## Étape 7 : Azure Backup Vault (Canada Central)

### 7.1 Créer Backup Vault

```bash
az backup vault create \
  --resource-group supfile-rg-canadacentral \
  --name supfile-backup-vault \
  --location canadacentral
```

### 7.2 Configurer les backups PostgreSQL

```bash
# Activer les backups automatiques sur PostgreSQL
az postgres flexible-server backup create \
  --resource-group supfile-rg-eastus \
  --server-name supfile-db-primary \
  --backup-name daily-backup
```

## Étape 8 : Monitoring

### 8.1 Créer Application Insights

```bash
az monitor app-insights component create \
  --app supfile-insights \
  --location eastus \
  --resource-group supfile-rg-eastus \
  --application-type web
```

### 8.2 Configurer les alertes

```bash
az monitor metrics alert create \
  --name "High CPU Alert" \
  --resource-group supfile-rg-eastus \
  --scopes /subscriptions/<sub-id>/resourceGroups/supfile-rg-eastus/providers/Microsoft.Web/sites/supfile-backend-eastus \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --evaluation-frequency 1m
```

## Étape 9 : Sécurité

### 9.1 Créer Azure Key Vault

```bash
az keyvault create \
  --name supfile-keyvault \
  --resource-group supfile-rg-eastus \
  --location eastus
```

### 9.2 Stocker les secrets

```bash
az keyvault secret set \
  --vault-name supfile-keyvault \
  --name database-password \
  --value <password>

az keyvault secret set \
  --vault-name supfile-keyvault \
  --name jwt-secret \
  --value <jwt-secret>
```

### 9.3 Configurer Managed Identity

```bash
# Activer Managed Identity sur App Service
az webapp identity assign \
  --resource-group supfile-rg-eastus \
  --name supfile-backend-eastus

# Donner accès au Key Vault
az keyvault set-policy \
  --name supfile-keyvault \
  --object-id <managed-identity-object-id> \
  --secret-permissions get list
```

## Étape 10 : Tests de déploiement

### 10.1 Vérifier la santé des services

```bash
# Backend East US
curl https://supfile-backend-eastus.azurewebsites.net/health

# Backend France Central
curl https://supfile-backend-francecentral.azurewebsites.net/health

# Front Door
curl https://supfile-frontdoor.azurefd.net/health
```

### 10.2 Tester l'upload de fichier

```bash
# Obtenir un token
TOKEN=$(curl -X POST https://supfile-frontdoor.azurefd.net/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test&password=test" | jq -r '.access_token')

# Upload un fichier
curl -X POST https://supfile-frontdoor.azurefd.net/api/v1/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.txt"
```

## Maintenance

### Mise à jour des images

```bash
# Rebuild et push
docker build -t supfileregistry.azurecr.io/supfile-backend:v2 .
docker push supfileregistry.azurecr.io/supfile-backend:v2

# Redéployer
az webapp config container set \
  --resource-group supfile-rg-eastus \
  --name supfile-backend-eastus \
  --docker-custom-image-name supfileregistry.azurecr.io/supfile-backend:v2
```

### Scaling

```bash
# Scale up App Service Plan
az appservice plan update \
  --name supfile-plan-eastus \
  --resource-group supfile-rg-eastus \
  --sku P1V2

# Scale out (augmenter le nombre d'instances)
az appservice plan update \
  --name supfile-plan-eastus \
  --resource-group supfile-rg-eastus \
  --number-of-workers 3
```

## Dépannage

### Logs

```bash
# Logs App Service
az webapp log tail \
  --resource-group supfile-rg-eastus \
  --name supfile-backend-eastus

# Logs Application Insights
az monitor app-insights query \
  --app supfile-insights \
  --analytics-query "requests | take 10"
```

### Diagnostic

```bash
# Tester la connexion à la base de données
az postgres flexible-server connect \
  --name supfile-db-primary \
  --admin-user supfileadmin \
  --admin-password <password>
```

## Coûts estimés

Voir [ARCHITECTURE.md](./ARCHITECTURE.md) pour les détails des coûts.

## Support

Pour toute question ou problème, consulter :
- [Documentation Azure](https://docs.microsoft.com/azure)
- [Architecture SUPFile](./ARCHITECTURE.md)
- [Sécurité](./SECURITY.md)

