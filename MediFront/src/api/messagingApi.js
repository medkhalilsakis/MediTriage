import { axiosInstance } from './axiosInstance'

export const listMessagingContacts = async () => {
  const { data } = await axiosInstance.get('/messaging/contacts/')
  return data
}

export const listMessagingConversations = async () => {
  const { data } = await axiosInstance.get('/messaging/conversations/')
  return data
}

export const openMessagingConversation = async (recipientId) => {
  const { data } = await axiosInstance.post('/messaging/conversations/', {
    recipient_id: recipientId,
  })
  return data
}

export const listConversationMessages = async (conversationId, limit = 120) => {
  const { data } = await axiosInstance.get(`/messaging/conversations/${conversationId}/messages/`, {
    params: { limit },
  })
  return data
}

export const sendConversationMessage = async (conversationId, content) => {
  const { data } = await axiosInstance.post(`/messaging/conversations/${conversationId}/messages/`, {
    content,
  })
  return data
}

export const sendPresenceHeartbeat = async (payload = { is_online: true }) => {
  const { data } = await axiosInstance.post('/messaging/presence/heartbeat/', payload)
  return data
}

export const getMessagingSummary = async () => {
  const { data } = await axiosInstance.get('/messaging/summary/')
  return data
}
