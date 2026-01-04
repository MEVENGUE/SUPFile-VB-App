import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { toast } from 'react-toastify'
import { authService } from '../services/authService'

const OAuthCallback = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { setTokens } = useAuth()
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        // Check for error first
        const error = searchParams.get('error')
        if (error) {
          const message = searchParams.get('message') || 'Erreur lors de la connexion OAuth2'
          toast.error(decodeURIComponent(message))
          navigate('/login')
          return
        }

        // New method: Check for temporary token (used for Microsoft OAuth to avoid ERR_INVALID_REDIRECT)
        const tempToken = searchParams.get('token')
        if (tempToken) {
          try {
            // Exchange temporary token for JWT tokens
            const response = await authService.exchangeOAuthToken(tempToken)
            
            // Store tokens
            localStorage.setItem('token', response.access_token)
            localStorage.setItem('refreshToken', response.refresh_token)
            
            // Update auth context
            setTokens(response.access_token, response.refresh_token)
            
            toast.success('Connexion réussie!')
            navigate('/dashboard')
            return
          } catch (error: any) {
            console.error('Error exchanging OAuth token:', error)
            toast.error(error.response?.data?.detail || 'Erreur lors de l\'échange du token OAuth')
            navigate('/login')
            return
          }
        }

        // Legacy method: Try to get tokens from URL fragment or query params
        const hash = window.location.hash.substring(1) // Remove the # symbol
        const hashParams = new URLSearchParams(hash)
        
        const accessToken = hashParams.get('access_token') || searchParams.get('access_token')
        const refreshToken = hashParams.get('refresh_token') || searchParams.get('refresh_token')

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
      } catch (error) {
        console.error('OAuth callback error:', error)
        toast.error('Erreur lors de la connexion OAuth2')
        navigate('/login')
      } finally {
        setIsLoading(false)
      }
    }

    handleOAuthCallback()
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

