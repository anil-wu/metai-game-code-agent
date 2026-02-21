import { useState, useEffect, useCallback } from 'react'
import './index.css'
import Header from './components/Header'
import LeftArea from './components/LeftArea'
import ChatArea from './components/ChatArea'

function App() {
  const [auth, setAuth] = useState({
    token: null,
    userId: null,
    email: null,
  })
  const [ws, setWs] = useState(null)
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [currentMode, setCurrentMode] = useState('agent')
  const [runMode, setRunMode] = useState('stream')
  const [config, setConfig] = useState({
    apiBaseUrl: 'https://localhost:8890',
    wsUrl: 'ws://127.0.0.1:8001/ws',
    email: 'Test@sparkx.com',
    password: '111',
    userId: '',
    sessionId: '',
    projectId: '',
  })

  useEffect(() => {
    const apiToken = localStorage.getItem('apiToken')
    const apiUserId = localStorage.getItem('apiUserId')
    const apiEmail = localStorage.getItem('apiEmail')
    if (apiToken) {
      setAuth({
        token: apiToken,
        userId: apiUserId,
        email: apiEmail,
      })
    }

    const savedApiBaseUrl = localStorage.getItem('apiBaseUrl')
    const savedWsUrl = localStorage.getItem('wsUrl')
    const savedUserId = localStorage.getItem('userId')
    const savedSessionId = localStorage.getItem('sessionId')
    const savedProjectId = localStorage.getItem('projectId')
    const savedEmail = localStorage.getItem('email')
    const savedPassword = localStorage.getItem('password')
    const savedMode = localStorage.getItem('agentMode')
    const savedRunMode = localStorage.getItem('runMode')

    setConfig({
      apiBaseUrl: savedApiBaseUrl || 'https://localhost:8890',
      wsUrl: savedWsUrl || 'ws://127.0.0.1:8001/ws',
      email: savedEmail || 'Test@sparkx.com',
      password: savedPassword || '111',
      userId: savedUserId || '',
      sessionId: savedSessionId || '',
      projectId: savedProjectId || '',
    })

    if (savedMode && (savedMode === 'agent' || savedMode === 'skill')) {
      setCurrentMode(savedMode)
    }

    if (savedRunMode && (savedRunMode === 'stream' || savedRunMode === 'async')) {
      setRunMode(savedRunMode)
    }
  }, [])

  const updateConfig = useCallback((key, value) => {
    setConfig(prev => {
      const newConfig = { ...prev, [key]: value }
      localStorage.setItem(key, value)
      return newConfig
    })
  }, [])

  const handleLogin = async (email, password) => {
    const baseUrl = config.apiBaseUrl.replace(/\/+$/, '')
    if (!baseUrl || !email || !password) {
      return { success: false, message: '登录信息不完整' }
    }

    try {
      const res = await fetch(`${baseUrl}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          loginType: 'email',
          email,
          password,
        }),
      })

      const text = await res.text()
      let data
      try {
        data = text ? JSON.parse(text) : null
      } catch {
        data = null
      }

      if (!res.ok) {
        const detail = data?.message || data?.msg || text || `HTTP ${res.status}`
        return { success: false, message: `登录失败：${detail}` }
      }

      const token = data?.token
      if (!token) {
        return { success: false, message: '登录失败：未返回 token' }
      }

      const newAuth = {
        token,
        userId: data?.userId ?? null,
        email,
      }
      setAuth(newAuth)
      localStorage.setItem('apiToken', token)
      if (data?.userId != null) {
        localStorage.setItem('apiUserId', String(data.userId))
        setConfig(prev => {
          const newConfig = { ...prev, userId: String(data.userId) }
          localStorage.setItem('userId', String(data.userId))
          return newConfig
        })
      }
      localStorage.setItem('apiEmail', email)

      return { success: true, message: '登录成功' }
    } catch (e) {
      return { success: false, message: `登录请求失败：${e?.message || String(e)}` }
    }
  }

  const handleLogout = () => {
    setAuth({ token: null, userId: null, email: config.email })
    localStorage.removeItem('apiToken')
    localStorage.removeItem('apiUserId')
    localStorage.removeItem('apiEmail')
  }

  const handleConnect = () => {
    if (!auth.token) {
      return { success: false, message: '请先登录获取 token，再连接 WebSocket' }
    }

    if (!auth.userId) {
      return { success: false, message: '登录未返回 userId，无法连接 WebSocket' }
    }

    if (ws) {
      try {
        ws.close()
      } catch {}
    }

    setConnecting(true)

    let url = config.wsUrl
    try {
      const u = new URL(config.wsUrl)
      u.searchParams.set('token', auth.token)
      url = u.toString()
    } catch {}

    const newWs = new WebSocket(url)
    setWs(newWs)

    newWs.onopen = () => {
      setConnected(true)
      setConnecting(false)
      try {
        const authMsg = {
          type: 'auth',
          token: auth.token,
          project_id: config.projectId,
          user_id: String(auth.userId),
        }
        newWs.send(JSON.stringify(authMsg))
        if (currentMode !== 'agent') {
          const modeMsg = {
            type: 'mode',
            mode: currentMode,
          }
          newWs.send(JSON.stringify(modeMsg))
        }
      } catch {}
    }

    newWs.onclose = () => {
      setConnected(false)
      setConnecting(false)
      setWs(null)
    }

    newWs.onerror = () => {
      setConnected(false)
      setConnecting(false)
    }

    return { success: true, message: '连接中...' }
  }

  const handleDisconnect = () => {
    if (ws) {
      try {
        ws.close()
      } catch {}
    }
    setConnected(false)
    setConnecting(false)
    setWs(null)
  }

  const handleSend = (text) => {
    if (!connected || !ws || ws.readyState !== WebSocket.OPEN) {
      return false
    }

    const requestId = crypto.randomUUID ? crypto.randomUUID() : `r_${Date.now()}_${Math.random().toString(16).slice(2)}`
    const payload = {
      type: 'message',
      request_id: requestId,
      text,
      mode: currentMode,
      message_mode: runMode,
      user_id: config.userId || undefined,
      session_id: config.sessionId || undefined,
    }
    ws.send(JSON.stringify(payload))
    return requestId
  }

  const handleModeChange = (mode) => {
    setCurrentMode(mode)
    localStorage.setItem('agentMode', mode)
    if (connected && ws && ws.readyState === WebSocket.OPEN) {
      const payload = {
        type: 'mode',
        mode,
      }
      ws.send(JSON.stringify(payload))
    }
  }

  const handleRunModeChange = (mode) => {
    setRunMode(mode)
    localStorage.setItem('runMode', mode)
  }

  return (
    <div className="app">
      <Header
        auth={auth}
        connected={connected}
        connecting={connecting}
        config={config}
        updateConfig={updateConfig}
        onLogin={handleLogin}
        onLogout={handleLogout}
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
      />
      <main className="main">
        <LeftArea
          auth={auth}
          config={config}
          updateConfig={updateConfig}
        />
        <ChatArea
          connected={connected}
          ws={ws}
          currentMode={currentMode}
          runMode={runMode}
          onSend={handleSend}
          onModeChange={handleModeChange}
          onRunModeChange={handleRunModeChange}
        />
      </main>
    </div>
  )
}

export default App
