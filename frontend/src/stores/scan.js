import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useScanStore = defineStore('scan', () => {
  // State
  const currentScan = ref(null)
  const scanHistory = ref([])
  const loading = ref(false)
  const error = ref(null)
  const uploadProgress = ref(0)

  // Actions
  async function scanImage(imageFile) {
    loading.value = true
    error.value = null
    uploadProgress.value = 0
    
    try {
      const formData = new FormData()
      formData.append('file', imageFile)
      
      const response = await api.post('/scan/ocr', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          uploadProgress.value = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
        }
      })
      
      currentScan.value = response
      return response
    } catch (err) {
      error.value = err.message || 'Scan failed'
      throw err
    } finally {
      loading.value = false
      uploadProgress.value = 0
    }
  }

  async function fetchScanHistory(limit = 20, offset = 0) {
    loading.value = true
    error.value = null
    
    try {
      const response = await api.get('/scans', {
        params: { limit, skip: offset }
      })
      
      if (offset === 0) {
        scanHistory.value = response
      } else {
        scanHistory.value.push(...response)
      }
      
      return response
    } catch (err) {
      error.value = err.message || 'Failed to load history'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function getScanById(scanId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await api.get(`/scans/${scanId}`)
      currentScan.value = response
      return response
    } catch (err) {
      error.value = err.message || 'Failed to load scan'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteScan(scanId) {
    loading.value = true
    error.value = null
    
    try {
      await api.delete(`/scans/${scanId}`)
      scanHistory.value = scanHistory.value.filter(scan => scan.id !== scanId)
      return true
    } catch (err) {
      error.value = err.message || 'Failed to delete scan'
      return false
    } finally {
      loading.value = false
    }
  }

  function clearCurrentScan() {
    currentScan.value = null
    error.value = null
  }

  return {
    // State
    currentScan,
    scanHistory,
    loading,
    error,
    uploadProgress,
    // Actions
    scanImage,
    fetchScanHistory,
    getScanById,
    deleteScan,
    clearCurrentScan
  }
})

