import { useEffect } from 'react'

function ToastNotification({ tone = 'success', message, onDismiss }) {
  useEffect(() => {
    const timer = window.setTimeout(onDismiss, 5000)
    return () => window.clearTimeout(timer)
  }, [onDismiss])

  return (
    <div className={`toast toast-${tone}`} role="status">
      <span className="toast-indicator" aria-hidden="true" />
      <span>{message}</span>
      <button type="button" aria-label="Dismiss notification" onClick={onDismiss}>&times;</button>
    </div>
  )
}

export default ToastNotification