import axios from 'axios'
import { API_URL } from '../config/api'

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
    try {
      const url = `${API_URL}/share/${token}`
      console.log('Fetching share link from:', url)
      const response = await axios.get(url, {
        params: password ? { password } : {},
        // Explicitly don't send auth headers for public share links
        headers: {},
      })
      console.log('Share link response:', response.status, response.data)
      return response.data
    } catch (error: any) {
      // Log the error for debugging
      console.error('Error fetching share link:', error)
      console.error('Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        url: error.config?.url
      })
      throw error
    }
  },

  /**
   * Get preview URL for a shared file
   * If fileId is provided, it's for a file in a shared folder
   */
  async getSharedFilePreview(token: string, password?: string, fileId?: number): Promise<{ preview_url: string; content_type: string; filename: string }> {
    try {
      const params: any = {}
      if (password) params.password = password
      if (fileId) params.file_id = fileId
      
      const response = await axios.get(`${API_URL}/share/${token}/preview`, {
        params,
        // Explicitly don't send auth headers for public share links
        headers: {},
      })
      return response.data
    } catch (error: any) {
      console.error('Error fetching shared file preview:', error)
      throw error
    }
  },

  /**
   * Get folder content for a shared folder
   */
  async getSharedFolderContent(token: string, password?: string, skip = 0, limit = 100): Promise<{
    folder: { id: number; name: string; created_at: string | null }
    files: Array<{
      id: number
      filename: string
      original_filename: string
      file_size: number
      content_type: string
      created_at: string | null
    }>
    subfolders: Array<{
      id: number
      name: string
      created_at: string | null
    }>
    files_total: number
    subfolders_total: number
  }> {
    try {
      const response = await axios.get(`${API_URL}/share/${token}/folder`, {
        params: {
          ...(password ? { password } : {}),
          skip,
          limit,
        },
        // Explicitly don't send auth headers for public share links
        headers: {},
      })
      return response.data
    } catch (error: any) {
      console.error('Error fetching shared folder content:', error)
      throw error
    }
  },

  /**
   * Download a file from a shared folder
   */
  async downloadFileFromSharedFolder(token: string, fileId: number, password?: string): Promise<void> {
    try {
      const response = await axios.get(`${API_URL}/share/${token}/files/${fileId}/download`, {
        params: password ? { password } : {},
        responseType: 'blob',
        // Explicitly don't send auth headers for public share links
        headers: {},
      })
      
      // Get filename from Content-Disposition header
      const contentDisposition = response.headers['content-disposition']
      let downloadFilename = 'file'
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
        if (filenameMatch && filenameMatch[1]) {
          downloadFilename = filenameMatch[1].replace(/['"]/g, '')
        }
      }
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', downloadFilename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error: any) {
      console.error('Error downloading file from shared folder:', error)
      throw error
    }
  },

  /**
   * Download a shared file or folder
   * Files are downloaded directly, folders are downloaded as ZIP
   */
  async downloadSharedFile(token: string, password?: string, filename?: string): Promise<void> {
    try {
      const response = await axios.get(`${API_URL}/share/${token}/download`, {
        params: password ? { password } : {},
        responseType: 'blob',
        // Explicitly don't send auth headers for public share links
        headers: {},
      })
      
      // Extract filename from Content-Disposition header if available
      const contentDisposition = response.headers['content-disposition']
      let downloadFilename = filename || 'file'
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
        if (filenameMatch && filenameMatch[1]) {
          downloadFilename = filenameMatch[1].replace(/['"]/g, '')
        }
      }
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', downloadFilename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error: any) {
      console.error('Error downloading shared file:', error)
      throw error
    }
  },

  /**
   * Download a shared folder as ZIP
   */
  async downloadSharedFolder(token: string, folderName: string, password?: string): Promise<void> {
    try {
      const response = await axios.get(`${API_URL}/share/${token}/download`, {
        params: password ? { password } : {},
        responseType: 'blob',
        // Explicitly don't send auth headers for public share links
        headers: {},
      })
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/zip' }))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `${folderName}.zip`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error: any) {
      console.error('Error downloading shared folder:', error)
      throw error
    }
  },

  /**
   * Get full share URL
   */
  getFullShareUrl(token: string): string {
    return `${window.location.origin}/share/${token}`
  },
}
