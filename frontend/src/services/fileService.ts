import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export interface FileMetadata {
  id: number
  filename: string
  original_filename: string
  file_size: number
  content_type: string
  created_at: string
  upload_region?: string
}

export interface FileListResponse {
  files: FileMetadata[]
  total: number
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return {
    Authorization: `Bearer ${token}`,
  }
}

export const fileService = {
  async uploadFile(file: File): Promise<FileMetadata> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await axios.post(`${API_URL}/files/upload`, formData, {
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  async listFiles(skip = 0, limit = 100): Promise<FileListResponse> {
    const response = await axios.get(`${API_URL}/files/`, {
      params: { skip, limit },
      headers: getAuthHeaders(),
    })
    return response.data
  },

  async getFile(fileId: number): Promise<FileMetadata> {
    const response = await axios.get(`${API_URL}/files/${fileId}`, {
      headers: getAuthHeaders(),
    })
    return response.data
  },

  async downloadFile(fileId: number, filename: string): Promise<void> {
    const response = await axios.get(`${API_URL}/files/${fileId}/download`, {
      headers: getAuthHeaders(),
      responseType: 'blob',
    })

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  async deleteFile(fileId: number): Promise<void> {
    await axios.delete(`${API_URL}/files/${fileId}`, {
      headers: getAuthHeaders(),
    })
  },
}

