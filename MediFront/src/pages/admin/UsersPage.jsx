import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ShieldAlert, Stethoscope, Users } from 'lucide-react'
import { listDoctorProfiles } from '../../api/doctorsApi'
import { listPatientProfiles } from '../../api/patientsApi'

function UsersPage() {
  const patientsQuery = useQuery({ queryKey: ['admin-patients'], queryFn: listPatientProfiles })
  const doctorsQuery = useQuery({ queryKey: ['admin-doctors'], queryFn: listDoctorProfiles })

  const patients = useMemo(
    () => patientsQuery.data?.results || patientsQuery.data || [],
    [patientsQuery.data],
  )
  const doctors = useMemo(
    () => doctorsQuery.data?.results || doctorsQuery.data || [],
    [doctorsQuery.data],
  )

  const activeDoctors = doctors.filter((doctor) => doctor.user_is_active).length
  const archivedPatients = patients.filter((patient) => patient.is_account_deleted).length

  if (patientsQuery.isLoading || doctorsQuery.isLoading) {
    return <p>Loading users directory...</p>
  }

  return (
    <div className="stacked-grid dashboard-surface dashboard-compact dashboard-admin admin-users-page admin-users-hub-page">
      <section className="card page-hero admin-users-hero">
        <div>
          <h2>Users Governance</h2>
          <p className="muted">
            Manage patients and doctors independently with dedicated pages and focused admin actions.
          </p>
        </div>
        <div className="admin-users-metrics">
          <article className="admin-users-metric">
            <Users size={18} />
            <div>
              <p>Total Patients</p>
              <strong>{patients.length}</strong>
            </div>
          </article>
          <article className="admin-users-metric">
            <Stethoscope size={18} />
            <div>
              <p>Active Doctors</p>
              <strong>
                {activeDoctors} / {doctors.length}
              </strong>
            </div>
          </article>
          <article className="admin-users-metric">
            <ShieldAlert size={18} />
            <div>
              <p>Archived Patients</p>
              <strong>{archivedPatients}</strong>
            </div>
          </article>
        </div>
      </section>

      <section className="split-grid admin-users-hub-grid">
        <article className="card admin-users-nav-card">
          <div className="admin-users-nav-card-head">
            <Users size={20} />
            <span className="chip">Patients</span>
          </div>
          <h3>Patients Directory</h3>
          <p className="muted">
            Browse patient cards with profile picture, identity details, and archival delete action.
          </p>
          <p className="admin-users-nav-stat">
            <strong>{patients.length}</strong> patient accounts
          </p>
          <Link to="/admin/users/patients" className="admin-users-nav-btn">
            Open patients page
            <ArrowRight size={16} />
          </Link>
        </article>

        <article className="card admin-users-nav-card">
          <div className="admin-users-nav-card-head">
            <Stethoscope size={20} />
            <span className="chip">Doctors</span>
          </div>
          <h3>Doctors Directory</h3>
          <p className="muted">
            Browse doctor cards with profile picture, specialization, and activate/deactivate controls.
          </p>
          <p className="admin-users-nav-stat">
            <strong>{activeDoctors}</strong> active doctors
            <span className="muted"> out of {doctors.length}</span>
          </p>
          <Link to="/admin/users/doctors" className="admin-users-nav-btn">
            Open doctors page
            <ArrowRight size={16} />
          </Link>
        </article>
      </section>

      <section className="card admin-users-info-banner">
        <ShieldAlert size={18} />
        <p>
          Archived patients: <strong>{archivedPatients}</strong>. Patient historical records remain preserved.
        </p>
      </section>
    </div>
  )
}

export default UsersPage
