# Script de vérification de la configuration Azure (PowerShell)
# Usage: .\scripts\check-azure-setup.ps1

Write-Host "🔍 Vérification de la configuration Azure..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier Azure CLI
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Azure CLI n'est pas installé" -ForegroundColor Red
    Write-Host "   Installez-le: https://docs.microsoft.com/cli/azure/install-azure-cli" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Azure CLI installé" -ForegroundColor Green

# Vérifier la connexion
try {
    $accountOutput = az account show 2>&1
    if ($LASTEXITCODE -ne 0 -or -not $accountOutput) {
        Write-Host "❌ Non connecté à Azure" -ForegroundColor Red
        Write-Host "   Exécutez: az login" -ForegroundColor Yellow
        exit 1
    }
    $account = $accountOutput | ConvertFrom-Json
} catch {
    Write-Host "❌ Non connecté à Azure" -ForegroundColor Red
    Write-Host "   Exécutez: az login" -ForegroundColor Yellow
    exit 1
}

$accountName = $account.name
$subscriptionId = $account.id
Write-Host "✅ Connecté à Azure" -ForegroundColor Green
Write-Host "   Compte: $accountName" -ForegroundColor Gray
Write-Host "   Subscription: $subscriptionId" -ForegroundColor Gray
Write-Host ""

# Vérifier Docker
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "✅ Docker installé" -ForegroundColor Green
    try {
        docker ps | Out-Null
        Write-Host "✅ Docker fonctionne" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Docker n'est pas démarré" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Docker n'est pas installé" -ForegroundColor Yellow
}
Write-Host ""

# Vérifier les Resource Groups
Write-Host "📦 Resource Groups:" -ForegroundColor Cyan
$resourceGroups = @("supfile-rg-eastus", "supfile-rg-francecentral", "supfile-rg-canadacentral")
foreach ($rg in $resourceGroups) {
    $exists = az group show --name $rg 2>&1
    if ($LASTEXITCODE -eq 0 -and $exists) {
        Write-Host "   ✅ $rg existe" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $rg n'existe pas" -ForegroundColor Red
    }
}
Write-Host ""

# Vérifier ACR
Write-Host "🐳 Azure Container Registry:" -ForegroundColor Cyan
$acrExists = az acr show --name supfileregistry 2>&1
if ($LASTEXITCODE -eq 0 -and $acrExists) {
    Write-Host "   ✅ supfileregistry existe" -ForegroundColor Green
    $loginServer = az acr show --name supfileregistry --query loginServer -o tsv 2>&1
    if ($LASTEXITCODE -eq 0 -and $loginServer) {
        Write-Host "   Login Server: $loginServer" -ForegroundColor Gray
    }
} else {
    Write-Host "   ❌ supfileregistry n'existe pas" -ForegroundColor Red
}
Write-Host ""

# Vérifier PostgreSQL
Write-Host "🗄️  PostgreSQL:" -ForegroundColor Cyan
$dbExists = az postgres flexible-server show --name supfile-db-primary --resource-group supfile-rg-eastus 2>&1
if ($LASTEXITCODE -eq 0 -and $dbExists) {
    Write-Host "   ✅ supfile-db-primary existe" -ForegroundColor Green
} else {
    Write-Host "   ❌ supfile-db-primary n'existe pas" -ForegroundColor Red
}
Write-Host ""

# Vérifier Storage Account
Write-Host "💾 Storage Account:" -ForegroundColor Cyan
$storageExists = az storage account show --name supfilestorage --resource-group supfile-rg-eastus 2>&1
if ($LASTEXITCODE -eq 0 -and $storageExists) {
    Write-Host "   ✅ supfilestorage existe" -ForegroundColor Green
} else {
    Write-Host "   ❌ supfilestorage n'existe pas" -ForegroundColor Red
}
Write-Host ""

# Vérifier App Services
Write-Host "🌐 App Services:" -ForegroundColor Cyan
$apps = @("supfile-backend-eastus", "supfile-frontend-eastus")
foreach ($app in $apps) {
    $appExists = az webapp show --name $app --resource-group supfile-rg-eastus 2>&1
    if ($LASTEXITCODE -eq 0 -and $appExists) {
        Write-Host "   ✅ $app existe" -ForegroundColor Green
        $url = az webapp show --name $app --resource-group supfile-rg-eastus --query defaultHostName -o tsv 2>&1
        if ($LASTEXITCODE -eq 0 -and $url) {
            Write-Host "      URL: https://$url" -ForegroundColor Gray
        }
    } else {
        Write-Host "   ❌ $app n'existe pas" -ForegroundColor Red
    }
}
Write-Host ""

Write-Host "✅ Vérification terminée!" -ForegroundColor Green
Write-Host ""
Write-Host "Pour déployer, consultez: scripts/azure-quickstart.md" -ForegroundColor Cyan

