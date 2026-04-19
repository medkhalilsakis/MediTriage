import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { AlertTriangle, Camera, LogOut, Save, Shield, Trash2, UserCog } from 'lucide-react'
import { deleteMyAccount, getMyAccount, updateMyAccount } from '../../api/authApi'
import { useAuthStore } from '../../store/authStore'

const BLOOD_GROUP_OPTIONS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
const GENDER_OPTIONS = ['male', 'female', 'other']
const DOCTOR_DEPARTMENT_OPTIONS = [
  { value: 'general_medicine', label: 'General medicine' },
  { value: 'cardiology', label: 'Cardiology' },
  { value: 'respiratory', label: 'Respiratory diseases' },
  { value: 'neurology', label: 'Neurology' },
  { value: 'gastroenterology', label: 'Gastroenterology' },
  { value: 'dermatology', label: 'Dermatology' },
  { value: 'endocrinology', label: 'Endocrinology' },
]

const ROLE_SETTINGS_COPY = {
  patient: {
    eyebrow: 'Patient Settings',
    title: 'Manage your health identity and security',
    subtitle: 'Update your account details, emergency data, and profile image.',
    dashboardPath: '/patient/dashboard',
  },
  doctor: {
    eyebrow: 'Doctor Settings',
    title: 'Manage your professional profile and security',
    subtitle: 'Update your medical identity, credentials, and profile image.',
    dashboardPath: '/doctor/dashboard',
  },
  admin: {
    eyebrow: 'Admin Settings',
    title: 'Manage your administration account',
    subtitle: 'Update your account details and secure your admin workspace.',
    dashboardPath: '/admin/dashboard',
  },
}

const INITIAL_FORM = {
  email: '',
  username: '',
  first_name: '',
  last_name: '',
  phone_number: '',

  dob: '',
  gender: '',
  blood_group: '',
  allergies: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
  address: '',

  specialization: '',
  department: 'general_medicine',
  license_number: '',
  years_of_experience: 0,
  consultation_fee: '0.00',
  bio: '',
}

const parseApiError = (error, fallback = 'Unable to save account settings.') => {
  const payload = error?.response?.data
  if (!payload) return fallback

  if (typeof payload === 'string') {
    return payload
  }

  if (payload.detail) {
    return String(payload.detail)
  }

  const firstEntry = Object.values(payload)[0]
  if (firstEntry) {
    return Array.isArray(firstEntry) ? firstEntry.join(', ') : String(firstEntry)
  }

  return fallback
}

function AccountSettingsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const updateUser = useAuthStore((state) => state.updateUser)

  const [form, setForm] = useState(INITIAL_FORM)
  const [selectedImageFile, setSelectedImageFile] = useState(null)
  const [imagePreviewUrl, setImagePreviewUrl] = useState('')

  const role = user?.role || 'patient'
  const roleCopy = ROLE_SETTINGS_COPY[role] || ROLE_SETTINGS_COPY.patient

  const accountQuery = useQuery({ queryKey: ['auth-me'], queryFn: getMyAccount })

  useEffect(() => {
    const account = accountQuery.data
    if (!account) {
      return
    }

    setForm({
      email: account.email || '',
      username: account.username || '',
      first_name: account.first_name || '',
      last_name: account.last_name || '',
      phone_number: account.phone_number || '',

      dob: account.dob || '',
      gender: account.gender || '',
      blood_group: account.blood_group || '',
      allergies: account.allergies || '',
      emergency_contact_name: account.emergency_contact_name || '',
      emergency_contact_phone: account.emergency_contact_phone || '',
      address: account.address || '',

      specialization: account.specialization || '',
      department: account.department || 'general_medicine',
      license_number: account.license_number || '',
      years_of_experience: Number(account.years_of_experience || 0),
      consultation_fee: String(account.consultation_fee || '0.00'),
      bio: account.bio || '',
    })

    setImagePreviewUrl(account.profile_image_url || '')
    setSelectedImageFile(null)
  }, [accountQuery.data])

  const canSubmit = useMemo(() => {
    return Boolean(form.email.trim() && form.username.trim() && form.first_name.trim() && form.last_name.trim())
  }, [form.email, form.username, form.first_name, form.last_name])

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
        role: data.role || role,
        profile_image_url: data.profile_image_url || '',
      })

      queryClient.invalidateQueries({ queryKey: ['auth-me'] })
      toast.success('Settings updated successfully.')
    },
    onError: (error) => {
      toast.error(parseApiError(error))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteMyAccount,
    onSuccess: () => {
      logout()
      queryClient.clear()
      toast.success('Account deleted successfully.')
      navigate('/', { replace: true })
    },
    onError: () => {
      toast.error('Unable to delete account.')
    },
  })

  const isBusy = updateMutation.isPending || deleteMutation.isPending

  const handleInputChange = (event) => {
    const { name, value } = event.target
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleImageChange = (event) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    setSelectedImageFile(file)
    const localUrl = URL.createObjectURL(file)
    setImagePreviewUrl(localUrl)
  }

  const buildPayload = () => {
    const basePayload = {
      email: form.email.trim(),
      username: form.username.trim(),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      phone_number: form.phone_number.trim(),
    }

    if (role === 'patient') {
      return {
        ...basePayload,
        dob: form.dob || null,
        gender: form.gender || '',
        blood_group: form.blood_group || '',
        allergies: form.allergies || '',
        emergency_contact_name: form.emergency_contact_name || '',
        emergency_contact_phone: form.emergency_contact_phone || '',
        address: form.address || '',
      }
    }

    if (role === 'doctor') {
      return {
        ...basePayload,
        specialization: form.specialization.trim(),
        department: form.department,
        license_number: form.license_number.trim(),
        years_of_experience: Number(form.years_of_experience || 0),
        consultation_fee: Number(form.consultation_fee || 0),
        bio: form.bio || '',
      }
    }

    return basePayload
  }

  const buildMultipartPayload = () => {
    const payload = buildPayload()
    const formData = new FormData()

    Object.entries(payload).forEach(([key, value]) => {
      if (value === null || value === undefined || value === '') {
        return
      }
      formData.append(key, value)
    })

    if (selectedImageFile) {
      formData.append('profile_image', selectedImageFile)
    }

    return formData
  }

  const handleSave = (event) => {
    event.preventDefault()

    if (!canSubmit) {
      toast.error('Email, username, first name, and last name are required.')
      return
    }

    if (role === 'doctor' && !form.license_number.trim()) {
      toast.error('Doctor license number is required.')
      return
    }

    const payload = selectedImageFile ? buildMultipartPayload() : buildPayload()
    updateMutation.mutate(payload)
  }

  const handleDelete = () => {
    if (isBusy) {
      return
    }

    const confirmed = window.confirm('Delete your account permanently? This action cannot be undone.')
    if (!confirmed) {
      return
    }

    deleteMutation.mutate()
  }

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <p className="auth-eyebrow">{roleCopy.eyebrow}</p>
        <h2>{roleCopy.title}</h2>
        <p className="muted">{roleCopy.subtitle}</p>
      </section>

      <div className="split-grid settings-layout">
        <section className="card settings-main-card">
          <div className="inline-header">
            <h3>
              <UserCog size={18} />
              Profile settings
            </h3>
          </div>

          {accountQuery.isLoading ? <p className="muted">Loading account...</p> : null}
          {accountQuery.isError ? <p className="error">Unable to load account profile.</p> : null}

          <form className="form-grid" onSubmit={handleSave}>
            <div className="settings-avatar-section">
              <div className="settings-avatar-frame">
                {imagePreviewUrl ? (
                  <img src={imagePreviewUrl} alt="Profile" className="settings-avatar-image" />
                ) : (
                  <span className="settings-avatar-fallback">
                    {(form.first_name?.[0] || user?.email?.[0] || 'U').toUpperCase()}
                  </span>
                )}
              </div>
              <label className="ghost-btn settings-upload-label">
                <Camera size={16} />
                Upload profile image
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={handleImageChange}
                  disabled={isBusy}
                  hidden
                />
              </label>
              <p className="muted">Accepted formats: JPG, PNG, WEBP</p>
            </div>

            <div className="settings-grid-two">
              <label>
                Email
                <input type="email" name="email" value={form.email} onChange={handleInputChange} required disabled={isBusy} />
              </label>
              <label>
                Username
                <input type="text" name="username" value={form.username} onChange={handleInputChange} required disabled={isBusy} />
              </label>
              <label>
                First name
                <input type="text" name="first_name" value={form.first_name} onChange={handleInputChange} required disabled={isBusy} />
              </label>
              <label>
                Last name
                <input type="text" name="last_name" value={form.last_name} onChange={handleInputChange} required disabled={isBusy} />
              </label>
              <label>
                Phone number
                <input type="text" name="phone_number" value={form.phone_number} onChange={handleInputChange} disabled={isBusy} />
              </label>
            </div>

            {role === 'patient' ? (
              <div className="settings-role-block">
                <h4>Patient medical identity</h4>
                <div className="settings-grid-two">
                  <label>
                    Birth date
                    <input type="date" name="dob" value={form.dob} onChange={handleInputChange} disabled={isBusy} />
                  </label>
                  <label>
                    Gender
                    <select name="gender" value={form.gender} onChange={handleInputChange} disabled={isBusy}>
                      <option value="">Prefer not to say</option>
                      {GENDER_OPTIONS.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Blood group
                    <select name="blood_group" value={form.blood_group} onChange={handleInputChange} disabled={isBusy}>
                      <option value="">Not specified</option>
                      {BLOOD_GROUP_OPTIONS.map((group) => (
                        <option key={group} value={group}>{group}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Allergies
                    <input type="text" name="allergies" value={form.allergies} onChange={handleInputChange} disabled={isBusy} />
                  </label>
                  <label>
                    Emergency contact name
                    <input type="text" name="emergency_contact_name" value={form.emergency_contact_name} onChange={handleInputChange} disabled={isBusy} />
                  </label>
                  <label>
                    Emergency contact phone
                    <input type="text" name="emergency_contact_phone" value={form.emergency_contact_phone} onChange={handleInputChange} disabled={isBusy} />
                  </label>
                </div>
                <label>
                  Address
                  <textarea name="address" value={form.address} onChange={handleInputChange} disabled={isBusy} />
                </label>
              </div>
            ) : null}

            {role === 'doctor' ? (
              <div className="settings-role-block">
                <h4>Doctor professional profile</h4>
                <div className="settings-grid-two">
                  <label>
                    Specialization
                    <input type="text" name="specialization" value={form.specialization} onChange={handleInputChange} disabled={isBusy} />
                  </label>
                  <label>
                    Department
                    <select name="department" value={form.department} onChange={handleInputChange} disabled={isBusy}>
                      {DOCTOR_DEPARTMENT_OPTIONS.map((department) => (
                        <option key={department.value} value={department.value}>{department.label}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    License number
                    <input type="text" name="license_number" value={form.license_number} onChange={handleInputChange} disabled={isBusy} />
                  </label>
                  <label>
                    Years of experience
                    <input
                      type="number"
                      name="years_of_experience"
                      min="0"
                      value={form.years_of_experience}
                      onChange={handleInputChange}
                      disabled={isBusy}
                    />
                  </label>
                  <label>
                    Consultation fee
                    <input
                      type="number"
                      name="consultation_fee"
                      min="0"
                      step="0.01"
                      value={form.consultation_fee}
                      onChange={handleInputChange}
                      disabled={isBusy}
                    />
                  </label>
                </div>
                <label>
                  Professional bio
                  <textarea name="bio" value={form.bio} onChange={handleInputChange} disabled={isBusy} />
                </label>
              </div>
            ) : null}

            <div className="patient-inline-group">
              <button type="submit" className="inline-action" disabled={isBusy || !canSubmit}>
                <Save size={16} />
                {updateMutation.isPending ? 'Saving...' : 'Save settings'}
              </button>
              <button
                type="button"
                className="ghost-btn inline-action"
                onClick={() => navigate(roleCopy.dashboardPath)}
                disabled={isBusy}
              >
                Back to dashboard
              </button>
            </div>
          </form>
        </section>

        <section className="card settings-side-card">
          <div className="inline-header">
            <h3>
              <Shield size={18} />
              Security actions
            </h3>
          </div>
          <ul className="compact-list">
            <li>Use strong, unique credentials for your account.</li>
            <li>Logout after each session on shared devices.</li>
            <li>Only authenticated users can access protected APIs.</li>
          </ul>

          <div className="patient-inline-group">
            <button type="button" className="secondary-btn inline-action" onClick={handleLogout} disabled={isBusy}>
              <LogOut size={16} />
              Logout
            </button>
          </div>

          <div className="patient-danger-zone">
            <h4>
              <AlertTriangle size={16} />
              Danger zone
            </h4>
            <p className="muted">Delete your account permanently. This action cannot be reversed.</p>
            <button type="button" className="danger-btn inline-action" onClick={handleDelete} disabled={isBusy}>
              <Trash2 size={16} />
              {deleteMutation.isPending ? 'Deleting...' : 'Delete account'}
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}

export default AccountSettingsPage
