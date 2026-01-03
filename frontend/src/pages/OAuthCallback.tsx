import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { toast } from 'react-toastify'

const OAuthCallback = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { setTokens } = useAuth()

  useEffect(() => {
    const accessToken = searchParams.get('access_token')
    const refreshToken = searchParams.get('refresh_token')
    const error = searchParams.get('error')

    if (error) {
      toast.error('Erreur lors de la connexion OAuth2')
      navigate('/login')
      return
    }

    if (accessToken && refreshToken) {
      // Store tokens
      localStorage.setItem('token', accessToken)
      localStorage.setItem('refreshToken', refreshToken)
      
      // Update auth context
      setTokens(accessToken, refreshToken)
      
      toast.success('Connexion réussie!')
      navigate('/dashboard')
    } else {
      toast.error('Tokens manquants')
      navigate('/login')
    }
  }, [searchParams, navigate, setTokens])

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh' 
    }}>
      <div>
        <div className="spinner"></div>
        <p>Connexion en cours...</p>
      </div>
    </div>
  )
}

export default OAuthCallback

