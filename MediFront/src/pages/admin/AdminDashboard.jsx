import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getAdminDashboardStats } from '../../api/adminApi'
import { approveDoctorLeave, listDoctorLeaves, rejectDoctorLeave } from '../../api/doctorsApi'

const COLORS = ['#e94f37', '#f6aa1c', '#53b3cb', '#3f7cac']

function AdminDashboard() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['admin-stats'], queryFn: getAdminDashboardStats })
  const pendingLeavesQuery = useQuery({
    queryKey: ['doctor-leaves-pending'],
    queryFn: () => listDoctorLeaves({ status: 'pending' }),
  })

  const approveLeaveMutation = useMutation({
    mutationFn: ({ id, reviewNote }) => approveDoctorLeave(id, { review_note: reviewNote || '' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doctor-leaves-pending'] })
      queryClient.invalidateQueries({ queryKey: ['doctor-leaves'] })
      toast.success('Leave request approved.')
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail || 'Unable to approve leave request.'
      toast.error(String(detail))
    },
  })

  const rejectLeaveMutation = useMutation({
    mutationFn: ({ id, reviewNote }) => rejectDoctorLeave(id, { review_note: reviewNote || '' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doctor-leaves-pending'] })
      queryClient.invalidateQueries({ queryKey: ['doctor-leaves'] })
      toast.success('Leave request rejected.')
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail || 'Unable to reject leave request.'
      toast.error(String(detail))
    },
  })

  if (isLoading || pendingLeavesQuery.isLoading) return <p>Loading dashboard...</p>

  const consultationsByWeek = (data?.consultations_by_week || []).map((item) => ({
    week: item.week?.slice(0, 10),
    count: item.count,
  }))

  const urgencySplit = (data?.urgency_split || []).map((item) => ({
    name: item.urgency_level,
    value: item.count,
  }))

  const pendingLeaves = pendingLeavesQuery.data?.results || pendingLeavesQuery.data || []

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>Platform Intelligence Dashboard</h2>
        <p className="muted">Observe capacity, demand, and urgency distribution across the full care system.</p>
      </section>

      <section className="card stats-grid">
        <div className="metric-card"><h4>Users</h4><strong>{data?.users_total || 0}</strong></div>
        <div className="metric-card"><h4>Patients</h4><strong>{data?.patients_total || 0}</strong></div>
        <div className="metric-card"><h4>Doctors</h4><strong>{data?.doctors_total || 0}</strong></div>
        <div className="metric-card"><h4>Appointments</h4><strong>{data?.appointments_total || 0}</strong></div>
      </section>

      <section className="card chart-grid">
        <article>
          <h3>Consultations / Week</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={consultationsByWeek}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#e94f37" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </article>

        <article>
          <h3>Urgency Split</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={urgencySplit} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90}>
                {urgencySplit.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </article>
      </section>

      <section className="card">
        <div className="inline-header">
          <h3>Pending Leave Requests</h3>
          <span className="chip">Admin validation required</span>
        </div>

        <div className="timeline">
          {pendingLeaves.length === 0 ? <p className="muted">No pending leave request.</p> : null}

          {pendingLeaves.map((leave) => (
            <article key={leave.id} className="timeline-item">
              <p>
                Doctor: <strong>{leave.doctor_email}</strong>
              </p>
              <p>
                Period: <strong>{leave.start_date}</strong> to <strong>{leave.end_date}</strong>
              </p>
              <p className="muted">Reason: {leave.reason || 'No reason provided.'}</p>

              <div className="doctor-actions-row">
                <button
                  type="button"
                  onClick={() => approveLeaveMutation.mutate({ id: leave.id })}
                  disabled={approveLeaveMutation.isPending || rejectLeaveMutation.isPending}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => rejectLeaveMutation.mutate({ id: leave.id })}
                  disabled={approveLeaveMutation.isPending || rejectLeaveMutation.isPending}
                >
                  Reject
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

export default AdminDashboard
