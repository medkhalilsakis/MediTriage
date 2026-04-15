import { axiosInstance } from './axiosInstance'

export const createChatSession = async (payload) => {
  const { data } = await axiosInstance.post('/chatbot/sessions/', payload)
  return data
}

export const sendChatMessage = async (sessionId, contentOrPayload, options = {}) => {
  const payload =
    typeof contentOrPayload === 'string'
      ? { content: contentOrPayload, ...options }
      : contentOrPayload

  const { data } = await axiosInstance.post(`/chatbot/sessions/${sessionId}/message/`, payload)
  return data
}

export const listChatSessions = async () => {
  const { data } = await axiosInstance.get('/chatbot/sessions/')
  return data
}

export const deleteChatSession = async (sessionId) => {
  await axiosInstance.delete(`/chatbot/sessions/${sessionId}/`)
}
