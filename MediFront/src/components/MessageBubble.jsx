import StructuredChatText from './StructuredChatText'

function MessageBubble({ message }) {
  const isPatient = message.sender === 'patient'

  return (
    <div className={isPatient ? 'message-row right' : 'message-row left'}>
      <div className={isPatient ? 'message-bubble patient' : 'message-bubble bot'}>
        <StructuredChatText text={message.content} />
      </div>
    </div>
  )
}

export default MessageBubble
