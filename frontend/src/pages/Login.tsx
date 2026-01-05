import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { toast } from 'react-toastify'
import './Auth.css'

const Login = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // Handle OAuth errors from URL parameters
  useEffect(() => {
    const error = searchParams.get('error')
    const message = searchParams.get('message')
    
    if (error) {
      const errorMessages: { [key: string]: string } = {
        'oauth_error': message || 'Erreur lors de la connexion OAuth',
        'oauth_code_expired': message || 'Le code d\'autorisation a expiré. Veuillez réessayer.',
        'oauth_config_error': message || 'Configuration OAuth incorrecte. Contactez l\'administrateur.',
        'oauth_http_error': message || 'Erreur HTTP lors de la connexion OAuth',
        'oauth_token_error': message || 'Erreur lors de l\'obtention du token OAuth',
        'oauth_timeout': message || 'Timeout lors de la connexion OAuth. Veuillez réessayer.'
      }
      
      toast.error(errorMessages[error] || 'Erreur lors de la connexion OAuth')
      
      // Clean URL parameters
      navigate('/login', { replace: true })
    }
  }, [searchParams, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await login(username, password)
      toast.success('Connexion réussie!')
      // Check if there's a redirect URL stored (e.g., from a shared folder)
      const redirectUrl = sessionStorage.getItem('redirectAfterLogin')
      if (redirectUrl) {
        sessionStorage.removeItem('redirectAfterLogin')
        navigate(redirectUrl)
      } else {
        navigate('/dashboard')
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <img src="/logo.jpg" alt="SUPFile Logo" className="auth-logo" />
          <h1>SUPFile</h1>
          <p>Connexion à votre compte</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="username">Nom d'utilisateur ou Email</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="votre@email.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Mot de passe</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
            />
          </div>

          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? 'Connexion...' : 'Se connecter'}
          </button>
        </form>

        <div className="oauth-divider">
          <span>ou</span>
        </div>

        <div className="oauth-buttons">
          <a
            href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/auth/google/authorize`}
            className="oauth-button oauth-google"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/>
              <path d="M9 18c2.43 0 4.467-.806 5.965-2.184l-2.908-2.258c-.806.54-1.837.86-3.057.86-2.35 0-4.34-1.587-5.053-3.72H.957v2.331C2.438 15.983 5.482 18 9 18z" fill="#34A853"/>
              <path d="M3.947 10.698c-.18-.54-.282-1.117-.282-1.698s.102-1.158.282-1.698V4.971H.957C.348 6.175 0 7.55 0 9s.348 2.825.957 4.029l2.99-2.331z" fill="#FBBC05"/>
              <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.971L3.947 7.302C4.66 5.167 6.65 3.58 9 3.58z" fill="#EA4335"/>
            </svg>
            Continuer avec Google
          </a>
          <a
            href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/auth/github/authorize`}
            className="oauth-button oauth-github"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            Continuer avec GitHub
          </a>
          <a
            href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/auth/microsoft/authorize`}
            className="oauth-button oauth-microsoft"
          >
            <svg width="18" height="18" viewBox="0 0 23 23" fill="none">
              <path d="M0 0h10.5v10.5H0V0z" fill="#f25022"/>
              <path d="M12.5 0H23v10.5H12.5V0z" fill="#00a4ef"/>
              <path d="M0 12.5h10.5V23H0V12.5z" fill="#7fba00"/>
              <path d="M12.5 12.5H23V23H12.5V12.5z" fill="#ffb900"/>
            </svg>
            Continuer avec Microsoft
          </a>
        </div>

        <div className="auth-footer">
          <p>
            Pas encore de compte? <Link to="/register">S&apos;inscrire</Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default Login

