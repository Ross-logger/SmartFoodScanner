import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const token = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const userName = computed(() => user.value?.full_name || user.value?.username || 'User')

  // Actions
  function initAuth() {
    const savedToken = localStorage.getItem('auth_token')
    const savedUser = localStorage.getItem('user')
    
    if (savedToken && savedUser) {
      token.value = savedToken
      user.value = JSON.parse(savedUser)
      api.setAuthToken(savedToken)
    }
  }

  async function login(credentials) {
    loading.value = true
    error.value = null
    
    try {
      const response = await api.post('/auth/login', credentials)
      
      token.value = response.access_token
      user.value = response.user
      
      localStorage.setItem('auth_token', response.access_token)
      localStorage.setItem('user', JSON.stringify(response.user))
      api.setAuthToken(response.access_token)
      
      return true
    } catch (err) {
      error.value = err.message || 'Login failed'
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(userData) {
    loading.value = true
    error.value = null
    
    try {
      const response = await api.post('/auth/register', userData)
      
      token.value = response.access_token
      user.value = response.user
      
      localStorage.setItem('auth_token', response.access_token)
      localStorage.setItem('user', JSON.stringify(response.user))
      api.setAuthToken(response.access_token)
      
      return true
    } catch (err) {
      error.value = err.message || 'Registration failed'
      return false
    } finally {
      loading.value = false
    }
  }

  function logout() {
    user.value = null
    token.value = null
    
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
    api.setAuthToken(null)
  }

  async function updateProfile(updates) {
    loading.value = true
    error.value = null
    
    try {
      const response = await api.put('/users/me', updates)
      user.value = { ...user.value, ...response }
      localStorage.setItem('user', JSON.stringify(user.value))
      return true
    } catch (err) {
      error.value = err.message || 'Update failed'
      return false
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    user,
    token,
    loading,
    error,
    // Getters
    isAuthenticated,
    userName,
    // Actions
    initAuth,
    login,
    register,
    logout,
    updateProfile
  }
})

