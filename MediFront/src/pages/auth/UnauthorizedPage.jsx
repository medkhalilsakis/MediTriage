import { Link } from 'react-router-dom'

function UnauthorizedPage() {
  return (
    <div className="center-page">
      <section className="card auth-card center-card">
        <p className="auth-eyebrow">Access Control</p>
        <h1 className="auth-title">Unauthorized</h1>
        <p className="auth-note">You do not have permission to access this area.</p>
        <Link className="primary-link" to="/login">Back to login</Link>
      </section>
    </div>
  )
}

export default UnauthorizedPage
