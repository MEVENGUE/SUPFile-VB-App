/**
 * Configuration API — architecture hybride :
 * Vercel (frontend) → Tailscale Funnel / HAProxy → FastAPI (VM VirtualBox)
 */

const LOCAL_API = 'http://localhost:8080/api/v1'
const LOCAL_WS = 'ws://localhost:8080/api/v1/ws'

function trimSlash(url: string): string {
  return url.replace(/\/+$/, '')
}

/** URL de base de l'API (doit finir par /api/v1) */
export function getApiUrl(): string {
  const envUrl = import.meta.env.VITE_API_URL
  if (envUrl) {
    return trimSlash(envUrl)
  }

  if (import.meta.env.DEV) {
    return LOCAL_API
  }

  console.error(
    'VITE_API_URL non défini. Sur Vercel : URL Tailscale Funnel ou HAProxy, ex. https://web1-paris.xxx.ts.net/api/v1'
  )
  return LOCAL_API
}

/** URL WebSocket (wss en production) */
export function getWsUrl(token: string): string {
  const envWs = import.meta.env.VITE_WS_URL
  if (envWs) {
    const base = trimSlash(envWs)
    return base.includes('?') ? `${base}&token=${token}` : `${base}?token=${token}`
  }

  const apiUrl = getApiUrl()
  const wsBase = apiUrl
    .replace(/^https:/, 'wss:')
    .replace(/^http:/, 'ws:')
    .replace(/\/api\/v1$/, '')

  return `${wsBase}/api/v1/ws?token=${token}`
}

/** URL publique du backend (OAuth, liens absolus) */
export function getBackendPublicUrl(): string {
  const env = import.meta.env.VITE_BACKEND_PUBLIC_URL
  if (env) {
    return trimSlash(env)
  }
  return trimSlash(getApiUrl().replace(/\/api\/v1$/, ''))
}

export const API_URL = getApiUrl()
