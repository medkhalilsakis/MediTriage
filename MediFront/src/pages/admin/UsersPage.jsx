import { useQuery } from '@tanstack/react-query'
import { listDoctorProfiles } from '../../api/doctorsApi'
import { listPatientProfiles } from '../../api/patientsApi'

function UsersPage() {
  const patientsQuery = useQuery({ queryKey: ['admin-patients'], queryFn: listPatientProfiles })
  const doctorsQuery = useQuery({ queryKey: ['admin-doctors'], queryFn: listDoctorProfiles })

  const patients = patientsQuery.data?.results || patientsQuery.data || []
  const doctors = doctorsQuery.data?.results || doctorsQuery.data || []

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>Users Directory</h2>
        <p className="muted">Explore patient and doctor profiles with a consolidated operational view.</p>
      </section>

      <div className="split-grid">
        <section className="card">
          <h3>Patients</h3>
          {patients.length === 0 ? <p className="muted">No patients found.</p> : null}
          {patients.map((patient) => (
            <article key={patient.id} className="timeline-item">
              <h4>{patient.user_email}</h4>
              <p>Blood group: {patient.blood_group || 'N/A'}</p>
            </article>
          ))}
        </section>

        <section className="card">
          <h3>Doctors</h3>
          {doctors.length === 0 ? <p className="muted">No doctors found.</p> : null}
          {doctors.map((doctor) => (
            <article key={doctor.id} className="timeline-item">
              <h4>{doctor.user_email}</h4>
              <p>Specialization: {doctor.specialization}</p>
              <p>Department: {doctor.department_label || doctor.department || 'General Medicine'}</p>
            </article>
          ))}
        </section>
      </div>
    </div>
  )
}

export default UsersPage
