import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

interface User {
  id: number
  email: string
  username: string
  full_name?: string
}

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    
    const response = await axios.post(`${API_URL}/auth/login`, formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return response.data
  },

  async register(
    email: string,
    username: string,
    password: string,
    fullName?: string
  ): Promise<void> {
    await axios.post(`${API_URL}/auth/register`, {
      email,
      username,
      password,
      full_name: fullName,
    })
  },

  async getCurrentUser(token: string): Promise<User> {
    const response = await axios.get(`${API_URL}/users/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
    return response.data
  },

  async exchangeOAuthToken(tempToken: string): Promise<LoginResponse> {
    const response = await axios.get(`${API_URL}/auth/exchange-token/${tempToken}`)
    return response.data
  },
}

export function getAuthHeaders() {
  const token = localStorage.getItem('token')
  return {
    Authorization: `Bearer ${token}`,
  }
}
