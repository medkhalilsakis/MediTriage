import { useQuery } from '@tanstack/react-query'
import { listPrescriptions } from '../../api/prescriptionsApi'

function ReportsPage() {
  const { data } = useQuery({ queryKey: ['reports-prescriptions'], queryFn: listPrescriptions })
  const prescriptions = data?.results || data || []

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>Clinical Reports</h2>
        <p className="muted">Track prescription activity and identify workload trends across the organization.</p>
      </section>

      <section className="card">
        <h3>Reports</h3>
        <p className="muted">Prescription activity report</p>
        {prescriptions.length === 0 ? <p className="muted">No report data available yet.</p> : null}
        {prescriptions.map((item) => (
          <article key={item.id} className="timeline-item">
            <h4>Prescription #{item.id}</h4>
            <p>Doctor: {item.doctor_email}</p>
            <p>Patient: {item.patient_email}</p>
            <p>Date: {new Date(item.created_at).toLocaleString()}</p>
          </article>
        ))}
      </section>
    </div>
  )
}

export default ReportsPage
