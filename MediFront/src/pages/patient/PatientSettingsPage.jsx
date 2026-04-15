import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { AlertTriangle, Shield, Trash2, UserCog } from 'lucide-react'
import { deleteMyAccount, getMyAccount, updateMyAccount } from '../../api/authApi'
import { useAuthStore } from '../../store/authStore'

const INITIAL_FORM = {
  email: '',
  username: '',
  first_name: '',
  last_name: '',
  phone_number: '',
  dob: '',
  gender: '',
  blood_group: '',
}

const getErrorMessage = (error) => {
  const payload = error?.response?.data
  if (!payload) return 'Unable to update account. Please check your data.'
  if (typeof payload === 'string') return payload

  const firstKey = Object.keys(payload)[0]
  const firstValue = payload[firstKey]
  if (Array.isArray(firstValue) && firstValue.length > 0) {
    return String(firstValue[0])
  }

  return 'Unable to update account. Please check your data.'
}

function PatientSettingsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const logout = useAuthStore((state) => state.logout)
  const user = useAuthStore((state) => state.user)
  const updateUser = useAuthStore((state) => state.updateUser)
  const [form, setForm] = useState(INITIAL_FORM)

  const accountQuery = useQuery({ queryKey: ['auth-me'], queryFn: getMyAccount })

  useEffect(() => {
    if (!accountQuery.data) return

    setForm({
      email: accountQuery.data.email || '',
      username: accountQuery.data.username || '',
      first_name: accountQuery.data.first_name || '',
      last_name: accountQuery.data.last_name || '',
      phone_number: accountQuery.data.phone_number || '',
      dob: accountQuery.data.dob || '',
      gender: accountQuery.data.gender || '',
      blood_group: accountQuery.data.blood_group || '',
    })
  }, [accountQuery.data])

  const updateMutation = useMutation({
    mutationFn: updateMyAccount,
    onSuccess: (data) => {
      updateUser({
        ...(user || {}),
        id: data.id,
        email: data.email,
        username: data.username,
        first_name: data.first_name,
        last_name: data.last_name,
        phone_number: data.phone_number,
        role: data.role || user?.role,
      })

      queryClient.invalidateQueries({ queryKey: ['auth-me'] })
      queryClient.invalidateQueries({ queryKey: ['patient-profiles'] })
      toast.success('Account updated successfully.')
    },
    onError: (error) => {
      toast.error(getErrorMessage(error))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteMyAccount,
    onSuccess: () => {
      logout()
      queryClient.clear()
      toast.success('Your account has been deleted.')
      navigate('/', { replace: true })
    },
    onError: () => {
      toast.error('Unable to delete account.')
    },
  })

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleFieldChange = (event) => {
    const { name, value } = event.target
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleSave = (event) => {
    event.preventDefault()

    if (!form.email || !form.username || !form.first_name || !form.last_name) {
      toast.error('Email, username, first name, and last name are required.')
      return
    }

    updateMutation.mutate({
      email: form.email.trim(),
      username: form.username.trim(),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      phone_number: form.phone_number.trim(),
      dob: form.dob || null,
      gender: form.gender,
      blood_group: form.blood_group,
    })
  }

  const handleDeleteAccount = () => {
    if (deleteMutation.isPending) return

    const confirmed = window.confirm(
      'Delete your account permanently? This will remove your profile and cannot be undone.',
    )

    if (!confirmed) return
    deleteMutation.mutate()
  }

  const isBusy = updateMutation.isPending || deleteMutation.isPending

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <p className="auth-eyebrow">Account Settings</p>
        <h2>Profile and security control center</h2>
        <p className="muted">
          Update personal information and health identity data from one secure page.
        </p>
      </section>

      <div className="split-grid patient-settings-grid">
        <section className="card">
          <div className="inline-header">
            <h3>
              <UserCog size={18} />
              Account information
            </h3>
          </div>

          {accountQuery.isLoading ? <p className="muted">Loading account data...</p> : null}
          {accountQuery.isError ? <p className="error">Unable to load your account details.</p> : null}

          <form className="form-grid patient-account-form" onSubmit={handleSave}>
            <div className="patient-account-columns">
              <label>
                Email
                <input
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleFieldChange}
                  required
                  disabled={isBusy}
                />
              </label>

              <label>
                Username
                <input
                  type="text"
                  name="username"
                  value={form.username}
                  onChange={handleFieldChange}
                  required
                  disabled={isBusy}
                />
              </label>

              <label>
                First name
                <input
                  type="text"
                  name="first_name"
                  value={form.first_name}
                  onChange={handleFieldChange}
                  required
                  disabled={isBusy}
                />
              </label>

              <label>
                Last name
                <input
                  type="text"
                  name="last_name"
                  value={form.last_name}
                  onChange={handleFieldChange}
                  required
                  disabled={isBusy}
                />
              </label>

              <label>
                Phone number
                <input
                  type="text"
                  name="phone_number"
                  value={form.phone_number}
                  onChange={handleFieldChange}
                  disabled={isBusy}
                />
              </label>

              <label>
                Birth date
                <input
                  type="date"
                  name="dob"
                  value={form.dob}
                  onChange={handleFieldChange}
                  disabled={isBusy}
                />
              </label>

              <label>
                Gender
                <select name="gender" value={form.gender} onChange={handleFieldChange} disabled={isBusy}>
                  <option value="">Prefer not to say</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </label>

              <label>
                Blood group
                <select
                  name="blood_group"
                  value={form.blood_group}
                  onChange={handleFieldChange}
                  disabled={isBusy}
                >
                  <option value="">Not specified</option>
                  <option value="A+">A+</option>
                  <option value="A-">A-</option>
                  <option value="B+">B+</option>
                  <option value="B-">B-</option>
                  <option value="AB+">AB+</option>
                  <option value="AB-">AB-</option>
                  <option value="O+">O+</option>
                  <option value="O-">O-</option>
                </select>
              </label>
            </div>

            <p className="muted">
              Role: <strong>{user?.role || 'patient'}</strong>
            </p>

            <div className="patient-inline-group patient-account-actions">
              <button type="submit" className="inline-action" disabled={isBusy || accountQuery.isLoading}>
                {updateMutation.isPending ? 'Saving...' : 'Save changes'}
              </button>
              <button
                type="button"
                className="ghost-btn inline-action"
                onClick={() => navigate('/patient/dashboard')}
                disabled={isBusy}
              >
                Back to dashboard
              </button>
            </div>
          </form>
        </section>

        <section className="card">
          <div className="inline-header">
            <h3>
              <Shield size={18} />
              Data security
            </h3>
          </div>

          <ul className="compact-list">
            <li>Your API session uses secured Bearer tokens.</li>
            <li>Only authenticated users can access patient data routes.</li>
            <li>Log out from shared devices after each session.</li>
            <li>Use a strong password and rotate it periodically.</li>
          </ul>

          <div className="patient-inline-group">
            <button type="button" className="danger-btn inline-action" onClick={handleLogout} disabled={isBusy}>
              Logout
            </button>
          </div>
        </section>
      </div>

      <section className="card patient-danger-zone">
        <div className="inline-header">
          <h3>
            <AlertTriangle size={18} />
            Danger zone
          </h3>
        </div>
        <p className="muted">
          You can permanently delete your account at any time. This action deletes your profile and cannot be undone.
        </p>
        <button
          type="button"
          className="danger-btn inline-action"
          onClick={handleDeleteAccount}
          disabled={isBusy}
        >
          <Trash2 size={16} />
          {deleteMutation.isPending ? 'Deleting...' : 'Delete my account'}
        </button>
      </section>
    </div>
  )
}

export default PatientSettingsPage
