import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export interface FolderMetadata {
  id: number
  name: string
  user_id: number
  parent_id: number | null
  created_at: string
  updated_at: string | null
  children_count: number
  files_count: number
}

export interface FolderListResponse {
  folders: FolderMetadata[]
  total: number
}

export interface FolderCreate {
  name: string
  parent_id?: number | null
}

export interface FolderUpdate {
  name?: string
  parent_id?: number | null
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return {
    Authorization: `Bearer ${token}`,
  }
}

export const folderService = {
  /**
   * Create a new folder
   */
  async createFolder(data: FolderCreate): Promise<FolderMetadata> {
    const response = await axios.post(`${API_URL}/folders/`, data, {
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * List folders
   * @param parentId - If provided, returns only children of that folder. If null, returns root folders.
   */
  async listFolders(parentId: number | null = null, skip = 0, limit = 100): Promise<FolderListResponse> {
    const params: any = { skip, limit }
    if (parentId !== null && parentId !== undefined) {
      params.parent_id = parentId
    }
    
    const response = await axios.get(`${API_URL}/folders/`, {
      params,
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * Get a specific folder by ID
   */
  async getFolder(folderId: number): Promise<FolderMetadata> {
    const response = await axios.get(`${API_URL}/folders/${folderId}`, {
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * Update a folder (rename or move)
   */
  async updateFolder(folderId: number, data: FolderUpdate): Promise<FolderMetadata> {
    const response = await axios.put(`${API_URL}/folders/${folderId}`, data, {
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * Delete a folder (soft delete by default)
   */
  async deleteFolder(folderId: number, permanent = false): Promise<void> {
    await axios.delete(`${API_URL}/folders/${folderId}`, {
      params: { permanent },
      headers: getAuthHeaders(),
    })
  },

  /**
   * Get folder breadcrumbs (path from root to folder)
   */
  async getBreadcrumbs(folderId: number | null): Promise<FolderMetadata[]> {
    if (folderId === null) {
      return []
    }

    const breadcrumbs: FolderMetadata[] = []
    let currentId: number | null = folderId

    while (currentId !== null) {
      const folder = await this.getFolder(currentId)
      breadcrumbs.unshift(folder)
      currentId = folder.parent_id
    }

    return breadcrumbs
  },

  /**
   * Rename a folder
   */
  async renameFolder(folderId: number, newName: string): Promise<FolderMetadata> {
    const response = await axios.patch(
      `${API_URL}/folders/${folderId}/rename`,
      { new_name: newName },
      { headers: getAuthHeaders() }
    )
    return response.data
  },

  /**
   * Move a folder to another parent
   */
  async moveFolder(folderId: number, parentId?: number | null): Promise<FolderMetadata> {
    const response = await axios.patch(
      `${API_URL}/folders/${folderId}/move`,
      { parent_id: parentId === null ? null : parentId },
      { headers: getAuthHeaders() }
    )
    return response.data
  },

  /**
   * List deleted folders (trash)
   */
  async listTrashFolders(skip = 0, limit = 100): Promise<FolderListResponse> {
    const response = await axios.get(`${API_URL}/folders/trash`, {
      params: { skip, limit },
      headers: getAuthHeaders(),
    })
    return response.data
  },

  /**
   * Restore a deleted folder from trash
   */
  async restoreFolder(folderId: number): Promise<FolderMetadata> {
    const response = await axios.post(
      `${API_URL}/folders/${folderId}/restore`,
      {},
      { headers: getAuthHeaders() }
    )
    return response.data
  },

  /**
   * Download a folder as ZIP file
   */
  async downloadFolder(folderId: number, folderName: string): Promise<void> {
    const response = await axios.get(`${API_URL}/folders/${folderId}/download`, {
      headers: getAuthHeaders(),
      responseType: 'blob',
    })

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${folderName}.zip`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

