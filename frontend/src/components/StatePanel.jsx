function StatePanel({ type, title, description, action }) {
  return (
    <div className={`state-panel state-${type}`}>
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      {action}
    </div>
  )
}

export default StatePanel