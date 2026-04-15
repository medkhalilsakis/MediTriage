import { create } from 'zustand'

const getInitialAuth = () => {
  try {
    const raw = localStorage.getItem('medismart_auth')
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
  localStorage.setItem('medismart_auth', JSON.stringify(payload))
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
    set({ user: null, accessToken: null, refreshToken: null })
    localStorage.removeItem('medismart_auth')
  },

  isAuthenticated: () => Boolean(get().accessToken),
}))
