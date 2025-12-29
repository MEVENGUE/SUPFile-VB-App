#!/bin/bash

# Script de déploiement complet sur Azure
# Usage: ./scripts/azure-deploy.sh [resource-group-name]

set -e

# Configuration
RESOURCE_GROUP="${1:-supfile-rg-eastus}"
LOCATION="${2:-eastus}"
ACR_NAME="${ACR_NAME:-supfileregistry}"
APP_NAME_BACKEND="supfile-backend-${LOCATION}"
APP_NAME_FRONTEND="supfile-frontend-${LOCATION}"

echo "🚀 Déploiement SUPFile sur Azure"
echo "================================="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo ""

# Vérifier Azure CLI
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI n'est pas installé"
    exit 1
fi

# Vérifier la connexion
if ! az account show &> /dev/null; then
    echo "❌ Connectez-vous d'abord: az login"
    exit 1
fi

# Créer Resource Group si nécessaire
if ! az group show --name $RESOURCE_GROUP &> /dev/null; then
    echo "📦 Création du Resource Group..."
    az group create --name $RESOURCE_GROUP --location $LOCATION
fi

# Créer App Service Plan
echo "📋 Création de l'App Service Plan..."
az appservice plan create \
    --name "supfile-plan-${LOCATION}" \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --is-linux \
    --sku B1 \
    --output none

# Créer App Service Backend
echo "🔧 Création de l'App Service Backend..."
az webapp create \
    --resource-group $RESOURCE_GROUP \
    --plan "supfile-plan-${LOCATION}" \
    --name $APP_NAME_BACKEND \
    --deployment-container-image-name "${ACR_NAME}.azurecr.io/supfile-backend:latest" \
    --output none

# Configurer les variables d'environnement (à personnaliser)
echo "⚙️  Configuration des variables d'environnement..."
echo "⚠️  ATTENTION: Vous devez configurer ces variables avec vos valeurs réelles!"

read -p "Database URL (PostgreSQL): " DATABASE_URL
read -p "Secret Key (min 32 chars): " SECRET_KEY
read -p "JWT Secret Key (min 32 chars): " JWT_SECRET_KEY
read -p "Azure Storage Account Name: " STORAGE_ACCOUNT
read -p "Azure Storage Account Key: " STORAGE_KEY

az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME_BACKEND \
    --settings \
        DATABASE_URL="$DATABASE_URL" \
        SECRET_KEY="$SECRET_KEY" \
        JWT_SECRET_KEY="$JWT_SECRET_KEY" \
        AZURE_STORAGE_ACCOUNT_NAME="$STORAGE_ACCOUNT" \
        AZURE_STORAGE_ACCOUNT_KEY="$STORAGE_KEY" \
        AZURE_STORAGE_CONTAINER_NAME="supfile-files" \
        CORS_ORIGINS="https://${APP_NAME_FRONTEND}.azurewebsites.net" \
        DEBUG="False" \
    --output none

# Configurer ACR authentication
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)
az webapp config container set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME_BACKEND \
    --docker-custom-image-name "${ACR_NAME}.azurecr.io/supfile-backend:latest" \
    --docker-registry-server-url "https://${ACR_NAME}.azurecr.io" \
    --docker-registry-server-user $ACR_NAME \
    --docker-registry-server-password "$ACR_PASSWORD" \
    --output none

# Créer App Service Frontend
echo "🎨 Création de l'App Service Frontend..."
az webapp create \
    --resource-group $RESOURCE_GROUP \
    --plan "supfile-plan-${LOCATION}" \
    --name $APP_NAME_FRONTEND \
    --deployment-container-image-name "${ACR_NAME}.azurecr.io/supfile-frontend:latest" \
    --output none

az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME_FRONTEND \
    --settings \
        VITE_API_URL="https://${APP_NAME_BACKEND}.azurewebsites.net/api/v1" \
    --output none

az webapp config container set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME_FRONTEND \
    --docker-custom-image-name "${ACR_NAME}.azurecr.io/supfile-frontend:latest" \
    --docker-registry-server-url "https://${ACR_NAME}.azurecr.io" \
    --docker-registry-server-user $ACR_NAME \
    --docker-registry-server-password "$ACR_PASSWORD" \
    --output none

echo ""
echo "✅ Déploiement terminé!"
echo ""
echo "🌐 URLs:"
echo "Backend:  https://${APP_NAME_BACKEND}.azurewebsites.net"
echo "Frontend: https://${APP_NAME_FRONTEND}.azurewebsites.net"
echo ""
echo "📋 Prochaines étapes:"
echo "1. Vérifier les logs: az webapp log tail --name $APP_NAME_BACKEND --resource-group $RESOURCE_GROUP"
echo "2. Tester: curl https://${APP_NAME_BACKEND}.azurewebsites.net/health"

