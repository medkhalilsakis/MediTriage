import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Circle, MessageCircle, Send, UserRound } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import {
  getMessagingSummary,
  listConversationMessages,
  listMessagingContacts,
  listMessagingConversations,
  openMessagingConversation,
  sendConversationMessage,
} from '../../api/messagingApi'
import { useAuthStore } from '../../store/authStore'

const REFRESH_CONTACTS_MS = 5000
const REFRESH_CONVERSATIONS_MS = 5000
const REFRESH_MESSAGES_MS = 2500
const formatDateTime = (value) => {
  if (!value) {
    return ''
  }
  return new Date(value).toLocaleString()
}

const safeText = (value, fallback = '') => {
  const text = String(value || '').trim()
  return text || fallback
}

function MessagingPage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const [searchParams, setSearchParams] = useSearchParams()

  const [activeContactId, setActiveContactId] = useState(null)
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [draft, setDraft] = useState('')

  const targetContactEmail = safeText(searchParams.get('contact')).toLowerCase()

  const contactsQuery = useQuery({
    queryKey: ['messaging-contacts'],
    queryFn: listMessagingContacts,
    refetchInterval: REFRESH_CONTACTS_MS,
    refetchOnWindowFocus: true,
  })

  const summaryQuery = useQuery({
    queryKey: ['messaging-summary'],
    queryFn: getMessagingSummary,
    refetchInterval: REFRESH_CONTACTS_MS,
    refetchOnWindowFocus: true,
  })

  const conversationsQuery = useQuery({
    queryKey: ['messaging-conversations'],
    queryFn: listMessagingConversations,
    refetchInterval: REFRESH_CONVERSATIONS_MS,
    refetchOnWindowFocus: true,
  })

  const messagesQuery = useQuery({
    queryKey: ['messaging-conversation-messages', activeConversationId],
    queryFn: () => listConversationMessages(activeConversationId),
    enabled: Boolean(activeConversationId),
    refetchInterval: REFRESH_MESSAGES_MS,
    refetchOnWindowFocus: true,
  })

  const openConversationMutation = useMutation({
    mutationFn: openMessagingConversation,
    onSuccess: (payload) => {
      setActiveConversationId(payload?.conversation?.id || null)
      setActiveContactId(payload?.other_user?.id || null)
      queryClient.invalidateQueries({ queryKey: ['messaging-conversations'] })
      queryClient.invalidateQueries({ queryKey: ['messaging-summary'] })
      queryClient.invalidateQueries({ queryKey: ['messaging-contacts'] })
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail || 'Unable to open this conversation.'
      toast.error(String(detail))
    },
  })

  const sendMessageMutation = useMutation({
    mutationFn: ({ conversationId, content }) => sendConversationMessage(conversationId, content),
    onSuccess: () => {
      setDraft('')
      queryClient.invalidateQueries({ queryKey: ['messaging-conversation-messages', activeConversationId] })
      queryClient.invalidateQueries({ queryKey: ['messaging-conversations'] })
      queryClient.invalidateQueries({ queryKey: ['messaging-summary'] })
      queryClient.invalidateQueries({ queryKey: ['messaging-contacts'] })
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail || 'Unable to send message.'
      toast.error(String(detail))
    },
  })

  const contacts = contactsQuery.data?.results || []
  const conversations = conversationsQuery.data?.results || []
  const summary = summaryQuery.data || {}

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId) || null,
    [conversations, activeConversationId],
  )

  const activeMessages = messagesQuery.data?.messages || []

  const activeContact = useMemo(() => {
    if (messagesQuery.data?.other_user) {
      return messagesQuery.data.other_user
    }

    if (activeConversation?.other_user) {
      return activeConversation.other_user
    }

    if (activeContactId) {
      return contacts.find((item) => item.id === activeContactId) || null
    }

    return null
  }, [messagesQuery.data, activeConversation, activeContactId, contacts])

  useEffect(() => {
    if (activeConversationId || conversations.length === 0) {
      return
    }

    setActiveConversationId(conversations[0].id)
    setActiveContactId(conversations[0].other_user?.id || null)
  }, [conversations, activeConversationId])

  useEffect(() => {
    if (!targetContactEmail || contacts.length === 0 || openConversationMutation.isPending) {
      return
    }

    const target = contacts.find((contact) => String(contact.email).toLowerCase() === targetContactEmail)
    if (!target) {
      return
    }

    if (activeContactId === target.id) {
      return
    }

    openConversationMutation.mutate(target.id)
    setSearchParams({})
  }, [
    targetContactEmail,
    contacts,
    openConversationMutation,
    activeContactId,
    setSearchParams,
  ])

  const handleSelectContact = (contact) => {
    setActiveContactId(contact.id)
    openConversationMutation.mutate(contact.id)
  }

  const handleSend = () => {
    const content = draft.trim()
    if (!content || !activeConversationId || sendMessageMutation.isPending) {
      return
    }

    sendMessageMutation.mutate({
      conversationId: activeConversationId,
      content,
    })
  }

  const handleInputKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  const isLoadingInitial = contactsQuery.isLoading || conversationsQuery.isLoading

  return (
    <div className="stacked-grid dashboard-surface dashboard-compact messaging-page">
      <section className="card page-hero messaging-hero">
        <p className="auth-eyebrow">Realtime Messaging</p>
        <h2>Secure communication between patient, doctor, and admin</h2>
        <p className="muted">
          Status is updated continuously, and authorized contacts are restricted by care workflow rules.
        </p>
        <div className="doctor-calendar-legend">
          <span className="chip">Logged role: {user?.role || 'unknown'}</span>
          <span className="chip">Unread: {summary.unread_messages || 0}</span>
          <span className="chip">Online contacts: {summary.online_contacts || 0}</span>
          <span className="chip">Conversations: {summary.active_conversations || 0}</span>
        </div>
      </section>

      {isLoadingInitial ? <p className="muted">Loading messaging center...</p> : null}

      <section className="card messaging-layout">
        <aside className="messaging-sidebar">
          <div className="inline-header">
            <h3>Contacts</h3>
            <span className="chip">{contacts.length}</span>
          </div>

          <div className="timeline compact-scroll messaging-contact-list">
            {contacts.length === 0 ? <p className="muted">No authorized contacts yet.</p> : null}

            {contacts.map((contact) => (
              <button
                key={contact.id}
                type="button"
                className={`messaging-contact-item ${activeContactId === contact.id ? 'active' : ''}`}
                onClick={() => handleSelectContact(contact)}
                disabled={openConversationMutation.isPending}
              >
                <div className="messaging-contact-header">
                  <strong>{contact.full_name || contact.email}</strong>
                  <span className={`status-tag ${contact.is_online ? 'completed' : 'pending'}`}>
                    <Circle size={10} />
                    {contact.is_online ? 'online' : 'offline'}
                  </span>
                </div>
                <p className="muted">{contact.email}</p>
                <p className="muted">Role: {contact.role}</p>
                {contact.unread_count > 0 ? <span className="chip">{contact.unread_count} unread</span> : null}
              </button>
            ))}
          </div>
        </aside>

        <div className="messaging-main">
          {!activeConversationId ? (
            <div className="messaging-empty-state">
              <MessageCircle size={26} />
              <p>Select a contact to start secure messaging.</p>
            </div>
          ) : (
            <>
              <div className="messaging-thread-head">
                <div>
                  <h3>{activeContact?.full_name || activeContact?.email || 'Conversation'}</h3>
                  <p className="muted">{activeContact?.email || ''}</p>
                </div>
                <span className={`status-tag ${activeContact?.is_online ? 'completed' : 'pending'}`}>
                  <Circle size={10} />
                  {activeContact?.is_online ? 'connected now' : 'not connected'}
                </span>
              </div>

              <div className="messaging-thread compact-scroll">
                {activeMessages.length === 0 ? <p className="muted">No message yet. Send the first message.</p> : null}

                {activeMessages.map((message) => {
                  const isMine = message.sender_id === user?.id
                  return (
                    <div key={message.id} className={`messaging-row ${isMine ? 'right' : 'left'}`}>
                      <article className={`messaging-bubble ${isMine ? 'mine' : 'theirs'}`}>
                        <p>{message.content}</p>
                        <span>{formatDateTime(message.created_at)}</span>
                      </article>
                    </div>
                  )
                })}
              </div>

              <div className="message-input-row messaging-input-row">
                <textarea
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={handleInputKeyDown}
                  placeholder="Write your message..."
                  disabled={sendMessageMutation.isPending}
                  rows={2}
                />
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={sendMessageMutation.isPending || !draft.trim()}
                  className="send-btn"
                  title="Send message"
                >
                  <Send size={18} />
                </button>
              </div>
            </>
          )}
        </div>

        <aside className="messaging-side-summary">
          <div className="inline-header">
            <h3>Recent conversations</h3>
            <UserRound size={16} />
          </div>

          <div className="timeline compact-scroll">
            {conversations.length === 0 ? <p className="muted">No active conversation.</p> : null}
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                className={`messaging-conversation-item ${activeConversationId === conversation.id ? 'active' : ''}`}
                onClick={() => {
                  setActiveConversationId(conversation.id)
                  setActiveContactId(conversation.other_user?.id || null)
                }}
              >
                <p>
                  <strong>{conversation.other_user?.full_name || conversation.other_user?.email}</strong>
                </p>
                <p className="muted">{safeText(conversation.last_message, 'No message yet')}</p>
                <p className="muted">{formatDateTime(conversation.last_message_at)}</p>
                {conversation.unread_count > 0 ? <span className="chip">{conversation.unread_count} unread</span> : null}
              </button>
            ))}
          </div>
        </aside>
      </section>
    </div>
  )
}

export default MessagingPage
