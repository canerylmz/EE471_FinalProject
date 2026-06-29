import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 130000,
})

/**
 * Unwrap the `{success, data}` / `{success, error}` envelope used by the
 * Flask backend, throwing a plain Error with a user-friendly message.
 */
export async function unwrap(promise) {
  try {
    const response = await promise
    const body = response.data
    if (!body || body.success !== true) {
      throw new Error((body && body.error) || 'An unknown error occurred.')
    }
    return body.data
  } catch (err) {
    if (err.response?.data?.error) {
      throw new Error(err.response.data.error)
    }
    if (err.code === 'ECONNABORTED') {
      throw new Error('The request timed out. Please try again.')
    }
    if (err.message === 'Network Error') {
      throw new Error('Could not connect to the server. Is the backend running?')
    }
    throw err
  }
}

export default client
