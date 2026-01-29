import axios from 'axios'

// Base URL for API - will use proxy in development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

class ApiService {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 120000, // 2 minutes - OCR + LLM processing can take time
      headers: {
        'Content-Type': 'application/json'
      }
    })

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        return response.data
      },
      (error) => {
        const errorMessage = this.handleError(error)
        return Promise.reject(new Error(errorMessage))
      }
    )
  }

  handleError(error) {
    if (error.response) {
      // Server responded with error
      const status = error.response.status
      const data = error.response.data

      if (status === 401) {
        // Unauthorized - clear auth and redirect to login
        localStorage.removeItem('auth_token')
        localStorage.removeItem('user')
        window.location.href = '/login'
        return 'Session expired. Please login again.'
      }

      if (status === 422) {
        // Validation error
        const details = data.detail
        if (Array.isArray(details)) {
          return details.map(d => d.msg).join(', ')
        }
        return details || 'Validation error'
      }

      return data.detail || data.message || `Error: ${status}`
    } else if (error.request) {
      // Request made but no response
      return 'No response from server. Please check your connection.'
    } else {
      // Something else happened
      return error.message || 'An unexpected error occurred'
    }
  }

  setAuthToken(token) {
    if (token) {
      this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`
    } else {
      delete this.client.defaults.headers.common['Authorization']
    }
  }

  // HTTP Methods
  get(url, config = {}) {
    return this.client.get(url, config)
  }

  post(url, data, config = {}) {
    return this.client.post(url, data, config)
  }

  put(url, data, config = {}) {
    return this.client.put(url, data, config)
  }

  patch(url, data, config = {}) {
    return this.client.patch(url, data, config)
  }

  delete(url, config = {}) {
    return this.client.delete(url, config)
  }
}

// Export singleton instance
export default new ApiService()

