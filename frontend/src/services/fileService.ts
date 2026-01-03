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
  folder_id?: number | null
  deleted_at?: string | null
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
  async uploadFile(file: File, folderId?: number | null): Promise<FileMetadata> {
    const formData = new FormData()
    formData.append('file', file)
    if (folderId !== null && folderId !== undefined) {
      formData.append('folder_id', folderId.toString())
    }

    const response = await axios.post(`${API_URL}/files/upload`, formData, {
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  async listFiles(folderId?: number | null, skip = 0, limit = 100): Promise<FileListResponse> {
    const params: any = { skip, limit }
    if (folderId !== null && folderId !== undefined) {
      params.folder_id = folderId
    }
    
    const response = await axios.get(`${API_URL}/files/`, {
      params,
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

  async getPreviewUrl(fileId: number): Promise<{ preview_url: string; content_type: string; filename: string }> {
    const response = await axios.get(`${API_URL}/files/${fileId}/preview`, {
      headers: getAuthHeaders(),
    })
    return response.data
  },

  async searchFiles(
    query: string,
    contentType?: string,
    folderId?: number | null,
    skip = 0,
    limit = 100
  ): Promise<FileListResponse> {
    const params: any = { q: query, skip, limit }
    if (contentType) {
      params.content_type = contentType
    }
    if (folderId !== null && folderId !== undefined) {
      params.folder_id = folderId
    }
    
    const response = await axios.get(`${API_URL}/files/search`, {
      params,
      headers: getAuthHeaders(),
    })
    return response.data
  },

  async renameFile(fileId: number, newFilename: string): Promise<FileMetadata> {
    const response = await axios.patch(
      `${API_URL}/files/${fileId}/rename`,
      { new_filename: newFilename },
      { headers: getAuthHeaders() }
    )
    return response.data
  },

  async moveFile(fileId: number, folderId?: number | null): Promise<FileMetadata> {
    const response = await axios.patch(
      `${API_URL}/files/${fileId}/move`,
      { folder_id: folderId === null ? null : folderId },
      { headers: getAuthHeaders() }
    )
    return response.data
  },

  async listTrashFiles(skip = 0, limit = 100): Promise<FileListResponse> {
    const response = await axios.get(`${API_URL}/files/trash`, {
      params: { skip, limit },
      headers: getAuthHeaders(),
    })
    return response.data
  },

  async restoreFile(fileId: number): Promise<FileMetadata> {
    const response = await axios.post(
      `${API_URL}/files/${fileId}/restore`,
      {},
      { headers: getAuthHeaders() }
    )
    return response.data
  },

  async deleteFilePermanent(fileId: number): Promise<void> {
    await axios.delete(`${API_URL}/files/${fileId}/permanent`, {
      headers: getAuthHeaders(),
    })
  },
}

