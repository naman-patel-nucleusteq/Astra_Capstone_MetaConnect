import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PagePlaceholder from '../components/PagePlaceholder.jsx'
import { useAuth } from '../services/auth.js'
import StatePanel from '../components/StatePanel.jsx'
import api from '../services/api.js'

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : '--'
}

function Dashboard() {
  const { user } = useAuth()
  const [metrics, setMetrics] = useState({ services: 0, databases: 0, schemas: 0, tables: 0 })
  const [recentRuns, setRecentRuns] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const greetingText = user ? `Welcome Back, ${user.username}` : 'Welcome Back'

  // Load the catalog summary and recent ingestion activity for the overview.
  async function loadDashboard() {
    setIsLoading(true)
    try {
      const response = await api.get('/api/catalog/overview')
      const overview = response.data
      setMetrics({
        services: overview.services,
        databases: overview.databases,
        schemas: overview.schemas,
        tables: overview.tables,
      })
      setRecentRuns(overview.runs.map((run) => ({ ...run, source: run.service_name })))
      setError(null)
    } catch {
      setError('Dashboard data could not be loaded. Check that the API and metadata service are available.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    const loadTimer = window.setTimeout(loadDashboard, 0)
    return () => window.clearTimeout(loadTimer)
  }, [])

  return (
    <>
      <PagePlaceholder
        title={greetingText}
        description="A clear view of your data assets and metadata activity"
      />

      <div className="metric-grid">
        <article className="metric-card">
          <span className="metric-label">Total Connected sources</span>
          <strong>{isLoading ? '--' : metrics.services}</strong>
        </article>

        <article className="metric-card">
          <span className="metric-label">Total Databases</span>
          <strong>{isLoading ? '--' : metrics.databases}</strong>
        </article>

        <article className="metric-card">
          <span className="metric-label">No. of Schemas</span>
          <strong>{isLoading ? '--' : metrics.schemas}</strong>
        </article>

        <article className="metric-card">
          <span className="metric-label">Total Tables</span>
          <strong>{isLoading ? '--' : metrics.tables}</strong>
        </article>
      </div>

      {/* recent pipeline runs  */}
      <section className="content-section">
        <div className="section-heading">
          <div>
            <h2>Recent Pipeline runs</h2>
          </div>
          <Link className="action-link" to="/pipeline-runs">View all</Link>
        </div>
        {isLoading && (
          <StatePanel
            type="loading"
            title="Loading pipeline activity"
            description="Collecting recent ingestion runs from your connected sources."
          />
        )}
        {!isLoading && error && (
          <StatePanel
            type="error"
            title="Unable to load dashboard"
            description={error}
            action={<button className="button button-secondary" type="button" onClick={loadDashboard}>Try again</button>}
          />
        )}
        {!isLoading && !error && recentRuns.length === 0 && (
          <StatePanel
            type="empty"
            title="No pipeline runs"
            description="Run metadata ingestion from a connection to see activity here."
          />
        )}
        {!isLoading && !error && recentRuns.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Service</th>
                  <th>Airflow DAG</th>
                  <th>Status</th>
                  <th>Last Ingestion Time</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.slice(0, 5).map((run) => (
                  <tr key={`${run.service_uuid}-${run.id}`}>
                    <td className="table-primary">{run.id}</td>
                    <td>{run.source}</td>
                    <td>{run.dag_id}</td>
                    <td><span className={`status-badge status-${run.status.toLowerCase()}`}>{run.status}</span></td>
                    <td>{formatDate(run.finished_at || run.started_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}

export default Dashboard