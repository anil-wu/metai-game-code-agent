import { useState } from 'react'

function Header({ auth, connected, connecting, config, updateConfig, onLogin, onLogout, onConnect, onDisconnect }) {
  const [loginLoading, setLoginLoading] = useState(false)
  const [loginMessage, setLoginMessage] = useState('')

  const handleLoginClick = async () => {
    setLoginLoading(true)
    setLoginMessage('')
    const result = await onLogin(config.email, config.password)
    setLoginLoading(false)
    setLoginMessage(result.message)
    if (!result.success) {
      setTimeout(() => setLoginMessage(''), 3000)
    }
  }

  const handleConnectClick = () => {
    const result = onConnect()
    if (result?.message) {
      console.log(result.message)
    }
  }

  const getStatusClass = (status) => {
    return `status status--${status}`
  }

  const getAuthStatusClass = () => {
    if (auth.token) return 'status status--connected'
    return 'status status--disconnected'
  }

  return (
    <header className="header">
      <div className="header-row">
        <span className={getAuthStatusClass()}>
          {auth.token ? `Logged In …${auth.token.slice(-6)}` : 'Not Logged In'}
        </span>
        <div className="header-actions">
          <input
            className="input input--url"
            type="text"
            spellCheck="false"
            placeholder="API Base URL"
            value={config.apiBaseUrl}
            onChange={(e) => updateConfig('apiBaseUrl', e.target.value)}
          />
          <input
            className="input input--id"
            type="text"
            spellCheck="false"
            placeholder="Email"
            value={config.email}
            onChange={(e) => updateConfig('email', e.target.value)}
          />
          <input
            className="input input--id"
            type="password"
            spellCheck="false"
            placeholder="Password"
            value={config.password}
            onChange={(e) => updateConfig('password', e.target.value)}
          />
          <button
            className="btn btn--small"
            onClick={handleLoginClick}
            disabled={loginLoading || !!auth.token}
          >
            {loginLoading ? 'Logging In...' : 'Login'}
          </button>
          <button
            className="btn btn--small btn--secondary"
            onClick={onLogout}
            disabled={!auth.token}
          >
            Logout
          </button>
        </div>
      </div>

      <div className="header-row header-row--border">
        <span className={getStatusClass(connected ? 'connected' : connecting ? 'connecting' : 'disconnected')}>
          {connected ? 'Connected' : connecting ? 'Connecting...' : 'Disconnected'}
        </span>
        <div className="header-actions">
          <input
            className="input input--url"
            type="text"
            spellCheck="false"
            placeholder="WebSocket URL"
            value={config.wsUrl}
            onChange={(e) => updateConfig('wsUrl', e.target.value)}
          />
          <input
            className="input input--id"
            type="text"
            spellCheck="false"
            placeholder="User ID"
            value={config.userId}
            onChange={(e) => updateConfig('userId', e.target.value)}
          />
          <input
            className="input input--id"
            type="text"
            spellCheck="false"
            placeholder="Session ID"
            value={config.sessionId}
            onChange={(e) => updateConfig('sessionId', e.target.value)}
          />
          <input
            className="input input--id"
            type="text"
            spellCheck="false"
            placeholder="项目 ID"
            value={config.projectId}
            onChange={(e) => updateConfig('projectId', e.target.value)}
          />
          <button
            className="btn btn--small"
            onClick={handleConnectClick}
            disabled={connected || connecting}
          >
            Connect
          </button>
          <button
            className="btn btn--small btn--secondary"
            onClick={onDisconnect}
            disabled={!connected && !connecting}
          >
            Disconnect
          </button>
        </div>
      </div>
    </header>
  )
}

export default Header
