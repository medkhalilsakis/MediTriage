import { axiosInstance } from './axiosInstance'

export const listPatientProfiles = async (params = {}) => {
  const { data } = await axiosInstance.get('/patients/', { params })
  return data
}

export const deletePatientAccountByAdmin = async (id) => {
  const { data } = await axiosInstance.post(`/patients/${id}/delete-account/`)
  return data
}
