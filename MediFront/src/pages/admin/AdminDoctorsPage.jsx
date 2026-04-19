import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Search, ShieldAlert, ShieldCheck, Stethoscope } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  deactivateDoctorAccount,
  listDoctorProfiles,
  reactivateDoctorAccount,
} from '../../api/doctorsApi'

const toInitials = (firstName, lastName, email) => {
  const seed = `${firstName || ''}${lastName || ''}`.trim()
  if (seed) {
    return seed
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((value) => value[0]?.toUpperCase() || '')
      .join('')
  }
  return (email?.[0] || 'D').toUpperCase()
}

function AdminDoctorsPage() {
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [pendingDoctorId, setPendingDoctorId] = useState(null)

  const doctorsQuery = useQuery({ queryKey: ['admin-doctors'], queryFn: listDoctorProfiles })

  const toggleDoctorMutation = useMutation({
    mutationFn: ({ id, activate }) => (activate ? reactivateDoctorAccount(id) : deactivateDoctorAccount(id)),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['admin-doctors'] })
      toast.success(variables.activate ? 'Doctor account reactivated.' : 'Doctor account deactivated.')
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail || 'Unable to update doctor account status.'
      toast.error(String(detail))
    },
    onSettled: () => {
      setPendingDoctorId(null)
    },
  })

  const doctors = useMemo(
    () => doctorsQuery.data?.results || doctorsQuery.data || [],
    [doctorsQuery.data],
  )

  const filteredDoctors = useMemo(() => {
    const needle = searchTerm.trim().toLowerCase()
    if (!needle) {
      return doctors
    }

    return doctors.filter((doctor) => {
      const haystack = [
        doctor.user_email,
        doctor.user_first_name,
        doctor.user_last_name,
        doctor.specialization,
        doctor.department_label,
      ]
        .join(' ')
        .toLowerCase()

      return haystack.includes(needle)
    })
  }, [doctors, searchTerm])

  const activeDoctors = doctors.filter((doctor) => doctor.user_is_active).length

  const handleDoctorToggle = (doctor, activate) => {
    const fullName = [doctor.user_first_name, doctor.user_last_name].filter(Boolean).join(' ').trim() || doctor.user_email
    const actionLabel = activate ? 'reactivate' : 'deactivate'
    const confirmation = window.confirm(`Do you want to ${actionLabel} Dr. ${fullName}?`)

    if (!confirmation) {
      return
    }

    setPendingDoctorId(doctor.id)
    toggleDoctorMutation.mutate({ id: doctor.id, activate })
  }

  if (doctorsQuery.isLoading) {
    return <p>Loading doctors directory...</p>
  }

  return (
    <div className="stacked-grid admin-users-page admin-users-collection-page">
      <section className="card page-hero admin-users-hero">
        <div>
          <h2>Doctors Directory</h2>
          <p className="muted">
            Independent doctor page with profile cards, image, and account activation controls.
          </p>
        </div>
        <div className="admin-users-subnav">
          <Link to="/admin/users/patients" className="admin-users-subnav-link">
            Patients
          </Link>
          <Link to="/admin/users/doctors" className="admin-users-subnav-link active">
            Doctors
          </Link>
        </div>
      </section>

      <section className="card admin-users-panel">
        <div className="admin-users-panel-header">
          <div>
            <h3>Doctor cards</h3>
            <p className="muted">Each card contains profile image, specialization data, and admin controls.</p>
          </div>
          <span className="chip">{filteredDoctors.length} visible</span>
        </div>

        <div className="admin-users-toolbar">
          <label className="admin-users-search" htmlFor="doctor-search-page">
            <Search size={15} />
            <input
              id="doctor-search-page"
              type="search"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search by name, email, specialization, department..."
            />
          </label>
          <span className="chip">{activeDoctors} active / {doctors.length} total</span>
        </div>

        <div className="admin-entity-grid">
          {filteredDoctors.length === 0 ? (
            <article className="card admin-entity-card admin-entity-card-empty">
              <Stethoscope size={20} />
              <p className="muted">No doctor matches the current filters.</p>
            </article>
          ) : null}

          {filteredDoctors.map((doctor) => {
            const fullName = [doctor.user_first_name, doctor.user_last_name].filter(Boolean).join(' ').trim() || 'Unnamed doctor'
            const isActive = Boolean(doctor.user_is_active)
            const isPending = pendingDoctorId === doctor.id && toggleDoctorMutation.isPending

            return (
              <article key={doctor.id} className="card admin-entity-card">
                <header className="admin-entity-head">
                  <div className="admin-entity-avatar" aria-hidden="true">
                    {doctor.user_profile_image_url ? (
                      <img src={doctor.user_profile_image_url} alt={fullName} className="admin-entity-avatar-image" />
                    ) : (
                      <span>{toInitials(doctor.user_first_name, doctor.user_last_name, doctor.user_email)}</span>
                    )}
                  </div>

                  <div className="admin-entity-identity">
                    <h4>Dr. {fullName}</h4>
                    <p className="admin-user-email">{doctor.user_email}</p>
                  </div>

                  <span className={`account-state ${isActive ? 'active' : 'inactive'}`}>
                    {isActive ? 'Active' : 'Inactive'}
                  </span>
                </header>

                <div className="admin-entity-body">
                  <p className="admin-user-meta">
                    Specialization: <strong>{doctor.specialization || 'General specialist'}</strong>
                  </p>
                  <p className="admin-user-meta">
                    Department: <strong>{doctor.department_label || doctor.department || 'General medicine'}</strong>
                  </p>
                  <p className="admin-user-meta">
                    Experience: <strong>{doctor.years_of_experience || 0} years</strong>
                  </p>
                </div>

                <footer className="admin-entity-actions">
                  {isActive ? (
                    <button
                      type="button"
                      className="secondary-btn inline-action"
                      onClick={() => handleDoctorToggle(doctor, false)}
                      disabled={isPending || toggleDoctorMutation.isPending}
                    >
                      <ShieldAlert size={15} />
                      {isPending ? 'Deactivating...' : 'Deactivate'}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="ghost-btn inline-action"
                      onClick={() => handleDoctorToggle(doctor, true)}
                      disabled={isPending || toggleDoctorMutation.isPending}
                    >
                      <ShieldCheck size={15} />
                      {isPending ? 'Reactivating...' : 'Reactivate'}
                    </button>
                  )}
                </footer>
              </article>
            )
          })}
        </div>
      </section>
    </div>
  )
}

export default AdminDoctorsPage
