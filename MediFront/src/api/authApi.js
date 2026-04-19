import { axiosInstance } from './axiosInstance'

export const registerUser = async (payload) => {
  const { data } = await axiosInstance.post('/auth/register/', payload)
  return data
}

export const loginUser = async (payload) => {
  const { data } = await axiosInstance.post('/auth/login/', payload)
  return data
}

export const refreshTokenApi = async (refresh) => {
  const { data } = await axiosInstance.post('/auth/token/refresh/', { refresh })
  return data
}

export const getMyAccount = async () => {
  const { data } = await axiosInstance.get('/auth/me/')
  return data
}

export const updateMyAccount = async (payload) => {
  const isFormData = typeof FormData !== 'undefined' && payload instanceof FormData
  const { data } = await axiosInstance.patch('/auth/me/', payload, {
    headers: isFormData
      ? {
        'Content-Type': 'multipart/form-data',
      }
      : undefined,
  })
  return data
}

export const deleteMyAccount = async () => {
  await axiosInstance.delete('/auth/me/')
}

export const fetchAdminStats = async () => {
  const { data } = await axiosInstance.get('/admin/stats/')
  return data
}
