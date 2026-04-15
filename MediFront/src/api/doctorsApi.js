import { axiosInstance } from './axiosInstance'

export const listDoctorProfiles = async (params = {}) => {
  const { data } = await axiosInstance.get('/doctors/profiles/', { params })
  return data
}

export const listDoctorAvailability = async (params = {}) => {
  const { data } = await axiosInstance.get('/doctors/availability/', { params })
  return data
}

export const listDoctorLeaves = async (params = {}) => {
  const { data } = await axiosInstance.get('/doctors/leaves/', { params })
  return data
}

export const createDoctorLeave = async (payload) => {
  const { data } = await axiosInstance.post('/doctors/leaves/', payload)
  return data
}

export const updateDoctorLeave = async (id, payload) => {
  const { data } = await axiosInstance.patch(`/doctors/leaves/${id}/`, payload)
  return data
}

export const approveDoctorLeave = async (id, payload = {}) => {
  const { data } = await axiosInstance.post(`/doctors/leaves/${id}/approve/`, payload)
  return data
}

export const rejectDoctorLeave = async (id, payload = {}) => {
  const { data } = await axiosInstance.post(`/doctors/leaves/${id}/reject/`, payload)
  return data
}

export const cancelDoctorLeave = async (id) => {
  const { data } = await axiosInstance.post(`/doctors/leaves/${id}/cancel/`)
  return data
}
