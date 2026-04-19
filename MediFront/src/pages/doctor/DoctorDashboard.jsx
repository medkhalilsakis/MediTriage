import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import { MessageSquare } from 'lucide-react'
import {
  completeAppointment,
  delayAppointment,
  getTodayAppointments,
  listAppointments,
} from '../../api/appointmentsApi'
import {
  cancelDoctorLeave,
  createDoctorLeave,
  listDoctorLeaves,
} from '../../api/doctorsApi'
import { listConsultations } from '../../api/medicalRecordsApi'

const INITIAL_LEAVE_FORM = {
  start_date: '',
  end_date: '',
  reason: '',
}

const SLOT_DURATION_MINUTES = 30
const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const pad2 = (value) => String(value).padStart(2, '0')

const toDateOnlyKey = (value) => {
  const date = value instanceof Date ? value : new Date(value)
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
}

const fromDateOnlyKey = (value) => {
  if (!value) {
    return null
  }
  const [year, month, day] = String(value).split('-').map((item) => Number(item))
  if (!year || !month || !day) {
    return null
  }
  return new Date(year, month - 1, day)
}

const addDays = (value, days) => {
  const date = new Date(value)
  date.setDate(date.getDate() + days)
  return date
}

const isWeekendDate = (value) => {
  const day = value.getDay()
  return day === 0 || day === 6
}

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

function DoctorDashboard() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const [scheduleDate, setScheduleDate] = useState(new Date().toISOString().slice(0, 10))
  const [calendarCursor, setCalendarCursor] = useState(new Date())
  const [leaveForm, setLeaveForm] = useState(INITIAL_LEAVE_FORM)
  const [delayInputs, setDelayInputs] = useState({})
  const [historySearch, setHistorySearch] = useState('')

  const todayQuery = useQuery({
    queryKey: ['appointments-today', scheduleDate],
    queryFn: () => getTodayAppointments({ date: scheduleDate }),
  })
  const allQuery = useQuery({ queryKey: ['appointments-all'], queryFn: listAppointments })
  const leavesQuery = useQuery({ queryKey: ['doctor-leaves'], queryFn: listDoctorLeaves })
  const consultationsQuery = useQuery({ queryKey: ['doctor-consultations-history'], queryFn: listConsultations })

  const completeAppointmentMutation = useMutation({
    mutationFn: completeAppointment,
    onSuccess: (_, appointmentId) => {
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
      queryClient.invalidateQueries({ queryKey: ['appointments-today'] })
      queryClient.invalidateQueries({ queryKey: ['appointments-all'] })
      toast.success('Appointment delayed successfully.')
    },
    onError: (error) => toast.error(extractApiError(error, 'Unable to delay appointment.')),
  })

  const leaveMutation = useMutation({
    mutationFn: createDoctorLeave,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doctor-leaves'] })
      queryClient.invalidateQueries({ queryKey: ['appointments-today'] })
      queryClient.invalidateQueries({ queryKey: ['appointments-all'] })
      setLeaveForm(INITIAL_LEAVE_FORM)
      toast.success('Leave request submitted and pending admin approval.')
    },
    onError: (error) => toast.error(extractApiError(error, 'Unable to save leave period.')),
  })

  const cancelLeaveMutation = useMutation({
    mutationFn: cancelDoctorLeave,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doctor-leaves'] })
      queryClient.invalidateQueries({ queryKey: ['appointments-today'] })
      queryClient.invalidateQueries({ queryKey: ['appointments-all'] })
      toast.success('Leave request cancelled.')
    },
    onError: (error) => toast.error(extractApiError(error, 'Unable to cancel leave request.')),
  })

  const today = todayQuery.data?.results || todayQuery.data || []
  const all = allQuery.data?.results || allQuery.data || []
  const leaves = leavesQuery.data?.results || leavesQuery.data || []
  const consultations = consultationsQuery.data?.results || consultationsQuery.data || []

  const todaySchedulable = useMemo(
    () => today.filter((item) => ['pending', 'confirmed'].includes(item.status)),
    [today],
  )

  const activeAppointments = useMemo(
    () => all.filter((item) => !['cancelled', 'completed', 'no_show'].includes(item.status)),
    [all],
  )

  const futureAppointments = useMemo(() => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    return all
      .filter((item) => ['pending', 'confirmed'].includes(item.status) && new Date(item.scheduled_at) >= today)
      .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))
  }, [all])

  const appointmentsByDate = useMemo(() => {
    const mapping = {}
    futureAppointments.forEach((appointment) => {
      const key = toDateOnlyKey(appointment.scheduled_at)
      if (!mapping[key]) {
        mapping[key] = []
      }
      mapping[key].push(appointment)
    })
    return mapping
  }, [futureAppointments])

  const leaveCoverageByDate = useMemo(() => {
    const mapping = {}

    leaves.forEach((leave) => {
      const leaveStart = fromDateOnlyKey(leave.start_date)
      const leaveEnd = fromDateOnlyKey(leave.end_date)

      if (!leaveStart || !leaveEnd) {
        return
      }

      const isApproved = leave.status === 'approved' && leave.is_active
      const isPending = leave.status === 'pending'

      if (!isApproved && !isPending) {
        return
      }

      let cursor = new Date(leaveStart)
      while (cursor <= leaveEnd) {
        const key = toDateOnlyKey(cursor)
        if (!mapping[key]) {
          mapping[key] = { approved: 0, pending: 0 }
        }

        if (isApproved) {
          mapping[key].approved += 1
        }
        if (isPending) {
          mapping[key].pending += 1
        }

        cursor = addDays(cursor, 1)
      }
    })

    return mapping
  }, [leaves])

  const monthTitle = useMemo(
    () => calendarCursor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }),
    [calendarCursor],
  )

  const calendarDays = useMemo(() => {
    const monthStart = new Date(calendarCursor.getFullYear(), calendarCursor.getMonth(), 1)
    const mondayIndex = (monthStart.getDay() + 6) % 7
    const gridStart = addDays(monthStart, -mondayIndex)
    return Array.from({ length: 42 }, (_, index) => addDays(gridStart, index))
  }, [calendarCursor])

  const calendarStats = useMemo(() => {
    const weekendCount = calendarDays.filter((day) => isWeekendDate(day) && day.getMonth() === calendarCursor.getMonth()).length
    const leaveDays = Object.entries(leaveCoverageByDate).filter((entry) => {
      const date = fromDateOnlyKey(entry[0])
      return date && date.getMonth() === calendarCursor.getMonth() && entry[1].approved > 0
    }).length

    const monthAppointments = calendarDays.reduce((total, day) => {
      if (day.getMonth() !== calendarCursor.getMonth()) {
        return total
      }
      return total + (appointmentsByDate[toDateOnlyKey(day)]?.length || 0)
    }, 0)

    return {
      monthAppointments,
      weekendCount,
      leaveDays,
    }
  }, [appointmentsByDate, calendarCursor, calendarDays, leaveCoverageByDate])

  const consultationByAppointmentId = useMemo(() => {
    const mapping = {}
    consultations.forEach((consultation) => {
      if (consultation.appointment) {
        mapping[consultation.appointment] = consultation
      }
    })
    return mapping
  }, [consultations])

  const completedAppointments = useMemo(
    () => all
      .filter((item) => item.status === 'completed')
      .sort((a, b) => new Date(b.scheduled_at) - new Date(a.scheduled_at)),
    [all],
  )

  const filteredHistoryAppointments = useMemo(() => {
    const normalizedSearch = historySearch.trim().toLowerCase()
    if (!normalizedSearch) {
      return completedAppointments
    }

    return completedAppointments.filter((appointment) => {
      const consultation = consultationByAppointmentId[appointment.id]
      return (
        String(appointment.id).includes(normalizedSearch)
        || String(appointment.patient_email || '').toLowerCase().includes(normalizedSearch)
        || String(appointment.reason || '').toLowerCase().includes(normalizedSearch)
        || String(consultation?.diagnosis || '').toLowerCase().includes(normalizedSearch)
      )
    })
  }, [completedAppointments, consultationByAppointmentId, historySearch])

  const handleLeaveSubmit = (event) => {
    event.preventDefault()

    if (!leaveForm.start_date || !leaveForm.end_date) {
      toast.error('Please provide start and end dates for leave.')
      return
    }

    leaveMutation.mutate({
      start_date: leaveForm.start_date,
      end_date: leaveForm.end_date,
      reason: leaveForm.reason,
    })
  }

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

  const openPatientsTodayDetails = (appointmentId) => {
    navigate(`/doctor/patients-today?date=${scheduleDate}&appointment=${appointmentId}`)
  }

  return (
    <div className="stacked-grid dashboard-surface dashboard-compact dashboard-doctor">
      <section className="card page-hero hero-with-visual">
        <h2>Doctor Command Center</h2>
        <p className="muted">
          Configure leave periods, manage daily appointments, and access history from a compact operations view.
        </p>
        <div className="patient-inline-group">
          <button
            type="button"
            className="ghost-btn inline-action"
            onClick={() => navigate('/doctor/settings')}
          >
            Open settings
          </button>
          <button
            type="button"
            className="secondary-btn inline-action"
            onClick={() => navigate('/doctor/history')}
          >
            Open full history
          </button>
          <button
            type="button"
            className="ghost-btn inline-action"
            onClick={() => navigate('/doctor/messages')}
          >
            Open messaging
          </button>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <img src="/visuals/dashboard-hero.svg" alt="" />
        </div>
      </section>

      <section className="card messaging-dashboard-section">
        <div className="inline-header">
          <h3>
            <MessageSquare size={18} />
            Realtime messaging section
          </h3>
          <button
            type="button"
            className="ghost-btn inline-action"
            onClick={() => navigate('/doctor/messages')}
          >
            Open messaging center
          </button>
        </div>
        <p className="muted">
          Contact your followed patients from appointments and collaborate with admins with live online status.
        </p>
      </section>

      <section className="card doctor-calendar-card">
        <div className="inline-header">
          <h3>Master calendar: appointments, weekends, and leaves</h3>
          <div className="doctor-actions-row doctor-calendar-month-actions">
            <button
              type="button"
              className="ghost-btn inline-action"
              onClick={() => setCalendarCursor((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1))}
            >
              Previous month
            </button>
            <button
              type="button"
              className="ghost-btn inline-action"
              onClick={() => setCalendarCursor(new Date())}
            >
              Current month
            </button>
            <button
              type="button"
              className="ghost-btn inline-action"
              onClick={() => setCalendarCursor((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1))}
            >
              Next month
            </button>
          </div>
        </div>

        <div className="doctor-calendar-meta">
          <h4>{monthTitle}</h4>
          <div className="doctor-calendar-legend">
            <span className="calendar-pill appointments">Future appointments</span>
            <span className="calendar-pill weekend">Weekend</span>
            <span className="calendar-pill leave">Approved leave</span>
            <span className="calendar-pill leave-pending">Pending leave</span>
          </div>
        </div>

        <div className="doctor-calendar-stats">
          <article>
            <strong>{calendarStats.monthAppointments}</strong>
            <span>Future appointments in month</span>
          </article>
          <article>
            <strong>{calendarStats.weekendCount}</strong>
            <span>Weekend days in month</span>
          </article>
          <article>
            <strong>{calendarStats.leaveDays}</strong>
            <span>Approved leave days in month</span>
          </article>
        </div>

        <div className="doctor-calendar-weekdays">
          {WEEKDAY_LABELS.map((weekday) => (
            <span key={weekday}>{weekday}</span>
          ))}
        </div>

        <div className="doctor-calendar-grid">
          {calendarDays.map((day) => {
            const dayKey = toDateOnlyKey(day)
            const dayAppointments = appointmentsByDate[dayKey] || []
            const leaveInfo = leaveCoverageByDate[dayKey] || { approved: 0, pending: 0 }

            const isCurrentMonth = day.getMonth() === calendarCursor.getMonth()
            const isToday = dayKey === toDateOnlyKey(new Date())
            const isSelected = dayKey === scheduleDate
            const weekend = isWeekendDate(day)

            return (
              <button
                key={dayKey}
                type="button"
                className={[
                  'doctor-calendar-day',
                  isCurrentMonth ? '' : 'outside-month',
                  isToday ? 'today' : '',
                  isSelected ? 'selected' : '',
                  weekend ? 'is-weekend' : '',
                ].join(' ')}
                onClick={() => {
                  setScheduleDate(dayKey)
                  setCalendarCursor(new Date(day.getFullYear(), day.getMonth(), 1))
                }}
              >
                <div className="doctor-calendar-day-top">
                  <span>{day.getDate()}</span>
                  {dayAppointments.length > 0 ? <span className="day-count">{dayAppointments.length}</span> : null}
                </div>

                <div className="doctor-calendar-day-tags">
                  {weekend ? <span className="calendar-pill weekend">Weekend</span> : null}
                  {leaveInfo.approved > 0 ? <span className="calendar-pill leave">Leave</span> : null}
                  {leaveInfo.pending > 0 ? <span className="calendar-pill leave-pending">Pending leave</span> : null}
                </div>

                {dayAppointments.length > 0 ? (
                  <div className="doctor-calendar-day-events">
                    {dayAppointments.slice(0, 2).map((appointment) => (
                      <p key={appointment.id} className="appointment-chip">
                        {new Date(appointment.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · {appointment.patient_email}
                      </p>
                    ))}
                    {dayAppointments.length > 2 ? <p className="muted">+{dayAppointments.length - 2} more</p> : null}
                  </div>
                ) : (
                  <p className="muted">No appointment</p>
                )}
              </button>
            )
          })}
        </div>
      </section>

      <section className="card split-grid doctor-dashboard-actions">
        <article className="timeline-item">
          <h3>Plan leave period</h3>
          <form className="form-grid" onSubmit={handleLeaveSubmit}>
            <label>
              Start date
              <input
                type="date"
                value={leaveForm.start_date}
                onChange={(event) => setLeaveForm((prev) => ({ ...prev, start_date: event.target.value }))}
                required
              />
            </label>
            <label>
              End date
              <input
                type="date"
                value={leaveForm.end_date}
                onChange={(event) => setLeaveForm((prev) => ({ ...prev, end_date: event.target.value }))}
                required
              />
            </label>
            <label>
              Reason
              <textarea
                value={leaveForm.reason}
                onChange={(event) => setLeaveForm((prev) => ({ ...prev, reason: event.target.value }))}
                placeholder="Optional leave reason"
              />
            </label>
            <button type="submit" disabled={leaveMutation.isPending}>
              {leaveMutation.isPending ? 'Saving leave...' : 'Save leave period'}
            </button>
          </form>
        </article>

        <article className="timeline-item">
          <h3>Leave requests</h3>
          <div className="timeline compact-scroll">
            {leaves.length === 0 ? <p className="muted">No leave request configured yet.</p> : null}
            {leaves.slice(0, 6).map((leave) => (
              <div key={leave.id} className="timeline-item">
                <p>
                  <strong>{leave.start_date}</strong> to <strong>{leave.end_date}</strong>
                </p>
                <p>
                  Status:{' '}
                  <span className={`status-tag ${leave.status || (leave.is_active ? 'approved' : 'pending')}`}>
                    {leave.status_label || leave.status || (leave.is_active ? 'approved' : 'pending')}
                  </span>
                </p>
                {leave.review_note ? <p className="muted">Admin note: {leave.review_note}</p> : null}
                <p className="muted">{leave.reason || 'No reason provided.'}</p>
                {['pending', 'approved'].includes(leave.status) ? (
                  <button
                    type="button"
                    className="secondary-btn inline-action"
                    onClick={() => cancelLeaveMutation.mutate(leave.id)}
                    disabled={cancelLeaveMutation.isPending}
                  >
                    Cancel leave
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="card">
        <div className="inline-header">
          <h3>Daily patient list and actions</h3>
          <div className="doctor-actions-row">
            <input
              type="date"
              value={scheduleDate}
              onChange={(event) => setScheduleDate(event.target.value)}
            />
          </div>
        </div>
        <p className="muted">Summary only in this dashboard section. Click an appointment to open full details in Patients Today.</p>
        <p className="muted">Working hours enforced by backend: 08:00-16:00, maximum 2 patients per hour.</p>
        {todaySchedulable.length === 0 ? <p className="muted">No appointments planned for today.</p> : null}

        <div className="timeline compact-scroll">
          {todaySchedulable.map((appointment) => (
            <article key={appointment.id} className="timeline-item">
              <div className="inline-header">
                <h4>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => openPatientsTodayDetails(appointment.id)}
                  >
                    {new Date(appointment.scheduled_at).toLocaleString()} - {appointment.patient_email}
                  </button>
                </h4>
                <button
                  type="button"
                  className="secondary-btn inline-action"
                  onClick={() => openPatientsTodayDetails(appointment.id)}
                >
                  View details
                </button>
              </div>

              <p className="muted">Reason: {appointment.reason || 'General visit'}</p>
              <p>
                Status: <span className={`status-tag ${appointment.status}`}>{appointment.status}</span>
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
            </article>
          ))}
        </div>
      </section>

      <section className="card stats-grid">
        <div className="metric-card">
          <h4>Total appointments</h4>
          <strong>{all.length}</strong>
        </div>
        <div className="metric-card">
          <h4>Today appointments</h4>
          <strong>{todaySchedulable.length}</strong>
        </div>
        <div className="metric-card">
          <h4>Active appointments</h4>
          <strong>{activeAppointments.length}</strong>
        </div>
        <div className="metric-card">
          <h4>Approved leaves</h4>
          <strong>{leaves.filter((leave) => leave.status === 'approved' && leave.is_active).length}</strong>
        </div>
      </section>

      <section className="card">
        <div className="inline-header">
          <h3>My consultation history</h3>
          <input
            value={historySearch}
            onChange={(event) => setHistorySearch(event.target.value)}
            placeholder="Search by patient email, diagnosis, reason, or appointment id"
          />
        </div>
        <p className="muted">
          Every completed appointment is historized. You can reopen any visited patient dossier at any time.
        </p>

        {filteredHistoryAppointments.length === 0 ? (
          <p className="muted">No completed appointments found for this filter.</p>
        ) : null}

        <div className="timeline compact-scroll">
          {filteredHistoryAppointments.slice(0, 12).map((appointment) => {
            const consultation = consultationByAppointmentId[appointment.id]

            return (
              <article key={`history-${appointment.id}`} className="timeline-item">
                <p className="muted">{new Date(appointment.scheduled_at).toLocaleString()}</p>
                <p>
                  Patient: <strong>{appointment.patient_email}</strong>
                </p>
                <p>
                  Appointment ID: <strong>#{appointment.id}</strong>
                </p>
                <p>
                  Status: <span className={`status-tag ${appointment.status}`}>{appointment.status}</span>
                </p>
                <p className="muted">Reason: {appointment.reason || 'General visit'}</p>

                {consultation ? (
                  <div className="timeline-item read" style={{ opacity: 1 }}>
                    <p>
                      Consultation ID: <strong>#{consultation.id}</strong>
                    </p>
                    <p className="muted">Diagnosis: {consultation.diagnosis || 'Not specified'}</p>
                  </div>
                ) : (
                  <p className="muted">No consultation note saved yet for this completed appointment.</p>
                )}

                <div className="doctor-actions-row">
                  <button
                    type="button"
                    className="secondary-btn inline-action"
                    onClick={() => navigate(`/doctor/consultation?appointment=${appointment.id}`)}
                  >
                    Open medical dossier
                  </button>
                  <button
                    type="button"
                    className="ghost-btn inline-action"
                    onClick={() => navigate(`/doctor/patients-today?date=${appointment.scheduled_at.slice(0, 10)}&appointment=${appointment.id}`)}
                  >
                    Open daily context
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      </section>
    </div>
  )
}

export default DoctorDashboard
