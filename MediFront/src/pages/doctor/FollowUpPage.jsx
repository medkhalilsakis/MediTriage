import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { createFollowUp, listFollowUps } from '../../api/followUpApi'
import FollowUpTimeline from '../../components/FollowUpTimeline'

function FollowUpPage() {
  const queryClient = useQueryClient()
  const { data } = useQuery({ queryKey: ['follow-ups'], queryFn: listFollowUps })

  const mutation = useMutation({
    mutationFn: createFollowUp,
    onSuccess: () => {
      toast.success('Follow-up created')
      queryClient.invalidateQueries({ queryKey: ['follow-ups'] })
    },
    onError: () => toast.error('Unable to create follow-up'),
  })

  const followUps = data?.results || data || []

  const handleSubmit = (event) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    mutation.mutate({
      patient: Number(form.get('patient')),
      doctor: Number(form.get('doctor')),
      consultation: form.get('consultation') ? Number(form.get('consultation')) : null,
      notes: form.get('notes'),
      scheduled_at: form.get('scheduled_at'),
      status: 'scheduled',
    })
    event.currentTarget.reset()
  }

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>Follow-up Planner</h2>
        <p className="muted">Plan post-consultation continuity and monitor adherence through scheduled checks.</p>
      </section>

      <section className="card">
        <h3>Create Follow-up</h3>
        <form className="form-grid" onSubmit={handleSubmit}>
          <input name="patient" placeholder="Patient Profile ID" required />
          <input name="doctor" placeholder="Doctor Profile ID" required />
          <input name="consultation" placeholder="Consultation ID (optional)" />
          <textarea name="notes" placeholder="Notes" />
          <input type="datetime-local" name="scheduled_at" required />
          <button type="submit">Save</button>
        </form>
      </section>
      <FollowUpTimeline followUps={followUps} />
    </div>
  )
}

export default FollowUpPage
