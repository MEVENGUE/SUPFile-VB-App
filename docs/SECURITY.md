# Sécurité SUPFile

Ce document décrit les mesures de sécurité implémentées dans SUPFile.

## Vue d'ensemble

SUPFile implémente une sécurité en couches (defense in depth) pour protéger :
- Les données utilisateur
- L'infrastructure Azure
- Les communications réseau
- L'authentification et l'autorisation

## 1. Authentification

### 1.1 JWT Tokens

- **Access Tokens** : Durée de vie de 30 minutes
- **Refresh Tokens** : Durée de vie de 7 jours
- **Algorithme** : HS256 (HMAC-SHA256)
- **Secret** : Stocké dans Azure Key Vault, jamais en clair

### 1.2 Password Security

- **Hashing** : bcrypt avec 12 rounds
- **Validation** : Minimum 6 caractères (recommandé : 8+ avec complexité)
- **Stockage** : Jamais en clair, hash uniquement

### 1.3 OAuth2 (Futur)

- Support prévu pour Google et GitHub OAuth2
- Délégation d'authentification externe

## 2. Autorisation

### 2.1 Contrôle d'accès

- **User-based** : Chaque utilisateur ne peut accéder qu'à ses propres fichiers
- **Middleware** : Vérification JWT sur toutes les routes protégées
- **Database** : Filtrage par `user_id` au niveau SQL

### 2.2 Validation des permissions

```python
# Exemple de vérification dans le backend
file = db.query(File).filter(
    File.id == file_id,
    File.user_id == current_user_id  # Vérification stricte
).first()
```

## 3. Sécurité réseau

### 3.1 HTTPS/TLS

- **Obligatoire** : Toutes les communications en HTTPS
- **TLS Version** : Minimum TLS 1.2
- **Certificats** : Gérés par Azure Front Door (certificats automatiques)

### 3.2 CORS (Cross-Origin Resource Sharing)

- **Origines autorisées** : Configurées explicitement
- **Credentials** : Supporté pour les cookies/tokens
- **Headers** : Contrôle strict des headers autorisés

```python
CORS_ORIGINS = [
    "https://supfile.azurefd.net",
    "https://supfile-frontend-eastus.azurewebsites.net"
]
```

### 3.3 Network Security Groups (NSG)

- **Règles** : Restriction des ports d'entrée
- **Private Endpoints** : Pour PostgreSQL (pas d'accès public direct)
- **Firewall** : Azure Firewall pour protection avancée

## 4. Protection des données

### 4.1 Chiffrement au repos

- **Azure Blob Storage** : Chiffrement automatique (AES-256)
- **PostgreSQL** : Chiffrement des données avec clés gérées par Azure
- **Backups** : Chiffrés avant stockage dans Backup Vault

### 4.2 Chiffrement en transit

- **TLS 1.2+** : Toutes les communications
- **Database** : SSL obligatoire pour PostgreSQL
- **Blob Storage** : HTTPS uniquement

### 4.3 Secrets Management

- **Azure Key Vault** : Stockage des secrets
- **Managed Identity** : Pas de credentials en dur
- **Environment Variables** : Secrets injectés au runtime

## 5. Validation des entrées

### 5.1 Backend (FastAPI)

- **Pydantic** : Validation automatique des schémas
- **File Validation** :
  - Extension autorisée
  - Taille maximale (100MB)
  - Type MIME vérifié

```python
# Exemple de validation
ALLOWED_EXTENSIONS = ["txt", "pdf", "png", "jpg", "jpeg"]
MAX_FILE_SIZE_MB = 100
```

### 5.2 Frontend (React)

- **Input Sanitization** : Nettoyage des entrées utilisateur
- **TypeScript** : Typage fort pour prévenir les erreurs
- **XSS Protection** : React échappe automatiquement le HTML

## 6. Protection contre les attaques

### 6.1 Web Application Firewall (WAF)

- **Azure Front Door WAF** : Protection OWASP Top 10
- **Règles** : 
  - SQL Injection
  - XSS (Cross-Site Scripting)
  - CSRF (Cross-Site Request Forgery)
  - DDoS Protection

### 6.2 Rate Limiting

- **Nginx** : Limitation du nombre de requêtes par IP
- **Azure Front Door** : Protection DDoS intégrée
- **Backend** : Middleware de rate limiting (à implémenter si nécessaire)

### 6.3 Fail2ban équivalent

- **Log Analysis** : Détection des tentatives d'intrusion
- **Azure Monitor** : Alertes sur patterns suspects
- **Auto-blocking** : Blocage automatique des IPs malveillantes

## 7. Sécurité Azure Blob Storage

### 7.1 Accès privé

- **Container** : Privé (pas d'accès public)
- **SAS Tokens** : Pour téléchargements temporaires uniquement
- **Expiration** : SAS tokens expirent après 1 heure

### 7.2 Noms de fichiers

- **Sanitization** : Nettoyage des noms de fichiers
- **UUID** : Utilisation d'UUID pour éviter les collisions
- **Structure** : `{user_id}/{uuid}/{filename}`

## 8. Logging et Monitoring

### 8.1 Logs de sécurité

- **Authentification** : Toutes les tentatives de connexion
- **Accès fichiers** : Upload, download, delete
- **Erreurs** : Logs détaillés des erreurs

### 8.2 Alertes

- **Tentatives échouées** : Alertes sur échecs d'authentification multiples
- **Anomalies** : Détection de comportements suspects
- **Performance** : Alertes sur latence anormale

### 8.3 Audit

- **Azure Monitor** : Centralisation des logs
- **Log Analytics** : Analyse des patterns
- **Rétention** : 90 jours minimum

## 9. Bonnes pratiques de développement

### 9.1 Code Security

- **Dependencies** : Mise à jour régulière des packages
- **Vulnerability Scanning** : Scan des dépendances
- **Code Review** : Revue de code pour sécurité

### 9.2 Secrets dans le code

- ❌ **Jamais** : Secrets en dur dans le code
- ✅ **Toujours** : Variables d'environnement ou Key Vault
- ✅ **Git** : `.env` dans `.gitignore`

### 9.3 Error Handling

- **Messages d'erreur** : Génériques pour l'utilisateur
- **Logs détaillés** : Pour le debugging interne
- **Pas d'informations sensibles** : Dans les réponses API

## 10. Conformité et réglementation

### 10.1 RGPD (GDPR)

- **Droit à l'oubli** : Suppression des données utilisateur
- **Portabilité** : Export des données
- **Consentement** : Gestion du consentement utilisateur

### 10.2 SOC 2

- **Contrôles** : Alignement avec SOC 2 Type II
- **Documentation** : Procédures documentées
- **Audit** : Traçabilité complète

## 11. Incident Response

### 11.1 Procédure en cas d'incident

1. **Détection** : Monitoring et alertes
2. **Isolation** : Isolation de la menace
3. **Analyse** : Investigation approfondie
4. **Correction** : Correction de la vulnérabilité
5. **Documentation** : Rapport d'incident

### 11.2 Contacts

- **Équipe sécurité** : security@supfile.example.com
- **Azure Support** : Via Azure Portal
- **Urgences** : Procédure d'escalade documentée

## 12. Checklist de sécurité

### Déploiement

- [ ] Secrets dans Azure Key Vault
- [ ] HTTPS activé partout
- [ ] WAF configuré
- [ ] Monitoring activé
- [ ] Backups configurés
- [ ] Firewall rules configurées
- [ ] Private endpoints pour database
- [ ] Managed Identity configuré

### Maintenance

- [ ] Mise à jour des dépendances
- [ ] Scan de vulnérabilités
- [ ] Revue des logs
- [ ] Tests de sécurité
- [ ] Mise à jour des certificats

## 13. Ressources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Azure Security Best Practices](https://docs.microsoft.com/azure/security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [React Security](https://reactjs.org/docs/dom-elements.html#security)

## 14. Améliorations futures

- [ ] 2FA (Two-Factor Authentication)
- [ ] OAuth2 (Google, GitHub)
- [ ] Audit logging avancé
- [ ] Penetration testing
- [ ] Security scanning automatisé (CI/CD)

