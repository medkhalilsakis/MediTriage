import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <div className="center-page">
      <section className="card auth-card center-card">
        <p className="auth-eyebrow">Routing</p>
        <h1 className="auth-title">Page Not Found</h1>
        <p className="auth-note">The page you are looking for does not exist or has been moved.</p>
        <Link className="primary-link" to="/login">Go to login</Link>
      </section>
    </div>
  )
}

export default NotFoundPage
