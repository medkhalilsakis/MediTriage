import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Search, Trash2, Users } from 'lucide-react'
import toast from 'react-hot-toast'
import { deletePatientAccountByAdmin, listPatientProfiles } from '../../api/patientsApi'

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
  return (email?.[0] || 'P').toUpperCase()
}

function AdminPatientsPage() {
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [showArchivedPatients, setShowArchivedPatients] = useState(false)
  const [pendingPatientId, setPendingPatientId] = useState(null)

  const patientsQuery = useQuery({ queryKey: ['admin-patients'], queryFn: listPatientProfiles })

  const deletePatientMutation = useMutation({
    mutationFn: (id) => deletePatientAccountByAdmin(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-patients'] })
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] })
      toast.success('Patient account archived. Future appointments removed.')
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail || 'Unable to archive patient account.'
      toast.error(String(detail))
    },
    onSettled: () => {
      setPendingPatientId(null)
    },
  })

  const patients = useMemo(
    () => patientsQuery.data?.results || patientsQuery.data || [],
    [patientsQuery.data],
  )

  const filteredPatients = useMemo(() => {
    const needle = searchTerm.trim().toLowerCase()

    return patients
      .filter((patient) => (showArchivedPatients ? true : !patient.is_account_deleted))
      .filter((patient) => {
        if (!needle) {
          return true
        }

        const haystack = [
          patient.user_email,
          patient.user_first_name,
          patient.user_last_name,
          patient.blood_group,
          patient.gender,
          patient.allergies,
        ]
          .join(' ')
          .toLowerCase()

        return haystack.includes(needle)
      })
  }, [patients, searchTerm, showArchivedPatients])

  const archivedPatients = patients.filter((patient) => patient.is_account_deleted).length

  const handleDeletePatient = (patient) => {
    const fullName = [patient.user_first_name, patient.user_last_name].filter(Boolean).join(' ').trim() || patient.user_email
    const confirmation = window.confirm(
      `Delete account for ${fullName}? Future appointments will be removed while historical records remain archived.`,
    )

    if (!confirmation) {
      return
    }

    setPendingPatientId(patient.id)
    deletePatientMutation.mutate(patient.id)
  }

  if (patientsQuery.isLoading) {
    return <p>Loading patient directory...</p>
  }

  return (
    <div className="stacked-grid admin-users-page admin-users-collection-page">
      <section className="card page-hero admin-users-hero">
        <div>
          <h2>Patients Directory</h2>
          <p className="muted">
            Independent patient page with identity cards, profile image, and archive action.
          </p>
        </div>
        <div className="admin-users-subnav">
          <Link to="/admin/users/patients" className="admin-users-subnav-link active">
            Patients
          </Link>
          <Link to="/admin/users/doctors" className="admin-users-subnav-link">
            Doctors
          </Link>
        </div>
      </section>

      <section className="card admin-users-panel">
        <div className="admin-users-panel-header">
          <div>
            <h3>Patient cards</h3>
            <p className="muted">Each card contains profile information, image, and admin action.</p>
          </div>
          <span className="chip">{filteredPatients.length} visible</span>
        </div>

        <div className="admin-users-toolbar">
          <label className="admin-users-search" htmlFor="patient-search-page">
            <Search size={15} />
            <input
              id="patient-search-page"
              type="search"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search by name, email, blood group, allergies..."
            />
          </label>

          <label className="admin-users-checkbox" htmlFor="show-archived-patients-page">
            <input
              id="show-archived-patients-page"
              type="checkbox"
              checked={showArchivedPatients}
              onChange={(event) => setShowArchivedPatients(event.target.checked)}
            />
            Show archived patients ({archivedPatients})
          </label>
        </div>

        <div className="admin-entity-grid">
          {filteredPatients.length === 0 ? (
            <article className="card admin-entity-card admin-entity-card-empty">
              <Users size={20} />
              <p className="muted">No patient matches the current filters.</p>
            </article>
          ) : null}

          {filteredPatients.map((patient) => {
            const isArchived = Boolean(patient.is_account_deleted)
            const isPending = pendingPatientId === patient.id && deletePatientMutation.isPending
            const fullName = [patient.user_first_name, patient.user_last_name].filter(Boolean).join(' ').trim() || 'Unnamed patient'
            const deletedAtLabel = patient.account_deleted_at ? new Date(patient.account_deleted_at).toLocaleString() : ''

            return (
              <article key={patient.id} className={`card admin-entity-card ${isArchived ? 'is-archived' : ''}`}>
                <header className="admin-entity-head">
                  <div className="admin-entity-avatar" aria-hidden="true">
                    {patient.user_profile_image_url ? (
                      <img src={patient.user_profile_image_url} alt={fullName} className="admin-entity-avatar-image" />
                    ) : (
                      <span>{toInitials(patient.user_first_name, patient.user_last_name, patient.user_email)}</span>
                    )}
                  </div>

                  <div className="admin-entity-identity">
                    <h4>{fullName}</h4>
                    <p className="admin-user-email">{patient.user_email}</p>
                  </div>

                  <span className={`account-state ${isArchived ? 'archived' : 'active'}`}>
                    {isArchived ? 'Archived' : 'Active'}
                  </span>
                </header>

                <div className="admin-entity-body">
                  <p className="admin-user-meta">
                    Blood group: <strong>{patient.blood_group || 'N/A'}</strong>
                  </p>
                  <p className="admin-user-meta">
                    Gender: <strong>{patient.gender || 'N/A'}</strong>
                  </p>
                  <p className="admin-user-meta">
                    Allergies: <strong>{patient.allergies || 'None reported'}</strong>
                  </p>
                  {isArchived && deletedAtLabel ? (
                    <p className="admin-user-meta">
                      Archived at: <strong>{deletedAtLabel}</strong>
                    </p>
                  ) : null}
                </div>

                <footer className="admin-entity-actions">
                  <button
                    type="button"
                    className="danger-btn inline-action"
                    onClick={() => handleDeletePatient(patient)}
                    disabled={isArchived || isPending || deletePatientMutation.isPending}
                  >
                    <Trash2 size={15} />
                    {isArchived ? 'Archived' : isPending ? 'Archiving...' : 'Delete account'}
                  </button>
                </footer>
              </article>
            )
          })}
        </div>
      </section>
    </div>
  )
}

export default AdminPatientsPage
