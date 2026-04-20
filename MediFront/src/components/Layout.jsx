import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { sendPresenceHeartbeat } from '../api/messagingApi'
import { useAuthStore } from '../store/authStore'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

const PRESENCE_HEARTBEAT_MS = 20000

const getTokenExpiryMs = (token) => {
  try {
    const payload = token.split('.')[1]
    if (!payload) {
      return null
    }

    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const normalized = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    const decoded = JSON.parse(atob(normalized))
    if (!decoded?.exp) {
      return null
    }

    return Number(decoded.exp) * 1000
  } catch {
    return null
  }
}

const isTokenExpired = (token, safetyBufferSeconds = 20) => {
  const expiry = getTokenExpiryMs(token)
  if (!expiry) {
    return false
  }
  return Date.now() >= (expiry - (safetyBufferSeconds * 1000))
}

const postPresenceKeepAlive = (token, isOnline) => {
  if (!token) {
    return
  }

  const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
  const endpoint = `${apiBaseUrl}/messaging/presence/heartbeat/`

  try {
    fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ is_online: isOnline }),
      keepalive: true,
    })
  } catch {
    // Ignore best-effort presence update errors.
  }
}

function Layout() {
  const accessToken = useAuthStore((state) => state.accessToken)

  useEffect(() => {
    if (!accessToken || isTokenExpired(accessToken)) {
      return undefined
    }

    sendPresenceHeartbeat({ is_online: true }).catch(() => {})

    const heartbeatTimer = setInterval(() => {
      if (isTokenExpired(accessToken)) {
        return
      }
      sendPresenceHeartbeat({ is_online: true }).catch(() => {})
    }, PRESENCE_HEARTBEAT_MS)

    const handlePageClose = () => {
      if (isTokenExpired(accessToken)) {
        return
      }
      postPresenceKeepAlive(accessToken, false)
    }

    window.addEventListener('pagehide', handlePageClose)
    window.addEventListener('beforeunload', handlePageClose)

    return () => {
      clearInterval(heartbeatTimer)
      window.removeEventListener('pagehide', handlePageClose)
      window.removeEventListener('beforeunload', handlePageClose)
      if (!isTokenExpired(accessToken)) {
        postPresenceKeepAlive(accessToken, false)
      }
    }
  }, [accessToken])

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="content-shell">
        <Topbar />
        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout
