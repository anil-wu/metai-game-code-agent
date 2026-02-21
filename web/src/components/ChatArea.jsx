import { useState, useRef, useEffect } from 'react'

function ChatArea({ connected, ws, currentMode, runMode, onSend, onModeChange, onRunModeChange }) {
  const [messages, setMessages] = useState([])
  const [expandedThinkingIds, setExpandedThinkingIds] = useState(new Set())
  const [expandedFunctionIds, setExpandedFunctionIds] = useState(new Set())
  const [inputText, setInputText] = useState('')
  const [messageOrder, setMessageOrder] = useState(0)
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
      handleTextMessage(message_id, content, author, timeInfo, message_type, event)
    } else {
      handleNonTextMessage(message_id, message_type, content, author, timeInfo, event)
    }
  }

  const handleTextMessage = (messageId, content, author, timeInfo, messageType, rawData) => {
    console.log('Received text message:', messageId, content, author, timeInfo, rawData)
    setMessages(prev => {
      const existingIndex = prev.findIndex(msg => msg.id === messageId)
      if (existingIndex !== -1) {
        const existingMsg = prev[existingIndex]
        const newMessages = [...prev]
        const updatedContent = existingMsg.content + (content || '')
        newMessages[existingIndex] = {
          ...existingMsg,
          content: updatedContent,
          rawData,
        }
        
        if (messageType === 'thinking' && !expandedThinkingIds.has(messageId)) {
          setExpandedThinkingIds(prev => new Set(prev).add(messageId))
        }
        
        return newMessages
      } else {
        const currentOrder = messageOrder
        setMessageOrder(prev => prev + 1)
        return [...prev, {
          id: messageId,
          type: messageType,
          content,
          author,
          timeInfo,
          rawData,
          order: currentOrder,
        }]
      }
    })
  }

  const handleNonTextMessage = (messageId, messageType, content, author, timeInfo, rawData) => {
    console.log('Received non-text message:', messageId, messageType, content, author, timeInfo, rawData)
    setMessages(prev => {
      const existingIndex = prev.findIndex(msg => msg.id === messageId)
      if (existingIndex !== -1) {
        const existingMsg = prev[existingIndex]
        const newMessages = [...prev]
        newMessages[existingIndex] = {
          ...existingMsg,
          content: existingMsg.content + (content || ''),
          rawData,
        }
        return newMessages
      } else {
        const currentOrder = messageOrder
        setMessageOrder(prev => prev + 1)
        return [...prev, {
          id: messageId,
          type: messageType,
          content,
          author,
          timeInfo,
          rawData,
          order: currentOrder,
        }]
      }
    })
  }

  const formatTimeInfo = (serverTime, elapsedMs) => {
    if (!serverTime) {
      return elapsedMs !== undefined ? `[${elapsedMs}ms]` : ''
    }
    const date = new Date(serverTime)
    const timeStr = date.toLocaleTimeString()
    return elapsedMs !== undefined ? `${timeStr} [${elapsedMs}ms]` : timeStr
  }

  const toggleThinkingExpand = (messageId) => {
    setExpandedThinkingIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(messageId)) {
        newSet.delete(messageId)
      } else {
        newSet.add(messageId)
      }
      return newSet
    })
  }

  const toggleFunctionExpand = (messageId) => {
    setExpandedFunctionIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(messageId)) {
        newSet.delete(messageId)
      } else {
        newSet.add(messageId)
      }
      return newSet
    })
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

  const getMessageTypeIcon = (type) => {
    const icons = {
      'message': '💬',
      'thinking': '🤔',
      'function_call': '⚙️',
      'function_response': '📤',
      'error': '❌',
    }
    return icons[type] || 'ℹ️'
  }

  const getMessageTypeLabel = (type) => {
    const labels = {
      'message': '消息',
      'thinking': '思考',
      'function_call': '函数调用',
      'function_response': '函数返回',
      'error': '错误',
    }
    return labels[type] || '未知'
  }

  const renderMessageContent = (msg) => {
    if (msg.type === 'thinking') {
      const isExpanded = expandedThinkingIds.has(msg.id)
      const hasContent = msg.content && msg.content.trim()
      
      return (
        <div className="thinking-message">
          <div 
            className="thinking-header"
            onClick={() => toggleThinkingExpand(msg.id)}
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <span>{isExpanded ? '▼' : '▶'}</span>
            <span style={{ fontWeight: 'bold' }}>思考过程</span>
            {!isExpanded && hasContent && (
              <span style={{ color: '#888', fontSize: '0.9em' }}>
                {msg.content.slice(0, 50)}{msg.content.length > 50 ? '...' : ''}
              </span>
            )}
          </div>
          {isExpanded && (
            <div className="thinking-content" style={{ marginTop: '8px', paddingLeft: '16px' }}>
              {msg.content}
            </div>
          )}
        </div>
      )
    }
    
    if (msg.type === 'function_call') {
      try {
        const data = JSON.parse(msg.content)
        const isExpanded = expandedFunctionIds.has(msg.id)
        const functionName = data.name || 'Unknown'
        const argsPreview = data.args 
          ? JSON.stringify(data.args).slice(0, 60) + (JSON.stringify(data.args).length > 60 ? '...' : '')
          : ''
        
        return (
          <div className="function-call">
            <div 
              className="function-header"
              onClick={() => toggleFunctionExpand(msg.id)}
              style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <span>{isExpanded ? '▼' : '▶'}</span>
              <span style={{ fontWeight: 'bold' }}>调用：{functionName}</span>
              {!isExpanded && argsPreview && (
                <span style={{ color: '#888', fontSize: '0.85em' }}>
                  {argsPreview}
                </span>
              )}
            </div>
            {isExpanded && data.args && (
              <pre style={{ 
                background: '#f5f5f5', 
                padding: '8px', 
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '0.85em',
                marginTop: '8px',
                marginLeft: '16px'
              }}>
                {JSON.stringify(data.args, null, 2)}
              </pre>
            )}
          </div>
        )
      } catch {
        return <div>{msg.content}</div>
      }
    }
    
    if (msg.type === 'function_response') {
      try {
        const data = JSON.parse(msg.content)
        const isExpanded = expandedFunctionIds.has(msg.id)
        const status = data.status || 'Unknown'
        const responsePreview = JSON.stringify(data).slice(0, 60) + (JSON.stringify(data).length > 60 ? '...' : '')
        
        return (
          <div className="function-response">
            <div 
              className="function-header"
              onClick={() => toggleFunctionExpand(msg.id)}
              style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <span>{isExpanded ? '▼' : '▶'}</span>
              <span style={{ fontWeight: 'bold' }}>返回：{status}</span>
              {!isExpanded && (
                <span style={{ color: '#888', fontSize: '0.85em' }}>
                  {responsePreview}
                </span>
              )}
            </div>
            {isExpanded && (
              <pre style={{ 
                background: '#f5f5f5', 
                padding: '8px', 
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '0.85em',
                marginTop: '8px',
                marginLeft: '16px'
              }}>
                {JSON.stringify(data, null, 2)}
              </pre>
            )}
          </div>
        )
      } catch {
        return <div>{msg.content}</div>
      }
    }
    
    if (msg.type === 'error') {
      return (
        <div className="error-message" style={{ color: '#d32f2f' }}>
          {msg.content}
        </div>
      )
    }
    
    return <div>{msg.content}</div>
  }

  return (
    <aside className="chat-area">
      <div className="panel-header">
        <span className="panel-title-chat">聊天 Chat</span>
      </div>
      <div className="messages">
        {[...messages].sort((a, b) => (a.order || 0) - (b.order || 0)).map((msg, index) => (
          <div key={msg.id || index} className={`msg msg--${msg.role || 'assistant'}`}>
            <div className="meta">
              <span className="pill" title={getMessageTypeLabel(msg.type)}>
                {getMessageTypeIcon(msg.type)} {getMessageTypeLabel(msg.type)}
              </span>
              <span className="pill">{msg.time || msg.timeInfo}</span>
              {msg.id && <span className="pill">{String(msg.id).slice(0, 8)}</span>}
              {msg.author && <span className="pill">{msg.author}</span>}
            </div>
            <div className="body">
              {renderMessageContent(msg)}
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
