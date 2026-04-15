import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
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

const INITIAL_LEAVE_FORM = {
  start_date: '',
  end_date: '',
  reason: '',
}

const SLOT_DURATION_MINUTES = 30

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
  const [leaveForm, setLeaveForm] = useState(INITIAL_LEAVE_FORM)
  const [delayInputs, setDelayInputs] = useState({})

  const todayQuery = useQuery({
    queryKey: ['appointments-today', scheduleDate],
    queryFn: () => getTodayAppointments({ date: scheduleDate }),
  })
  const allQuery = useQuery({ queryKey: ['appointments-all'], queryFn: listAppointments })
  const leavesQuery = useQuery({ queryKey: ['doctor-leaves'], queryFn: listDoctorLeaves })

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

  const todaySchedulable = useMemo(
    () => today.filter((item) => ['pending', 'confirmed'].includes(item.status)),
    [today],
  )

  const activeAppointments = useMemo(
    () => all.filter((item) => !['cancelled', 'completed', 'no_show'].includes(item.status)),
    [all],
  )

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
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>Doctor Command Center</h2>
        <p className="muted">
          Configure leave periods, review a summary of daily appointments, and use Accept or Delay actions directly.
        </p>
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
          <div className="timeline">
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

        <div className="timeline">
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
    </div>
  )
}

export default DoctorDashboard
