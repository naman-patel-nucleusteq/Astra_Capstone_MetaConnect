import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import PagePlaceholder from '../components/PagePlaceholder.jsx'
import api from '../services/api.js'
import { getApiErrorMessage } from '../services/apiErrors.js'

const initialForm = {
  name: '',
  description: '',
  username: '',
  password: '',
  account: '',
  warehouse: '',
  role: '',
}

function SnowflakeConnection() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [isTesting, setIsTesting] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [error, setError] = useState(null)

  // Keep form edits local until the connection is tested and saved.
  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
    setTestResult(null)
    setError(null)
  }

  function validateForm() {
    const requiredFields = [
      ['name', 'Connection name'],
      ['username', 'Username'],
      ['password', 'Password'],
      ['account', 'Account'],
      ['warehouse', 'Warehouse'],
    ]
    const missingField = requiredFields.find(([field]) => !form[field].trim())
    if (missingField) return `${missingField[1]} is required.`
    if (!/[A-Za-z]/.test(form.name.trim())) return 'Connection name must contain at least one letter.'
    if (form.description.trim() && !/[A-Za-z]/.test(form.description.trim())) return 'Description must contain at least one letter.'
    return null
  }


  function buildSnowflakePayload() {
    return {
      username: form.username.trim(),
      password: form.password,
      account: form.account.trim(),
      warehouse: form.warehouse.trim(),
      database: null,
      schema: null,
      role: form.role.trim() || null,
    }
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
      const response = await api.post('/api/connections/test', buildSnowflakePayload())
      setTestResult({ tone: 'success', message: response.data.message || 'Snowflake connection successful.' })
    } 
    catch (requestError) {
      setTestResult({ tone: 'error', message: getApiErrorMessage(requestError, 'The Snowflake connection test failed.') })
    } 
    finally {
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
        service_type: 'snowflake',
        username: form.username.trim(),
        password: form.password,
        connection_details: {
          account: form.account.trim(),
          warehouse: form.warehouse.trim(),
          role: form.role.trim() || null,
        },
      })
      navigate('/connections', { replace: true, state: { notice: 'Snowflake connection saved.' } })
    } 
    catch (requestError) {
      setError(getApiErrorMessage(requestError, 'The connection could not be saved.'))
    } 
    finally {
      setIsSaving(false)
    }
  }


  return (
    <>
      <PagePlaceholder
        title="Snowflake connection"
      >
        <Link className="button button-secondary" to="/connections/available">Back to types</Link>
      </PagePlaceholder>

      {/* snowflake connection form */}
      <form className="connection-form" onSubmit={submitForm}>
        
        <div className="form-section">
          <h2>Connection details</h2>
          <div className="form-grid">
            <label>
              Connection name
              <input required name="name" value={form.name} onChange={updateField} placeholder="Analytics Snowflake" />
            </label>
            <label className="form-field-wide">
              <div>Description <span className="optional">(Optional)</span></div>
              <textarea name="description" value={form.description} onChange={updateField} rows="3" placeholder="Primary analytics warehouse" />
            </label>
          </div>
        </div>

        <div className="form-section">
          <h2>Snowflake Credentials</h2>
          <div className="form-grid">
            <label>
              Username
              <input required name="username" value={form.username} onChange={updateField} autoComplete="username" />
            </label>
            <label>
              Password
              <input required type="password" name="password" value={form.password} onChange={updateField} autoComplete="new-password" />
            </label>
            <label>
              Account
              <input required name="account" value={form.account} onChange={updateField} placeholder="org-account" />
            </label>
            <label>
              Warehouse
              <input required name="warehouse" value={form.warehouse} onChange={updateField} />
            </label>
            <label>
              <div>Role <span className="optional">(Optional)</span></div>
              <input name="role" value={form.role} onChange={updateField} />
            </label>
          </div>
        </div>
         
         {/* action buttons */}
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

export default SnowflakeConnection
