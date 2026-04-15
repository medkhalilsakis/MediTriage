import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

function ProtectedRoute({ allowedRoles = [] }) {
  const user = useAuthStore((state) => state.user)
  const accessToken = useAuthStore((state) => state.accessToken)

  if (!accessToken || !user) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />
  }

  return <Outlet />
}

export default ProtectedRoute
