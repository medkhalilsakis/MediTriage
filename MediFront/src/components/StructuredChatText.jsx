function classifyLine(line) {
  const trimmed = (line || '').trim()
  if (!trimmed) return 'empty'

  if (trimmed === 'Triage summary') return 'title'
  if (/^\d+\.\s/.test(trimmed)) return 'numbered'
  if (trimmed.startsWith('- ')) return 'bullet'
  if (trimmed.endsWith(':')) return 'section'
  if (/^[A-Za-z][A-Za-z\s]{2,40}:\s+/.test(trimmed)) return 'keyvalue'

  return 'text'
}

function renderKeyValue(line) {
  const separatorIndex = line.indexOf(':')
  if (separatorIndex === -1) {
    return line
  }

  const label = line.slice(0, separatorIndex + 1)
  const value = line.slice(separatorIndex + 1).trim()

  return (
    <>
      <strong>{label}</strong>
      {value ? ` ${value}` : ''}
    </>
  )
}

function StructuredChatText({ text }) {
  const lines = String(text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  if (lines.length === 0) {
    return <p className="structured-chat-line text" />
  }

  return (
    <div className="structured-chat-text">
      {lines.map((line, index) => {
        const lineType = classifyLine(line)
        return (
          <p key={`${line}-${index}`} className={`structured-chat-line ${lineType}`}>
            {lineType === 'keyvalue' ? renderKeyValue(line) : line}
          </p>
        )
      })}
    </div>
  )
}

export default StructuredChatText
