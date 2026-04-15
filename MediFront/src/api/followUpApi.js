import { axiosInstance } from './axiosInstance'

export const listFollowUps = async (params = {}) => {
  const { data } = await axiosInstance.get('/follow-up/', { params })
  return data
}

export const createFollowUp = async (payload) => {
  const { data } = await axiosInstance.post('/follow-up/', payload)
  return data
}
