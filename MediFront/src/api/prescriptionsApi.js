import { axiosInstance } from './axiosInstance'

export const listPrescriptions = async (params = {}) => {
  const { data } = await axiosInstance.get('/prescriptions/', { params })
  return data
}

export const createPrescription = async (payload) => {
  const { data } = await axiosInstance.post('/prescriptions/', payload)
  return data
}

export const getPrescriptionPdfUrl = (id) => {
  const base = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
  return `${base}/prescriptions/${id}/pdf/`
}
