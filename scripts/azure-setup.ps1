# Script d'aide au déploiement Azure pour SUPFile (PowerShell)
# Usage: .\scripts\azure-setup.ps1

Write-Host "🔐 Configuration Azure pour SUPFile" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier Azure CLI
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Azure CLI n'est pas installé" -ForegroundColor Red
    Write-Host "Installez-le depuis: https://docs.microsoft.com/cli/azure/install-azure-cli" -ForegroundColor Yellow
    exit 1
}

# Vérifier la connexion
Write-Host "📋 Vérification de la connexion Azure..." -ForegroundColor Yellow
try {
    $accountOutput = az account show 2>&1
    if ($LASTEXITCODE -ne 0 -or -not $accountOutput) {
        Write-Host "⚠️  Vous n'êtes pas connecté à Azure" -ForegroundColor Yellow
        Write-Host "Exécutez: az login" -ForegroundColor Yellow
        exit 1
    }
    $account = $accountOutput | ConvertFrom-Json
} catch {
    Write-Host "⚠️  Vous n'êtes pas connecté à Azure" -ForegroundColor Yellow
    Write-Host "Exécutez: az login" -ForegroundColor Yellow
    exit 1
}

$accountName = $account.name
$subscriptionId = $account.id

Write-Host "✅ Connecté à: $accountName" -ForegroundColor Green
Write-Host "   Subscription ID: $subscriptionId" -ForegroundColor Gray
Write-Host ""

# Demander confirmation
$confirmation = Read-Host "Voulez-vous continuer avec ce compte? (y/n)"
if ($confirmation -ne "y" -and $confirmation -ne "Y") {
    Write-Host "Annulé." -ForegroundColor Yellow
    exit 0
}

# Variables
$resourceGroupEastUs = "supfile-rg-eastus"
$resourceGroupFranceCentral = "supfile-rg-francecentral"
$resourceGroupCanada = "supfile-rg-canadacentral"
$locationEastUs = "eastus"
$locationFrance = "francecentral"
$locationCanada = "canadacentral"

Write-Host ""
Write-Host "📦 Étape 1: Création des Resource Groups..." -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

# Créer Resource Groups
az group create --name $resourceGroupEastUs --location $locationEastUs
az group create --name $resourceGroupFranceCentral --location $locationFrance
az group create --name $resourceGroupCanada --location $locationCanada

Write-Host "✅ Resource Groups créés" -ForegroundColor Green
Write-Host ""

Write-Host "📝 Étape 2: Configuration requise..." -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Vous devrez configurer manuellement:" -ForegroundColor Yellow
Write-Host "1. Azure Container Registry (ACR)"
Write-Host "2. PostgreSQL Database"
Write-Host "3. Azure Blob Storage"
Write-Host "4. Azure Key Vault (pour les secrets)"
Write-Host ""
Write-Host "Consultez scripts/azure-quickstart.md pour les instructions détaillées" -ForegroundColor Cyan
Write-Host ""

# Afficher les commandes suivantes
Write-Host "📋 Commandes suivantes à exécuter:" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "# 1. Créer Azure Container Registry" -ForegroundColor Gray
Write-Host "az acr create --resource-group $resourceGroupEastUs --name supfileregistry --sku Basic --admin-enabled true" -ForegroundColor White
Write-Host ""
Write-Host "# 2. Se connecter à ACR" -ForegroundColor Gray
Write-Host "az acr login --name supfileregistry" -ForegroundColor White
Write-Host ""
Write-Host "# 3. Build et push des images Docker" -ForegroundColor Gray
Write-Host "cd backend; docker build -t supfileregistry.azurecr.io/supfile-backend:latest ." -ForegroundColor White
Write-Host "docker push supfileregistry.azurecr.io/supfile-backend:latest" -ForegroundColor White
Write-Host "cd ..\frontend; docker build -t supfileregistry.azurecr.io/supfile-frontend:latest ." -ForegroundColor White
Write-Host "docker push supfileregistry.azurecr.io/supfile-frontend:latest" -ForegroundColor White
Write-Host ""

Write-Host "✅ Script terminé!" -ForegroundColor Green
Write-Host ""
Write-Host "Consultez scripts/azure-quickstart.md pour la suite" -ForegroundColor Cyan

