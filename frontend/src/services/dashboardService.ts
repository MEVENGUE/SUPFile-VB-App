import axios from 'axios'

import { API_URL } from '../config/api'

export interface DashboardStats {
  total_files: number
  total_folders: number
  total_size_bytes: number
  total_size_mb: number
  files_by_type: Record<string, number>
  recent_files: Array<{
    id: number
    filename: string
    size: number
    content_type: string
    created_at: string
  }>
  storage_usage_percentage: number
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return {
    Authorization: `Bearer ${token}`,
  }
}

export const dashboardService = {
  async getStats(): Promise<DashboardStats> {
    const response = await axios.get(`${API_URL}/dashboard/stats`, {
      headers: getAuthHeaders(),
    })
    return response.data
  },
}

