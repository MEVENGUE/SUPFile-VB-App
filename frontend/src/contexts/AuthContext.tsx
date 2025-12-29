import React, { createContext, useContext, useState, useEffect } from 'react'
import { authService } from '../services/authService'

interface User {
  id: number
  email: string
  username: string
  full_name?: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (username: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))

  useEffect(() => {
    if (token) {
      // Verify token and get user info
      authService.getCurrentUser(token)
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('token')
          setToken(null)
        })
    }
  }, [token])

  const login = async (username: string, password: string) => {
    const response = await authService.login(username, password)
    setToken(response.access_token)
    localStorage.setItem('token', response.access_token)
    const userData = await authService.getCurrentUser(response.access_token)
    setUser(userData)
  }

  const register = async (email: string, username: string, password: string, fullName?: string) => {
    await authService.register(email, username, password, fullName)
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    localStorage.removeItem('token')
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        register,
        logout,
        isAuthenticated: !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

