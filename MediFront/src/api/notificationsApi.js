import { axiosInstance } from './axiosInstance'

export const listNotifications = async () => {
  const { data } = await axiosInstance.get('/notifications/')
  return data
}

export const markAllNotificationsRead = async () => {
  const { data } = await axiosInstance.post('/notifications/mark-all-read/')
  return data
}
