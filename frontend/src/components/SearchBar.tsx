import { useState, useEffect } from 'react'
import './SearchBar.css'

interface SearchBarProps {
  onSearch: (query: string, contentType?: string) => void
  placeholder?: string
}

const SearchBar: React.FC<SearchBarProps> = ({ onSearch, placeholder = "Rechercher des fichiers..." }) => {
  const [query, setQuery] = useState('')
  const [contentType, setContentType] = useState<string>('')
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    // Debounce search to avoid too many API calls
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }

    const timer = setTimeout(() => {
      if (query.trim() || contentType) {
        onSearch(query.trim(), contentType || undefined)
      } else {
        onSearch('')
      }
    }, 300) // 300ms debounce

    setDebounceTimer(timer)

    return () => {
      if (debounceTimer) {
        clearTimeout(debounceTimer)
      }
    }
  }, [query, contentType])

  const handleClear = () => {
    setQuery('')
    setContentType('')
    onSearch('')
  }

  return (
    <div className="search-bar" role="search" aria-label="Recherche de fichiers">
      <div className="search-input-wrapper">
        <svg className="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <input
          type="text"
          className="search-input"
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Rechercher des fichiers"
          aria-describedby="search-description"
        />
        <span id="search-description" className="sr-only">Recherche de fichiers par nom ou type</span>
        {query && (
          <button className="search-clear" onClick={handleClear} aria-label="Effacer la recherche">
            <span aria-hidden="true">✕</span>
          </button>
        )}
      </div>
      <select
        className="search-filter"
        value={contentType}
        onChange={(e) => setContentType(e.target.value)}
        aria-label="Filtrer par type de fichier"
      >
        <option value="">Tous les types</option>
        <option value="image">Images</option>
        <option value="video">Vidéos</option>
        <option value="audio">Audio</option>
        <option value="application/pdf">PDF</option>
        <option value="text">Texte</option>
        <option value="application">Documents</option>
      </select>
    </div>
  )
}

export default SearchBar

