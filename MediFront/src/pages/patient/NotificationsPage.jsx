import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listNotifications, markAllNotificationsRead } from '../../api/notificationsApi'

function NotificationsPage() {
  const queryClient = useQueryClient()
  const { data } = useQuery({ queryKey: ['notifications'], queryFn: listNotifications })

  const mutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  const notifications = data?.results || data || []

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>Notifications Center</h2>
        <p className="muted">Stay updated with appointments, prescriptions, and follow-up reminders.</p>
      </section>

      <section className="card">
        <div className="inline-header">
          <h3>Notifications</h3>
          <button className="ghost-btn" onClick={() => mutation.mutate()}>Mark all as read</button>
        </div>
        {notifications.length === 0 ? <p className="muted">No notifications at the moment.</p> : null}
        {notifications.map((item) => (
          <article key={item.id} className={item.is_read ? 'timeline-item read' : 'timeline-item unread'}>
            <h4>{item.title}</h4>
            <p>{item.message}</p>
          </article>
        ))}
      </section>
    </div>
  )
}

export default NotificationsPage
