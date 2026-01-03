# Instructions pour pousser le code vers GitHub

## Méthode 1 : Utiliser le script PowerShell (Recommandé)

1. Ouvrez PowerShell dans le répertoire racine du projet SUPFile
2. Exécutez le script :
```powershell
.\git-push.ps1
```

## Méthode 2 : Commandes manuelles

Ouvrez PowerShell ou Git Bash dans le répertoire racine du projet et exécutez ces commandes dans l'ordre :

```bash
# 1. Initialiser Git (si pas déjà fait)
git init

# 2. Ajouter tous les fichiers
git add .

# 3. Créer le commit initial
git commit -m "first commit"

# 4. Renommer la branche en main
git branch -M main

# 5. Ajouter le remote GitHub
git remote add origin https://github.com/MEVENGUE/SUPFile-Vercel-App.git

# Si le remote existe déjà, utilisez :
# git remote set-url origin https://github.com/MEVENGUE/SUPFile-Vercel-App.git

# 6. Pousser vers GitHub
git push -u origin main
```

## Notes importantes

- **Authentification GitHub** : Vous devrez peut-être vous authentifier avec GitHub. Options :
  - Utiliser un Personal Access Token (PAT)
  - Utiliser GitHub CLI (`gh auth login`)
  - Utiliser les credentials Windows

- **Si vous avez déjà un dépôt Git** : 
  - Vérifiez d'abord avec `git remote -v`
  - Si un remote existe, utilisez `git remote set-url origin <url>` au lieu de `git remote add`

- **Si le push échoue** : 
  - Vérifiez que le dépôt GitHub existe et que vous avez les permissions
  - Vérifiez votre authentification GitHub

## Après le push

Une fois le code poussé, vous pouvez :
1. Configurer Vercel pour le frontend (voir DEPLOYMENT.md)
2. Configurer Railway pour le backend (voir DEPLOYMENT.md)

