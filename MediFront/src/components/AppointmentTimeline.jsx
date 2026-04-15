function AppointmentTimeline({ items = [] }) {
  return (
    <section className="card">
      <h3>Appointment Timeline</h3>
      <div className="timeline">
        {items.length === 0 ? <p className="muted">No appointments available right now.</p> : null}
        {items.map((item) => (
          <article key={item.id} className="timeline-item">
            <p className="muted">{new Date(item.scheduled_at).toLocaleString()}</p>
            <h4>{item.reason || 'General consultation'}</h4>
            <p>
              Department: <strong>{item.department_label || item.department || 'General Medicine'}</strong>
            </p>
            <p>
              Doctor: <strong>{item.doctor_email || 'Assigned automatically'}</strong>
            </p>
            <p>
              Status: <span className={`status-tag ${item.status}`}>{item.status}</span>
            </p>
            <p>
              Urgency: <span className={`urgency-tag ${item.urgency_level}`}>{item.urgency_level}</span>
            </p>
          </article>
        ))}
      </div>
    </section>
  )
}

export default AppointmentTimeline
