/**
 * Utility function to get the appropriate icon for a file based on its extension or content type
 */
export const getFileIcon = (filename: string, contentType?: string): string => {
  if (!filename) return '/Fichier.jpg'
  
  const extension = filename.split('.').pop()?.toLowerCase() || ''
  
  // Images
  if (contentType?.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp'].includes(extension)) {
    return '/Fichier.jpg' // Use generic file icon for images
  }
  
  // Documents
  if (['pdf', 'doc', 'docx', 'txt', 'rtf'].includes(extension)) {
    return '/Fichier.jpg'
  }
  
  // Spreadsheets
  if (['xls', 'xlsx', 'csv'].includes(extension)) {
    return '/Fichier.jpg'
  }
  
  // Archives
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(extension)) {
    return '/Fichier.jpg'
  }
  
  // Default
  return '/Fichier.jpg'
}

export const getFileTypeLabel = (filename: string, contentType?: string): string => {
  if (!filename) return 'Fichier'
  
  const extension = filename.split('.').pop()?.toLowerCase() || ''
  
  if (contentType?.startsWith('image/')) return 'Image'
  if (contentType?.startsWith('video/')) return 'Vidéo'
  if (contentType?.startsWith('audio/')) return 'Audio'
  if (['pdf'].includes(extension)) return 'PDF'
  if (['doc', 'docx'].includes(extension)) return 'Document Word'
  if (['xls', 'xlsx'].includes(extension)) return 'Tableur'
  if (['zip', 'rar', '7z'].includes(extension)) return 'Archive'
  
  return 'Fichier'
}

