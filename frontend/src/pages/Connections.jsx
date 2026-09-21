import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import PagePlaceholder from '../components/PagePlaceholder.jsx'
import StatePanel from '../components/StatePanel.jsx'
import ToastNotification from '../components/ToastNotification.jsx'
import api from '../services/api.js'

function formatDate(value) {
  return value ? new Date(value).toLocaleDateString() : '--'
}

function Connections() {
  const location = useLocation()
  const [connections, setConnections] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(() => {
    const message = location.state?.notice
    return message ? { tone: 'success', message } : null
  })
  const [busyId, setBusyId] = useState(null)
  const [connectionToDelete, setConnectionToDelete] = useState(null)


  async function loadConnections() {
    try {
      const response = await api.get('/api/services')
      setConnections(response.data)
      setError(null)
    } catch {
      setError('Saved connections could not be loaded. Check the API and try again.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let active = true

    api.get('/api/services')
      .then((response) => {
        if (active) {
          setConnections(response.data)
          setError(null)
        }
      })
      .catch(() => {
        if (active) {
          setError('Saved connections could not be loaded. Check the API and try again.')
        }
      })
      .finally(() => {
        if (active) {
          setIsLoading(false)
        }
      })

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!notice) return undefined
    const timer = window.setTimeout(() => setNotice(null), 5000)
    return () => window.clearTimeout(timer)
  }, [notice])


  function requestConnectionDelete(connection) {
    setConnectionToDelete(connection)
  }

  async function deleteConnection() {
    const connection = connectionToDelete

    if (!connection) {
      return
    }

    setConnectionToDelete(null)
    setBusyId(connection.uuid)
    try {
      await api.delete(`/api/services/${connection.uuid}`)
      setConnections((current) => current.filter((item) => item.uuid !== connection.uuid))
      setNotice({ tone: 'success', message: 'Connection deleted.' })
    } catch {
      setNotice({ tone: 'error', message: 'Connection could not be deleted.' })
    } finally {
      setBusyId(null)
    }
  }

  return (
    <>
      <PagePlaceholder
        title="Connections "
        description="Manage the systems that feed your organization's metadata catalog."
      >
        <Link className="button button-primary" to="/connections/available">Add connection</Link>
      </PagePlaceholder>

      <section className="content-section connection-list-section">
        <div className="section-heading">
          <div><h2>Saved connections</h2></div>
          <span className="section-caption">{connections.length} configured</span>
        </div>
        {isLoading && <StatePanel type="loading" title="Loading connections" description="Retrieving saved data sources from the catalog." />}
        {!isLoading && error && <StatePanel type="error" title="Unable to load connections" description={error} action={<button className="button button-secondary" type="button" onClick={loadConnections}>Try again</button>} />}
        {!isLoading && !error && connections.length === 0 && <StatePanel type="empty" title="No connections yet" description="Add a data source to start ingesting metadata into MetaConnect." />}
        {!isLoading && !error && connections.length > 0 && (
          <div className="table-wrap">
            <table className="connections-table">
              <thead>
                <tr>
                  <th>Connection name</th>
                  <th>UUID</th>
                  <th>Type</th>
                  <th>Owner</th>
                  <th>Created at</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {connections.map((connection) => (
                  <tr key={connection.uuid}>
                    <td className="table-primary">{connection.name}</td>
                    <td className="uuid-cell">{connection.uuid}</td>
                    <td>{connection.service_type}</td>
                    <td>{connection.created_by || '--'}</td>
                    <td>{formatDate(connection.created_at)}</td>
                    <td><span className="status-badge status-active">Active</span></td>
                    <td>
                      <div className="table-actions">
                        <Link className="action-link" to={`/connections/${connection.uuid}`}>View</Link>
                        <button className="action-link action-danger" type="button" disabled={busyId === connection.uuid} onClick={() => requestConnectionDelete(connection)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {connectionToDelete && (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={() => setConnectionToDelete(null)}
        >
          <section
            className="modal-panel confirmation-modal"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-connection-title"
            aria-describedby="delete-connection-description"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <span className="eyebrow">Delete connection</span>
                <h2 id="delete-connection-title">Confirm deletion</h2>
              </div>

              <button
                className="modal-close"
                type="button"
                aria-label="Close delete confirmation"
                onClick={() => setConnectionToDelete(null)}
              >
                &times;
              </button>
            </div>

            <div className="confirmation-content">
              <p id="delete-connection-description">
                Delete connection{' '}
                <strong>{connectionToDelete.name}</strong>?
                Its pipelines, ingestion runs, and catalog metadata will also be removed.
              </p>

              <div className="form-actions">
                <button
                  className="button button-secondary"
                  type="button"
                  onClick={() => setConnectionToDelete(null)}
                >
                  Cancel
                </button>

                <button
                  className="button button-danger"
                  type="button"
                  onClick={deleteConnection}
                  disabled={busyId === connectionToDelete.uuid}
                >
                  {busyId === connectionToDelete.uuid
                    ? 'Deleting...'
                    : 'Delete Connection'}
                </button>
              </div>
            </div>
          </section>
        </div>
      )}

      {notice && <ToastNotification {...notice} onDismiss={() => setNotice(null)} />}
    </>
  )
}

export default Connections