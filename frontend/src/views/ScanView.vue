<template>
  <div class="scan-view">
    <!-- Header -->
    <div class="header">
      <h1 class="page-title">Scan Food Product</h1>
      <p class="page-subtitle">
        Scan ingredient labels, upload images, or scan barcodes
      </p>
    </div>

    <!-- Scan Mode Selection -->
    <div v-if="!showCamera" class="scan-mode-container">
      <div class="scan-mode-tabs">
        <button
          @click="scanMode = 'camera'"
          class="scan-mode-tab"
          :class="{ active: scanMode === 'camera' }"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
          </svg>
          Camera
        </button>

        <button
          @click="scanMode = 'upload'"
          class="scan-mode-tab"
          :class="{ active: scanMode === 'upload' }"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Upload
        </button>

        <button
          @click="scanMode = 'barcode'"
          class="scan-mode-tab"
          :class="{ active: scanMode === 'barcode' }"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
              d="M3 4h3v16H3V4zm5 0h1v16H8V4zm3 0h2v16h-2V4zm4 0h1v16h-1V4zm3 0h3v16h-3V4z" />
          </svg>
          Barcode
        </button>
      </div>

      <!-- Camera Mode -->
      <div v-if="scanMode === 'camera'" class="mode-content">
        <!-- Native Camera Input (Works on all devices!) -->
        <input
          ref="cameraInput"
          type="file"
          accept="image/*"
          capture="environment"
          @change="handleCameraCapture"
          class="hidden"
        />
        
        <div 
          @click="$refs.cameraInput.click()"
          class="camera-trigger"
        >
          <div class="camera-icon-container">
            <svg class="w-32 h-32 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          
          <h3 class="text-2xl font-bold text-gray-900 mb-2">
            Tap to Scan
          </h3>
          
          <p class="text-gray-600 mb-6 max-w-md text-center">
            Take a photo of the ingredient label on your food product
          </p>
          
          <div class="scan-button">
            <svg class="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            </svg>
            Open Camera
          </div>
        </div>
      </div>

      <!-- Upload Mode -->
      <div v-else-if="scanMode === 'upload'" class="mode-content">
        <ImageUpload @upload="handleImageUpload" />
      </div>

      <!-- Barcode Mode -->
      <div v-else-if="scanMode === 'barcode'" class="mode-content">
        <BarcodeScanner @scan="handleBarcodeScan" />
      </div>

      <!-- Scan History Section -->
      <div class="history-section">
        <div class="history-header">
          <div class="history-header-icon">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h2 class="history-title">Recent Scans</h2>
            <p class="history-subtitle">Your previous scan results</p>
          </div>
        </div>

        <!-- Loading State -->
        <div v-if="historyLoading && !scanHistory.length" class="history-loading">
          <LoadingSpinner message="Loading history..." />
        </div>

        <!-- Empty State -->
        <div v-else-if="!historyLoading && !scanHistory.length" class="history-empty">
          <svg class="w-12 h-12 text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p class="text-gray-500 text-sm">No scans yet. Your scan history will appear here.</p>
        </div>

        <!-- History List -->
        <div v-else class="history-list">
          <div
            v-for="scan in scanHistory"
            :key="scan.id"
            class="history-item"
            @click="viewScan(scan.id)"
          >
            <div class="history-image">
              <img
                v-if="scan.image_url"
                :src="scan.image_url"
                :alt="`Scan ${scan.id}`"
                class="w-full h-full object-cover"
              />
              <div v-else class="image-placeholder">
                <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
            </div>

            <div class="history-content">
              <div class="history-meta">
                <span class="history-date">{{ formatDate(scan.created_at) }}</span>
                <span class="history-badge">
                  {{ getIngredientCount(scan) }} ingredients
                </span>
              </div>

              <p v-if="scan.ocr_text" class="history-text">
                {{ truncateText(scan.ocr_text, 100) }}
              </p>

              <div class="history-safety">
                <span v-if="scan.is_safe === true" class="safety-tag safety-safe">Safe</span>
                <span v-else-if="scan.is_safe === false" class="safety-tag safety-warning">Warning</span>
              </div>
            </div>

            <button
              @click.stop="deleteScan(scan.id)"
              class="delete-button"
              title="Delete scan"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>

          <!-- Load More Button -->
          <div v-if="hasMore" class="load-more-container">
            <button
              @click="loadMore"
              :disabled="historyLoading"
              class="btn-load-more"
            >
              {{ historyLoading ? 'Loading...' : 'Load More' }}
            </button>
          </div>
        </div>
      </div>
    </div>


    <!-- Loading State -->
    <div v-if="isProcessing" class="processing-overlay">
      <div class="processing-content">
        <LoadingSpinner
          size="lg"
          color="white"
          indicator="ring"
          :message="processingMessage"
          :message-class="processingMessageClass"
        />
        <div v-if="uploadProgress > 0" class="progress-bar">
          <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-message">
      <svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p>{{ error }}</p>
      <button @click="error = null" class="text-red-600 underline">Dismiss</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useScanStore } from '@/stores/scan'
import ImageUpload from '@/components/ImageUpload.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import BarcodeScanner from '@/components/BarcodeScanner.vue'

const router = useRouter()
const scanStore = useScanStore()

// State
const scanMode = ref('camera') // Camera now works great on all devices!
const cameraInput = ref(null)
const error = ref(null)

// History state
const historyLoading = ref(false)
const hasMore = ref(true)
const currentOffset = ref(0)
const pageSize = 20

const scanHistory = computed(() => scanStore.scanHistory)

// Computed
const isProcessing = computed(() => scanStore.loading)
const uploadProgress = computed(() => scanStore.uploadProgress)
const ANALYZING_INGREDIENTS_MSG = 'Analyzing ingredients...'

const processingMessage = computed(() => {
  if (uploadProgress.value > 0 && uploadProgress.value < 100) {
    return `Uploading... ${uploadProgress.value}%`
  }
  if (scanMode.value === 'barcode') {
    return 'Looking up product and analyzing ingredients...'
  }
  return ANALYZING_INGREDIENTS_MSG
})

const processingMessageClass = computed(() =>
  processingMessage.value === ANALYZING_INGREDIENTS_MSG
    ? 'text-green-400'
    : 'text-white'
)

onMounted(async () => {
  await loadHistory()
})

// Scan Methods
async function handleCameraCapture(event) {
  const file = event.target.files?.[0]
  if (file) {
    await processScan(file)
    // Reset input so same file can be selected again
    if (cameraInput.value) {
      cameraInput.value.value = ''
    }
  }
}

async function handleImageUpload(file) {
  await processScan(file)
}

async function processScan(file) {
  error.value = null
  
  try {
    const result = await scanStore.scanImage(file)
    
    // Navigate to result page
    if (result.scan_id) {
      router.push({ name: 'Result', params: { id: result.scan_id } })
    }
  } catch (err) {
    error.value = err.message || 'Failed to process image. Please try again.'
  }
}

async function handleBarcodeScan(barcode) {
  error.value = null
  
  try {
    const result = await scanStore.scanBarcode(barcode)
    
    // Navigate to result page
    if (result.scan_id) {
      router.push({ name: 'Result', params: { id: result.scan_id } })
    }
  } catch (err) {
    error.value = err.message || 'Failed to look up barcode. Please try again.'
  }
}

// History Methods
async function loadHistory() {
  historyLoading.value = true
  try {
    const results = await scanStore.fetchScanHistory(pageSize, currentOffset.value)
    if (results.length < pageSize) {
      hasMore.value = false
    }
  } catch (error) {
    console.error('Failed to load history:', error)
  } finally {
    historyLoading.value = false
  }
}

async function loadMore() {
  currentOffset.value += pageSize
  await loadHistory()
}

function viewScan(scanId) {
  router.push({ name: 'Result', params: { id: scanId } })
}

async function deleteScan(scanId) {
  if (!confirm('Are you sure you want to delete this scan?')) {
    return
  }
  try {
    await scanStore.deleteScan(scanId)
  } catch (error) {
    alert('Failed to delete scan. Please try again.')
  }
}

function formatDate(dateString) {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date

  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function truncateText(text, maxLength) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

function getIngredientCount(scan) {
  const ingredients = scan.ingredients || scan.corrected_ingredients || []
  return ingredients.length
}
</script>

<style scoped>
.scan-view {
  @apply min-h-screen bg-gray-50 pb-24;
}

.header {
  @apply bg-white border-b border-gray-200 px-4 py-8 text-center;
}

.page-title {
  @apply text-2xl font-bold text-gray-900 mb-2;
}

.page-subtitle {
  @apply text-gray-600 max-w-md mx-auto;
}

.scan-mode-container {
  @apply max-w-4xl mx-auto px-4 py-6;
}

.scan-mode-tabs {
  @apply flex gap-2 mb-6 bg-white rounded-lg p-1 shadow-sm;
}

.scan-mode-tab {
  @apply flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-md font-medium text-gray-600 transition-all duration-200;
}

.scan-mode-tab.active {
  @apply bg-primary-600 text-white shadow-md;
}

.mode-content {
  @apply bg-white rounded-xl shadow-sm border border-gray-200 p-6;
}

.camera-trigger {
  @apply flex flex-col items-center justify-center py-12 cursor-pointer transition-all duration-300 hover:bg-gray-50 rounded-lg;
  min-height: 400px;
}

.camera-icon-container {
  @apply mb-6 transform transition-transform duration-300 hover:scale-110;
}

.scan-button {
  @apply inline-flex items-center justify-center bg-primary-600 hover:bg-primary-700 text-white font-semibold px-8 py-4 rounded-xl shadow-lg transition-all duration-200 active:scale-95;
}

/* History Section */
.history-section {
  @apply mt-8 bg-gradient-to-r from-primary-50 to-blue-50 rounded-xl border-2 border-primary-200 p-5;
}

.history-header {
  @apply flex items-center gap-4 mb-5;
}

.history-header-icon {
  @apply flex-shrink-0 w-11 h-11 rounded-full bg-primary-600 text-white flex items-center justify-center shadow;
}

.history-title {
  @apply text-lg font-bold text-gray-900;
}

.history-subtitle {
  @apply text-xs text-gray-500 mt-0.5;
}

.history-loading {
  @apply flex items-center justify-center py-8;
}

.history-empty {
  @apply flex flex-col items-center justify-center py-8 text-center;
}

.history-list {
  @apply space-y-3;
}

.history-item {
  @apply bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex gap-4 cursor-pointer hover:shadow-md hover:border-primary-300 transition-all duration-200 active:scale-[0.98];
}

.history-image {
  @apply w-16 h-16 rounded-lg overflow-hidden bg-gray-100 flex-shrink-0;
}

.image-placeholder {
  @apply w-full h-full flex items-center justify-center;
}

.history-content {
  @apply flex-1 min-w-0;
}

.history-meta {
  @apply flex items-center gap-2 mb-1.5;
}

.history-date {
  @apply text-sm text-gray-500;
}

.history-badge {
  @apply text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full;
}

.history-text {
  @apply text-sm text-gray-700 mb-1.5 line-clamp-2;
}

.history-safety {
  @apply flex flex-wrap gap-2;
}

.safety-tag {
  @apply text-xs px-2 py-0.5 rounded-full font-medium;
}

.safety-safe {
  @apply bg-green-100 text-green-700;
}

.safety-warning {
  @apply bg-red-100 text-red-700;
}

.delete-button {
  @apply text-gray-400 hover:text-red-600 transition-colors flex-shrink-0 p-2 -mr-2;
}

.load-more-container {
  @apply flex justify-center mt-4;
}

.btn-load-more {
  @apply px-6 py-2.5 bg-white text-gray-700 font-medium rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed;
}

/* Processing & Error */
.processing-overlay {
  @apply fixed inset-0 z-50 bg-black bg-opacity-70 flex items-center justify-center;
}

.processing-content {
  @apply max-w-sm mx-auto px-4 text-center;
}

.progress-bar {
  @apply w-full h-2 bg-gray-700 rounded-full overflow-hidden mt-4;
}

.progress-fill {
  @apply h-full bg-primary-500 transition-all duration-300;
}

.error-message {
  @apply fixed bottom-20 left-4 right-4 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3 shadow-lg z-40;
}
</style>
