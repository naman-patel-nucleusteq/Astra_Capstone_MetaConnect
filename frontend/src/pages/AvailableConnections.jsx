import { Link, useNavigate } from 'react-router-dom'
import PagePlaceholder from '../components/PagePlaceholder.jsx'
import { CONNECTORS } from '../config/connectors.js'

function AvailableConnections() {
  const navigate = useNavigate()
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
          {Object.entries(CONNECTORS).map(([key, connector]) => (
            <button
              className="connection-type-card"
              key={connector.type}
              type="button"
              onClick={() => navigate(`/connections/new/${key}`)}
            >
              {connector.logo && <img className={`connection-type-logo connection-type-logo-${key}`} src={connector.logo} alt="" />}
              <span className="connection-type-name">{connector.label}</span>
              <span className="connection-type-description">{connector.description}</span>
            </button>
          ))}
        </div>
      </section>
    </>
  )
}

export default AvailableConnections