# Azure Deployment Configuration

Ce dossier contient les configurations pour déployer SUPFile sur Microsoft Azure avec une architecture multi-régions.

## Structure

```
azure/
├── app-service/          # Configurations Azure App Service
├── aks/                  # Configurations Azure Kubernetes Service
├── front-door/           # Configuration Azure Front Door
└── README.md
```

## Architecture Multi-Régions

- **DC1 (Actif)** : East US (New York)
- **DC2 (Actif)** : France Central (Paris)
- **DC3 (Backup/PRA)** : Canada Central (Toronto)

## Déploiement

### Option 1: Azure App Service (Recommandé pour débuter)

```bash
# Déployer le backend
az deployment group create \
  --resource-group supfile-rg \
  --template-file azure/app-service/backend-webapp.bicep \
  --parameters appServiceName=supfile-backend-api location=eastus

# Déployer le frontend
az deployment group create \
  --resource-group supfile-rg \
  --template-file azure/app-service/frontend-webapp.bicep \
  --parameters appServiceName=supfile-frontend location=eastus
```

### Option 2: Azure Kubernetes Service (AKS)

```bash
# Créer le cluster AKS
az deployment group create \
  --resource-group supfile-rg \
  --template-file azure/aks/aks-cluster.bicep \
  --parameters clusterName=supfile-aks location=eastus

# Appliquer les déploiements
kubectl apply -f azure/aks/backend-deployment.yaml
kubectl apply -f azure/aks/frontend-deployment.yaml
```

### Option 3: Azure Front Door (Multi-régions)

```bash
az deployment group create \
  --resource-group supfile-rg \
  --template-file azure/front-door/front-door.bicep \
  --parameters \
    frontDoorName=supfile-frontdoor \
    backendEastUsUrl=https://supfile-backend-eastus.azurewebsites.net \
    backendFranceCentralUrl=https://supfile-backend-francecentral.azurewebsites.net \
    frontendEastUsUrl=https://supfile-frontend-eastus.azurewebsites.net \
    frontendFranceCentralUrl=https://supfile-frontend-francecentral.azurewebsites.net
```

## Services Azure Requis

1. **Azure Database for PostgreSQL**
   - Primary: East US
   - Read Replica: France Central
   - Backups: Canada Central

2. **Azure Blob Storage**
   - Geo-replication activée
   - Accès privé uniquement

3. **Azure Key Vault**
   - Stockage des secrets (tokens, clés)

4. **Azure Monitor**
   - Logs et métriques
   - Alertes

5. **Azure Backup Vault**
   - Canada Central
   - Backups quotidiens

Voir [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) pour les instructions complètes.

