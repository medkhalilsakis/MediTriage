import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { listAppointments } from '../../api/appointmentsApi'
import { listConsultations } from '../../api/medicalRecordsApi'

const PERIOD_PRESETS = {
  all: null,
  '7d': 7,
  '30d': 30,
  '90d': 90,
  year: 365,
}

const toLocalDateKey = (value) => {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const toDateStart = (value) => {
  if (!value) {
    return null
  }
  const date = new Date(`${value}T00:00:00`)
  return Number.isNaN(date.getTime()) ? null : date
}

const toDateEnd = (value) => {
  if (!value) {
    return null
  }
  const date = new Date(`${value}T23:59:59`)
  return Number.isNaN(date.getTime()) ? null : date
}

function HistoryPage() {
  const navigate = useNavigate()

  const [searchTerm, setSearchTerm] = useState('')
  const [exactDate, setExactDate] = useState('')
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [periodPreset, setPeriodPreset] = useState('all')
  const [sortBy, setSortBy] = useState('newest')

  const appointmentsQuery = useQuery({ queryKey: ['doctor-history-appointments'], queryFn: listAppointments })
  const consultationsQuery = useQuery({ queryKey: ['doctor-history-consultations'], queryFn: listConsultations })

  const appointments = appointmentsQuery.data?.results || appointmentsQuery.data || []
  const consultations = consultationsQuery.data?.results || consultationsQuery.data || []

  const appointmentById = useMemo(() => {
    const mapping = {}
    appointments.forEach((appointment) => {
      mapping[appointment.id] = appointment
    })
    return mapping
  }, [appointments])

  const historyEntries = useMemo(() => {
    const byAppointment = {}

    consultations.forEach((consultation) => {
      const appointment = consultation.appointment ? appointmentById[consultation.appointment] : null
      const key = consultation.appointment ? `appointment-${consultation.appointment}` : `consultation-${consultation.id}`
      byAppointment[key] = {
        key,
        appointmentId: consultation.appointment || null,
        consultationId: consultation.id,
        medicalRecordId: consultation.medical_record || null,
        patientEmail: consultation.patient_email || appointment?.patient_email || 'unknown-patient',
        reason: appointment?.reason || '',
        diagnosis: consultation.diagnosis || '',
        status: appointment?.status || 'consulted',
        eventDate: appointment?.scheduled_at || consultation.created_at,
      }
    })

    appointments
      .filter((appointment) => appointment.status === 'completed')
      .forEach((appointment) => {
        const key = `appointment-${appointment.id}`
        if (!byAppointment[key]) {
          byAppointment[key] = {
            key,
            appointmentId: appointment.id,
            consultationId: null,
            medicalRecordId: null,
            patientEmail: appointment.patient_email,
            reason: appointment.reason || '',
            diagnosis: '',
            status: appointment.status,
            eventDate: appointment.scheduled_at,
          }
        }
      })

    return Object.values(byAppointment)
  }, [appointments, consultations, appointmentById])

  const filteredEntries = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase()

    const presetDays = PERIOD_PRESETS[periodPreset]
    const presetStart = presetDays ? (() => {
      const date = new Date()
      date.setDate(date.getDate() - presetDays)
      date.setHours(0, 0, 0, 0)
      return date
    })() : null

    const startDate = toDateStart(periodStart)
    const endDate = toDateEnd(periodEnd)

    const filtered = historyEntries.filter((entry) => {
      const eventDate = new Date(entry.eventDate)
      if (Number.isNaN(eventDate.getTime())) {
        return false
      }

      if (normalizedSearch) {
        const matchesSearch =
          String(entry.appointmentId || '').includes(normalizedSearch)
          || String(entry.consultationId || '').includes(normalizedSearch)
          || String(entry.patientEmail || '').toLowerCase().includes(normalizedSearch)
          || String(entry.reason || '').toLowerCase().includes(normalizedSearch)
          || String(entry.diagnosis || '').toLowerCase().includes(normalizedSearch)

        if (!matchesSearch) {
          return false
        }
      }

      if (exactDate && toLocalDateKey(entry.eventDate) !== exactDate) {
        return false
      }

      if (presetStart && eventDate < presetStart) {
        return false
      }

      if (startDate && eventDate < startDate) {
        return false
      }

      if (endDate && eventDate > endDate) {
        return false
      }

      return true
    })

    const sorted = [...filtered]
    if (sortBy === 'newest') {
      sorted.sort((a, b) => new Date(b.eventDate) - new Date(a.eventDate))
    } else if (sortBy === 'oldest') {
      sorted.sort((a, b) => new Date(a.eventDate) - new Date(b.eventDate))
    } else if (sortBy === 'patient_az') {
      sorted.sort((a, b) => String(a.patientEmail || '').localeCompare(String(b.patientEmail || '')))
    } else if (sortBy === 'patient_za') {
      sorted.sort((a, b) => String(b.patientEmail || '').localeCompare(String(a.patientEmail || '')))
    }

    return sorted
  }, [historyEntries, searchTerm, exactDate, periodPreset, periodStart, periodEnd, sortBy])

  const consultedCount = historyEntries.length
  const completedWithConsultationCount = historyEntries.filter((entry) => entry.consultationId).length

  const openMedicalDossier = (entry) => {
    if (!entry.appointmentId) {
      toast.error('No linked appointment found for this historical consultation.')
      return
    }
    navigate(`/doctor/consultation?appointment=${entry.appointmentId}`)
  }

  const resetFilters = () => {
    setSearchTerm('')
    setExactDate('')
    setPeriodStart('')
    setPeriodEnd('')
    setPeriodPreset('all')
    setSortBy('newest')
  }

  if (appointmentsQuery.isLoading || consultationsQuery.isLoading) {
    return <p>Loading consultation history...</p>
  }

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>History</h2>
        <p className="muted">
          Full doctor history for consulted appointments and consultations. Access any visited patient dossier at any time.
        </p>
      </section>

      <section className="card split-grid">
        <article className="metric-card">
          <h4>Total historical entries</h4>
          <strong>{consultedCount}</strong>
        </article>
        <article className="metric-card">
          <h4>Entries with consultation note</h4>
          <strong>{completedWithConsultationCount}</strong>
        </article>
      </section>

      <section className="card">
        <div className="inline-header">
          <h3>Filters and sorting</h3>
          <button type="button" className="ghost-btn inline-action" onClick={resetFilters}>
            Reset filters
          </button>
        </div>

        <div className="form-grid">
          <label>
            Search
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Patient email, diagnosis, reason, appointment ID"
            />
          </label>

          <label>
            Exact date
            <input
              type="date"
              value={exactDate}
              onChange={(event) => setExactDate(event.target.value)}
            />
          </label>

          <label>
            Period preset
            <select value={periodPreset} onChange={(event) => setPeriodPreset(event.target.value)}>
              <option value="all">All time</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="year">Last 12 months</option>
            </select>
          </label>

          <label>
            Period start
            <input
              type="date"
              value={periodStart}
              onChange={(event) => setPeriodStart(event.target.value)}
            />
          </label>

          <label>
            Period end
            <input
              type="date"
              value={periodEnd}
              onChange={(event) => setPeriodEnd(event.target.value)}
            />
          </label>

          <label>
            Sort by
            <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
              <option value="patient_az">Patient email A-Z</option>
              <option value="patient_za">Patient email Z-A</option>
            </select>
          </label>
        </div>
      </section>

      <section className="card">
        <h3>Historical timeline</h3>
        {filteredEntries.length === 0 ? <p className="muted">No history found with current filters.</p> : null}

        <div className="timeline">
          {filteredEntries.map((entry) => (
            <article key={entry.key} className="timeline-item">
              <p className="muted">{new Date(entry.eventDate).toLocaleString()}</p>
              <p>
                Patient: <strong>{entry.patientEmail}</strong>
              </p>
              <p>
                Appointment ID: <strong>{entry.appointmentId ? `#${entry.appointmentId}` : 'N/A'}</strong>
              </p>
              <p>
                Consultation ID: <strong>{entry.consultationId ? `#${entry.consultationId}` : 'N/A'}</strong>
              </p>
              <p>
                Status: <span className={`status-tag ${entry.status}`}>{entry.status}</span>
              </p>
              <p className="muted">Reason: {entry.reason || 'No reason provided'}</p>
              <p className="muted">Diagnosis: {entry.diagnosis || 'No diagnosis note recorded yet'}</p>

              <div className="doctor-actions-row">
                <button
                  type="button"
                  className="secondary-btn inline-action"
                  onClick={() => openMedicalDossier(entry)}
                >
                  Open medical dossier
                </button>
                {entry.appointmentId ? (
                  <button
                    type="button"
                    className="ghost-btn inline-action"
                    onClick={() => navigate(`/doctor/patients-today?appointment=${entry.appointmentId}`)}
                  >
                    Open daily context
                  </button>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

export default HistoryPage
