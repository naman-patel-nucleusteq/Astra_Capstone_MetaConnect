import Keycloak from 'keycloak-js'

const applicationUrl = import.meta.env.VITE_APP_URL || 'http://localhost:3000'

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8180',
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'metaconnect',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'metaconnect-app',
})

let initializationPromise

export function initializeKeycloak() {
  if (!initializationPromise) {
    initializationPromise = keycloak.init({
      onLoad: 'login-required',
      pkceMethod: 'S256',
      checkLoginIframe: false,
      redirectUri: applicationUrl + '/',
    })
  }

  return initializationPromise
}

export async function refreshAccessToken(minValidity = 30) {
  if (!keycloak.authenticated) {
    return false
  }

  return keycloak.updateToken(minValidity)
}

export function login() {
  return keycloak.login({ redirectUri: applicationUrl + '/' })
}

export function logout() {
  const redirectUri = applicationUrl + '/login'
  return keycloak.logout({ redirectUri })
}

export function getKeycloak() {
  return keycloak
}

export default keycloak