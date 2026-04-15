import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import './App.css'
import LoginPage from './pages/auth/LoginPage'
import NotFoundPage from './pages/auth/NotFoundPage'
import RegisterPage from './pages/auth/RegisterPage'
import UnauthorizedPage from './pages/auth/UnauthorizedPage'
import AdminDashboard from './pages/admin/AdminDashboard'
import ReportsPage from './pages/admin/ReportsPage'
import UsersPage from './pages/admin/UsersPage'
import ConsultationPage from './pages/doctor/ConsultationPage'
import DoctorDashboard from './pages/doctor/DoctorDashboard'
import FollowUpPage from './pages/doctor/FollowUpPage'
import PatientsTodayPage from './pages/doctor/PatientsTodayPage'
import PrescriptionPage from './pages/doctor/PrescriptionPage'
import AppointmentsPage from './pages/patient/AppointmentsPage'
import PatientDashboard from './pages/patient/PatientDashboard'
import PatientSettingsPage from './pages/patient/PatientSettingsPage'
import ChatbotPage from './pages/patient/ChatbotPage'
import MedicalRecordPage from './pages/patient/MedicalRecordPage'
import NotificationsPage from './pages/patient/NotificationsPage'
import LandingPage from './pages/public/LandingPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />

      <Route element={<ProtectedRoute allowedRoles={['patient', 'doctor', 'admin']} />}>
        <Route element={<Layout />}>
          <Route path="/patient" element={<Navigate to="/patient/dashboard" replace />} />
          <Route path="/patient/dashboard" element={<ProtectedRoute allowedRoles={['patient']} />}>
            <Route index element={<PatientDashboard />} />
          </Route>
          <Route path="/patient/chatbot" element={<ProtectedRoute allowedRoles={['patient']} />}>
            <Route index element={<ChatbotPage />} />
          </Route>
          <Route path="/patient/appointments" element={<ProtectedRoute allowedRoles={['patient']} />}>
            <Route index element={<AppointmentsPage />} />
          </Route>
          <Route path="/patient/medical-records" element={<ProtectedRoute allowedRoles={['patient']} />}>
            <Route index element={<MedicalRecordPage />} />
          </Route>
          <Route path="/patient/notifications" element={<ProtectedRoute allowedRoles={['patient']} />}>
            <Route index element={<NotificationsPage />} />
          </Route>
          <Route path="/patient/settings" element={<ProtectedRoute allowedRoles={['patient']} />}>
            <Route index element={<PatientSettingsPage />} />
          </Route>

          <Route path="/doctor/dashboard" element={<ProtectedRoute allowedRoles={['doctor']} />}>
            <Route index element={<DoctorDashboard />} />
          </Route>
          <Route path="/doctor/patients-today" element={<ProtectedRoute allowedRoles={['doctor']} />}>
            <Route index element={<PatientsTodayPage />} />
          </Route>
          <Route path="/doctor/consultation" element={<ProtectedRoute allowedRoles={['doctor']} />}>
            <Route index element={<ConsultationPage />} />
          </Route>
          <Route path="/doctor/prescriptions" element={<ProtectedRoute allowedRoles={['doctor']} />}>
            <Route index element={<PrescriptionPage />} />
          </Route>
          <Route path="/doctor/follow-up" element={<ProtectedRoute allowedRoles={['doctor']} />}>
            <Route index element={<FollowUpPage />} />
          </Route>

          <Route path="/admin/dashboard" element={<ProtectedRoute allowedRoles={['admin']} />}>
            <Route index element={<AdminDashboard />} />
          </Route>
          <Route path="/admin/users" element={<ProtectedRoute allowedRoles={['admin']} />}>
            <Route index element={<UsersPage />} />
          </Route>
          <Route path="/admin/reports" element={<ProtectedRoute allowedRoles={['admin']} />}>
            <Route index element={<ReportsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default App
