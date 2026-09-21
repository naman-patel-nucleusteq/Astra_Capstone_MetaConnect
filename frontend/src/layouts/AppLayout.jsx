import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import ToastNotification from '../components/ToastNotification.jsx'
import { useAuth } from '../services/auth.js'
import api from '../services/api.js'

const primaryLinks = [
  { to: '/dashboard', label: 'Overview'},
  { to: '/connections', label: 'Connections'},
  { to: '/metadata', label: 'Metadata explorer'},
  { to: '/pipeline-runs', label: 'Pipeline runs'},
]

function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const searchRef = useRef(null)
  const [searchParams] = useSearchParams()
  const { user, logout } = useAuth()
  const [toast, setToast] = useState(null)
  const [searchQuery, setSearchQuery] = useState(searchParams.get('q') || '')
  const [searchType, setSearchType] = useState(searchParams.get('type') || 'all')
  const [searchResults, setSearchResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [isSearchFocused, setIsSearchFocused] = useState(false)

  useEffect(() => {
    function closeSearch(event) {
      if (!searchRef.current?.contains(event.target)) 
        setIsSearchFocused(false)
    }
    document.addEventListener('pointerdown', closeSearch)
    return () => document.removeEventListener('pointerdown', closeSearch)
  }, [])

  useEffect(() => {
    const closeTimer = window.setTimeout(() => setIsSearchFocused(false), 0)
    return () => window.clearTimeout(closeTimer)
  }, [location.pathname])

  useEffect(() => {
    const query = searchQuery.trim()
    if (query.length < 2) {
      const resetTimer = window.setTimeout(() => setSearchResults([]), 0)
      return () => window.clearTimeout(resetTimer)
    }

    let active = true
    const timer = window.setTimeout(async () => {
      setIsSearching(true)
      try {
        const response = await api.get('/api/metadata/search', { params: { q: query, ...(searchType !== 'all' ? { type: searchType } : {}) } })
        if (active) setSearchResults(response.data)
      } catch {
        if (active) setSearchResults([])
      } finally {
        if (active) setIsSearching(false)
      }
    }, 250)

    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [searchQuery, searchType])


  function openSearch() {
    const query = searchQuery.trim()
    if (query) navigate(`/metadata?q=${encodeURIComponent(query)}${searchType === 'all' ? '' : `&type=${searchType}`}`)
  }

  function selectSearchResult(result) {
    setIsSearchFocused(false)
    setSearchResults([])
    navigate(`/metadata?q=${encodeURIComponent(searchQuery.trim())}&type=${result.type}&id=${result.id}`)
  }

  async function handleLogout() {
    setToast({ tone: 'success', message: 'Signing out ...' })
    try {
      await logout()
    } catch {
      navigate('/login', { replace: true })
    }
  }

  return (
    <div className="app-shell">

      {/* sidebar */}
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark">M</div>
          <div>
            <strong>MetaConnect</strong>
            <span>Data catalog</span>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          {primaryLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>


      {/* content area  */}
      <main className="main-content">
        <header className="topbar">

          {/* global search bar */}
          <div className="global-search" ref={searchRef}>
            <select
              aria-label="Search metadata type"
              value={searchType}
              onChange={(event) => setSearchType(event.target.value)}
            >
              <option value="all">All</option>
              <option value="database">Database</option>
              <option value="schema">Schema</option>
              <option value="table">Table</option>
              <option value="column">Column</option>
            </select>
            <input
              aria-label="Search catalog"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              onFocus={() => setIsSearchFocused(true)}
              onKeyDown={(event) => event.key === 'Enter' && openSearch()}
              placeholder="Search catalog..."
            />
            {isSearchFocused && searchQuery.trim().length >= 2 && (
              <div className="search-results">
                {isSearching && <span className="search-hint">Searching...</span>}
                {!isSearching && searchResults.length === 0 && <span className="search-hint">No catalog matches</span>}
                {!isSearching && searchResults.map((result) => (
                  <button key={`${result.type}-${result.id}`} type="button" onClick={() => selectSearchResult(result)}>
                    <strong>{result.name}</strong>
                    <span>{result.type} · {result.path || [result.parent, result.name].filter(Boolean).join('.')}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          
          {/* navbar right portion */}
          <div className="user-menu">
            <div className="current_user">
              <span className="avatar">{user?.username?.slice(0, 2).toUpperCase()}</span>
              <span className="user-name">{user?.username}</span>
            </div>
            <button className="topbar-logout" type="button" onClick={handleLogout}>Log out</button>
          </div>

        </header>
        
        {/* main content */}
        <div className="page-content">
          <Outlet />
        </div>

      </main>
      {toast && <ToastNotification {...toast} onDismiss={() => setToast(null)} />}
    </div>
  )
}

export default AppLayout