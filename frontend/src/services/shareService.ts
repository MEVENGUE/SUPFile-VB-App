import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export interface ShareLink {
  id: number
  token: string
  file_id: number | null
  folder_id: number | null
  share_url: string
  expires_at: string | null
  is_active: boolean
  access_count: number
  created_at: string
  has_password: boolean
}

export interface ShareLinkListResponse {
  share_links: ShareLink[]
  total: number
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return {
    Authorization: `Bearer ${token}`,
  }
}

export const shareService = {
  /**
   * List all share links created by the current user
   */
  async listShareLinks(skip = 0, limit = 100): Promise<ShareLinkListResponse> {
    const response = await axios.get(`${API_URL}/share/`, {
      params: { skip, limit },
      headers: getAuthHeaders(),
    })
    return response.data
  },
}
