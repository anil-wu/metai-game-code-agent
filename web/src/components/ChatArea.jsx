import { useState, useRef, useEffect } from 'react'

function ChatArea({ connected, ws, currentMode, runMode, onSend, onModeChange, onRunModeChange }) {
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (!ws) return

    ws.onmessage = async (ev) => {
      let msg
      try {
        msg = JSON.parse(ev.data)
      } catch {
        console.log('收到非 JSON:', String(ev.data).slice(0, 200))
        return
      }

      const type = msg.type
      if (type === 'pong') return
      
      if (type === 'auth_ok') {
        const pid = typeof msg.project_id === 'string' ? msg.project_id : ''
        if (pid) {
          console.log('Project ID:', pid)
        }
        console.log('Token 已发送到服务器')
        return
      }

      if (type === 'mode_ok') {
        const mode = msg.mode || 'agent'
        console.log(`模式已切换为：${mode === 'skill' ? 'Skill' : 'Agent'}`)
        return
      }

      if (type === 'event') {
        if (msg.message_type !== undefined) {
          handleEventMessage(msg)
          return
        }
      }

      console.log('收到消息:', JSON.stringify(msg).slice(0, 200))
    }

    ws.onerror = () => {
      console.log('连接发生错误')
    }
  }, [ws])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleEventMessage = (event) => {
    const { message_type, content, message_id, author, server_time, elapsed_ms } = event
    
    if (message_type === 'completed') {
      console.log('Streaming completed')
      return
    }

    const timeInfo = formatTimeInfo(server_time, elapsed_ms)
    
    if (message_type === 'message' || message_type === 'thinking') {
      handleTextMessage(message_id, content, author, timeInfo, event)
    } else {
      handleNonTextMessage(message_id, message_type, content, author, timeInfo, event)
    }
  }

  const handleTextMessage = (messageId, content, author, timeInfo, rawData) => {
    console.log('Received text message:', messageId, content, author, timeInfo, rawData)
    setMessages(prev => [...prev, {
      id: messageId,
      type: 'text',
      content,
      author,
      timeInfo,
      rawData,
    }])
  }

  const handleNonTextMessage = (messageId, messageType, content, author, timeInfo, rawData) => {
    console.log('Received non-text message:', messageId, messageType, content, author, timeInfo, rawData)
    setMessages(prev => [...prev, {
      id: messageId,
      type: messageType,
      content,
      author,
      timeInfo,
      rawData,
    }])
  }

  const formatTimeInfo = (serverTime, elapsedMs) => {
    if (!serverTime) {
      return elapsedMs !== undefined ? `[${elapsedMs}ms]` : ''
    }
    const date = new Date(serverTime)
    const timeStr = date.toLocaleTimeString()
    return elapsedMs !== undefined ? `${timeStr} [${elapsedMs}ms]` : timeStr
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!inputText.trim()) return

    const requestId = onSend(inputText.trim())
    if (requestId) {
      setMessages(prev => [...prev, {
        id: requestId,
        role: 'user',
        text: inputText.trim(),
        time: new Date().toLocaleTimeString(),
      }])
      setInputText('')
    }
  }

  const getMessageTypeLabel = (type) => {
    const labels = {
      'text': '文本',
      'thinking': '思考',
      'function_call': '函数调用',
      'function_response': '函数返回',
      'error': '错误',
    }
    return labels[type] || '未知'
  }

  return (
    <aside className="chat-area">
      <div className="panel-header">
        <span className="panel-title-chat">聊天 Chat</span>
      </div>
      <div className="messages">
        {messages.map((msg, index) => (
          <div key={msg.id || index} className={`msg msg--${msg.role || 'assistant'}`}>
            <div className="meta">
              <span className="pill">{msg.role || 'assistant'}</span>
              <span className="pill">{msg.time || msg.timeInfo}</span>
              {msg.id && <span className="pill">{String(msg.id).slice(0, 8)}</span>}
            </div>
            <div className="body">
              {msg.text || msg.content || JSON.stringify(msg.rawData, null, 2)}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <footer className="footer">
        <form className="composer" onSubmit={handleSubmit}>
          <input
            className="input input--text"
            type="text"
            placeholder="输入消息，回车发送"
            autoComplete="off"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={!connected}
          />
          <select
            className="select select--mode"
            value={currentMode}
            onChange={(e) => onModeChange(e.target.value)}
            disabled={!connected}
          >
            <option value="agent">Agent</option>
            <option value="skill">Skill</option>
          </select>
          <select
            className="select select--mode"
            value={runMode}
            onChange={(e) => onRunModeChange(e.target.value)}
            disabled={!connected}
          >
            <option value="stream">stream</option>
            <option value="async">Async</option>
          </select>
          <button
            className="btn"
            type="submit"
            disabled={!connected}
          >
            Send
          </button>
        </form>
      </footer>
    </aside>
  )
}

export default ChatArea
