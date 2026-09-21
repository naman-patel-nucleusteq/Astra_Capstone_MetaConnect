import { Link, useNavigate } from 'react-router-dom'
import snowflakeLogo from '../assets/snowflake.svg'
import mongodbLogo from '../assets/mongodb.svg'
import PagePlaceholder from '../components/PagePlaceholder.jsx'
import ToastNotification from '../components/ToastNotification.jsx'
import { useEffect, useState } from 'react'

function AvailableConnections() {

  const navigate = useNavigate()
  const [notice, setNotice] = useState(null)

  useEffect(() => {
    if (!notice) 
      return undefined
    const timer = window.setTimeout(() => setNotice(null), 5000)
    return () => window.clearTimeout(timer)
  }, [notice])

  
  return (
    <>
      <PagePlaceholder
        title="Available connections"
        description="Choose a supported source to begin configuring a metadata connection."
      >
        <Link className="button button-secondary" to="/connections">Back to connections</Link>
      </PagePlaceholder>

      <section className="content-section">
        <div className="connection-type-grid">
          <button className="connection-type-card" type="button" onClick={() => navigate('/connections/snowflake')}>
            <img src={snowflakeLogo} alt="" />
            <span className="connection-type-name">Snowflake</span>
            <span className="connection-type-description">Connect to Snowflake and ingest database metadata.</span>
          </button>

          {/* <button className="connection-type-card" type="button" onClick={() => setNotice({ tone: 'error', message: 'MongoDB is not available right now.' })}>
            <img src={mongodbLogo} alt="" />
            <span className="connection-type-name">Mongo DB</span>
            <span className="connection-type-description">Connect to Mongo DB and ingest database metadata.</span>
          </button> */}
        </div>
      </section>

      {notice && <ToastNotification {...notice} onDismiss={() => setNotice(null)} />}

    </>
  )
}

export default AvailableConnections