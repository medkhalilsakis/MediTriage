import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

function Topbar() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const now = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date())

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="topbar">
      <div>
        <p className="topbar-date">{now}</p>
        <h1 className="topbar-title">Welcome, {user?.first_name || user?.email}</h1>
        <p className="topbar-role">
          Role: <span className={`role-chip ${user?.role || ''}`}>{user?.role}</span>
        </p>
      </div>
      <button className="danger-btn topbar-logout" onClick={handleLogout}>
        Logout
      </button>
    </header>
  )
}

export default Topbar
