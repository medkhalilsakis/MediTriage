import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { BarChart3, MessageSquare } from 'lucide-react'
import { getAdminDashboardStats } from '../../api/adminApi'
import { approveDoctorLeave, listDoctorLeaves, rejectDoctorLeave } from '../../api/doctorsApi'

const COLORS = ['#e94f37', '#f6aa1c', '#53b3cb', '#3f7cac']
const POWERBI_EMBED_URL = import.meta.env.VITE_POWERBI_EMBED_URL || ''

const toLabel = (value, fallback = 'N/A') => {
  const text = String(value || '').trim()
  if (!text) {
    return fallback
  }
  return text
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

const toMonthLabel = (value) => {
  if (!value) {
    return 'N/A'
  }
  return new Date(value).toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
}

const toShortDate = (value) => {
  if (!value) {
    return 'N/A'
  }
  return new Date(value).toLocaleDateString()
}

const WEEKDAY_LABELS = {
  1: 'Sun',
  2: 'Mon',
  3: 'Tue',
  4: 'Wed',
  5: 'Thu',
  6: 'Fri',
  7: 'Sat',
}

function AdminDashboard() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
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

  const statusSplit = (data?.appointments_by_status || []).map((item) => ({
    name: toLabel(item.status),
    value: item.count,
  }))

  const departmentSplit = (data?.appointments_by_department || []).map((item) => ({
    name: toLabel(item.department),
    count: item.count,
  }))

  const usersByRole = (data?.users_by_role || []).map((item) => ({
    name: toLabel(item.role),
    value: item.count,
  }))

  const appointmentsByMonth = (data?.appointments_by_month || []).map((item) => ({
    monthKey: item.month,
    month: toMonthLabel(item.month),
    value: item.count,
  }))

  const consultationsByMonth = (data?.consultations_by_month || []).map((item) => ({
    monthKey: item.month,
    month: toMonthLabel(item.month),
    value: item.count,
  }))

  const monthlyTrendMap = {}
  appointmentsByMonth.forEach((item) => {
    monthlyTrendMap[item.monthKey] = {
      monthKey: item.monthKey,
      month: item.month,
      appointments: item.value,
      consultations: 0,
    }
  })
  consultationsByMonth.forEach((item) => {
    if (!monthlyTrendMap[item.monthKey]) {
      monthlyTrendMap[item.monthKey] = {
        monthKey: item.monthKey,
        month: item.month,
        appointments: 0,
        consultations: item.value,
      }
      return
    }

    monthlyTrendMap[item.monthKey].consultations = item.value
  })

  const monthlyTrend = Object.values(monthlyTrendMap).sort((a, b) => new Date(a.monthKey) - new Date(b.monthKey))

  const activityLast30Days = (data?.activity_last_30_days || []).map((item) => ({
    day: toShortDate(item.day),
    appointments: item.appointments,
    completed: item.completed,
    cancelled: item.cancelled,
  }))

  const appointmentsByWeekday = (data?.appointments_by_weekday || []).map((item) => ({
    day: WEEKDAY_LABELS[item.weekday] || String(item.weekday),
    count: item.count,
  }))

  const topDoctors = data?.top_doctors_by_load || []

  return (
    <div className="stacked-grid dashboard-surface dashboard-compact dashboard-admin">
      <section className="card page-hero hero-with-visual">
        <h2>Platform Intelligence Dashboard</h2>
        <p className="muted">
          Observe platform health with detailed analytics: demand, quality, doctor load, risk trends, and operational throughput.
        </p>
        <p className="muted">Generated at: {data?.generated_at ? new Date(data.generated_at).toLocaleString() : 'N/A'}</p>
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
          <button type="button" className="ghost-btn inline-action" onClick={() => navigate('/admin/messages')}>
            Open messaging center
          </button>
        </div>
        <p className="muted">
          Coordinate with doctors and patients in live conversations, with connected status visibility for fast triage operations.
        </p>
      </section>

      <section className="card stats-grid dashboard-metric-grid">
        <div className="metric-card"><h4>Users</h4><strong>{data?.users_total || 0}</strong></div>
        <div className="metric-card"><h4>Patients</h4><strong>{data?.patients_total || 0}</strong></div>
        <div className="metric-card"><h4>Doctors</h4><strong>{data?.doctors_total || 0}</strong></div>
        <div className="metric-card"><h4>Appointments</h4><strong>{data?.appointments_total || 0}</strong></div>
        <div className="metric-card"><h4>Active patients (30d)</h4><strong>{data?.active_patients_last_30_days || 0}</strong></div>
        <div className="metric-card"><h4>Open appointments</h4><strong>{data?.open_appointments_count || 0}</strong></div>
        <div className="metric-card"><h4>No-show rate</h4><strong>{data?.no_show_rate || 0}%</strong></div>
        <div className="metric-card"><h4>Completion rate</h4><strong>{data?.completion_rate || 0}%</strong></div>
      </section>

      <section className="card chart-grid">
        <article>
          <h3>Consultations / Week</h3>
          <ResponsiveContainer width="100%" height={230}>
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
          <ResponsiveContainer width="100%" height={230}>
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

      <section className="card chart-grid">
        <article>
          <h3>Appointments vs Consultations (Monthly)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={monthlyTrend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line dataKey="appointments" name="Appointments" stroke="#ef5b3f" strokeWidth={2} dot={false} />
              <Line dataKey="consultations" name="Consultations" stroke="#0c8a82" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </article>

        <article>
          <h3>Activity Last 30 Days</h3>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={activityLast30Days}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Area type="monotone" dataKey="appointments" stroke="#0c8a82" fill="#d8f1ee" name="Created" />
              <Area type="monotone" dataKey="completed" stroke="#2563eb" fill="#dbe9ff" name="Completed" />
              <Area type="monotone" dataKey="cancelled" stroke="#ef5b3f" fill="#ffe3dc" name="Cancelled" />
            </AreaChart>
          </ResponsiveContainer>
        </article>
      </section>

      <section className="card chart-grid">
        <article>
          <h3>Appointment Status Distribution</h3>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={statusSplit} dataKey="value" nameKey="name" innerRadius={50} outerRadius={88}>
                {statusSplit.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </article>

        <article>
          <h3>Department Demand</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={departmentSplit}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#3f7cac" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </article>
      </section>

      <section className="card chart-grid">
        <article>
          <h3>Appointments by Weekday</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={appointmentsByWeekday}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#f6aa1c" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </article>

        <article>
          <h3>User Role Distribution</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={usersByRole} dataKey="value" nameKey="name" innerRadius={48} outerRadius={82}>
                {usersByRole.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </article>
      </section>

      <section className="card powerbi-section">
        <div className="inline-header">
          <h3>
            <BarChart3 size={18} />
            Power BI analytics section
          </h3>
          <span className="chip">Optional embed</span>
        </div>

        {POWERBI_EMBED_URL ? (
          <iframe
            title="Power BI Admin Analytics"
            src={POWERBI_EMBED_URL}
            className="powerbi-frame"
            allowFullScreen
          />
        ) : (
          <p className="muted">
            Add VITE_POWERBI_EMBED_URL in your frontend environment to display your full Power BI report directly here.
          </p>
        )}
      </section>

      <section className="card">
        <div className="inline-header">
          <h3>Top Doctors by Operational Load</h3>
          <span className="chip">Avg / doctor: {data?.average_appointments_per_doctor || 0}</span>
        </div>

        <div className="timeline compact-scroll">
          {topDoctors.length === 0 ? <p className="muted">No doctor load data available.</p> : null}

          {topDoctors.map((doctor) => (
            <article key={`${doctor.doctor}-${doctor.doctor__user__email}`} className="timeline-item">
              <p>
                <strong>{doctor.doctor__user__email}</strong>
              </p>
              <p>Department: {toLabel(doctor.doctor__department)}</p>
              <p>Total appointments: <strong>{doctor.total}</strong></p>
              <p className="muted">
                Completed: {doctor.completed} | Confirmed: {doctor.confirmed} | Pending: {doctor.pending} | Cancelled: {doctor.cancelled} | No-show: {doctor.no_show}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="card">
        <div className="inline-header">
          <h3>Pending Leave Requests</h3>
          <span className="chip">{pendingLeaves.length} pending</span>
        </div>

        <div className="timeline compact-scroll">
          {pendingLeaves.length === 0 ? <p className="muted">No pending leave request.</p> : null}

          {pendingLeaves.slice(0, 8).map((leave) => (
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
