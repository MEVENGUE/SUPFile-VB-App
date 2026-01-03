# Script pour pousser le code vers GitHub
# Exécutez ce script depuis le répertoire racine du projet

# Obtenir le répertoire du script
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Répertoire de travail: $(Get-Location)" -ForegroundColor Cyan

# Initialiser Git
Write-Host "`n1. Initialisation de Git..." -ForegroundColor Green
if (-not (Test-Path .git)) {
    git init
} else {
    Write-Host "   Git déjà initialisé" -ForegroundColor Yellow
}

# Ajouter tous les fichiers
Write-Host "`n2. Ajout des fichiers..." -ForegroundColor Green
git add .

# Créer le commit
Write-Host "`n3. Création du commit..." -ForegroundColor Green
git commit -m "first commit"

# Renommer la branche en main
Write-Host "`n4. Configuration de la branche main..." -ForegroundColor Green
git branch -M main

# Ajouter le remote (ou le mettre à jour s'il existe)
Write-Host "`n5. Configuration du remote GitHub..." -ForegroundColor Green
$remoteUrl = "https://github.com/MEVENGUE/SUPFile-Vercel-App.git"
$remoteExists = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   Remote 'origin' existe déjà. Mise à jour..." -ForegroundColor Yellow
    git remote set-url origin $remoteUrl
} else {
    git remote add origin $remoteUrl
    Write-Host "   Remote 'origin' ajouté" -ForegroundColor Green
}

# Pousser vers GitHub
Write-Host "`n6. Push vers GitHub..." -ForegroundColor Green
Write-Host "   Note: Vous devrez peut-être vous authentifier." -ForegroundColor Yellow
git push -u origin main

Write-Host "`n✅ Terminé! Code poussé vers GitHub." -ForegroundColor Green
Write-Host "   URL: $remoteUrl" -ForegroundColor Cyan

