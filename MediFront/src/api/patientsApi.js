import { axiosInstance } from './axiosInstance'

export const listPatientProfiles = async (params = {}) => {
  const { data } = await axiosInstance.get('/patients/', { params })
  return data
}
