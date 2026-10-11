import snowflakeLogo from '../assets/snowflake.svg'
import pinotlogo from '../assets/pinotdb.png'

export const CONNECTORS = {
  snowflake: {
    type: 'SNOWFLAKE',
    label: 'Snowflake',
    description: 'Connect to Snowflake and ingest database metadata.',
    logo: snowflakeLogo,
    usernameRequired: true,
    passwordRequired: true,
    fields: [
      { name: 'account', label: 'Account', required: true, placeholder: 'org-account' },
      { name: 'warehouse', label: 'Warehouse', required: true},
      { name: 'role', label: 'Role', required: false},
    ],
  },
  pinot: {
    type: 'PINOT',
    label: 'PinotDB',
    description: 'Connect to Pinot and ingest tables and schema fields.',
    logo: pinotlogo,
    usernameRequired: false,
    passwordRequired: false,
    fields: [
      { name: 'controller_host', label: 'Controller host', required: true, placeholder: 'pinot-controller' },
      { name: 'controller_port', label: 'Controller port', required: true, type: 'number', placeholder: '9000' },
      { name: 'broker_host', label: 'Broker host', required: true, placeholder: 'pinot-broker' },
      { name: 'broker_port', label: 'Broker port', required: true, type: 'number', placeholder: '8099' },
    ],
  },
}

export function getConnectorConfig(serviceType) {
  return Object.values(CONNECTORS).find(
    (connector) => connector.type === String(serviceType || '').toUpperCase(),
  )
}
