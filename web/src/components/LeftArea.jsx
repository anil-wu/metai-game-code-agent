import { useState, useEffect } from 'react'

function LeftArea({ auth, config, updateConfig }) {
  const [buildVersions, setBuildVersions] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchBuildVersions = async () => {
    if (!auth.token || !config.projectId) {
      setBuildVersions([])
      return
    }

    setLoading(true)
    try {
      const baseUrl = config.apiBaseUrl.replace(/\/+$/, '')
      const res = await fetch(`${baseUrl}/api/v1/projects/${config.projectId}/build-versions?page=1&pageSize=50`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${auth.token}`,
        },
      })

      const text = await res.text()
      let data
      try {
        data = text ? JSON.parse(text) : null
      } catch {
        data = null
      }

      if (!res.ok) {
        console.error('获取构建版本失败:', data?.message || text || `HTTP ${res.status}`)
        setBuildVersions([])
        return
      }

      const list = Array.isArray(data?.list) ? data.list : []
      setBuildVersions(list)
    } catch (e) {
      console.error('获取构建版本请求失败:', e)
      setBuildVersions([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBuildVersions()
  }, [auth.token, config.projectId])

  const handleBuildVersionClick = (version) => {
    console.log('Selected build version:', version)
  }

  return (
    <section className="left-area">
      <div className="version-selector">
        <div className="panel-header">
          <div className="panel-title">
            <span className="title-zh">游戏版本选择</span>
            <span className="title-en">Game version selection</span>
          </div>
          <button
            className="btn btn--small btn--with-icon"
            onClick={fetchBuildVersions}
            disabled={loading || !auth.token}
          >
            <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
              <path d="M3 3v5h5"/>
              <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>
              <path d="M16 21h5v-5"/>
            </svg>
            刷新 Refresh
          </button>
        </div>
        <div className="build-versions-list">
          {buildVersions.length === 0 ? (
            <div className="build-version-empty">暂无构建版本 There is no build version yet</div>
          ) : (
            buildVersions.map((item) => (
              <div
                key={item.buildVersionId}
                className="build-version-item"
                data-id={item.buildVersionId}
                onClick={() => handleBuildVersionClick(item)}
              >
                <div className="build-version-name">
                  {item.description ? item.description.substring(0, 50) : `构建版本 #${item.buildVersionId}`}
                </div>
                <div className="build-version-desc" title={item.description || '无描述'}>
                  {item.description || '无描述'}
                </div>
                <div className="build-version-meta">
                  <span>ID: {item.buildVersionId}</span>
                  <span>Manifest: {item.softwareManifestId}</span>
                  <span>{item.createdAt || ''}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="game-preview">
        <div className="panel-header">
          <div className="panel-title">
            <span className="title-zh">游戏预览</span>
            <span className="title-en">Game preview</span>
          </div>
        </div>
        <div className="game-preview-content">
          <div className="preview-bg-decoration">
            <div className="bg-blob bg-blob--1"></div>
            <div className="bg-blob bg-blob--2"></div>
          </div>
          <div className="preview-content">
            <div className="game-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <line x1="6" y1="12" x2="10" y2="12"/>
                <line x1="8" y1="10" x2="8" y2="14"/>
                <line x1="15" y1="13" x2="15.01" y2="13"/>
                <line x1="18" y1="11" x2="18.01" y2="11"/>
                <rect x="2" y="6" width="20" height="12" rx="2"/>
              </svg>
            </div>
            <h3 className="preview-title">游戏预览</h3>
            <p className="preview-subtitle">请选择一个版本</p>
          </div>
        </div>
      </div>
    </section>
  )
}

export default LeftArea
