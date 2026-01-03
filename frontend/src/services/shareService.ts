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

export interface ShareLinkMetadata extends ShareLink {
  file?: {
    id: number
    original_filename: string
    content_type?: string
  }
  folder?: {
    id: number
    name: string
  }
}

export interface ShareAccessResponse {
  file?: {
    id: number
    original_filename: string
    content_type?: string
    size: number
    file_size?: number
    created_at?: string
  }
  folder?: {
    id: number
    name: string
    created_at?: string
  }
  share_link: ShareLink
}

interface CreateShareLinkData {
  file_id?: number | null
  folder_id?: number | null
  password?: string | null
  expires_in_days?: number | null
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

  /**
   * Create a new share link
   */
  async createShareLink(data: CreateShareLinkData): Promise<ShareLinkMetadata> {
    const response = await axios.post(`${API_URL}/share/`, data, {
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * Get share link details by token
   */
  async getShareLink(token: string, password?: string): Promise<ShareAccessResponse> {
    const response = await axios.get(`${API_URL}/share/${token}`, {
      params: password ? { password } : {},
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * Download a shared file
   */
  async downloadSharedFile(token: string, password?: string): Promise<void> {
    const response = await axios.get(`${API_URL}/share/${token}/download`, {
      params: password ? { password } : {},
      headers: getAuthHeaders(),
      responseType: 'blob',
    })
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'file')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  /**
   * Get full share URL
   */
  getFullShareUrl(token: string): string {
    return `${window.location.origin}/share/${token}`
  },
}
