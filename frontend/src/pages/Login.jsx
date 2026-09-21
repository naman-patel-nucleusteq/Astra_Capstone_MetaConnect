import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import LoadingScreen from '../components/LoadingScreen.jsx'
import { useAuth } from '../services/auth.js'

function Login() {
  const { isLoading, isAuthenticated, error: authError, login } = useAuth()

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !authError) {
      login()
    }
  }, [isLoading, isAuthenticated, authError, login])

  if (isLoading || isAuthenticated) {
    return isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoadingScreen />
  }

  if (authError) {
    return (
      <main className="auth-error-page">
        <div className="brand-mark">M</div>
        <span className="eyebrow">Authentication unavailable</span>
        <h1>Keycloak could not finish sign-in.</h1>
        <p>{authError}</p>
        <small>The frontend does not contain or send a client secret.</small>
      </main>
    )
  }

  return (
    <main className="login-page">
      
      <div className="login-panel">
        <div className="brand-lockup">
          <div className="brand-mark">M</div>
          <div>
            <strong>MetaConnect</strong>
            <span>Data catalog</span>
          </div>
        </div>

        <span className="eyebrow">Private workspace</span>
        <h1>Make your data discoverable.</h1>
        <p>Sign in to explore your organization’s metadata and data connections.</p>
        <p className="login-redirect-copy">Redirecting to secure Keycloak sign-in...</p>
        <small>Authentication is managed by your organization.</small>
      </div>

      <div className="login-aside">
        <span className="aside-number">01</span>
        <p>One clear view of the systems, structures, and data your teams rely on.</p>
      </div>

    </main>
  )
}

export default Login