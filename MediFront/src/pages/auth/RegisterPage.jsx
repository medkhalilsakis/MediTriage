import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { registerUser } from '../../api/authApi'
import { useAuthStore } from '../../store/authStore'

const DEPARTMENTS = [
  { value: 'cardiology', label: 'Cardiology' },
  { value: 'respiratory', label: 'Respiratory Diseases' },
  { value: 'neurology', label: 'Neurology' },
  { value: 'gastroenterology', label: 'Gastroenterology' },
  { value: 'dermatology', label: 'Dermatology' },
  { value: 'endocrinology', label: 'Endocrinology' },
  { value: 'general_medicine', label: 'General Medicine' },
]

const schema = z
  .object({
    email: z.string().email(),
    username: z.string().min(3),
    first_name: z.string().min(1),
    last_name: z.string().min(1),
    role: z.enum(['patient', 'doctor', 'admin']),
    password: z.string().min(8),
    specialization: z.string().optional(),
    department: z.string().optional(),
    license_number: z.string().optional(),
  })
  .superRefine((values, context) => {
    if (values.role !== 'doctor') {
      return
    }

    if (!values.specialization?.trim()) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['specialization'],
        message: 'Specialization is required for doctor accounts.',
      })
    }

    if (!values.department?.trim()) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['department'],
        message: 'Department is required for doctor accounts.',
      })
    }

    if (!values.license_number?.trim()) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['license_number'],
        message: 'License number is required for doctor accounts.',
      })
    }
  })

const getErrorMessage = (error) => {
  const data = error?.response?.data
  if (typeof data === 'string') return data
  if (data?.detail) return data.detail
  if (data && typeof data === 'object') {
    const [firstValue] = Object.values(data)
    if (Array.isArray(firstValue)) return firstValue[0]
    if (typeof firstValue === 'string') return firstValue
  }
  return 'Unable to register. Verify your data.'
}

function RegisterPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)
  const {
    register,
    watch,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      role: 'patient',
      specialization: '',
      department: '',
      license_number: '',
    },
  })

  const role = watch('role')

  const mutation = useMutation({
    mutationFn: registerUser,
    onSuccess: (data) => {
      setAuth(data)
      toast.success('Account created')
      const role = data.user.role
      if (role === 'patient') navigate('/patient/dashboard')
      if (role === 'doctor') navigate('/doctor/dashboard')
      if (role === 'admin') navigate('/admin/dashboard')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        <p className="auth-eyebrow">Start Your Workspace</p>
        <h1 className="auth-title">Create MediSmart Account</h1>
        <p className="auth-note">Set your role and join a unified care journey for patients, doctors, and admins.</p>
        <input placeholder="Email" {...register('email')} />
        <p className="error">{errors.email?.message}</p>
        <input placeholder="Username" {...register('username')} />
        <input placeholder="First name" {...register('first_name')} />
        <input placeholder="Last name" {...register('last_name')} />
        <select {...register('role')}>
          <option value="patient">Patient</option>
          <option value="doctor">Doctor</option>
          <option value="admin">Admin</option>
        </select>

        {role === 'doctor' ? (
          <>
            <input placeholder="Specialization" {...register('specialization')} />
            <p className="error">{errors.specialization?.message}</p>

            <label>
              Department
              <select {...register('department')}>
                <option value="">Select department</option>
                {DEPARTMENTS.map((department) => (
                  <option key={department.value} value={department.value}>
                    {department.label}
                  </option>
                ))}
              </select>
            </label>
            <p className="error">{errors.department?.message}</p>

            <input placeholder="Medical license number" {...register('license_number')} />
            <p className="error">{errors.license_number?.message}</p>
          </>
        ) : null}

        <input type="password" placeholder="Password" {...register('password')} />
        <p className="error">{errors.password?.message}</p>
        <button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Loading...' : 'Register'}</button>
        <p>
          Already registered? <Link className="primary-link" to="/login">Login</Link>
        </p>
      </form>
    </div>
  )
}

export default RegisterPage
