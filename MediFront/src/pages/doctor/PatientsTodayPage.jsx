import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { completeAppointment, delayAppointment, getTodayAppointments } from '../../api/appointmentsApi'

const WORKING_HOUR_START = 8
const WORKING_HOUR_END = 16
const SLOT_DURATION_MINUTES = 30

const formatHourLabel = (hour) => `${String(hour).padStart(2, '0')}:00 - ${String(hour + 1).padStart(2, '0')}:00`

const getHourFromSlot = (slot) => new Date(slot).getHours()

const toDateTimeInput = (value) => {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

const normalizeDateTimeLocalToSlot = (value) => {
  if (!value) {
    return ''
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  date.setSeconds(0, 0)
  const remainder = date.getMinutes() % SLOT_DURATION_MINUTES
  if (remainder !== 0) {
    date.setMinutes(date.getMinutes() + (SLOT_DURATION_MINUTES - remainder))
  }

  return toDateTimeInput(date.toISOString())
}

const extractApiError = (error, fallback) => {
  const responseData = error?.response?.data
  const detail = responseData?.detail
  if (detail) {
    return String(detail)
  }

  const scheduledAtError = responseData?.scheduled_at
  if (scheduledAtError) {
    return Array.isArray(scheduledAtError) ? scheduledAtError.join(', ') : String(scheduledAtError)
  }

  if (responseData && typeof responseData === 'object') {
    const firstFieldError = Object.values(responseData)[0]
    if (firstFieldError) {
      return Array.isArray(firstFieldError) ? firstFieldError.join(', ') : String(firstFieldError)
    }
  }

  return fallback
}

function PatientsTodayPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const queryDate = searchParams.get('date')
  const defaultDate = /^\d{4}-\d{2}-\d{2}$/.test(queryDate || '')
    ? queryDate
    : new Date().toISOString().slice(0, 10)

  const highlightedAppointmentId = searchParams.get('appointment') || ''

  const [selectedDate, setSelectedDate] = useState(defaultDate)
  const [selectedHour, setSelectedHour] = useState('all')
  const [delayInputs, setDelayInputs] = useState({})

  const completeAppointmentMutation = useMutation({
    mutationFn: completeAppointment,
    onSuccess: (_, appointmentId) => {
      queryClient.invalidateQueries({ queryKey: ['doctor-patients-daily'] })
      queryClient.invalidateQueries({ queryKey: ['appointments-today'] })
      queryClient.invalidateQueries({ queryKey: ['appointments-all'] })
      toast.success('Appointment accepted and completed. Opening medical dossier...')
      navigate(`/doctor/consultation?appointment=${appointmentId}`)
    },
    onError: (error) => toast.error(extractApiError(error, 'Unable to accept this appointment.')),
  })

  const delayMutation = useMutation({
    mutationFn: ({ id, scheduledAt }) => delayAppointment(id, scheduledAt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doctor-patients-daily'] })
      queryClient.invalidateQueries({ queryKey: ['appointments-today'] })
      queryClient.invalidateQueries({ queryKey: ['appointments-all'] })
      toast.success('Appointment delayed successfully.')
    },
    onError: (error) => toast.error(extractApiError(error, 'Unable to delay appointment.')),
  })

  const dailyPatientsQuery = useQuery({
    queryKey: ['doctor-patients-daily', selectedDate],
    queryFn: () => getTodayAppointments({ date: selectedDate }),
  })

  const appointments = dailyPatientsQuery.data?.results || dailyPatientsQuery.data || []

  const allowedStatuses = new Set(['pending', 'confirmed'])
  const schedulableAppointments = useMemo(
    () => appointments.filter((item) => allowedStatuses.has(item.status)),
    [appointments],
  )

  const hourOptions = useMemo(
    () => Array.from({ length: WORKING_HOUR_END - WORKING_HOUR_START }, (_, idx) => WORKING_HOUR_START + idx),
    [],
  )

  const filteredAppointments = useMemo(() => {
    if (selectedHour === 'all') {
      return schedulableAppointments
    }

    const targetHour = Number(selectedHour)
    return schedulableAppointments.filter((appointment) => getHourFromSlot(appointment.scheduled_at) === targetHour)
  }, [schedulableAppointments, selectedHour])

  const appointmentsByHour = useMemo(() => {
    const base = {}
    for (const hour of hourOptions) {
      base[hour] = []
    }

    filteredAppointments.forEach((appointment) => {
      const hour = getHourFromSlot(appointment.scheduled_at)
      if (Object.prototype.hasOwnProperty.call(base, hour)) {
        base[hour].push(appointment)
      }
    })

    return base
  }, [filteredAppointments, hourOptions])

  const totalShown = filteredAppointments.length

  const handleDelay = (appointment) => {
    const inputValue = delayInputs[appointment.id]
    if (!inputValue) {
      toast.error('Please select a new date and time before delaying.')
      return
    }

    delayMutation.mutate({
      id: appointment.id,
      scheduledAt: new Date(inputValue).toISOString(),
    })
  }

  if (dailyPatientsQuery.isLoading) {
    return <p>Loading daily patients...</p>
  }

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>Patients Today</h2>
        <p className="muted">
          Daily and hourly view of scheduled patients. Capacity target: maximum 2 patients per hour between 08:00 and 16:00.
        </p>
      </section>

      <section className="card">
        <div className="doctor-day-controls">
          <label>
            Date
            <input
              type="date"
              value={selectedDate}
              onChange={(event) => setSelectedDate(event.target.value)}
            />
          </label>

          <label>
            Hour filter
            <select value={selectedHour} onChange={(event) => setSelectedHour(event.target.value)}>
              <option value="all">All hours</option>
              {hourOptions.map((hour) => (
                <option key={hour} value={hour}>
                  {formatHourLabel(hour)}
                </option>
              ))}
            </select>
          </label>

          <div className="doctor-day-summary">
            <span className="chip">Displayed patients: {totalShown}</span>
            <Link className="ghost-btn inline-action" to="/doctor/dashboard">
              Open dashboard actions
            </Link>
          </div>
        </div>
      </section>

      <section className="card">
        <h3>Appointments by hour</h3>

        {totalShown === 0 ? <p className="muted">No scheduled patients for this filter.</p> : null}

        <div className="timeline">
          {hourOptions.map((hour) => {
            const bucket = appointmentsByHour[hour] || []
            if (bucket.length === 0) {
              return null
            }

            return (
              <article key={hour} className="timeline-item">
                <div className="inline-header">
                  <h4>{formatHourLabel(hour)}</h4>
                  <span className="chip">{bucket.length} patient(s)</span>
                </div>

                <div className="timeline">
                  {bucket
                    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))
                    .map((appointment) => (
                      <div key={appointment.id} className="timeline-item read">
                        {String(appointment.id) === highlightedAppointmentId ? (
                          <p className="muted"><strong>Selected from dashboard summary</strong></p>
                        ) : null}
                        <p className="muted">{new Date(appointment.scheduled_at).toLocaleString()}</p>
                        <p>
                          Patient: <strong>{appointment.patient_email}</strong>
                        </p>
                        <p>
                          Reason: <strong>{appointment.reason || 'General consultation'}</strong>
                        </p>
                        <p>
                          Status: <span className={`status-tag ${appointment.status}`}>{appointment.status}</span>
                        </p>
                        <p>
                          Urgency:{' '}
                          <span className={`urgency-tag ${appointment.urgency_level}`}>{appointment.urgency_level}</span>
                        </p>

                        <div className="doctor-actions-row">
                          <button
                            type="button"
                            className="ghost-btn inline-action"
                            onClick={() => completeAppointmentMutation.mutate(appointment.id)}
                            disabled={completeAppointmentMutation.isPending}
                          >
                            Accept
                          </button>

                          <input
                            type="datetime-local"
                            step={1800}
                            value={delayInputs[appointment.id] || toDateTimeInput(appointment.scheduled_at)}
                            onChange={(event) =>
                              setDelayInputs((prev) => ({
                                ...prev,
                                [appointment.id]: normalizeDateTimeLocalToSlot(event.target.value),
                              }))
                            }
                          />

                          <button
                            type="button"
                            className="secondary-btn inline-action"
                            onClick={() => handleDelay(appointment)}
                            disabled={delayMutation.isPending}
                          >
                            Delay
                          </button>
                        </div>
                      </div>
                    ))}
                </div>
              </article>
            )
          })}
        </div>
      </section>
    </div>
  )
}

export default PatientsTodayPage
