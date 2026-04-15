function DiagnosisCard({ analysis }) {
  if (!analysis) {
    return (
      <section className="card diagnosis-card">
        <h3>AI Triage Result</h3>
        <p className="muted">
          No analysis yet. Send a symptom message to generate probable conditions, urgency level, and department
          guidance.
        </p>
      </section>
    )
  }

  const probableDiseases = analysis.probable_diseases || []
  const detectedSymptoms = analysis.detected_symptoms || []
  const precautions = analysis.precautions || []
  const recommendation = analysis.recommended_appointment || {}
  const topCondition = probableDiseases[0]

  return (
    <section className="card diagnosis-card">
      <h3>AI Triage Result</h3>
      <p className={`chip urgency-chip ${analysis.urgency_level}`}>Urgency: {analysis.urgency_level}</p>
      <p className="chip">Department: {analysis.department || 'General Medicine'}</p>

      {topCondition ? (
        <article className="timeline-item diagnosis-highlight">
          <h4>Most likely condition: {topCondition.disease}</h4>
          {topCondition.description ? <p className="muted">{topCondition.description}</p> : null}
        </article>
      ) : null}

      {detectedSymptoms.length > 0 ? (
        <div className="diagnosis-symptoms">
          <h4>Detected symptoms</h4>
          <div className="symptom-tag-list">
            {detectedSymptoms.map((symptom) => (
              <span key={symptom} className="chip">
                {symptom}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <div className="score-list">
        {probableDiseases.map((item) => (
          <div key={item.disease} className="score-row">
            <span>{item.disease}</span>
            <div className="score-bar">
              <div style={{ width: `${item.score}%` }} className="score-fill" />
            </div>
            <strong>{item.score}%</strong>
          </div>
        ))}
      </div>

      {recommendation.should_schedule ? (
        <article className="timeline-item diagnosis-appointment-box">
          <h4>Appointment recommendation</h4>
          <p>
            Suggested window: <strong>{recommendation.suggested_window}</strong>
          </p>
          <p>
            Suggested date: <strong>{recommendation.suggested_datetime_label}</strong>
          </p>
          <p>
            Department: <strong>{recommendation.department || analysis.department}</strong>
          </p>
          {(recommendation.candidate_doctors || []).length > 0 ? (
            <div>
              <p className="muted">Candidate doctors</p>
              <ul className="compact-list">
                {recommendation.candidate_doctors.map((doctor) => (
                  <li key={doctor.id}>
                    {doctor.email} - {doctor.specialization}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </article>
      ) : (
        <p className="muted">Enable appointment recommendation if you want a suggested booking window.</p>
      )}

      {precautions.length > 0 ? (
        <div className="diagnosis-precautions">
          <h4>Suggested precautions</h4>
          <ul className="compact-list">
            {precautions.slice(0, 4).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="muted">{analysis.summary}</p>
    </section>
  )
}

export default DiagnosisCard
