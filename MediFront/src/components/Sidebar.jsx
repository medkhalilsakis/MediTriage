import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

const navByRole = {
  patient: [
    { to: '/patient/dashboard', label: 'Dashboard' },
    { to: '/patient/chatbot', label: 'AI Chatbot (Optional)' },
    { to: '/patient/appointments', label: 'Appointments' },
    { to: '/patient/medical-records', label: 'Medical Records' },
    { to: '/patient/notifications', label: 'Notifications' },
    { to: '/patient/settings', label: 'Account & Security' },
  ],
  doctor: [
    { to: '/doctor/dashboard', label: 'Dashboard' },
    { to: '/doctor/patients-today', label: 'Patients Today' },
    { to: '/doctor/consultation', label: 'Consultation' },
    { to: '/doctor/prescriptions', label: 'Prescriptions' },
    { to: '/doctor/follow-up', label: 'Follow-up' },
  ],
  admin: [
    { to: '/admin/dashboard', label: 'KPIs Dashboard' },
    { to: '/admin/users', label: 'Users' },
    { to: '/admin/reports', label: 'Reports' },
  ],
}

function Sidebar() {
  const user = useAuthStore((state) => state.user)
  const links = navByRole[user?.role] || []

  return (
    <aside className="sidebar">
      <div className="brand-wrap">
        <span className="brand-mark" aria-hidden="true">+</span>
        <div>
          <h2 className="brand">MediSmart</h2>
          <p className="subtitle">Clinical Intelligence Suite</p>
        </div>
      </div>
      <p className="role-pill">{(user?.role || 'guest').toUpperCase()}</p>
      <p className="nav-caption">Navigation</p>
      <nav className="sidebar-nav">
        {links.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

export default Sidebar
