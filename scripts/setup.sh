#!/bin/bash

# Script de configuration initiale pour SUPFile
# Usage: ./scripts/setup.sh

set -e

echo "🚀 Configuration de SUPFile..."

# Vérifier les prérequis
command -v docker >/dev/null 2>&1 || { echo "❌ Docker n'est pas installé"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose n'est pas installé"; exit 1; }

# Créer les fichiers .env si ils n'existent pas
if [ ! -f backend/.env ]; then
    echo "📝 Création de backend/.env..."
    cp backend/.env.example backend/.env
    echo "⚠️  N'oubliez pas de configurer backend/.env avec vos valeurs Azure!"
fi

if [ ! -f frontend/.env ]; then
    echo "📝 Création de frontend/.env..."
    cp frontend/.env.example frontend/.env
fi

echo "✅ Configuration terminée!"
echo ""
echo "Prochaines étapes:"
echo "1. Configurez backend/.env avec vos credentials Azure"
echo "2. Lancez: docker-compose up -d"
echo "3. Accédez à: http://localhost:3000"

