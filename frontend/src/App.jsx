import { useState, useEffect, useRef } from 'react'

function App() {
  const [goal, setGoal] = useState('')
  const [logs, setLogs] = useState([])
  const [screenshot, setScreenshot] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [reportLink, setReportLink] = useState(null) // New State
  const [isPaused, setIsPaused] = useState(false)

  const wsRef = useRef(null)
  const logsEndRef = useRef(null)

  useEffect(() => {
    // Connect to WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws')

    ws.onopen = () => {
      setIsConnected(true)
      addLog({ type: 'log', message: 'Connected to AI Brain' })
    }

    ws.onclose = () => {
      setIsConnected(false)
      addLog({ type: 'error', message: 'Disconnected from server' })
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'state') {
        setScreenshot(`data:image/jpeg;base64,${data.screenshot}`)
        if (data.events && (data.events.console.length > 0 || data.events.errors.length > 0)) {
          data.events.console.forEach(msg => addLog({ type: 'protocol', message: msg }))
          data.events.errors.forEach(err => addLog({ type: 'error', message: err }))
        }
      } else if (data.type === 'report') {
        console.log("RX REPORT:", data.url)
        setReportLink(data.url)
        addLog({ type: 'success', message: 'Report generated: ' + data.url })
      } else if (data.type === 'pause') {
        setIsPaused(true)
        addLog(data)
      } else {
        addLog(data)
        if (data.message === 'Goal Achieved!' || data.type === 'error' || data.message === 'Execution Interrupted.') {
          setIsRunning(false)
          setIsPaused(false)
          // Do NOT reset reportLink here
        }
      }
    }

    wsRef.current = ws

    return () => {
      ws.close()
    }
  }, [])

  const addLog = (log) => {
    setLogs(prev => [...prev, { ...log, timestamp: new Date().toLocaleTimeString() }])
  }

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const handleStart = () => {
    if (!goal.trim()) return

    setIsRunning(true)
    setLogs([]) // Clear previous runs
    setReportLink(null) // Reset report link
    addLog({ type: 'log', message: 'Starting new test session...' })

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ goal, step_by_step: false })) // Disabled step_by_step
    } else {
      addLog({ type: 'error', message: 'WebSocket is not connected.' })
    }
  }

  const handleStop = () => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: 'stop' }))
    }
    // Don't set isRunning(false) immediately, let backend confirm interrupt
  }

  const handleReset = () => {
    setIsRunning(false)
    setGoal('')
    setLogs([])
    setScreenshot(null)
    setReportLink(null)
  }

  const handleOpenReport = () => {
    if (reportLink) {
      window.open(reportLink, '_blank')
    }
  }

  return (
    <div className="app-container">
      {/* Top Bar */}
      <div className="top-bar glass panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1>Antigravity Automation</h1>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <span style={{ color: isConnected ? '#22c55e' : '#ef4444', fontSize: '0.8rem' }}>
              ● {isConnected ? 'System Online' : 'Offline'}
            </span>
            {!isRunning && (
              <button className="btn-primary" onClick={handleReset} style={{ background: '#334155' }}>
                New Test
              </button>
            )}
          </div>
        </div>

        <div className="input-area">
          <input
            type="text"
            className="input-box"
            placeholder="Describe your test scenario... (e.g., 'Go to google.com and search for AI')"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            disabled={isRunning}
            onKeyDown={(e) => e.key === 'Enter' && handleStart()}
          />
          <button
            className="btn-primary"
            onClick={handleStart}
            disabled={isRunning || !isConnected}
          >
            {isRunning ? (isPaused ? 'Paused' : 'Running...') : 'Run Test'}
          </button>

          {isRunning && (
            <button className="btn-primary" onClick={handleStop} style={{ background: '#ef4444', minWidth: '80px', flexShrink: 0 }}>
              Stop
            </button>
          )}

          <button
            className="btn-primary"
            onClick={handleOpenReport}
            disabled={!reportLink}
            style={{ background: reportLink ? '#8b5cf6' : '#475569', opacity: reportLink ? 1 : 0.5, marginLeft: '10px' }}
          >
            Open Report
          </button>

        </div>
      </div>

      <div className="main-content">
        {/* Left Panel: Intelligence Log */}
        <div className="left-panel panel glass">
          <div style={{ padding: '15px', borderBottom: '1px solid var(--border)' }}>
            <h3>Intelligence Log</h3>
          </div>
          <div className="log-stream" style={{ padding: '15px' }}>
            {logs.length === 0 && <span style={{ color: 'var(--text-dim)', textAlign: 'center', marginTop: '20px' }}>Ready for instructions.</span>}
            {logs.map((log, idx) => (
              <div className={`log-item ${log.type}`} key={idx}>
                <div className="log-meta">
                  {log.timestamp} • {log.type.toUpperCase()}
                </div>
                <div className="log-content">
                  {log.message || log.thought}
                </div>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>

        {/* Right Panel: Browser View */}
        <div className="right-panel panel glass">
          <div style={{ padding: '10px 15px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(0,0,0,0.2)' }}>
            <div style={{ display: 'flex', gap: '5px' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ff5f56' }}></div>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ffbd2e' }}></div>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#27c93f' }}></div>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.1)', flex: 1, padding: '4px 12px', borderRadius: '15px', fontSize: '0.75rem', color: 'var(--text-dim)', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
              {logs.findLast(l => l.url)?.url || 'Waiting for browser...'}
            </div>
          </div>
          <div style={{ padding: '10px 15px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3>Live Stream</h3>
            <span className="badge" style={{ fontSize: '0.7rem', color: '#22d3ee' }}>CDP Active</span>
          </div>
          <div className="browser-view">
            {screenshot ? (
              <img src={screenshot} alt="Live Browser Stream" />
            ) : (
              <div className="browser-placeholder">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                  <line x1="8" y1="21" x2="16" y2="21"></line>
                  <line x1="12" y1="17" x2="12" y2="21"></line>
                </svg>
                <span>Browser Inactive</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
