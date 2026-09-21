import { useEffect, useMemo, useState } from 'react'
import keycloak, {
  getKeycloak,
  initializeKeycloak,
  login as startLogin,
  logout as endSession,
  refreshAccessToken,
} from '../services/keycloakAuth.js'
import { AuthContext } from '../services/auth.js'

function getUser(keycloakInstance) {
  const claims = keycloakInstance.tokenParsed || {}
  return {
    username: claims.preferred_username || claims.email || 'User',
    name: claims.name || claims.preferred_username || claims.email || 'User',
  }
}

export function AuthProvider({ children }) {
  const [authState, setAuthState] = useState({
    isLoading: true,
    isAuthenticated: false,
    user: null,
    error: null,
  })

  useEffect(() => {
    let isMounted = true

    async function initialize() {
      try {
        const isAuthenticated = await initializeKeycloak()
        if (isAuthenticated) await refreshAccessToken()

        if (isMounted) {
          setAuthState({
            isLoading: false,
            isAuthenticated,
            user: isAuthenticated ? getUser(keycloak) : null,
            error: null,
          })
        }
      } 
      catch {
        if (isMounted) {
          setAuthState({
            isLoading: false,
            isAuthenticated: false,
            user: null,
            error: 'Keycloak could not complete the browser login. Check that the application client is configured as public.',
          })
        }
      }
    }

    initialize()
    return () => { isMounted = false }
  }, [])


  useEffect(() => {
    if (!authState.isAuthenticated) return undefined

    let active = true
    async function refresh() {
      try {
        const refreshed = await refreshAccessToken()
        if (refreshed && active) setAuthState((current) => ({ ...current, user: getUser(getKeycloak()) }))
      } 
      catch {
        if (active) {
          setAuthState({ isLoading: false, isAuthenticated: false, user: null, error: null })
          try { await endSession() } catch { return }
        }
      }
    }

    const refreshTimer = window.setInterval(refresh, 20000)
    keycloak.onTokenExpired = refresh
    return () => {
      active = false
      window.clearInterval(refreshTimer)
      keycloak.onTokenExpired = undefined
    }
  }, [authState.isAuthenticated])

  async function logout() {
    setAuthState({ isLoading: false, isAuthenticated: false, user: null, error: null })
    return endSession()
  }

  const value = useMemo(() => ({
    ...authState,
    keycloak,
    login: startLogin,
    logout,
    refreshToken: refreshAccessToken,
  }), [authState])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

