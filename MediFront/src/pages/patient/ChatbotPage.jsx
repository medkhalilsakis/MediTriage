import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { createChatSession, deleteChatSession, listChatSessions, sendChatMessage } from '../../api/chatbotApi'
import ChatWindow from '../../components/ChatWindow'
import DiagnosisCard from '../../components/DiagnosisCard'

const getErrorMessage = (error) => {
  const payload = error?.response?.data
  if (!payload) return 'Unable to send message.'
  if (typeof payload === 'string') return payload
  if (payload.detail) return payload.detail

  const firstValue = Object.values(payload)[0]
  if (Array.isArray(firstValue) && firstValue.length > 0) return String(firstValue[0])
  if (typeof firstValue === 'string' && firstValue.trim()) return firstValue

  return 'Unable to send message.'
}

function ChatbotPage() {
  const queryClient = useQueryClient()
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [input, setInput] = useState('')

  const sessionsQuery = useQuery({ queryKey: ['chat-sessions'], queryFn: listChatSessions })

  const sessions = sessionsQuery.data?.results || sessionsQuery.data || []

  useEffect(() => {
    if (sessions.length === 0) {
      if (activeSessionId !== null) {
        setActiveSessionId(null)
      }
      return
    }

    if (!activeSessionId) {
      setActiveSessionId(sessions[0].id)
      return
    }

    const exists = sessions.some((session) => session.id === activeSessionId)
    if (!exists) {
      setActiveSessionId(sessions[0].id)
    }
  }, [sessions, activeSessionId])

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) || null,
    [sessions, activeSessionId],
  )

  const messages = activeSession?.messages || []

  const analysis = useMemo(() => {
    const botMessageWithMetadata = [...messages]
      .reverse()
      .find((message) => message.sender === 'bot' && message.metadata && Object.keys(message.metadata).length > 0)

    if (!botMessageWithMetadata?.metadata) {
      return activeSession?.latest_analysis || null
    }

    const metadata = botMessageWithMetadata.metadata
    if (metadata.probable_diseases || metadata.recommended_appointment || metadata.urgency_level) {
      return metadata
    }

    return activeSession?.latest_analysis || null
  }, [messages, activeSession])

  const createSessionMutation = useMutation({
    mutationFn: () => createChatSession({ title: `Triage ${new Date().toLocaleString()}` }),
    onSuccess: (createdSession) => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      setActiveSessionId(createdSession.id)
      toast.success('New conversation created.')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })

  const deleteSessionMutation = useMutation({
    mutationFn: deleteChatSession,
    onSuccess: (_, deletedSessionId) => {
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      if (activeSessionId === deletedSessionId) {
        setActiveSessionId(null)
      }
      toast.success('Conversation deleted.')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })

  const sendMutation = useMutation({
    mutationFn: async ({ content }) => {
      let currentSessionId = activeSessionId
      if (!currentSessionId) {
        const session = await createChatSession({ title: 'Triage Session' })
        currentSessionId = session.id
        setActiveSessionId(currentSessionId)
      }
      return sendChatMessage(currentSessionId, {
        content,
      })
    },
    onSuccess: (data) => {
      if (data?.session?.id) {
        setActiveSessionId(data.session.id)
      }
      queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      setInput('')
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })

  const handleSend = () => {
    if (!input.trim()) return
    sendMutation.mutate({
      content: input.trim(),
    })
  }

  const handleInputKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>AI Symptom Triage</h2>
        <p className="muted">
          Describe your symptoms in any language. Each conversation is saved in your history. You can start several
          conversations, delete any conversation, and the chatbot can auto-book one appointment per conversation if
          you accept.
        </p>
      </section>

      <div className="grid-two">
        <section className="card chatbot-sessions-card">
          <div className="inline-header">
            <h3>Conversations history</h3>
            <button
              type="button"
              className="ghost-btn inline-action"
              onClick={() => createSessionMutation.mutate()}
              disabled={createSessionMutation.isPending}
            >
              New conversation
            </button>
          </div>

          <div className="timeline">
            {sessions.length === 0 ? <p className="muted">No conversation yet.</p> : null}

            {sessions.map((session) => {
              const isActive = session.id === activeSessionId
              return (
                <article key={session.id} className={`timeline-item ${isActive ? 'unread' : 'read'}`}>
                  <p>
                    <strong>{session.title || `Conversation #${session.id}`}</strong>
                  </p>
                  <p className="muted">Created: {new Date(session.created_at).toLocaleString()}</p>
                  <p>
                    Status:{' '}
                    <span className={`status-tag ${session.is_closed ? 'completed' : 'pending'}`}>
                      {session.is_closed ? 'closed' : 'active'}
                    </span>
                  </p>

                  <div className="patient-inline-group">
                    <button type="button" onClick={() => setActiveSessionId(session.id)}>
                      Open
                    </button>
                    <button
                      type="button"
                      className="secondary-btn"
                      onClick={() => deleteSessionMutation.mutate(session.id)}
                      disabled={deleteSessionMutation.isPending}
                    >
                      Delete
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        </section>

        <div>
          <ChatWindow messages={messages} />
          {activeSession?.awaiting_appointment_confirmation ? (
            <p className="chip">Waiting your answer: reply yes or no for appointment booking.</p>
          ) : null}
          {activeSession?.booked_appointment ? (
            <p className="chip">Booked appointment ID: {activeSession.booked_appointment}</p>
          ) : null}
          {activeSession?.is_closed ? (
            <p className="muted">This conversation is closed after appointment booking. Start a new conversation.</p>
          ) : null}
          <div className="message-input-row">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleInputKeyDown}
              placeholder="Describe your symptoms..."
              disabled={activeSession?.is_closed}
            />
            <button onClick={handleSend} disabled={sendMutation.isPending || Boolean(activeSession?.is_closed)}>
              {sendMutation.isPending ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>
        <DiagnosisCard analysis={analysis} />
      </div>
    </div>
  )
}

export default ChatbotPage
