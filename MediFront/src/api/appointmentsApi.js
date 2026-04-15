import { axiosInstance } from './axiosInstance'

export const listAppointments = async (params = {}) => {
  const { data } = await axiosInstance.get('/appointments/', { params })
  return data
}

export const createAppointment = async (payload) => {
  const { data } = await axiosInstance.post('/appointments/', payload)
  return data
}

export const getAppointmentById = async (id) => {
  const { data } = await axiosInstance.get(`/appointments/${id}/`)
  return data
}

export const updateAppointment = async (id, payload) => {
  const { data } = await axiosInstance.patch(`/appointments/${id}/`, payload)
  return data
}

export const cancelAppointment = async (id) => {
  const { data } = await axiosInstance.patch(`/appointments/${id}/`, { status: 'cancelled' })
  return data
}

export const getTodayAppointments = async (params = {}) => {
  const { data } = await axiosInstance.get('/appointments/today/', { params })
  return data
}

export const acceptAppointment = async (id) => {
  const { data } = await axiosInstance.post(`/appointments/${id}/accept/`)
  return data
}

export const completeAppointment = async (id) => {
  const { data } = await axiosInstance.post(`/appointments/${id}/complete/`)
  return data
}

export const delayAppointment = async (id, scheduledAt) => {
  const { data } = await axiosInstance.post(`/appointments/${id}/delay/`, {
    scheduled_at: scheduledAt,
  })
  return data
}

export const reassignAppointment = async (id, doctorId, scheduledAt) => {
  const payload = { doctor_id: doctorId }
  if (scheduledAt) {
    payload.scheduled_at = scheduledAt
  }

  const { data } = await axiosInstance.post(`/appointments/${id}/reassign/`, payload)
  return data
}

export const requestRescheduleAppointment = async (id, scheduledAt) => {
  const { data } = await axiosInstance.post(`/appointments/${id}/request-reschedule/`, {
    scheduled_at: scheduledAt,
  })
  return data
}

export const listAdvanceOffers = async (params = {}) => {
  const { data } = await axiosInstance.get('/appointments/advance-offers/', { params })
  return data
}

export const respondAdvanceOffer = async (id, decision) => {
  const { data } = await axiosInstance.post(`/appointments/advance-offers/${id}/respond/`, {
    decision,
  })
  return data
}
