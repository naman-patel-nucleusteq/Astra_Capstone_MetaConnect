import { useEffect, useState } from 'react'
import PagePlaceholder from '../components/PagePlaceholder.jsx'
import StatePanel from '../components/StatePanel.jsx'
import api from '../services/api.js'

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : '--'
}

function PipelineRuns() {
  const [runs, setRuns] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  async function loadRuns() {
    setIsLoading(true)
    try {
      const response = await api.get('/api/catalog/runs')
      setRuns(response.data)
      setError(null)
    } catch {
      setError('Pipeline runs could not be loaded.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(loadRuns, 0)
    return () => window.clearTimeout(timer)
  }, [])

  const renderRunTable = () => (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Service</th>
            <th>Pipeline / DAG</th>
            <th>Status</th>
            <th>Started</th>
            <th>Ended</th>
            <th>Error</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={`${run.service_uuid}-${run.id}`}>
              <td className="table-primary">{run.id}</td>
              <td>{run.service_name}</td>
              <td>{run.dag_id || run.name}</td>
              <td><span className={`status-badge status-${run.status.toLowerCase()}`}>{run.status}</span></td>
              <td>{formatDate(run.started_at)}</td>
              <td>{formatDate(run.finished_at)}</td>
              <td>{run.error_message || '--'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  return (
    <>
      <PagePlaceholder title="Pipeline runs" description="Review every metadata ingestion run across your connected services." />
      {isLoading && <StatePanel type="loading" title="Loading pipeline runs" description="Retrieving ingestion history." />}
      {!isLoading && error && <StatePanel type="error" title="Unable to load pipeline runs" description={error} action={<button className="button button-secondary" type="button" onClick={loadRuns}>Try again</button>} />}
      {!isLoading && !error && runs.length === 0 && <StatePanel type="empty" title="No pipeline runs" description="Run metadata ingestion from a connection to create pipeline activity." />}
      {!isLoading && !error && runs.length > 0 && <section className="content-section">{renderRunTable()}</section>}
    </>
  )
}

export default PipelineRuns
