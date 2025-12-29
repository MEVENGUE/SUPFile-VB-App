#!/bin/bash

# Script d'aide au déploiement Azure pour SUPFile
# Usage: ./scripts/azure-setup.sh

set -e

echo "🔐 Configuration Azure pour SUPFile"
echo "===================================="
echo ""

# Vérifier Azure CLI
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI n'est pas installé"
    echo "Installez-le depuis: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi

# Vérifier la connexion
echo "📋 Vérification de la connexion Azure..."
if ! az account show &> /dev/null; then
    echo "⚠️  Vous n'êtes pas connecté à Azure"
    echo "Exécutez: az login"
    exit 1
fi

ACCOUNT=$(az account show --query name -o tsv)
SUBSCRIPTION=$(az account show --query id -o tsv)

echo "✅ Connecté à: $ACCOUNT"
echo "   Subscription ID: $SUBSCRIPTION"
echo ""

# Demander confirmation
read -p "Voulez-vous continuer avec ce compte? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Annulé."
    exit 1
fi

# Variables
RESOURCE_GROUP_EASTUS="supfile-rg-eastus"
RESOURCE_GROUP_FRANCECENTRAL="supfile-rg-francecentral"
RESOURCE_GROUP_CANADA="supfile-rg-canadacentral"
LOCATION_EASTUS="eastus"
LOCATION_FRANCE="francecentral"
LOCATION_CANADA="canadacentral"

echo ""
echo "📦 Étape 1: Création des Resource Groups..."
echo "==========================================="

# Créer Resource Groups
az group create --name $RESOURCE_GROUP_EASTUS --location $LOCATION_EASTUS
az group create --name $RESOURCE_GROUP_FRANCECENTRAL --location $LOCATION_FRANCE
az group create --name $RESOURCE_GROUP_CANADA --location $LOCATION_CANADA

echo "✅ Resource Groups créés"
echo ""

echo "📝 Étape 2: Configuration requise..."
echo "====================================="
echo ""
echo "Vous devrez configurer manuellement:"
echo "1. Azure Container Registry (ACR)"
echo "2. PostgreSQL Database"
echo "3. Azure Blob Storage"
echo "4. Azure Key Vault (pour les secrets)"
echo ""
echo "Consultez docs/DEPLOYMENT.md pour les instructions détaillées"
echo ""

# Afficher les commandes suivantes
echo "📋 Commandes suivantes à exécuter:"
echo "=================================="
echo ""
echo "# 1. Créer Azure Container Registry"
echo "az acr create --resource-group $RESOURCE_GROUP_EASTUS --name supfileregistry --sku Basic --admin-enabled true"
echo ""
echo "# 2. Se connecter à ACR"
echo "az acr login --name supfileregistry"
echo ""
echo "# 3. Build et push des images Docker"
echo "cd backend && docker build -t supfileregistry.azurecr.io/supfile-backend:latest ."
echo "docker push supfileregistry.azurecr.io/supfile-backend:latest"
echo "cd ../frontend && docker build -t supfileregistry.azurecr.io/supfile-frontend:latest ."
echo "docker push supfileregistry.azurecr.io/supfile-frontend:latest"
echo ""

echo "✅ Script terminé!"
echo ""
echo "Consultez docs/DEPLOYMENT.md pour la suite"

