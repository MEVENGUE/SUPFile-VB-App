// Service Worker pour PWA
const CACHE_NAME = 'supfile-v2'; // Incrémenter la version pour forcer la mise à jour
const urlsToCache = [
  '/manifest.json'
];

// Installation du Service Worker
self.addEventListener('install', (event) => {
  // Forcer l'activation immédiate du nouveau service worker
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Cache ouvert:', CACHE_NAME);
        // Ne cacher que les fichiers statiques, pas les pages HTML
        return cache.addAll(urlsToCache);
      })
  );
});

// Activation du Service Worker
self.addEventListener('activate', (event) => {
  // Prendre le contrôle immédiatement
  event.waitUntil(
    Promise.all([
      // Supprimer tous les anciens caches
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              console.log('Suppression de l\'ancien cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      // Prendre le contrôle de toutes les pages
      clients.claim()
    ])
  );
});

// Interception des requêtes
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Pour les pages HTML, utiliser "network first" pour toujours avoir la dernière version
  if (request.method === 'GET' && request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Si la requête réseau réussit, mettre à jour le cache
          if (response.ok) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseToCache);
            });
          }
          return response;
        })
        .catch(() => {
          // Si la requête réseau échoue, essayer le cache
          return caches.match(request).then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            // Si pas de cache, retourner une réponse d'erreur
            return new Response('Offline', { status: 503 });
          });
        })
    );
    return;
  }

  // Pour les autres ressources (CSS, JS, images), utiliser "cache first" avec fallback réseau
  event.respondWith(
    caches.match(request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          // En arrière-plan, vérifier s'il y a une mise à jour
          fetch(request).then((networkResponse) => {
            if (networkResponse.ok) {
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(request, networkResponse.clone());
              });
            }
          }).catch(() => {
            // Ignorer les erreurs réseau en arrière-plan
          });
          return cachedResponse;
        }
        // Si pas dans le cache, faire une requête réseau
        return fetch(request).then((response) => {
          // Mettre en cache si la réponse est valide
          if (response.ok && url.origin === location.origin) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseToCache);
            });
          }
          return response;
        });
      })
  );
});

