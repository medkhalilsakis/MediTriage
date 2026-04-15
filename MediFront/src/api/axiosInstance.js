import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'

export const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

let isRefreshing = false
let pendingRequests = []
const PUBLIC_AUTH_ENDPOINTS = ['/auth/register/', '/auth/login/', '/auth/token/refresh/']

const isPublicAuthEndpoint = (url = '') => PUBLIC_AUTH_ENDPOINTS.some((endpoint) => url.includes(endpoint))

const isReactQueryContextParams = (params) => {
  if (!params || typeof params !== 'object') {
    return false
  }

  return Object.prototype.hasOwnProperty.call(params, 'queryKey')
    && Object.prototype.hasOwnProperty.call(params, 'signal')
    && Object.prototype.hasOwnProperty.call(params, 'client')
}

const processQueue = (error, token = null) => {
  pendingRequests.forEach((promise) => {
    if (error) {
      promise.reject(error)
    } else {
      promise.resolve(token)
    }
  })
  pendingRequests = []
}

axiosInstance.interceptors.request.use((config) => {
  const { accessToken } = useAuthStore.getState()
  if (accessToken && !isPublicAuthEndpoint(config.url)) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }

  // React Query passes an internal context object when queryFn is a direct reference.
  // Prevent leaking client/queryKey/signal as URL params.
  if (isReactQueryContextParams(config.params)) {
    config.params = {}
  }

  return config
})

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status
    const { refreshToken, setTokens, logout } = useAuthStore.getState()

    if (status === 401 && !isPublicAuthEndpoint(originalRequest?.url) && !refreshToken) {
      logout()
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
      return Promise.reject(error)
    }

    if (status !== 401 || originalRequest._retry || isPublicAuthEndpoint(originalRequest?.url)) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingRequests.push({ resolve, reject })
      }).then((newToken) => {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return axiosInstance(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
        refresh: refreshToken,
      })
      const newAccess = response.data.access
      const newRefresh = response.data.refresh || refreshToken
      setTokens(newAccess, newRefresh)
      processQueue(null, newAccess)
      originalRequest.headers.Authorization = `Bearer ${newAccess}`
      return axiosInstance(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError, null)
      logout()
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)
