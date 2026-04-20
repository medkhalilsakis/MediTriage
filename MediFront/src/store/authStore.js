import { create } from 'zustand'

const AUTH_STORAGE_KEY = 'meditriage_auth'
const LEGACY_AUTH_STORAGE_KEY = 'medismart_auth'
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'

const postOfflinePresence = (accessToken) => {
  if (!accessToken) {
    return
  }

  try {
    fetch(`${API_BASE_URL}/messaging/presence/heartbeat/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ is_online: false }),
      keepalive: true,
    })
  } catch {
    // Ignore best-effort presence update errors during logout.
  }
}

const getInitialAuth = () => {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY) || localStorage.getItem(LEGACY_AUTH_STORAGE_KEY)
    if (!raw) return { user: null, accessToken: null, refreshToken: null }
    return JSON.parse(raw)
  } catch {
    return { user: null, accessToken: null, refreshToken: null }
  }
}

const persistAuth = (state) => {
  const payload = {
    user: state.user,
    accessToken: state.accessToken,
    refreshToken: state.refreshToken,
  }
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(payload))
  localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY)
}

const initial = getInitialAuth()

export const useAuthStore = create((set, get) => ({
  user: initial.user,
  accessToken: initial.accessToken,
  refreshToken: initial.refreshToken,

  setAuth: ({ user, access, refresh }) => {
    set({ user, accessToken: access, refreshToken: refresh })
    persistAuth(get())
  },

  setTokens: (access, refresh) => {
    set((state) => ({
      ...state,
      accessToken: access,
      refreshToken: refresh,
    }))
    persistAuth(get())
  },

  updateUser: (user) => {
    set((state) => ({ ...state, user }))
    persistAuth(get())
  },

  logout: () => {
    postOfflinePresence(get().accessToken)
    set({ user: null, accessToken: null, refreshToken: null })
    localStorage.removeItem(AUTH_STORAGE_KEY)
    localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY)
  },

  isAuthenticated: () => Boolean(get().accessToken),
}))
