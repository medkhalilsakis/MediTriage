import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  cancelAppointment,
  listAdvanceOffers,
  listAppointments,
  requestRescheduleAppointment,
  respondAdvanceOffer,
} from '../../api/appointmentsApi'

const toDateTimeInput = (value) => {
  if (!value) {
    return ''
  }

  const date = new Date(value)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

function AppointmentsPage() {
  const queryClient = useQueryClient()
  const [rescheduleInputs, setRescheduleInputs] = useState({})

  const appointmentsQuery = useQuery({ queryKey: ['appointments'], queryFn: listAppointments })
  const offersQuery = useQuery({ queryKey: ['appointment-advance-offers'], queryFn: listAdvanceOffers })

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

  const offerMutation = useMutation({
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

  const appointments = appointmentsQuery.data?.results || appointmentsQuery.data || []
  const offers = offersQuery.data?.results || offersQuery.data || []

  const pendingOffers = useMemo(
    () => offers.filter((offer) => offer.status === 'pending'),
    [offers],
  )

  const handleReschedule = (appointment) => {
    const inputValue = rescheduleInputs[appointment.id] || toDateTimeInput(appointment.scheduled_at)
    if (!inputValue) {
      toast.error('Please choose the new appointment date and time.')
      return
    }

    rescheduleMutation.mutate({
      id: appointment.id,
      scheduledAt: new Date(inputValue).toISOString(),
    })
  }

  const isLoading = appointmentsQuery.isLoading || offersQuery.isLoading
  if (isLoading) {
    return <p>Loading appointments...</p>
  }

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>Appointment Flow</h2>
        <p className="muted">
          Manage your booking anytime: cancel, delay, and answer earlier-slot proposals from the waiting list flow.
        </p>
      </section>

      <section className="card">
        <div className="inline-header">
          <h3>Earlier slot offers</h3>
          <span className="chip">Response window: 15 minutes</span>
        </div>

        <div className="timeline">
          {pendingOffers.length === 0 ? <p className="muted">No early-slot proposal at this moment.</p> : null}

          {pendingOffers.map((offer) => (
            <article key={offer.id} className="timeline-item unread">
              <p className="muted">Offered slot: {new Date(offer.offered_slot).toLocaleString()}</p>
              <p className="muted">Current slot: {new Date(offer.current_scheduled_at).toLocaleString()}</p>
              <p>Doctor: <strong>{offer.doctor_email}</strong></p>
              <p>Expires at: <strong>{new Date(offer.expires_at).toLocaleString()}</strong></p>
              <div className="patient-inline-group">
                <button
                  type="button"
                  onClick={() => offerMutation.mutate({ id: offer.id, decision: 'accept' })}
                  disabled={offerMutation.isPending}
                >
                  Accept earlier slot
                </button>
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => offerMutation.mutate({ id: offer.id, decision: 'reject' })}
                  disabled={offerMutation.isPending}
                >
                  Reject
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="card">
        <h3>All appointments</h3>
        <div className="timeline">
          {appointments.length === 0 ? <p className="muted">No appointments available right now.</p> : null}

          {appointments.map((appointment) => {
            const isFinalStatus = ['cancelled', 'completed', 'no_show'].includes(appointment.status)
            return (
              <article key={appointment.id} className="timeline-item">
                <p className="muted">{new Date(appointment.scheduled_at).toLocaleString()}</p>
                <h4>{appointment.reason || 'General consultation'}</h4>
                <p>
                  Department: <strong>{appointment.department_label || appointment.department || 'General Medicine'}</strong>
                </p>
                <p>
                  Doctor: <strong>{appointment.doctor_email || 'Assigned automatically'}</strong>
                </p>
                <p>
                  Status: <span className={`status-tag ${appointment.status}`}>{appointment.status}</span>
                </p>
                <p>
                  Urgency: <span className={`urgency-tag ${appointment.urgency_level}`}>{appointment.urgency_level}</span>
                </p>

                {isFinalStatus ? null : (
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
                )}
              </article>
            )
          })}
        </div>
      </section>
    </div>
  )
}

export default AppointmentsPage
