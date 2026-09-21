import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../services/api.js'
import StatePanel from '../components/StatePanel.jsx'
import ToastNotification from '../components/ToastNotification.jsx'
import { getApiErrorMessage } from '../services/apiErrors.js'

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : '--'
}

function ConnectionDetails() {
  const { connectionId } = useParams()
  const navigate = useNavigate()
  const [connection, setConnection] = useState(null)
  const [pipelines, setPipelines] = useState([])
  const [runs, setRuns] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [editingConnection, setEditingConnection] = useState(false)
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [isSavingConnection, setIsSavingConnection] = useState(false)
  const [connectionTest, setConnectionTest] = useState(null)
  const [connectionFormError, setConnectionFormError] = useState(null)
  const [connectionForm, setConnectionForm] = useState(null)
  const [editingPipeline, setEditingPipeline] = useState(null)
  const [pipelineForm, setPipelineForm] = useState(null)
  const [pipelineToDelete, setPipelineToDelete] = useState(null)
  const [serviceDeleteRequested, setServiceDeleteRequested] = useState(false)
  const [activeTab, setActiveTab] = useState('details')

  useEffect(() => {
    function closeOnEscape(event) {
      if (event.key !== 'Escape') return
      setEditingConnection(false)
      setEditingPipeline(null)
      setPipelineToDelete(null)
      setServiceDeleteRequested(false)
    }

    document.addEventListener('keydown', closeOnEscape)
    const previousOverflow = document.body.style.overflow

    if (editingConnection || editingPipeline || pipelineToDelete || serviceDeleteRequested) 
      document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', closeOnEscape)
      document.body.style.overflow = previousOverflow
    }
  }, [editingConnection, editingPipeline, pipelineToDelete, serviceDeleteRequested])


  const loadPipelines = useCallback(async () => {
    const pipelinesResponse = await api.get(`/api/services/${connectionId}/pipelines`)
    setPipelines(pipelinesResponse.data)
    if (pipelinesResponse.data.length === 0) {
      setRuns([])
      return
    }
    const runsResponse = await api.get(`/api/pipelines/${pipelinesResponse.data[0].id}/ingestion-runs`)
    setRuns(runsResponse.data)
  }, [connectionId])


  useEffect(() => {
    let active = true

    async function loadConnection() {
      try {
        const [connectionResponse, pipelinesResponse] = await Promise.all([
          api.get(`/api/services/${connectionId}`),
          api.get(`/api/services/${connectionId}/pipelines`),
        ])
        const runsResponse = pipelinesResponse.data.length > 0
          ? await api.get(`/api/pipelines/${pipelinesResponse.data[0].id}/ingestion-runs`)
          : { data: [] }
        if (active) {
          setConnection(connectionResponse.data)
          setConnectionForm({
            name: connectionResponse.data.name,
            description: connectionResponse.data.description || '',
            username: connectionResponse.data.username || '',
            password: '',
            account: connectionResponse.data.connection_details?.account || '',
            warehouse: connectionResponse.data.connection_details?.warehouse || '',
            role: connectionResponse.data.connection_details?.role || '',
            details: JSON.stringify(connectionResponse.data.connection_details || {}, null, 2),
          })
          setPipelines(pipelinesResponse.data)
          setRuns(runsResponse.data)
        }
      } catch (requestError) {
        if (active) {
          setError(getApiErrorMessage(requestError, 'This connection could not be loaded from the catalog.'))
        }
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }

    loadConnection()
    return () => {active = false}
  }, [connectionId])

  async function runPipeline(pipeline) {
    setBusyId(pipeline.id)
    setNotice(null)
    try {
      await api.post(`/api/pipelines/${pipeline.id}/run`)
      setNotice({ tone: 'success', message: `Pipeline ${pipeline.name} started.` })
      await loadPipelines()
    } 
    catch (requestError) {
      setNotice({ tone: 'error', message: getApiErrorMessage(requestError, 'The pipeline could not be started.') })
    } 
    finally {
      setBusyId(null)
    }
  }

  function startPipelineEdit(pipeline) {
    setEditingPipeline(pipeline.id)
    setPipelineForm({
      name: pipeline.name,
      database_name: pipeline.database_name || '',
      schema_name: pipeline.schema_name || '',
      schedule_type: pipeline.schedule_type || 'MANUAL',
      schedule: pipeline.schedule || '',
    })
  }
 
  async function savePipeline(event) {
    event.preventDefault()
    if (!/[A-Za-z]/.test(pipelineForm.name.trim())) {
      setNotice({ tone: 'error', message: 'Pipeline name must contain at least one letter.' })
      return
    }
    try {
      await api.put(`/api/pipelines/${editingPipeline}`, {
        ...pipelineForm,
        database_name: pipelineForm.database_name.trim() || null,
        schema_name: pipelineForm.schema_name.trim() || null,
        schedule: pipelineForm.schedule.trim() || null,
      })
      setEditingPipeline(null)
      setPipelineForm(null)
      setNotice({ tone: 'success', message: 'Pipeline updated.' })
      await loadPipelines()
    } catch (requestError) {
      setNotice({ tone: 'error', message: getApiErrorMessage(requestError, 'The pipeline could not be updated.') })
    }
  }

  function requestPipelineDelete(pipeline) {
    setPipelineToDelete(pipeline)
  }

  // delete pipeline
  async function deletePipeline() {
    const pipeline = pipelineToDelete
    if (!pipeline) return

    setPipelineToDelete(null)
    try {
      await api.delete(`/api/pipelines/${pipeline.id}`)
      setNotice({ tone: 'success', message: 'Pipeline deleted. Its Airflow DAG was removed.' })
      await loadPipelines()
    } 
    catch (requestError) {
      setNotice({ tone: 'error', message: getApiErrorMessage(requestError, 'The pipeline could not be deleted.') })
    }
  }

  function requestServiceDelete() {
    setServiceDeleteRequested(true)
  }

  // delete connection
  async function deleteConnection() {
    setServiceDeleteRequested(false)
    try {
      await api.delete(`/api/services/${connectionId}`)
      navigate('/connections', { replace: true, state: { notice: 'Connection deleted.' } })
    } catch (requestError) {
      setNotice({ tone: 'error', message: getApiErrorMessage(requestError, 'The connection could not be deleted.') })
    }
  }

  function startConnectionEdit() {
    setConnectionTest(null)
    setConnectionFormError(null)
    setEditingConnection(true)
  }


  function updateConnectionField(event) {
    setConnectionForm((current) => ({ ...current, [event.target.name]: event.target.value }))
    setConnectionTest(null)
    setConnectionFormError(null)
  }

  // returning connector specific connection information
  function connectionDetailsPayload() {
    if (connection.service_type.toUpperCase() === 'SNOWFLAKE') {
      return {
        account: connectionForm.account.trim(),
        warehouse: connectionForm.warehouse.trim(),
        role: connectionForm.role.trim() || null,
      }
    }
    try {
      return JSON.parse(connectionForm.details || '{}')
    } 
    catch {
      throw new Error('Connection details must be valid JSON.')
    }
  }

  
  // test connection after updating a service information 
  async function testConnectionUpdate() {
    try {
      const details = connectionDetailsPayload()
      setIsTestingConnection(true)
      setConnectionTest(null)
      setConnectionFormError(null)
      const response = await api.post(`/api/services/${connectionId}/test`, {
        username: connectionForm.username.trim() || null,
        password: connectionForm.password || null,
        connection_details: details,
      })
      setConnectionTest({ tone: 'success', message: response.data.message || 'Connection test successful.' })
    } 
    catch (requestError) {
      setConnectionTest({ tone: 'error', message: requestError.message || getApiErrorMessage(requestError, 'The connection test failed.') })
    } 
    finally {
      setIsTestingConnection(false)
    }
  }

  
  // save connection after updating information
  async function saveConnectionUpdate(event) {
    event.preventDefault()

    if (!/[A-Za-z]/.test(connectionForm.name.trim())) {
      setConnectionFormError('Connection name must contain at least one letter.')
      return
    }
    if (connectionForm.description.trim() && !/[A-Za-z]/.test(connectionForm.description.trim())) {
      setConnectionFormError('Description must contain at least one letter.')
      return
    }
    if (connectionTest?.tone !== 'success') {
      setConnectionFormError('Test the updated connection successfully before saving.')
      return
    }
    try {
      const details = connectionDetailsPayload()
      setIsSavingConnection(true)
      setConnectionFormError(null)
      await api.put(`/api/services/${connectionId}`, {
        name: connectionForm.name.trim(),
        description: connectionForm.description.trim() || null,
        username: connectionForm.username.trim() || null,
        password: connectionForm.password || null,
        connection_details: details,
      })
      const response = await api.get(`/api/services/${connectionId}`)
      setConnection(response.data)
      setEditingConnection(false)
      setConnectionTest(null)
      setNotice({ tone: 'success', message: 'Connection details updated' })
    } 
    catch (requestError) {
      setConnectionFormError(requestError.message || getApiErrorMessage(requestError, 'The connection could not be updated.'))
    } 
    finally {
      setIsSavingConnection(false)
    }
  }

  if (isLoading) {
    return <StatePanel type="loading" title="Loading connection" description="Retrieving the saved connection details." />
  }

  if (error || !connection) {
    return <StatePanel type="error" title="Connection unavailable" description={error || 'The requested connection was not found.'} />
  }

  // connection details array
  const connectionDetailRows = [
    ['Connection name', connection.name],
    ['Description', connection.description || '--'],
    ['Connection UUID', connection.uuid],
    ['Connection type', connection.service_type],
    ['Username', connection.username || '--'],
    ['Account', connection.connection_details?.account || '--'],
    ['Warehouse', connection.connection_details?.warehouse || '--'],
    ['Role', connection.connection_details?.role || '--'],
    ['Owner', connection.created_by || 'Unknown'],
    ['Created at', formatDate(connection.created_at)],
    ['Airflow connection', connection.airflow_connection_id],
    ...Object.entries(connection.connection_details || {})
      .filter(([key]) => !['account', 'warehouse', 'role', 'password'].includes(key.toLowerCase()))
      .map(([key, value]) => [key, typeof value === 'object' ? JSON.stringify(value) : value || '--']),
  ]

  return (
    <>
      <section className="page-section">
        <div className="page-heading">
          <div>
            <h2>{connection.name}</h2>
          </div>
          <div>
            <Link className="button button-secondary" to="/connections">Back to Connections</Link>
          </div>
        </div>

        <nav className="detail-tabs" aria-label="Connection sections">
          <button className={activeTab === 'details' ? 'active' : ''} type="button" onClick={() => setActiveTab('details')}>Connection Details</button>
          <button className={activeTab === 'pipeline' ? 'active' : ''} type="button" onClick={() => setActiveTab('pipeline')}>Pipeline</button>
        </nav>
        
        {/* connection deatils section  */}
        {activeTab === 'details' && <>
          <div className="detail-actions">
            <button className="button button-danger" type="button" onClick={requestServiceDelete}>Delete</button>
            <button className="button button-primary" type="button" onClick={startConnectionEdit}>Update</button>
          </div>
          <div className="details-table-wrap">
            <table className="details-table">
              <tbody>
                {connectionDetailRows.map(([label, value]) => (
                  <tr key={label}>
                    <th scope="row">{label}</th>
                    <td className={label.includes('UUID') ? 'uuid-cell' : ''}>{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>}
      </section>
      
      {/* connection update form */}
      {activeTab === 'details' && editingConnection && connectionForm && <div className="modal-backdrop" role="presentation" onMouseDown={() => setEditingConnection(false)}>
        <section className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="connection-update-title" onMouseDown={(event) => event.stopPropagation()}>
          <div className="modal-header"><div><h2 id="connection-update-title">Update connection</h2></div><button className="modal-close" type="button" aria-label="Close connection update" onClick={() => setEditingConnection(false)}>&times;</button></div>
          <form className="connection-form" onSubmit={saveConnectionUpdate}>
            <div className="form-grid">
              <label>Connection name<input required name="name" value={connectionForm.name} onChange={updateConnectionField} /></label>
              <label className="form-field-wide">Description<textarea rows="3" name="description" value={connectionForm.description} onChange={updateConnectionField} /></label>
              <label>Username<input required name="username" value={connectionForm.username} onChange={updateConnectionField} autoComplete="username" /></label>
              <label>Password<input type="password" name="password" value={connectionForm.password} onChange={updateConnectionField} placeholder="Leave blank to keep current password" autoComplete="new-password" /></label>
              {connection.service_type.toUpperCase() === 'SNOWFLAKE' ? 
              <>
                <label>Account<input required name="account" value={connectionForm.account} onChange={updateConnectionField} /></label>
                <label>Warehouse<input required name="warehouse" value={connectionForm.warehouse} onChange={updateConnectionField} /></label>
                <label>
                  <div>Role <span className="optional">(Optional)</span></div>
                  <input name="role" value={connectionForm.role} onChange={updateConnectionField} />
                </label>
              </> 
              : 
              <label className="form-field-wide">
                Connection details (JSON)<textarea rows="6" name="details" value={connectionForm.details} onChange={updateConnectionField} />
              </label>}
            </div>
            {connectionTest && <p className={`form-message form-message-${connectionTest.tone}`} role="status">{connectionTest.message}</p>}
            {connectionFormError && <p className="form-error" role="alert">{connectionFormError}</p>}
            <div className="form-actions"><button className="button button-secondary" type="button" onClick={testConnectionUpdate} disabled={isTestingConnection || isSavingConnection}>{isTestingConnection ? 'Testing connection...' : 'Test Connection'}</button><button className="button button-primary" type="submit" disabled={isTestingConnection || isSavingConnection}>{isSavingConnection ? 'Updating...' : 'Update Connection'}</button><button className="button button-secondary" type="button" onClick={() => setEditingConnection(false)}>Cancel</button></div>
          </form>
        </section>
      </div>}



      {/* Pipeline section */}
      {activeTab === 'pipeline' &&
        <section className="content-section">
          <div className="section-heading">
            <div><h2>Pipelines</h2></div>
            <button className="button button-primary" type="button" disabled={pipelines.length > 0} onClick={() => navigate(`/connections/${connectionId}/pipelines/new`)}>
              Add Pipeline
            </button>
          </div>
          {pipelines.length === 0 ? (
            <>
              <StatePanel type="empty" title="No pipelines yet" description="Create a pipeline to choose a DAG name and metadata scope, then run ingestion." />
            </>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Pipeline Name</th>
                    <th>Database</th>
                    <th>Schema</th>
                    <th>Schedule</th>
                    <th>Status</th>
                    <th>Last Run Status</th>
                    <th>Created At</th>
                    <th>Owner</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pipelines.map((pipeline) => (
                    <tr key={pipeline.id}>
                      <td className="table-primary">{pipeline.name}</td>
                      <td>{pipeline.database_name || '--'}</td>
                      <td>{pipeline.schema_name || '--'}</td>
                      <td>{pipeline.schedule_type === 'SCHEDULE' ? 'Yes' : 'No'}</td>
                      <td><span className={`status-badge status-${String(pipeline.status || 'READY').toLowerCase()}`}>{pipeline.status || 'READY'}</span></td>
                      <td><span className={`status-badge status-${String(pipeline.last_run_status || 'NEVER_RUN').toLowerCase()}`}>{pipeline.last_run_status || 'Never run'}</span></td>
                      <td>{formatDate(pipeline.created_at)}</td>
                      <td>{pipeline.created_by || '--'}</td>
                      <td>
                        <div className="table-actions">
                          <button className="action-link" type="button" onClick={() => startPipelineEdit(pipeline)}>Update</button>
                          <button className="action-link action-danger" type="button" onClick={() => requestPipelineDelete(pipeline)}>Delete</button>
                          <button className="action-link" type="button" disabled={busyId === pipeline.id} onClick={() => runPipeline(pipeline)}>Run Pipeline</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* pipeline update form */}
          {editingPipeline && pipelineForm && (
            <div className="modal-backdrop" role="presentation" onMouseDown={() => setEditingPipeline(null)}>
              <section className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="pipeline-update-title" onMouseDown={(event) => event.stopPropagation()}>
                <div className="modal-header"><div><span className="eyebrow">Pipeline configuration</span><h2 id="pipeline-update-title">Update pipeline</h2></div><button className="modal-close" type="button" aria-label="Close pipeline update" onClick={() => setEditingPipeline(null)}>&times;</button></div>
                <form className="connection-form pipeline-edit-form" onSubmit={savePipeline}>
                  <div className="form-section">
                    <div className="form-grid">
                      <label>Pipeline/DAG name<input required value={pipelineForm.name} onChange={(event) => setPipelineForm({ ...pipelineForm, name: event.target.value })} /></label>
                      <label>Database<input value={pipelineForm.database_name} onChange={(event) => setPipelineForm({ ...pipelineForm, database_name: event.target.value })} /></label>
                      <label>Schema<input value={pipelineForm.schema_name} onChange={(event) => setPipelineForm({ ...pipelineForm, schema_name: event.target.value })} /></label>
                      <label>Run mode

                        <div className="run-mode-buttons">
                          <button
                            type="button"
                            className={pipelineForm.schedule_type === "MANUAL" ? "active" : ""}
                            onClick={() =>
                              setPipelineForm({
                                ...pipelineForm,
                                schedule_type: "MANUAL",
                              })}
                          >
                            Manual
                          </button>

                          <button
                            type="button"
                            className={pipelineForm.schedule_type === "SCHEDULE" ? "active" : ""}
                            onClick={() =>
                              setPipelineForm({
                                ...pipelineForm,
                                schedule_type: "SCHEDULE",
                              })
                            }
                          >
                            Schedule
                          </button>
                        </div>
                      </label>

                      {pipelineForm.schedule_type === "SCHEDULE" && (
                        <label className="schedule-field">
                          Schedule
                          <input
                            required
                            value={pipelineForm.schedule}
                            onChange={(event) =>
                              setPipelineForm({
                                ...pipelineForm,
                                schedule: event.target.value,
                              })
                            }
                            placeholder="0 2 * * *"
                          />
                          <small className="schedule-hint">
                            <strong className='hint'>Cron format: </strong> minute hour day month weekday
                          </small>
                        </label>
                      )}
                    </div>
                  </div>
                  <div className="form-actions"><button className="button button-secondary" type="button" onClick={() => setEditingPipeline(null)}>Cancel</button><button className="button button-primary" type="submit">Save Pipeline</button></div>
                </form>
              </section>
            </div>
          )}

        </section>}


      {/* pipeline run section */}
      {activeTab === 'pipeline' && 
      <section className="content-section">
        <div className="section-heading"><div><h2>Pipeline Runs</h2></div><button className="action-link" type="button" onClick={loadPipelines}>Refresh status</button></div>
        {runs.length === 0 ?
          <StatePanel type="empty" title="No ingestion runs" description="Run a pipeline to populate this connection's catalog." />
          :
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
              <tbody>{runs.map((run) =>
                <tr key={run.id}>
                  <td className="table-primary">{run.id}</td>
                  <td>{connection.name}</td>
                  <td>{pipelines[0]?.airflow_dag_id || pipelines[0]?.name || '--'}</td>
                  <td>
                    <span className={`status-badge status-${run.status.toLowerCase()}`}>
                      {run.status}
                    </span>
                  </td>
                  <td>{formatDate(run.started_at)}</td>
                  <td>{formatDate(run.finished_at)}</td>
                  <td>{run.error_message || '--'}</td>
                </tr>)}
              </tbody>
            </table>
          </div>}
      </section>}

      {/* pipeline delete confirmation popup */}
      {pipelineToDelete && 
      <div className="modal-backdrop" role="presentation" onMouseDown={() => setPipelineToDelete(null)}>
        <section className="modal-panel confirmation-modal" role="alertdialog" aria-modal="true" aria-labelledby="delete-pipeline-title" aria-describedby="delete-pipeline-description" onMouseDown={(event) => event.stopPropagation()}>
         
          <div className="modal-header">
            <div>
              <span className="eyebrow">Delete pipeline</span>
              <h2 id="delete-pipeline-title">Confirm deletion</h2>
            </div>
            <button className="modal-close" type="button" aria-label="Close delete confirmation" onClick={() => setPipelineToDelete(null)}>&times;</button>
          </div>

          <div className="confirmation-content">
            <p id="delete-pipeline-description">Delete pipeline <strong>{pipelineToDelete.name}</strong>? Its Airflow DAG and ingestion history will also be removed.</p>
            <div className="form-actions">
              <button className="button button-secondary" type="button" onClick={() => setPipelineToDelete(null)}>Cancel</button>
              <button className="button button-danger" type="button" onClick={deletePipeline}>Delete Pipeline</button>
            </div>
          </div>

        </section>
      </div>}


      {/* service delete confirmation popup */}
      {serviceDeleteRequested && <div className="modal-backdrop" role="presentation" onMouseDown={() => setServiceDeleteRequested(false)}>
        <section className="modal-panel confirmation-modal" role="alertdialog" aria-modal="true" aria-labelledby="delete-service-title" aria-describedby="delete-service-description" onMouseDown={(event) => event.stopPropagation()}>
          
          <div className="modal-header">
            <div>
              <span className="eyebrow">Delete connection</span>
              <h2 id="delete-service-title">Confirm deletion</h2>
            </div>
            <button className="modal-close" type="button" aria-label="Close delete confirmation" onClick={() => setServiceDeleteRequested(false)}>&times;</button>
          </div>

          <div className="confirmation-content">
            <p id="delete-service-description">Delete connection <strong>{connection.name}</strong>? Its pipelines, ingestion runs, and catalog metadata will also be removed.</p>
            <div className="form-actions"><button className="button button-secondary" type="button" onClick={() => setServiceDeleteRequested(false)}>Cancel</button><button className="button button-danger" type="button" onClick={deleteConnection}>Delete Connection</button></div>
          </div>

        </section>
      </div>}
      
      {notice && <ToastNotification {...notice} onDismiss={() => setNotice(null)} />}
    </>
  )
}

export default ConnectionDetails
