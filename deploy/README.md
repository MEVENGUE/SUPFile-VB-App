# Architecture hybride SUPFile

```
Vercel (React)
      │ HTTPS
      ▼
Tailscale Funnel / HAProxy Paris
      │
web1-paris (Nginx :80 → Uvicorn :8080, systemd)
      │
      ├── ProxySQL :6033 → Galera (MySQL)
      └── GlusterFS (/mnt/gluster/supfile)
```

## Variables

| Où | Fichier / interface |
|----|---------------------|
| VM backend | `/etc/supfile/supfile.env` ← `deploy/supfile.env.example` |
| Vercel | `frontend/.env.example` → variables projet Vercel |

## Déploiement VM (résumé)

Voir les étapes dans les messages précédents : venv, `supfile.service`, `nginx-supfile.conf`, `tailscale funnel 80`.

```bash
curl http://127.0.0.1/health
```

Réponse attendue : `database.status=connected`, `storage.status=ok`.

## Initialisation DB Galera + migrations Alembic

1. Initialiser la base et l'utilisateur applicatif (via ProxySQL) :

```bash
mysql -h 10.10.1.32 -P 6033 -u admin -p < /opt/supfile/backend/scripts/init_galera_schema.sql
```

2. Exécuter les migrations du backend :

```bash
cd /opt/supfile/backend
chmod +x scripts/run_migrations.sh
/opt/supfile/venv/bin/pip install -r requirements.txt
/opt/supfile/venv/bin/alembic upgrade head
```

Notes:
- Les migrations ont été ajustées pour MySQL/Galera (`CURRENT_TIMESTAMP`, defaults bool/int).
- Une migration bootstrap crée `users` et `files` si la DB est vide.

## Code aligné sur cette architecture

- `DEPLOYMENT_MODE=hybrid`
- `STORAGE_BACKEND=local` + `UPLOAD_PATH` (GlusterFS)
- `DATABASE_URL=mysql+pymysql://...@ProxySQL:6033/...`
- Frontend : `frontend/src/config/api.ts` + `VITE_API_URL`
- Uploads chunkés backend (`/api/v1/files/upload/init|chunk|complete`) pour gros fichiers
- Healthcheck enrichi (`/health`) avec DC primaire/secondaire, sécurité stack, ingress compat

## Active/Active (étape suivante)

`deploy/haproxy.cfg.example` : ajouter `web2`, Keepalived VIP, lb-ny en miroir.

- Utiliser un split endpoint+méthode pour un vrai read/write split.
- Pour ProxySQL, conserver les écritures vers Paris et router les lectures vers le DC le plus proche.
- Pour les uploads chunkés, router toutes les étapes vers le même backend write-only.
- Pour les websockets, router le trafic `Upgrade: WebSocket` vers un backend sticky.

### HAProxy Read/Write split

Dans `deploy/haproxy.cfg.example`, sépare les backends par endpoint REST et par méthode :

- `supfile_health` → `/health`
- `websocket_backend` → trafic websocket
- `supfile_writes` → POST/PUT/PATCH/DELETE et chunked upload
- `supfile_reads` → endpoints de lecture listés

Endpoints typiques lecture :

- `GET /health`
- `GET /api/v1/files`
- `GET /api/v1/files/*`
- `GET /api/v1/users/me`
- `GET /api/v1/share/*`
- `GET /api/v1/search`
- `GET /api/v1/preview/*`

Endpoints typiques écriture :

- `POST /api/v1/files/upload/init`
- `POST /api/v1/files/upload/chunk`
- `POST /api/v1/files/upload/complete`
- `POST /api/v1/files`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
- `POST /api/v1/share`
- `PUT /api/v1/files/*`
- `DELETE /api/v1/files/*`
- `PATCH /api/v1/users/*`

Exemple :

```haproxy
frontend http_front
    bind *:80
    option forwardfor
    acl is_health path_beg /health
    acl is_chunked path_beg /api/v1/files/upload
    acl is_ws hdr(Upgrade) -i WebSocket
    acl is_read path_beg /api/v1/files /api/v1/search /api/v1/preview /api/v1/share /api/v1/users/me
    acl is_write method POST PUT PATCH DELETE

    use_backend supfile_health if is_health
    use_backend websocket_backend if is_ws
    use_backend supfile_writes if is_chunked
    use_backend supfile_writes if is_write
    use_backend supfile_reads if is_read
    default_backend supfile_reads

backend supfile_reads
    balance leastconn
    option httpchk GET /health
    http-check expect status 200
    server paris 10.10.1.11:80 check inter 2s rise 2 fall 3 weight 100
    server ny 10.10.2.11:80 check inter 2s rise 2 fall 3 weight 100

backend supfile_writes
    balance source
    option httpchk GET /health
    http-check expect status 200
    server paris-primary 10.10.1.11:80 check inter 2s rise 2 fall 3
    server paris-secondary 10.10.1.12:80 check inter 2s rise 2 fall 3 backup

backend websocket_backend
    balance source
    option httpchk GET /health
    http-check expect status 200
    server paris-primary 10.10.1.11:80 check inter 2s rise 2 fall 3
    server paris-secondary 10.10.1.12:80 check inter 2s rise 2 fall 3 backup
```

Pour un vrai Active/Active, ne pas déclarer `ny` en backup dans le backend de lecture.

- Sur `lb-paris`, privilégie Paris : `server paris weight 100`, `server ny weight 20`
- Sur `lb-ny`, privilégie NY : `server ny weight 100`, `server paris weight 20`

Cela donne : nearest-DC, bascule automatique et une architecture plus cohérente pour les uploads chunkés, les sessions, le refresh JWT et OAuth.

## Configurations VM à faire absolument

- Monter GlusterFS sur `UPLOAD_PATH` (`/mnt/gluster/supfile`) avec droits d'écriture pour l'utilisateur du service.
- Créer le dossier temporaire chunk upload:
  - `sudo mkdir -p /tmp/supfile-chunks && sudo chown vagrant:vagrant /tmp/supfile-chunks`
- Vérifier `CORS_ORIGINS` avec les 5 origines (Vercel + 2 tailnet + localhost dev).
- Déclarer exactement les callback OAuth autorisés dans les providers:
  - `https://supfile-webapp.vercel.app/auth/callback`
  - `https://web1-paris.tail69cc44.ts.net/auth/callback`
  - `https://web1-ny.tail69cc44.ts.net/auth/callback`
- Démarrer derrière Nginx/Haproxy sur `:80` et garder Uvicorn en `127.0.0.1:8080`.

## Sécurité: rotation immédiate des secrets

Après migration, changez immédiatement:
- mots de passe DB (`supfile_app`, admin ProxySQL)
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- tous les `OAUTH_*_CLIENT_SECRET`
