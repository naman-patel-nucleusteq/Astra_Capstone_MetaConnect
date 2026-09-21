export function getApiErrorMessage(error, fallback) {
  const messages = {
    400: 'Some connection details are invalid. Review the fields and try again.',
    401: 'Your session has expired. Sign in again and retry the request.',
    403: 'You do not have permission to perform this action.',
    409: 'A connection with these details already exists.',
    500: 'The server could not complete the request. Try again shortly.',
    502: 'The ingestion service could not be reached. Check the backend and Airflow status.',
    503: 'The service is temporarily unavailable. Try again shortly.',
  }

  return messages[error.response?.status] || fallback
}
