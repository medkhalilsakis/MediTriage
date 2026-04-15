function FollowUpTimeline({ followUps = [] }) {
  return (
    <section className="card">
      <h3>Follow-up Timeline</h3>
      <div className="timeline">
        {followUps.length === 0 ? <p className="muted">No follow-up scheduled yet.</p> : null}
        {followUps.map((item) => (
          <article key={item.id} className="timeline-item">
            <p className="muted">{new Date(item.scheduled_at).toLocaleString()}</p>
            <h4><span className={`status-tag ${item.status}`}>{item.status}</span></h4>
            <p>{item.notes || 'No notes'}</p>
          </article>
        ))}
      </div>
    </section>
  )
}

export default FollowUpTimeline
