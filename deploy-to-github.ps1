# Script pour initialiser Git et pousser vers GitHub
# Exécutez ce script depuis le répertoire racine du projet SUPFile

Write-Host "Initialisation du dépôt Git..." -ForegroundColor Green

# Initialiser Git si ce n'est pas déjà fait
if (-not (Test-Path .git)) {
    git init
    Write-Host "Dépôt Git initialisé." -ForegroundColor Green
} else {
    Write-Host "Dépôt Git déjà initialisé." -ForegroundColor Yellow
}

# Ajouter le remote GitHub
$GITHUB_URL = "https://github.com/MEVENGUE/SUPFile-Vercel-App.git"
Write-Host "Configuration du remote GitHub: $GITHUB_URL" -ForegroundColor Green

$remoteExists = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Remote 'origin' existe déjà. Mise à jour..." -ForegroundColor Yellow
    git remote set-url origin $GITHUB_URL
} else {
    git remote add origin $GITHUB_URL
    Write-Host "Remote 'origin' ajouté." -ForegroundColor Green
}

# Ajouter tous les fichiers
Write-Host "Ajout des fichiers..." -ForegroundColor Green
git add .

# Créer le commit initial
Write-Host "Création du commit initial..." -ForegroundColor Green
git commit -m "Initial commit: SUPFile project with Vercel and Railway configuration"

# Pousser vers GitHub
Write-Host "Push vers GitHub..." -ForegroundColor Green
Write-Host "Note: Vous devrez peut-être vous authentifier avec GitHub." -ForegroundColor Yellow
git branch -M main
git push -u origin main

Write-Host "Terminé! Votre code a été poussé vers GitHub." -ForegroundColor Green
Write-Host "URL du dépôt: $GITHUB_URL" -ForegroundColor Cyan

