import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import PagePlaceholder from '../components/PagePlaceholder.jsx'
import api from '../services/api.js'
import { getApiErrorMessage } from '../services/apiErrors.js'

const initialForm = {
  name: '',
  database_name: '',
  schema_name: '',
  schedule_type: 'MANUAL',
  schedule: '',
}

function CreatePipeline() {
  const { connectionId } = useParams()
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [connection, setConnection] = useState(null)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true
    api.get(`/api/services/${connectionId}`)
      .then((response) => {
        if (active) setConnection(response.data)
      })
      .catch((requestError) => {
        if (active) setError(getApiErrorMessage(requestError, 'Connection could not be loaded.'))
      })
    return () => {
      active = false
    }
  }, [connectionId])

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
    setError(null)
  }

  const supportsSchemas = connection?.capabilities?.supports_schemas !== false

  async function submitForm(event) {
    event.preventDefault()
    if (!form.name.trim()) {
      setError('DAG / pipeline name is required.')
      return
    }
    if (!/[A-Za-z]/.test(form.name.trim())) {
      setError('DAG / pipeline name must contain at least one letter.')
      return
    }

    setIsSaving(true)
    setError(null)
    try {
      await api.post(`/api/services/${connectionId}/pipelines`, {
        name: form.name.trim(),
        database_name: form.database_name.trim() || null,
        schema_name: supportsSchemas ? (form.schema_name.trim() || null) : null,
        schedule_type: form.schedule_type,
        schedule: form.schedule.trim() || null,
      })
      navigate(`/connections/${connectionId}?tab=pipeline`, {
        replace: true,
        state: { notice: 'Pipeline created.' },
      })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'The pipeline could not be created.'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <>
      <PagePlaceholder
        title="Create pipeline"
        description="Name the Airflow DAG and optionally limit metadata ingestion."
      >
        <Link className="button button-secondary" to={`/connections/${connectionId}`}>Back to connection</Link>
      </PagePlaceholder>

      {/* create pipeline form */}
      <form className="connection-form" onSubmit={submitForm}>

        <div className="form-section">
          <h2>Pipeline details</h2>
          <div className="form-grid">
            <label>DAG / Pipeline name
              <input required name="name" value={form.name} onChange={updateField} placeholder="student_metadata" />
            </label>

            <label>
              <div>Database name <span className="optional">(Optional)</span> </div>
              <input name="database_name" value={form.database_name} onChange={updateField} placeholder="SCHOOL_DB" />
            </label>

            {supportsSchemas && (
              <label>
                <div>Schema name <span className="optional">(Optional)</span></div>
                <input name="schema_name" value={form.schema_name} onChange={updateField} placeholder="PUBLIC" />
              </label>
            )}

            <label>
              Run mode

              <div className="run-mode-buttons">
                <button
                  type="button"
                  className={form.schedule_type === "MANUAL" ? "active" : ""}
                  onClick={() =>
                    setForm({
                      ...form,
                      schedule_type: "MANUAL",
                    })
                  }
                >
                  Manual
                </button>

                <button
                  type="button"
                  className={form.schedule_type === "SCHEDULE" ? "active" : ""}
                  onClick={() =>
                    setForm({
                      ...form,
                      schedule_type: "SCHEDULE",
                    })
                  }
                >
                  Schedule
                </button>
              </div>
            </label>

            {form.schedule_type === "SCHEDULE" && (
              <label className="schedule-field">
                Schedule
                <input
                  required
                  name="schedule"
                  value={form.schedule}
                  onChange={updateField}
                  placeholder="0 2 * * *"
                />
                <small className="schedule-hint">
                  <strong className="hint">Cron format: </strong>
                  minute hour day month weekday
                </small>
              </label>
            )}

          </div>
        </div>

        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="form-actions">
          <Link className="button button-secondary" to={`/connections/${connectionId}`}>Cancel</Link>
          <button className="button button-primary" type="submit" disabled={isSaving}>
            {isSaving ? 'Creating...' : 'Create Pipeline'}
          </button>
        </div>

      </form>
    </>
  )
}

export default CreatePipeline
