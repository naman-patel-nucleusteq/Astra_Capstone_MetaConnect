import axios from 'axios'
import { getKeycloak, refreshAccessToken } from './keycloakAuth.js'

const applicationUrl = import.meta.env.VITE_APP_URL || 'http://localhost:3000'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(async (config) => {
  const keycloak = getKeycloak()
  if (keycloak.authenticated) {
    try {
      await refreshAccessToken(30)
    } 
    catch (error) {
      await keycloak.logout({ redirectUri: applicationUrl + '/' })
      return Promise.reject(error)
    }
    config.headers.Authorization = `Bearer ${keycloak.token}`
  }
  return config
})


api.interceptors.response.use((response) => response, 
    async (error) => {
    const originalRequest = error.config
    const keycloak = getKeycloak()

    if (error.response?.status !== 401 || originalRequest?._retry || !keycloak.authenticated) {
      return Promise.reject(error)
    }

    originalRequest._retry = true

    try {
      await refreshAccessToken(30)
      originalRequest.headers.Authorization = `Bearer ${keycloak.token}`
      return api(originalRequest)
    } 
    catch {
      await keycloak.logout({ redirectUri: applicationUrl + '/' })
      return Promise.reject(error)
    }
  },
)

export default api