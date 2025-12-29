#!/bin/bash

# Script de vérification de la configuration Azure
# Usage: ./scripts/check-azure-setup.sh

echo "🔍 Vérification de la configuration Azure..."
echo "============================================"
echo ""

# Vérifier Azure CLI
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI n'est pas installé"
    echo "   Installez-le: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi
echo "✅ Azure CLI installé"

# Vérifier la connexion
if ! az account show &> /dev/null; then
    echo "❌ Non connecté à Azure"
    echo "   Exécutez: az login"
    exit 1
fi

ACCOUNT=$(az account show --query name -o tsv)
SUBSCRIPTION=$(az account show --query id -o tsv)
echo "✅ Connecté à Azure"
echo "   Compte: $ACCOUNT"
echo "   Subscription: $SUBSCRIPTION"
echo ""

# Vérifier Docker
if command -v docker &> /dev/null; then
    echo "✅ Docker installé"
    if docker ps &> /dev/null; then
        echo "✅ Docker fonctionne"
    else
        echo "⚠️  Docker n'est pas démarré"
    fi
else
    echo "⚠️  Docker n'est pas installé"
fi
echo ""

# Vérifier les Resource Groups
echo "📦 Resource Groups:"
for rg in "supfile-rg-eastus" "supfile-rg-francecentral" "supfile-rg-canadacentral"; do
    if az group show --name $rg &> /dev/null; then
        echo "   ✅ $rg existe"
    else
        echo "   ❌ $rg n'existe pas"
    fi
done
echo ""

# Vérifier ACR
echo "🐳 Azure Container Registry:"
if az acr show --name supfileregistry &> /dev/null; then
    echo "   ✅ supfileregistry existe"
    LOGIN_SERVER=$(az acr show --name supfileregistry --query loginServer -o tsv)
    echo "   Login Server: $LOGIN_SERVER"
else
    echo "   ❌ supfileregistry n'existe pas"
fi
echo ""

# Vérifier PostgreSQL
echo "🗄️  PostgreSQL:"
if az postgres flexible-server show --name supfile-db-primary --resource-group supfile-rg-eastus &> /dev/null; then
    echo "   ✅ supfile-db-primary existe"
else
    echo "   ❌ supfile-db-primary n'existe pas"
fi
echo ""

# Vérifier Storage Account
echo "💾 Storage Account:"
if az storage account show --name supfilestorage --resource-group supfile-rg-eastus &> /dev/null; then
    echo "   ✅ supfilestorage existe"
else
    echo "   ❌ supfilestorage n'existe pas"
fi
echo ""

# Vérifier App Services
echo "🌐 App Services:"
for app in "supfile-backend-eastus" "supfile-frontend-eastus"; do
    if az webapp show --name $app --resource-group supfile-rg-eastus &> /dev/null; then
        echo "   ✅ $app existe"
        URL=$(az webapp show --name $app --resource-group supfile-rg-eastus --query defaultHostName -o tsv)
        echo "      URL: https://$URL"
    else
        echo "   ❌ $app n'existe pas"
    fi
done
echo ""

echo "✅ Vérification terminée!"
echo ""
echo "Pour déployer, consultez: scripts/azure-quickstart.md"

