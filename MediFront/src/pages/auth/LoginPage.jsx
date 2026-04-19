import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { loginUser } from '../../api/authApi'
import { useAuthStore } from '../../store/authStore'

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})

function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)
  const { register, handleSubmit, formState: { errors } } = useForm({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: loginUser,
    onSuccess: (data) => {
      setAuth(data)
      toast.success('Login successful')
      const role = data.user.role
      if (role === 'patient') navigate('/patient/dashboard')
      if (role === 'doctor') navigate('/doctor/dashboard')
      if (role === 'admin') navigate('/admin/dashboard')
    },
    onError: () => toast.error('Unable to login. Check credentials.'),
  })

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        <img src="/visuals/meditriage-logo.svg" alt="MediTriage" className="auth-brand-logo" />
        <p className="auth-eyebrow">Digital Care Platform</p>
        <h1 className="auth-title">Sign In To MediTriage</h1>
        <p className="auth-note">Access triage, consultations, and patient follow-up in one secure workspace.</p>
        <input placeholder="Email" {...register('email')} />
        <p className="error">{errors.email?.message}</p>
        <input type="password" placeholder="Password" {...register('password')} />
        <p className="error">{errors.password?.message}</p>
        <button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Loading...' : 'Login'}</button>
        <p>
          Need an account? <Link className="primary-link" to="/register">Register</Link>
        </p>
      </form>
    </div>
  )
}

export default LoginPage
