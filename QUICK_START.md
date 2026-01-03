# 🚀 Guide Rapide - Déploiement SUPFile

## 📦 Fichiers de configuration créés

✅ **vercel.json** - Configuration Vercel (racine)
✅ **frontend/vercel.json** - Configuration Vercel pour le frontend
✅ **railway.json** - Configuration Railway pour le backend
✅ **backend/Dockerfile** - Mis à jour pour Railway (support de la variable PORT)
✅ **DEPLOYMENT.md** - Guide complet de déploiement
✅ **GITHUB_SETUP.md** - Instructions pour GitHub
✅ **git-push.ps1** - Script PowerShell pour pousser vers GitHub

---

## 🔵 Étape 1 : Pousser le code vers GitHub

### Option A : Script automatique (Recommandé)

1. Ouvrez PowerShell dans le répertoire racine du projet SUPFile
2. Exécutez :
```powershell
.\git-push.ps1
```

### Option B : Commandes manuelles

```bash
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/MEVENGUE/SUPFile-Vercel-App.git
git push -u origin main
```

**Note** : Si le remote existe déjà, utilisez :
```bash
git remote set-url origin https://github.com/MEVENGUE/SUPFile-Vercel-App.git
```

---

## 🟢 Étape 2 : Déployer sur Vercel (Frontend)

1. Allez sur [vercel.com](https://vercel.com) et connectez-vous avec GitHub
2. Cliquez sur **"Add New Project"**
3. Importez le dépôt `SUPFile-Vercel-App`
4. Configurez :
   - **Root Directory** : `frontend`
   - **Build Command** : `npm run build`
   - **Output Directory** : `dist`
5. Ajoutez la variable d'environnement :
   ```
   VITE_API_URL=https://votre-backend-railway.railway.app/api/v1
   ```
   *(Vous obtiendrez l'URL après le déploiement Railway)*
6. Cliquez sur **"Deploy"**

---

## 🟡 Étape 3 : Déployer sur Railway (Backend)

1. Allez sur [railway.app](https://railway.app) et connectez-vous avec GitHub
2. Créez un nouveau projet
3. Ajoutez **PostgreSQL** :
   - Cliquez sur **"+ New"** > **"Database"** > **"Add PostgreSQL"**
4. Déployez le backend :
   - Cliquez sur **"+ New"** > **"GitHub Repo"**
   - Sélectionnez `SUPFile-Vercel-App`
   - Railway détectera automatiquement le Dockerfile dans `backend/`
5. Configurez les variables d'environnement (voir DEPLOYMENT.md pour la liste complète) :
   ```env
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   SECRET_KEY=votre-secret-key-32-caracteres
   JWT_SECRET_KEY=votre-jwt-secret-key-32-caracteres
   AZURE_STORAGE_ACCOUNT_NAME=votre-compte
   AZURE_STORAGE_ACCOUNT_KEY=votre-cle
   AZURE_STORAGE_CONTAINER_NAME=supfile-files
   AZURE_STORAGE_CONNECTION_STRING=votre-connection-string
   CORS_ORIGINS=https://votre-frontend.vercel.app
   PORT=${{PORT}}
   ```
6. Exécutez les migrations :
   - Ouvrez la console Railway
   - Exécutez : `alembic upgrade head`
7. Activez **"Generate Domain"** pour obtenir l'URL publique

---

## 🔄 Étape 4 : Mettre à jour le frontend

1. Retournez sur Vercel
2. Mettez à jour `VITE_API_URL` avec l'URL réelle de votre backend Railway
3. Redéployez (automatique si activé)

---

## ✅ Vérification

- **Backend** : `https://votre-backend.railway.app/health`
- **Frontend** : Votre URL Vercel
- **API Docs** : `https://votre-backend.railway.app/api/docs`

---

## 📚 Documentation complète

Consultez **DEPLOYMENT.md** pour :
- Instructions détaillées
- Configuration Azure Blob Storage
- Dépannage
- Variables d'environnement complètes

---

**Bon déploiement ! 🎉**

