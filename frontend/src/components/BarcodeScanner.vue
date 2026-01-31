<template>
  <div class="barcode-scanner">
    <!-- Scanner View -->
    <div v-if="isScanning" class="scanner-container">
      <div id="barcode-reader" class="reader"></div>
      <button @click="stopScanning" class="stop-button">
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
        Stop Scanner
      </button>
    </div>

    <!-- Start Scanner / Manual Entry -->
    <div v-else class="entry-container">
      <div class="scan-option">
        <div class="barcode-icon-container">
          <svg class="w-24 h-24 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" 
              d="M3 4h3v16H3V4zm5 0h1v16H8V4zm3 0h2v16h-2V4zm4 0h1v16h-1V4zm3 0h3v16h-3V4z" />
          </svg>
        </div>
        
        <h3 class="text-xl font-bold text-gray-900 mb-2">
          Scan Barcode
        </h3>
        
        <p class="text-gray-600 mb-6 text-center max-w-md">
          Scan a product barcode to instantly get ingredient information from our database
        </p>

        <button @click="startScanning" class="scan-button">
          <svg class="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
              d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z" />
          </svg>
          Open Barcode Scanner
        </button>
      </div>

      <!-- Divider -->
      <div class="divider">
        <span class="divider-text">or enter manually</span>
      </div>

      <!-- Manual Entry -->
      <div class="manual-entry">
        <label for="barcode-input" class="label">Enter Barcode Number</label>
        <div class="input-group">
          <input
            id="barcode-input"
            v-model="manualBarcode"
            type="text"
            inputmode="numeric"
            pattern="[0-9]*"
            placeholder="e.g., 3017620422003"
            class="input"
            @keyup.enter="submitManualBarcode"
          />
          <button 
            @click="submitManualBarcode" 
            :disabled="!manualBarcode.trim()"
            class="submit-button"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </button>
        </div>
        <p class="hint">
          Enter the barcode number printed below the barcode lines
        </p>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="error" class="error-message">
      <svg class="w-5 h-5 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p class="flex-1">{{ error }}</p>
      <button @click="error = null" class="text-red-600 hover:text-red-700">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Html5Qrcode } from 'html5-qrcode'

const emit = defineEmits(['scan'])

// State
const isScanning = ref(false)
const manualBarcode = ref('')
const error = ref(null)
let html5Qrcode = null

// Methods
async function startScanning() {
  error.value = null
  
  try {
    html5Qrcode = new Html5Qrcode('barcode-reader')
    isScanning.value = true
    
    // Wait for DOM to update
    await new Promise(resolve => setTimeout(resolve, 100))
    
    const config = {
      fps: 10,
      qrbox: { width: 250, height: 150 },
      aspectRatio: 1.777778,
      formatsToSupport: [
        0,  // QR_CODE
        1,  // AZTEC
        2,  // CODABAR
        3,  // CODE_39
        4,  // CODE_93
        5,  // CODE_128
        6,  // DATA_MATRIX
        7,  // MAXICODE
        8,  // ITF
        9,  // EAN_13
        10, // EAN_8
        11, // PDF_417
        12, // RSS_14
        13, // RSS_EXPANDED
        14, // UPC_A
        15, // UPC_E
        16, // UPC_EAN_EXTENSION
      ]
    }
    
    await html5Qrcode.start(
      { facingMode: 'environment' },
      config,
      onScanSuccess,
      onScanFailure
    )
  } catch (err) {
    console.error('Failed to start scanner:', err)
    error.value = 'Failed to access camera. Please allow camera permissions or enter barcode manually.'
    isScanning.value = false
  }
}

function onScanSuccess(decodedText, decodedResult) {
  console.log('Barcode scanned:', decodedText)
  stopScanning()
  emit('scan', decodedText)
}

function onScanFailure(errorMessage) {
  // Ignore continuous scanning failures (normal when no barcode in view)
}

async function stopScanning() {
  if (html5Qrcode) {
    try {
      await html5Qrcode.stop()
    } catch (err) {
      console.error('Error stopping scanner:', err)
    }
    html5Qrcode = null
  }
  isScanning.value = false
}

function submitManualBarcode() {
  const barcode = manualBarcode.value.trim()
  if (barcode) {
    emit('scan', barcode)
    manualBarcode.value = ''
  }
}

// Cleanup on unmount
onUnmounted(() => {
  stopScanning()
})
</script>

<style scoped>
.barcode-scanner {
  @apply w-full;
}

.scanner-container {
  @apply flex flex-col items-center;
}

.reader {
  @apply w-full max-w-lg rounded-lg overflow-hidden;
}

.stop-button {
  @apply mt-4 flex items-center justify-center bg-red-600 hover:bg-red-700 text-white font-medium px-6 py-3 rounded-lg transition-colors duration-200;
}

.entry-container {
  @apply flex flex-col items-center py-8;
}

.scan-option {
  @apply flex flex-col items-center;
}

.barcode-icon-container {
  @apply mb-4;
}

.scan-button {
  @apply flex items-center justify-center bg-primary-600 hover:bg-primary-700 text-white font-semibold px-8 py-4 rounded-xl shadow-lg transition-all duration-200 active:scale-95;
}

.divider {
  @apply w-full flex items-center justify-center my-8;
}

.divider::before,
.divider::after {
  content: '';
  @apply flex-1 h-px bg-gray-300;
}

.divider-text {
  @apply px-4 text-gray-500 text-sm;
}

.manual-entry {
  @apply w-full max-w-sm;
}

.label {
  @apply block text-sm font-medium text-gray-700 mb-2;
}

.input-group {
  @apply flex gap-2;
}

.input {
  @apply flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-lg tracking-wider;
}

.submit-button {
  @apply px-4 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors duration-200;
}

.hint {
  @apply mt-2 text-sm text-gray-500;
}

.error-message {
  @apply mt-4 w-full max-w-sm bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3;
}
</style>
