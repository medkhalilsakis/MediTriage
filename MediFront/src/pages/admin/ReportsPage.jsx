import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
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
import { Activity, ClipboardList, Pill, Stethoscope, TrendingUp, UsersRound } from 'lucide-react'
import { getAdminDashboardStats } from '../../api/adminApi'
import { listPrescriptions } from '../../api/prescriptionsApi'

const CHART_COLORS = ['#ef5b3f', '#0c8a82', '#2563eb', '#f59e0b', '#7c3aed', '#0ea5e9']

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

const toShortDateTime = (value) => {
  if (!value) {
    return 'N/A'
  }
  return new Date(value).toLocaleString()
}

const countBy = (items, keyFn) => {
  const map = new Map()
  items.forEach((item) => {
    const key = keyFn(item)
    if (!key) {
      return
    }
    map.set(key, (map.get(key) || 0) + 1)
  })
  return map
}

function ReportsPage() {
  const statsQuery = useQuery({ queryKey: ['admin-reports-stats'], queryFn: getAdminDashboardStats })
  const prescriptionsQuery = useQuery({ queryKey: ['reports-prescriptions'], queryFn: listPrescriptions })

  const stats = statsQuery.data || {}
  const prescriptionPayload = prescriptionsQuery.data
  const recentPrescriptions = useMemo(
    () => prescriptionPayload?.results || prescriptionPayload || [],
    [prescriptionPayload],
  )

  const isLoading = statsQuery.isLoading || prescriptionsQuery.isLoading

  const statusSplit = useMemo(
    () => (stats?.appointments_by_status || []).map((item) => ({
      name: toLabel(item.status),
      value: item.count,
    })),
    [stats?.appointments_by_status],
  )

  const departmentSplit = useMemo(
    () => (stats?.appointments_by_department || []).map((item) => ({
      name: toLabel(item.department),
      count: item.count,
    })),
    [stats?.appointments_by_department],
  )

  const urgencySplit = useMemo(
    () => (stats?.urgency_split || []).map((item) => ({
      name: toLabel(item.urgency_level),
      value: item.count,
    })),
    [stats?.urgency_split],
  )

  const monthlyTrend = useMemo(() => {
    const appointmentsByMonth = (stats?.appointments_by_month || []).map((item) => ({
      monthKey: item.month,
      month: toMonthLabel(item.month),
      appointments: item.count,
      consultations: 0,
    }))

    const monthlyMap = new Map(appointmentsByMonth.map((item) => [item.monthKey, item]))

    ;(stats?.consultations_by_month || []).forEach((item) => {
      const existing = monthlyMap.get(item.month)
      if (existing) {
        existing.consultations = item.count
        return
      }

      monthlyMap.set(item.month, {
        monthKey: item.month,
        month: toMonthLabel(item.month),
        appointments: 0,
        consultations: item.count,
      })
    })

    return Array.from(monthlyMap.values()).sort((a, b) => new Date(a.monthKey) - new Date(b.monthKey))
  }, [stats?.appointments_by_month, stats?.consultations_by_month])

  const medicationSignals = useMemo(() => {
    const medications = []
    recentPrescriptions.forEach((prescription) => {
      ;(prescription.items || []).forEach((item) => {
        medications.push(toLabel(item.medication, 'Unknown medication'))
      })
    })

    const counts = countBy(medications, (item) => item)
    return Array.from(counts.entries())
      .map(([name, total]) => ({ name, total }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 8)
  }, [recentPrescriptions])

  const doctorsInRecentFeed = useMemo(() => {
    const counts = countBy(recentPrescriptions, (item) => item.doctor_email)
    return Array.from(counts.entries())
      .map(([email, total]) => ({ email, total }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 6)
  }, [recentPrescriptions])

  const avgItemsPerPrescription = useMemo(() => {
    if (recentPrescriptions.length === 0) {
      return 0
    }

    const totalItems = recentPrescriptions.reduce((sum, item) => sum + (item.items?.length || 0), 0)
    return (totalItems / recentPrescriptions.length).toFixed(1)
  }, [recentPrescriptions])

  const totalPrescriptions = stats?.prescriptions_total || prescriptionPayload?.count || recentPrescriptions.length
  const generatedAtLabel = stats?.generated_at ? new Date(stats.generated_at).toLocaleString() : 'N/A'

  if (isLoading) {
    return <p>Loading reports...</p>
  }

  return (
    <div className="stacked-grid dashboard-surface dashboard-compact dashboard-admin reports-page">
      <section className="card page-hero reports-hero">
        <p className="auth-eyebrow">Admin Reports</p>
        <h2>Clinical Intelligence & Operational Reporting</h2>
        <p className="muted">
          Explore prescription velocity, demand by department, urgency mix, and care workflow quality indicators.
        </p>
        <div className="doctor-calendar-legend">
          <span className="chip">Generated: {generatedAtLabel}</span>
          <span className="chip">Recent prescription feed: {recentPrescriptions.length}</span>
          <span className="chip">Total prescriptions: {totalPrescriptions}</span>
        </div>
      </section>

      <section className="stats-grid reports-kpi-grid">
        <article className="metric-card reports-kpi-card">
          <p className="reports-kpi-icon"><ClipboardList size={18} /></p>
          <h4>Total prescriptions</h4>
          <strong>{totalPrescriptions}</strong>
        </article>
        <article className="metric-card reports-kpi-card">
          <p className="reports-kpi-icon"><Pill size={18} /></p>
          <h4>Avg medications / prescription</h4>
          <strong>{avgItemsPerPrescription}</strong>
        </article>
        <article className="metric-card reports-kpi-card">
          <p className="reports-kpi-icon"><UsersRound size={18} /></p>
          <h4>Active patients (30d)</h4>
          <strong>{stats?.active_patients_last_30_days || 0}</strong>
        </article>
        <article className="metric-card reports-kpi-card">
          <p className="reports-kpi-icon"><TrendingUp size={18} /></p>
          <h4>Completion rate</h4>
          <strong>{stats?.completion_rate || 0}%</strong>
        </article>
        <article className="metric-card reports-kpi-card">
          <p className="reports-kpi-icon"><Activity size={18} /></p>
          <h4>No-show rate</h4>
          <strong>{stats?.no_show_rate || 0}%</strong>
        </article>
        <article className="metric-card reports-kpi-card">
          <p className="reports-kpi-icon"><Stethoscope size={18} /></p>
          <h4>Open appointments</h4>
          <strong>{stats?.open_appointments_count || 0}</strong>
        </article>
      </section>

      <section className="card reports-panel">
        <div className="inline-header">
          <h3>Demand & Care Workflow Trends</h3>
          <span className="chip">9-month + real-time split</span>
        </div>
        <div className="chart-grid reports-chart-grid">
          <article className="reports-chart-card">
            <h4>Appointments vs consultations (monthly)</h4>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={monthlyTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line dataKey="appointments" name="Appointments" stroke="#ef5b3f" strokeWidth={2.4} dot={false} />
                <Line dataKey="consultations" name="Consultations" stroke="#0c8a82" strokeWidth={2.4} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </article>

          <article className="reports-chart-card">
            <h4>Status distribution</h4>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={statusSplit} dataKey="value" nameKey="name" innerRadius={50} outerRadius={90}>
                  {statusSplit.map((entry, index) => (
                    <Cell key={entry.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </article>

          <article className="reports-chart-card">
            <h4>Department demand</h4>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={departmentSplit}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#2563eb" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </article>

          <article className="reports-chart-card">
            <h4>Urgency split</h4>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={urgencySplit} dataKey="value" nameKey="name" innerRadius={50} outerRadius={90}>
                  {urgencySplit.map((entry, index) => (
                    <Cell key={entry.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </article>
        </div>
      </section>

      <section className="split-grid reports-insights-grid dashboard-columns">
        <article className="card reports-panel">
          <div className="inline-header">
            <h3>Top medications (recent feed)</h3>
            <span className="chip">from latest {recentPrescriptions.length} prescriptions</span>
          </div>

          <div className="timeline compact-scroll reports-list-scroll">
            {medicationSignals.length === 0 ? <p className="muted">No medication signal available yet.</p> : null}
            {medicationSignals.map((item) => (
              <article key={item.name} className="timeline-item reports-leaderboard-item">
                <p><strong>{item.name}</strong></p>
                <p className="muted">Used in {item.total} prescription(s)</p>
              </article>
            ))}
          </div>
        </article>

        <article className="card reports-panel">
          <div className="inline-header">
            <h3>Top prescribers (recent feed)</h3>
            <span className="chip">prescription activity</span>
          </div>

          <div className="timeline compact-scroll reports-list-scroll">
            {doctorsInRecentFeed.length === 0 ? <p className="muted">No doctor activity available yet.</p> : null}
            {doctorsInRecentFeed.map((doctor) => (
              <article key={doctor.email} className="timeline-item reports-leaderboard-item">
                <p><strong>{doctor.email}</strong></p>
                <p className="muted">{doctor.total} prescription(s) in recent feed</p>
              </article>
            ))}
          </div>
        </article>
      </section>

      <section className="card reports-panel">
        <div className="inline-header">
          <h3>Recent prescription activity</h3>
          <span className="chip">latest entries</span>
        </div>

        {recentPrescriptions.length === 0 ? <p className="muted">No report data available yet.</p> : null}

        <div className="timeline compact-scroll reports-list-scroll">
          {recentPrescriptions.map((item) => (
            <article key={item.id} className="timeline-item reports-prescription-item">
              <div className="reports-prescription-head">
                <h4>Prescription #{item.id}</h4>
                <span className="chip">{(item.items || []).length} medication(s)</span>
              </div>

              <p>
                Doctor: <strong>{item.doctor_email}</strong>
              </p>
              <p>
                Patient: <strong>{item.patient_email}</strong>
              </p>
              <p className="muted">Created at: {toShortDateTime(item.created_at)}</p>

              {(item.items || []).length ? (
                <div className="reports-medications-row">
                  {(item.items || []).slice(0, 4).map((medication) => (
                    <span key={`${item.id}-${medication.id}`} className="chip">
                      {toLabel(medication.medication)} ({medication.dosage})
                    </span>
                  ))}
                </div>
              ) : null}

              {item.notes ? <p className="muted">Notes: {item.notes}</p> : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

export default ReportsPage
