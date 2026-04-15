import MessageBubble from './MessageBubble'

function ChatWindow({ messages }) {
  return (
    <section className="card chat-window">
      <h3>Conversation</h3>
      <p className="muted">Your private triage assistant conversation history.</p>
      <div className="message-list">
        {messages.length === 0 ? <p className="muted">Start describing your symptoms.</p> : null}
        {messages.map((message) => (
          <MessageBubble key={message.id || `${message.sender}-${message.content}`} message={message} />
        ))}
      </div>
    </section>
  )
}

export default ChatWindow
