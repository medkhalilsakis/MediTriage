import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Link } from 'react-router-dom'
import {
  Activity,
  BellRing,
  Bot,
  CalendarClock,
  CalendarPlus,
  ClipboardList,
  ShieldCheck,
  Stethoscope,
} from 'lucide-react'
import {
  cancelAppointment,
  createAppointment,
  listAdvanceOffers,
  listAppointments,
  requestRescheduleAppointment,
  respondAdvanceOffer,
} from '../../api/appointmentsApi'
import { listFollowUps } from '../../api/followUpApi'
import { listConsultations, listMedicalDocumentRequests, listMedicalRecords } from '../../api/medicalRecordsApi'
import { listNotifications, markAllNotificationsRead } from '../../api/notificationsApi'
import { listPatientProfiles } from '../../api/patientsApi'
import { listPrescriptions } from '../../api/prescriptionsApi'

const INITIAL_APPOINTMENT = {
  department: '',
  urgency_level: 'medium',
  reason: '',
  notes: '',
}

const DEPARTMENTS = [
  { value: 'cardiology', label: 'Cardiology' },
  { value: 'respiratory', label: 'Respiratory Diseases' },
  { value: 'neurology', label: 'Neurology' },
  { value: 'gastroenterology', label: 'Gastroenterology' },
  { value: 'dermatology', label: 'Dermatology' },
  { value: 'endocrinology', label: 'Endocrinology' },
  { value: 'general_medicine', label: 'General Medicine' },
]

const INITIAL_QUESTIONNAIRE = {
  wellbeing: 'stable',
  medication_adherence: 'yes',
  symptoms_change: 'none',
  notes: '',
}

const toDateTimeInput = (value) => {
  if (!value) {
    return ''
  }

  const date = new Date(value)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

function PatientDashboard() {
  const queryClient = useQueryClient()
  const [appointmentDraft, setAppointmentDraft] = useState(INITIAL_APPOINTMENT)
  const [questionnaire, setQuestionnaire] = useState(INITIAL_QUESTIONNAIRE)
  const [rescheduleInputs, setRescheduleInputs] = useState({})

  const appointmentsQuery = useQuery({ queryKey: ['appointments'], queryFn: listAppointments })
  const patientProfilesQuery = useQuery({ queryKey: ['patient-profiles'], queryFn: listPatientProfiles })
  const medicalRecordsQuery = useQuery({ queryKey: ['medical-records'], queryFn: listMedicalRecords })
  const consultationsQuery = useQuery({ queryKey: ['consultations'], queryFn: listConsultations })
  const documentRequestsQuery = useQuery({
    queryKey: ['medical-document-requests'],
    queryFn: listMedicalDocumentRequests,
  })
  const prescriptionsQuery = useQuery({ queryKey: ['prescriptions'], queryFn: listPrescriptions })
  const followUpsQuery = useQuery({ queryKey: ['follow-ups'], queryFn: listFollowUps })
  const notificationsQuery = useQuery({ queryKey: ['notifications'], queryFn: listNotifications })
  const advanceOffersQuery = useQuery({ queryKey: ['appointment-advance-offers'], queryFn: listAdvanceOffers })

  const createAppointmentMutation = useMutation({
    mutationFn: async (payload) => {
      const profiles = patientProfilesQuery.data?.results || patientProfilesQuery.data || []
      const currentProfile = profiles[0]
      if (!currentProfile?.id) {
        throw new Error('MISSING_PATIENT_PROFILE')
      }

      return createAppointment({
        ...payload,
        patient: currentProfile.id,
      })
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
      const doctorLabel = data?.doctor_email || 'assigned doctor'
      const dateLabel = data?.scheduled_at ? new Date(data.scheduled_at).toLocaleString() : 'next available slot'
      toast.success(`Appointment booked with ${doctorLabel} on ${dateLabel}.`)
      setAppointmentDraft(INITIAL_APPOINTMENT)
    },
    onError: (error) => {
      if (error?.message === 'MISSING_PATIENT_PROFILE') {
        toast.error('Patient profile not found. Please contact support.')
        return
      }
      const detail = error?.response?.data?.detail || 'Unable to create appointment. Check the form values.'
      toast.error(detail)
    },
  })

  const cancelMutation = useMutation({
    mutationFn: cancelAppointment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
      queryClient.invalidateQueries({ queryKey: ['appointment-advance-offers'] })
      toast.success('Appointment cancelled.')
    },
    onError: () => toast.error('Unable to cancel appointment.'),
  })

  const rescheduleMutation = useMutation({
    mutationFn: ({ id, scheduledAt }) => requestRescheduleAppointment(id, scheduledAt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
      queryClient.invalidateQueries({ queryKey: ['appointment-advance-offers'] })
      toast.success('Appointment delayed successfully.')
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail || error?.response?.data?.scheduled_at || 'Unable to delay appointment.'
      toast.error(Array.isArray(detail) ? detail.join(', ') : String(detail))
    },
  })

  const respondOfferMutation = useMutation({
    mutationFn: ({ id, decision }) => respondAdvanceOffer(id, decision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
      queryClient.invalidateQueries({ queryKey: ['appointment-advance-offers'] })
      toast.success('Offer response submitted.')
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail || 'Unable to submit offer response.'
      toast.error(String(detail))
    },
  })

  const markNotificationsMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      toast.success('Notifications marked as read.')
    },
    onError: () => toast.error('Unable to mark notifications as read.'),
  })

  const appointments = appointmentsQuery.data?.results || appointmentsQuery.data || []
  const medicalRecords = medicalRecordsQuery.data?.results || medicalRecordsQuery.data || []
  const consultations = consultationsQuery.data?.results || consultationsQuery.data || []
  const documentRequests = documentRequestsQuery.data?.results || documentRequestsQuery.data || []
  const prescriptions = prescriptionsQuery.data?.results || prescriptionsQuery.data || []
  const followUps = followUpsQuery.data?.results || followUpsQuery.data || []
  const notifications = notificationsQuery.data?.results || notificationsQuery.data || []
  const advanceOffers = advanceOffersQuery.data?.results || advanceOffersQuery.data || []

  const pendingAdvanceOffers = useMemo(
    () => advanceOffers.filter((offer) => offer.status === 'pending'),
    [advanceOffers],
  )

  const unreadNotifications = useMemo(
    () => notifications.filter((item) => !item.is_read),
    [notifications],
  )

  const pendingDocumentRequests = useMemo(
    () => documentRequests.filter((item) => ['pending', 'uploaded'].includes(item.status)),
    [documentRequests],
  )

  const upcomingAppointments = useMemo(() => {
    const now = new Date()
    return appointments
      .filter((item) => {
        const appointmentDate = new Date(item.scheduled_at)
        return appointmentDate >= now && !['cancelled', 'completed', 'no_show'].includes(item.status)
      })
      .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))
      .slice(0, 6)
  }, [appointments])

  const reminders = useMemo(() => {
    return followUps
      .flatMap((followUp) =>
        (followUp.alerts || []).map((alert) => ({
          ...alert,
          followUpStatus: followUp.status,
        })),
      )
      .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))
      .slice(0, 6)
  }, [followUps])

  const latestVitals = useMemo(() => {
    return consultations.find(
      (consultation) =>
        consultation.vitals &&
        typeof consultation.vitals === 'object' &&
        Object.keys(consultation.vitals).length > 0,
    )
  }, [consultations])

  const healthIndicators = {
    upcomingAppointments: upcomingAppointments.length,
    activeFollowUps: followUps.filter((item) => ['scheduled', 'in_progress'].includes(item.status)).length,
    prescriptions: prescriptions.length,
    unreadNotifications: unreadNotifications.length,
    pendingDocumentRequests: pendingDocumentRequests.length,
  }

  const isAnyLoading = [
    appointmentsQuery.isLoading,
    patientProfilesQuery.isLoading,
    consultationsQuery.isLoading,
    documentRequestsQuery.isLoading,
    prescriptionsQuery.isLoading,
    followUpsQuery.isLoading,
    notificationsQuery.isLoading,
    medicalRecordsQuery.isLoading,
    advanceOffersQuery.isLoading,
  ].some(Boolean)

  const handleCreateAppointment = (event) => {
    event.preventDefault()

    if (!appointmentDraft.reason?.trim()) {
      toast.error('Please describe your illness before booking.')
      return
    }

    createAppointmentMutation.mutate({
      urgency_level: appointmentDraft.urgency_level,
      department: appointmentDraft.department || undefined,
      reason: appointmentDraft.reason,
      notes: appointmentDraft.notes,
    })
  }

  const handleSubmitQuestionnaire = (event) => {
    event.preventDefault()
    toast.success('Follow-up questionnaire submitted (local draft).')
    setQuestionnaire(INITIAL_QUESTIONNAIRE)
  }

  const handleReschedule = (appointment) => {
    const inputValue = rescheduleInputs[appointment.id] || toDateTimeInput(appointment.scheduled_at)
    if (!inputValue) {
      toast.error('Please select a valid date and time to delay your appointment.')
      return
    }

    rescheduleMutation.mutate({
      id: appointment.id,
      scheduledAt: new Date(inputValue).toISOString(),
    })
  }

  const handleOfferDecision = (offerId, decision) => {
    respondOfferMutation.mutate({ id: offerId, decision })
  }

  return (
    <div className="stacked-grid">
      <section className="card page-hero patient-dashboard-hero">
        <p className="auth-eyebrow">Patient Dashboard</p>
        <h2>Your central care journey workspace</h2>
        <p className="muted">
          Access chatbot, appointments, medical history, follow-up plans, notifications, and account security in one
          place.
        </p>
        <div className="patient-hero-actions">
          <a href="#book-appointment" className="ghost-btn inline-action patient-inline-action">
            <CalendarPlus size={16} />
            Book appointment now (no chatbot needed)
          </a>
          <Link to="/patient/chatbot" className="ghost-btn inline-action patient-inline-action">
            <Bot size={16} />
            Open chatbot (optional)
          </Link>
          <Link to="/patient/settings" className="ghost-btn inline-action patient-inline-action">
            <ShieldCheck size={16} />
            Account & security
          </Link>
        </div>
      </section>

      <section className="stats-grid patient-summary-grid">
        <article className="metric-card patient-metric-card">
          <h4>Upcoming appointments</h4>
          <strong>{healthIndicators.upcomingAppointments}</strong>
        </article>
        <article className="metric-card patient-metric-card">
          <h4>Active follow-ups</h4>
          <strong>{healthIndicators.activeFollowUps}</strong>
        </article>
        <article className="metric-card patient-metric-card">
          <h4>Prescriptions</h4>
          <strong>{healthIndicators.prescriptions}</strong>
        </article>
        <article className="metric-card patient-metric-card">
          <h4>Unread notifications</h4>
          <strong>{healthIndicators.unreadNotifications}</strong>
        </article>
        <article className="metric-card patient-metric-card">
          <h4>Pending requested docs</h4>
          <strong>{healthIndicators.pendingDocumentRequests}</strong>
        </article>
      </section>

      {isAnyLoading ? <p className="muted">Loading patient dashboard...</p> : null}

      <div className="split-grid patient-dashboard-grid">
        <div className="stacked-grid">
          <section id="book-appointment" className="card">
            <div className="inline-header">
              <h3>
                <CalendarPlus size={18} />
                Direct appointment booking
              </h3>
              <span className="chip">Auto-assigned doctor + FIFO calendar</span>
            </div>

            <form className="form-grid" onSubmit={handleCreateAppointment}>
              <label>
                Department (optional)
                <select
                  value={appointmentDraft.department}
                  onChange={(event) => setAppointmentDraft((prev) => ({ ...prev, department: event.target.value }))}
                >
                  <option value="">Assign to general medicine</option>
                  {DEPARTMENTS.map((department) => (
                    <option key={department.value} value={department.value}>
                      {department.label}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Urgency
                <select
                  value={appointmentDraft.urgency_level}
                  onChange={(event) =>
                    setAppointmentDraft((prev) => ({ ...prev, urgency_level: event.target.value }))
                  }
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </label>

              <label>
                Illness description
                <textarea
                  value={appointmentDraft.reason}
                  onChange={(event) => setAppointmentDraft((prev) => ({ ...prev, reason: event.target.value }))}
                  placeholder="Describe your symptoms and illness"
                />
              </label>

              <label>
                Notes
                <textarea
                  value={appointmentDraft.notes}
                  onChange={(event) => setAppointmentDraft((prev) => ({ ...prev, notes: event.target.value }))}
                  placeholder="Optional notes for your doctor"
                />
              </label>

              <button type="submit" disabled={createAppointmentMutation.isPending}>
                {createAppointmentMutation.isPending ? 'Assigning...' : 'Request appointment'}
              </button>
            </form>

            <p className="muted">
              Scheduling is fully automated using FIFO. The system assigns the least-loaded eligible doctor and
              skips Sundays.
            </p>
          </section>

          <section className="card">
            <div className="inline-header">
              <h3>
                <CalendarClock size={18} />
                Upcoming appointments
              </h3>
              <Link className="ghost-btn inline-action" to="/patient/appointments">
                Full schedule
              </Link>
            </div>

            <div className="timeline">
              {upcomingAppointments.length === 0 ? (
                <p className="muted">No upcoming appointment. You can book one directly above.</p>
              ) : null}

              {upcomingAppointments.map((appointment) => (
                <article key={appointment.id} className="timeline-item">
                  <p className="muted">{new Date(appointment.scheduled_at).toLocaleString()}</p>
                  <h4>{appointment.reason || 'General consultation'}</h4>
                  <p>
                    Assigned department:{' '}
                    <strong>{appointment.department_label || appointment.department || 'General Medicine'}</strong>
                  </p>
                  <p>Assigned doctor: <strong>{appointment.doctor_email || 'TBD'}</strong></p>
                  <p>
                    Status: <span className={`status-tag ${appointment.status}`}>{appointment.status}</span>
                  </p>
                  <p>
                    Urgency:{' '}
                    <span className={`urgency-tag ${appointment.urgency_level}`}>{appointment.urgency_level}</span>
                  </p>

                  <div className="reschedule-row">
                    <input
                      type="datetime-local"
                      value={rescheduleInputs[appointment.id] || toDateTimeInput(appointment.scheduled_at)}
                      onChange={(event) =>
                        setRescheduleInputs((prev) => ({
                          ...prev,
                          [appointment.id]: event.target.value,
                        }))
                      }
                    />
                    <button
                      type="button"
                      className="ghost-btn inline-action"
                      onClick={() => handleReschedule(appointment)}
                      disabled={rescheduleMutation.isPending}
                    >
                      Delay appointment
                    </button>
                    <button
                      type="button"
                      className="secondary-btn inline-action"
                      onClick={() => cancelMutation.mutate(appointment.id)}
                      disabled={cancelMutation.isPending}
                    >
                      Cancel appointment
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="inline-header">
              <h3>
                <CalendarClock size={18} />
                Earlier slot offers
              </h3>
              <span className="chip">Response window: 15 minutes</span>
            </div>

            <div className="timeline">
              {pendingAdvanceOffers.length === 0 ? (
                <p className="muted">No early-slot proposal at this moment.</p>
              ) : null}

              {pendingAdvanceOffers.map((offer) => (
                <article key={offer.id} className="timeline-item unread">
                  <p className="muted">
                    Offered slot: {new Date(offer.offered_slot).toLocaleString()}
                  </p>
                  <p className="muted">
                    Current slot: {new Date(offer.current_scheduled_at).toLocaleString()}
                  </p>
                  <p>
                    Doctor: <strong>{offer.doctor_email}</strong>
                  </p>
                  <p>
                    Expires at: <strong>{new Date(offer.expires_at).toLocaleString()}</strong>
                  </p>

                  <div className="patient-inline-group">
                    <button
                      type="button"
                      onClick={() => handleOfferDecision(offer.id, 'accept')}
                      disabled={respondOfferMutation.isPending}
                    >
                      Accept earlier slot
                    </button>
                    <button
                      type="button"
                      className="secondary-btn"
                      onClick={() => handleOfferDecision(offer.id, 'reject')}
                      disabled={respondOfferMutation.isPending}
                    >
                      Reject
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="inline-header">
              <h3>
                <ClipboardList size={18} />
                Medical record overview
              </h3>
              <Link className="ghost-btn inline-action" to="/patient/medical-records">
                Open full record
              </Link>
            </div>

            <div className="patient-overview-grid">
              <article className="timeline-item">
                <h4>Recent consultations</h4>
                {consultations.slice(0, 3).map((consultation) => (
                  <p key={consultation.id}>
                    {new Date(consultation.created_at).toLocaleDateString()} - {consultation.diagnosis}
                  </p>
                ))}
                {consultations.length === 0 ? <p className="muted">No consultation found.</p> : null}
              </article>

              <article className="timeline-item">
                <h4>Recent prescriptions</h4>
                {prescriptions.slice(0, 3).map((prescription) => (
                  <p key={prescription.id}>
                    {new Date(prescription.created_at).toLocaleDateString()} - {prescription.items?.length || 0} meds
                  </p>
                ))}
                {prescriptions.length === 0 ? <p className="muted">No prescription available.</p> : null}
              </article>

              <article className="timeline-item">
                <h4>Exam and measure summary</h4>
                {latestVitals ? (
                  <ul className="compact-list">
                    {Object.entries(latestVitals.vitals).slice(0, 4).map(([key, value]) => (
                      <li key={key}>
                        {key}: <strong>{String(value)}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">No recent measurements in consultation records.</p>
                )}
                {medicalRecords.length === 0 ? <p className="muted">Medical record not initialized yet.</p> : null}
              </article>
            </div>
          </section>
        </div>

        <div className="stacked-grid">
          <section className="card">
            <div className="inline-header">
              <h3>
                <Stethoscope size={18} />
                Post-consultation follow-up
              </h3>
              <span className="chip">Care plans & reminders</span>
            </div>

            <div className="timeline">
              {followUps.slice(0, 4).map((followUp) => (
                <article key={followUp.id} className="timeline-item">
                  <p className="muted">{new Date(followUp.scheduled_at).toLocaleString()}</p>
                  <p>
                    Follow-up status: <span className={`status-tag ${followUp.status}`}>{followUp.status}</span>
                  </p>
                  <p>{followUp.notes || 'No care plan notes provided yet.'}</p>
                </article>
              ))}
              {followUps.length === 0 ? <p className="muted">No follow-up plan available.</p> : null}
            </div>

            <div className="timeline patient-reminder-block">
              <h4>Reminders</h4>
              {reminders.length === 0 ? <p className="muted">No reminder at the moment.</p> : null}
              {reminders.map((reminder) => (
                <article key={reminder.id} className="timeline-item">
                  <p className="muted">{new Date(reminder.scheduled_at).toLocaleString()}</p>
                  <p>
                    Type: <span className="chip">{reminder.alert_type}</span>
                    {' '}Status: <span className={`status-tag ${reminder.status}`}>{reminder.status}</span>
                  </p>
                  <p>{reminder.message || 'Reminder message not provided.'}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="inline-header">
              <h3>
                <ClipboardList size={18} />
                Requested analyses & documents
              </h3>
              <Link className="ghost-btn inline-action" to="/patient/medical-records">
                Upload in dossier
              </Link>
            </div>

            <div className="timeline">
              {pendingDocumentRequests.length === 0 ? (
                <p className="muted">No pending document request from your doctor.</p>
              ) : null}

              {pendingDocumentRequests.slice(0, 5).map((item) => (
                <article key={item.id} className="timeline-item unread">
                  <p>
                    <strong>{item.title}</strong>
                  </p>
                  <p>
                    Status: <span className={`status-tag ${item.status}`}>{item.status}</span>
                  </p>
                  <p>Type: {item.request_type}</p>
                  <p>{item.description || 'No additional description provided.'}</p>
                  {(item.requested_items || []).length > 0 ? (
                    <p className="muted">Requested items: {(item.requested_items || []).join(', ')}</p>
                  ) : null}
                  {item.due_date ? <p className="muted">Due date: {item.due_date}</p> : null}
                </article>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="inline-header">
              <h3>
                <Activity size={18} />
                Follow-up questionnaire
              </h3>
              <span className="chip">Weekly check-in</span>
            </div>

            <form className="form-grid" onSubmit={handleSubmitQuestionnaire}>
              <label>
                Overall wellbeing
                <select
                  value={questionnaire.wellbeing}
                  onChange={(event) =>
                    setQuestionnaire((prev) => ({ ...prev, wellbeing: event.target.value }))
                  }
                >
                  <option value="stable">Stable</option>
                  <option value="improving">Improving</option>
                  <option value="worsening">Worsening</option>
                </select>
              </label>

              <label>
                Medication adherence
                <select
                  value={questionnaire.medication_adherence}
                  onChange={(event) =>
                    setQuestionnaire((prev) => ({ ...prev, medication_adherence: event.target.value }))
                  }
                >
                  <option value="yes">Yes</option>
                  <option value="partly">Partly</option>
                  <option value="no">No</option>
                </select>
              </label>

              <label>
                Symptoms evolution
                <select
                  value={questionnaire.symptoms_change}
                  onChange={(event) =>
                    setQuestionnaire((prev) => ({ ...prev, symptoms_change: event.target.value }))
                  }
                >
                  <option value="none">No change</option>
                  <option value="better">Better</option>
                  <option value="worse">Worse</option>
                </select>
              </label>

              <label>
                Additional notes
                <textarea
                  value={questionnaire.notes}
                  onChange={(event) =>
                    setQuestionnaire((prev) => ({ ...prev, notes: event.target.value }))
                  }
                  placeholder="Add any details for your care team"
                />
              </label>

              <button type="submit">Submit questionnaire</button>
            </form>
          </section>

          <section className="card">
            <div className="inline-header">
              <h3>
                <BellRing size={18} />
                Notifications
              </h3>
              <div className="patient-inline-group">
                <button
                  type="button"
                  className="ghost-btn inline-action"
                  onClick={() => markNotificationsMutation.mutate()}
                  disabled={markNotificationsMutation.isPending}
                >
                  Mark all read
                </button>
                <Link className="ghost-btn inline-action" to="/patient/notifications">
                  Open center
                </Link>
              </div>
            </div>

            <div className="timeline">
              {notifications.slice(0, 5).map((item) => (
                <article key={item.id} className={item.is_read ? 'timeline-item read' : 'timeline-item unread'}>
                  <h4>{item.title}</h4>
                  <p>{item.message}</p>
                </article>
              ))}
              {notifications.length === 0 ? <p className="muted">No notifications.</p> : null}
            </div>
          </section>

          <section className="card">
            <div className="inline-header">
              <h3>
                <ShieldCheck size={18} />
                Account and data security
              </h3>
              <Link className="ghost-btn inline-action" to="/patient/settings">
                Manage account
              </Link>
            </div>
            <ul className="compact-list">
              <li>Protected access with JWT session tokens.</li>
              <li>Personal data exposed only to your care team according to your role.</li>
              <li>Use account settings to review profile and security guidance.</li>
            </ul>
          </section>

          <section className="card patient-chatbot-optional">
            <div className="inline-header">
              <h3>
                <Bot size={18} />
                AI triage chatbot
              </h3>
              <Link className="ghost-btn inline-action" to="/patient/chatbot">
                Open chatbot
              </Link>
            </div>
            <p className="muted">
              Describe symptoms in any language and receive an English triage response with likely condition,
              urgency level, and recommended department. If you request it, the chatbot also suggests a booking
              window for your next appointment.
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}

export default PatientDashboard
