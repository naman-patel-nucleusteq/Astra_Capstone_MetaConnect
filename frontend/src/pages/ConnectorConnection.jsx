import { useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import PagePlaceholder from '../components/PagePlaceholder.jsx'
import api from '../services/api.js'
import { getApiErrorMessage } from '../services/apiErrors.js'
import { CONNECTORS } from '../config/connectors.js'

function initialSettings(connector) {
  return Object.fromEntries(connector.fields.map((field) => [field.name, '']))
}

function ConnectorConnection({ connectorType: fixedConnectorType }) {
  const { connectorType: routeConnectorType } = useParams()
  const connector = CONNECTORS[fixedConnectorType || routeConnectorType]
  const navigate = useNavigate()
  const [form, setForm] = useState(() => ({
    name: '',
    description: '',
    username: '',
    password: '',
    settings: connector ? initialSettings(connector) : {},
  }))
  const [isTesting, setIsTesting] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [error, setError] = useState(null)

  if (!connector) return <Navigate to="/connections/available" replace />

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setTestResult(null)
    setError(null)
  }

  function updateSetting(event) {
    const { name, value } = event.target
    setForm((current) => ({
      ...current,
      settings: { ...current.settings, [name]: value },
    }))
    setTestResult(null)
    setError(null)
  }

  function validateForm() {
    if (!form.name.trim()) return 'Connection name is required.'
    if (!/[A-Za-z]/.test(form.name.trim())) return 'Connection name must contain at least one letter.'
    if (form.description.trim() && !/[A-Za-z]/.test(form.description.trim())) return 'Description must contain at least one letter.'
    if (connector.usernameRequired && !form.username.trim()) return 'Username is required.'
    if (connector.passwordRequired && !form.password) return 'Password is required.'

    for (const field of connector.fields) {
      const value = form.settings[field.name]?.trim()
      if (field.required && !value) return `${field.label} is required.`
      if (field.type === 'number' && value) {
        const port = Number(value)
        if (!Number.isInteger(port) || port < 1 || port > 65535) {
          return `${field.label} must be a port between 1 and 65535.`
        }
      }
    }
    return null
  }

  function connectionDetails() {
    return Object.fromEntries(connector.fields.map((field) => {
      const value = form.settings[field.name].trim()
      return [field.name, field.type === 'number' && value ? Number(value) : value || null]
    }))
  }

  async function testConnection() {
    const validationError = validateForm()
    if (validationError) {
      setError(validationError)
      return
    }

    setIsTesting(true)
    setTestResult(null)
    setError(null)
    try {
      const response = await api.post('/api/connections/test', {
        service_type: connector.type,
        username: form.username.trim() || null,
        password: form.password || null,
        connection_details: connectionDetails(),
      })
      setTestResult({ tone: 'success', message: response.data.message || `${connector.label} connection successful.` })
    } catch (requestError) {
      setTestResult({
        tone: 'error',
        message: getApiErrorMessage(requestError, `The ${connector.label} connection test failed.`),
      })
    } finally {
      setIsTesting(false)
    }
  }

  async function submitForm(event) {
    event.preventDefault()
    const validationError = validateForm()
    if (validationError) {
      setError(validationError)
      return
    }
    if (testResult?.tone !== 'success') {
      setError('Test the connection successfully before saving it.')
      return
    }

    setIsSaving(true)
    setError(null)
    try {
      await api.post('/api/services', {
        name: form.name.trim(),
        description: form.description.trim() || null,
        service_type: connector.type,
        username: form.username.trim() || null,
        password: form.password || null,
        connection_details: connectionDetails(),
      })
      navigate('/connections', {
        replace: true,
        state: { notice: `${connector.label} connection saved.` },
      })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'The connection could not be saved.'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <>
      <PagePlaceholder title={`${connector.label} connection`}>
        <Link className="button button-secondary" to="/connections/available">Back to types</Link>
      </PagePlaceholder>

      <form className="connection-form" onSubmit={submitForm}>
        <div className="form-section">
          <h2>Connection details</h2>
          <div className="form-grid">
            <label>
              Connection name
              <input required name="name" value={form.name} onChange={updateField} />
            </label>
            <label className="form-field-wide">
              <div>Description <span className="optional">(Optional)</span></div>
              <textarea name="description" value={form.description} onChange={updateField} rows="3" />
            </label>
          </div>
        </div>

        <div className="form-section">
          <h2>{connector.label} settings</h2>
          <div className="form-grid">
            <label>
              Username {connector.usernameRequired ? null : <span className="optional">(Optional)</span>}
              <input
                required={connector.usernameRequired}
                name="username"
                value={form.username}
                onChange={updateField}
                autoComplete="username"
              />
            </label>
            <label>
              Password {connector.passwordRequired ? null : <span className="optional">(Optional)</span>}
              <input
                required={connector.passwordRequired}
                type="password"
                name="password"
                value={form.password}
                onChange={updateField}
                autoComplete="new-password"
              />
            </label>
            {connector.fields.map((field) => (
              <label key={field.name}>
                {field.label} {!field.required && <span className="optional">(Optional)</span>}
                <input
                  required={field.required}
                  type={field.type || 'text'}
                  name={field.name}
                  value={form.settings[field.name]}
                  onChange={updateSetting}
                  placeholder={field.placeholder}
                />
              </label>
            ))}
          </div>
        </div>

        {testResult && <p className={`form-message form-message-${testResult.tone}`} role="status">{testResult.message}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="form-actions">
          <Link className="button button-secondary" to="/connections/available">Cancel</Link>
          <button className="button button-secondary" type="button" onClick={testConnection} disabled={isTesting || isSaving}>
            {isTesting ? 'Testing connection...' : 'Test Connection'}
          </button>
          <button className="button button-primary" type="submit" disabled={isTesting || isSaving}>
            {isSaving ? 'Saving...' : 'Save Connection'}
          </button>
        </div>
      </form>
    </>
  )
}

export default ConnectorConnection
