import { axiosInstance } from './axiosInstance'

export const listMedicalRecords = async (params = {}) => {
  const { data } = await axiosInstance.get('/medical-records/records/', { params })
  return data
}

export const getMedicalRecord = async (recordId) => {
  const { data } = await axiosInstance.get(`/medical-records/records/${recordId}/`)
  return data
}

export const listConsultations = async (params = {}) => {
  const { data } = await axiosInstance.get('/medical-records/consultations/', { params })
  return data
}

export const createConsultation = async (payload) => {
  const { data } = await axiosInstance.post('/medical-records/consultations/', payload)
  return data
}

export const updateConsultation = async (consultationId, payload) => {
  const { data } = await axiosInstance.patch(`/medical-records/consultations/${consultationId}/`, payload)
  return data
}

export const createConsultationFromAppointment = async (payload) => {
  const { data } = await axiosInstance.post('/medical-records/consultations/create-from-appointment/', payload)
  return data
}

export const scheduleFollowUpFromConsultation = async (consultationId, payload) => {
  const { data } = await axiosInstance.post(`/medical-records/consultations/${consultationId}/schedule-follow-up/`, payload)
  return data
}

export const referFromConsultation = async (consultationId, payload) => {
  const { data } = await axiosInstance.post(`/medical-records/consultations/${consultationId}/refer/`, payload)
  return data
}

export const updateMedicalRecord = async (recordId, payload) => {
  const { data } = await axiosInstance.patch(`/medical-records/records/${recordId}/`, payload)
  return data
}

export const closeMedicalRecord = async (recordId) => {
  const { data } = await axiosInstance.post(`/medical-records/records/${recordId}/close/`)
  return data
}

export const archiveMedicalRecord = async (recordId) => {
  const { data } = await axiosInstance.post(`/medical-records/records/${recordId}/archive/`)
  return data
}

export const reopenMedicalRecord = async (recordId) => {
  const { data } = await axiosInstance.post(`/medical-records/records/${recordId}/reopen/`)
  return data
}

export const listMedicalDocumentRequests = async (params = {}) => {
  const { data } = await axiosInstance.get('/medical-records/requests/', { params })
  return data
}

export const createMedicalDocumentRequest = async (payload) => {
  const { data } = await axiosInstance.post('/medical-records/requests/', payload)
  return data
}

export const updateMedicalDocumentRequest = async (id, payload) => {
  const { data } = await axiosInstance.patch(`/medical-records/requests/${id}/`, payload)
  return data
}

export const listMedicalDocuments = async (params = {}) => {
  const { data } = await axiosInstance.get('/medical-records/documents/', { params })
  return data
}

export const uploadMedicalDocument = async (payload) => {
  const formData = new FormData()

  Object.entries(payload || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return
    }
    formData.append(key, value)
  })

  const { data } = await axiosInstance.post('/medical-records/documents/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return data
}

export const updateMedicalDocument = async (id, payload) => {
  const { data } = await axiosInstance.patch(`/medical-records/documents/${id}/`, payload)
  return data
}
