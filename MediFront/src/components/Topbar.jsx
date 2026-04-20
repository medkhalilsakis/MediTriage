import { Link, useLocation, useNavigate } from 'react-router-dom'
import { LogOut, MessageSquare, Settings2, Sparkles } from 'lucide-react'
import { sendPresenceHeartbeat } from '../api/messagingApi'
import { useAuthStore } from '../store/authStore'

const toTitle = (value) =>
  value
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')

function Topbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const displayName = user?.first_name?.trim() || user?.email?.split('@')[0] || 'User'
  const roleBasePath = user?.role ? `/${user.role}` : ''
  const messagesPath = roleBasePath ? `${roleBasePath}/messages` : '/login'
  const settingsPath = roleBasePath ? `${roleBasePath}/settings` : '/login'
  const activeRouteLabel = (() => {
    const segments = location.pathname.split('/').filter(Boolean)
    const segment = segments[1] || 'dashboard'
    return toTitle(segment)
  })()

  const now = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date())

  const handleLogout = async () => {
    try {
      await sendPresenceHeartbeat({ is_online: false })
    } catch {
      // Ignore best-effort presence update errors before local logout.
    }

    logout()
    navigate('/login')
  }

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="topbar-avatar" aria-hidden="true">
          {displayName.charAt(0).toUpperCase()}
        </div>
        <div className="topbar-meta">
          <p className="topbar-date">{now}</p>
          <h1 className="topbar-title">Welcome, {displayName}</h1>
          <p className="topbar-role">
            Role: <span className={`role-chip ${user?.role || ''}`}>{user?.role}</span>
          </p>
          <p className="topbar-current-page">
            <Sparkles size={14} />
            <span>Current: {activeRouteLabel}</span>
          </p>
        </div>
      </div>

      <div className="topbar-right">
        <div className="topbar-actions">
          <Link to={messagesPath} className="ghost-btn topbar-action">
            <MessageSquare size={16} />
            <span>Messages</span>
          </Link>
          <Link to={settingsPath} className="ghost-btn topbar-action">
            <Settings2 size={16} />
            <span>Settings</span>
          </Link>
        </div>
        <button className="danger-btn topbar-logout" onClick={handleLogout}>
          <LogOut size={16} />
          <span>Logout</span>
        </button>
      </div>
    </header>
  )
}

export default Topbar
