import { useState, useEffect } from 'react'
import { checkHealth, checkDbHealth } from './api/client'
import './App.css'

function App() {
  const [health, setHealth] = useState<{ status: string; app: string; environment: string } | null>(null)
  const [dbHealth, setDbHealth] = useState<{ status: string; database: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadHealth() {
      try {
        setLoading(true)
        const [h, db] = await Promise.all([checkHealth(), checkDbHealth()])
        setHealth(h)
        setDbHealth(db)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load health')
      } finally {
        setLoading(false)
      }
    }
    loadHealth()
  }, [])

  if (loading) {
    return <div className="loading">Loading...</div>
  }

  return (
    <div className="container">
      <header style={{ marginBottom: '2rem' }}>
        <h1>vector-studio</h1>
        <p style={{ color: '#6b7280' }}>Self-hosted gym & body-weight tracker</p>
      </header>

      {error && <div className="error-message">{error}</div>}

      <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
        <div className="card">
          <h2>API Health</h2>
          {health ? (
            <dl style={{ margin: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <dt>Status</dt>
                <dd style={{ margin: 0, fontWeight: 600, color: health.status === 'ok' ? '#166534' : '#991b1b' }}>
                  {health.status}
                </dd>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <dt>App</dt>
                <dd style={{ margin: 0 }}>{health.app}</dd>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <dt>Environment</dt>
                <dd style={{ margin: 0 }}>{health.environment}</dd>
              </div>
            </dl>
          ) : (
            <p className="error-message">Failed to load</p>
          )}
        </div>

        <div className="card">
          <h2>Database Health</h2>
          {dbHealth ? (
            <dl style={{ margin: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <dt>Status</dt>
                <dd style={{ margin: 0, fontWeight: 600, color: dbHealth.status === 'ok' ? '#166534' : '#991b1b' }}>
                  {dbHealth.status}
                </dd>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <dt>Database</dt>
                <dd style={{ margin: 0 }}>{dbHealth.database}</dd>
              </div>
            </dl>
          ) : (
            <p className="error-message">Failed to load</p>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h2>Quick Links</h2>
        <ul style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', listStyle: 'none', padding: 0 }}>
          <li><a href="/api/docs" target="_blank" rel="noopener">API Docs (Swagger)</a></li>
          <li><a href="/api/redoc" target="_blank" rel="noopener">API Docs (ReDoc)</a></li>
        </ul>
      </div>

      <footer style={{ marginTop: '3rem', paddingTop: '1.5rem', borderTop: '1px solid #e5e7eb', color: '#6b7280', fontSize: '0.875rem' }}>
        <p>vector-studio \u2014 Ryan Vo (ryandtvo@gmail.com) | AI & Machine Learning</p>
      </footer>
    </div>
  )
}

export default App