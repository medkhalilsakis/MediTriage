import { NavLink } from 'react-router-dom'
import {
  BarChart3,
  BellRing,
  Bot,
  CalendarDays,
  FileText,
  HeartPulse,
  LayoutDashboard,
  MessageSquare,
  Settings,
  Shield,
  Stethoscope,
  Users,
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'

const navByRole = {
  patient: [
    { to: '/patient/dashboard', label: 'Dashboard', icon: LayoutDashboard, section: 'Overview' },
    { to: '/patient/appointments', label: 'Appointments', icon: CalendarDays, section: 'Care Journey' },
    { to: '/patient/medical-records', label: 'Medical Records', icon: FileText, section: 'Care Journey' },
    { to: '/patient/messages', label: 'Messaging (Realtime)', icon: MessageSquare, section: 'Communication' },
    { to: '/patient/chatbot', label: 'AI Chatbot (Optional)', icon: Bot, section: 'Communication' },
    { to: '/patient/notifications', label: 'Notifications', icon: BellRing, section: 'Communication' },
    { to: '/patient/settings', label: 'Account & Security', icon: Shield, section: 'Account' },
  ],
  doctor: [
    { to: '/doctor/dashboard', label: 'Dashboard', icon: LayoutDashboard, section: 'Overview' },
    { to: '/doctor/patients-today', label: 'Patients Today', icon: HeartPulse, section: 'Clinical Flow' },
    { to: '/doctor/consultation', label: 'Consultation', icon: Stethoscope, section: 'Clinical Flow' },
    { to: '/doctor/prescriptions', label: 'Prescriptions', icon: FileText, section: 'Clinical Flow' },
    { to: '/doctor/follow-up', label: 'Follow-up', icon: CalendarDays, section: 'Clinical Flow' },
    { to: '/doctor/history', label: 'History', icon: BarChart3, section: 'Analytics' },
    { to: '/doctor/messages', label: 'Messaging (Realtime)', icon: MessageSquare, section: 'Communication' },
    { to: '/doctor/settings', label: 'Settings', icon: Settings, section: 'Account' },
  ],
  admin: [
    { to: '/admin/dashboard', label: 'KPIs Dashboard', icon: LayoutDashboard, section: 'Overview' },
    { to: '/admin/users', label: 'Users', icon: Users, section: 'Governance' },
    { to: '/admin/reports', label: 'Reports', icon: BarChart3, section: 'Governance' },
    { to: '/admin/messages', label: 'Messaging (Realtime)', icon: MessageSquare, section: 'Communication' },
    { to: '/admin/settings', label: 'Settings', icon: Settings, section: 'Account' },
  ],
}

function Sidebar() {
  const user = useAuthStore((state) => state.user)
  const links = navByRole[user?.role] || []
  const displayName = user?.first_name?.trim() || user?.email?.split('@')[0] || 'User'

  const groupedLinks = links.reduce((acc, item) => {
    const section = item.section || 'General'
    if (!acc[section]) {
      acc[section] = []
    }
    acc[section].push(item)
    return acc
  }, {})

  return (
    <aside className="sidebar">
      <div className="brand-wrap sidebar-brand-top">
        <span className="brand-mark brand-mark-logo" aria-hidden="true">
          <img src="/visuals/meditriage-mark.svg" alt="" className="brand-mark-image" />
        </span>
        <div>
          <h2 className="brand">MediTriage</h2>
          <p className="subtitle">Intelligent Healthcare Platform</p>
        </div>
      </div>

      <section className="sidebar-profile-card">
        <div className="sidebar-avatar">
          {user?.profile_image_url ? (
            <img src={user.profile_image_url} alt={displayName} className="sidebar-avatar-image" />
          ) : (
            <span>{displayName.charAt(0).toUpperCase()}</span>
          )}
        </div>
        <div>
          <p className="sidebar-profile-name">{displayName}</p>
          <p className="sidebar-profile-email">{user?.email || 'guest@meditriage'}</p>
        </div>
        <p className="role-pill">{(user?.role || 'guest').toUpperCase()}</p>
      </section>

      <div className="sidebar-nav-stack">
        {Object.entries(groupedLinks).map(([section, sectionLinks]) => (
          <section key={section} className="sidebar-nav-section">
            <p className="nav-caption sidebar-section-title">{section}</p>
            <nav className="sidebar-nav">
              {sectionLinks.map((item) => {
                const ItemIcon = item.icon
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                  >
                    <span className="nav-link-content">
                      <span className="nav-link-icon">
                        <ItemIcon size={16} />
                      </span>
                      <span>{item.label}</span>
                    </span>
                  </NavLink>
                )
              })}
            </nav>
          </section>
        ))}
      </div>

      <section className="sidebar-visual-card">
        <img src="/visuals/sidebar-health.svg" alt="Healthcare illustration" className="sidebar-illustration" />
        <p className="sidebar-visual-title">Unified Care Operations</p>
        <p className="sidebar-visual-note">Appointments, records, messaging and analytics in one structure.</p>
      </section>
    </aside>
  )
}

export default Sidebar
