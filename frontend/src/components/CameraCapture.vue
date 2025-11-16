<template>
  <div class="camera-capture">
    <!-- Loading State -->
    <div v-if="!isActive && !error && !capturedImage" class="loading-state">
      <div class="loading-content">
        <svg class="animate-spin w-12 h-12 text-white mb-4" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="text-white text-lg mb-6">Requesting camera access...</p>
        <button @click="closeCamera" class="btn-secondary">
          Cancel
        </button>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error && !capturedImage" class="error-state">
      <div class="error-content">
        <svg class="w-16 h-16 text-red-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <h3 class="text-xl font-semibold text-white mb-2">Camera Access Failed</h3>
        <p class="text-white text-center mb-6 max-w-md">{{ error }}</p>
        <button @click="closeCamera" class="btn-primary">
          Use Upload Instead
        </button>
      </div>
    </div>

    <!-- Camera View -->
    <div v-if="isActive" class="camera-container">
      <video
        ref="videoElement"
        autoplay
        playsinline
        class="camera-video"
        :class="{ 'mirror': facingMode === 'user' }"
      ></video>

      <!-- Camera Controls -->
      <div class="camera-controls">
        <button
          @click="switchCamera"
          v-if="hasMultipleCameras"
          class="control-btn"
          :disabled="isSwitching"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>

        <button
          @click="capturePhoto"
          class="capture-btn"
          :disabled="isCapturing"
        >
          <div class="capture-btn-inner"></div>
        </button>

        <button
          @click="closeCamera"
          class="control-btn"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Camera Error -->
      <div v-if="error" class="camera-error">
        {{ error }}
      </div>
    </div>

    <!-- Preview Mode -->
    <div v-else-if="capturedImage" class="preview-container">
      <img :src="capturedImage" alt="Captured" class="preview-image" />

      <div class="preview-controls">
        <button @click="retake" class="btn-secondary">
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Retake
        </button>

        <button @click="confirmCapture" class="btn-primary">
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          Use Photo
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import cameraService from '@/services/camera'

const emit = defineEmits(['capture', 'close'])

// State
const videoElement = ref(null)
const isActive = ref(false)
const capturedImage = ref(null)
const capturedBlob = ref(null)
const error = ref(null)
const facingMode = ref('environment') // 'user' or 'environment'
const hasMultipleCameras = ref(false)
const isSwitching = ref(false)
const isCapturing = ref(false)

// Methods
async function initCamera() {
  try {
    error.value = null
    const hasCamera = await cameraService.checkCameraAvailability()
    
    if (!hasCamera) {
      error.value = 'No camera found on this device'
      return
    }

    hasMultipleCameras.value = cameraService.capabilities.hasMultipleCameras

    const stream = await cameraService.requestCameraAccess(facingMode.value)
    
    if (videoElement.value) {
      videoElement.value.srcObject = stream
      isActive.value = true
    }
  } catch (err) {
    error.value = err.message
    console.error('Camera initialization error:', err)
  }
}

async function switchCamera() {
  if (isSwitching.value) return
  
  isSwitching.value = true
  facingMode.value = facingMode.value === 'user' ? 'environment' : 'user'
  
  cameraService.stopCamera()
  await initCamera()
  
  isSwitching.value = false
}

async function capturePhoto() {
  if (!videoElement.value || isCapturing.value) return
  
  try {
    isCapturing.value = true
    const blob = await cameraService.captureImage(videoElement.value)
    
    capturedBlob.value = blob
    capturedImage.value = URL.createObjectURL(blob)
    
    cameraService.stopCamera()
    isActive.value = false
  } catch (err) {
    error.value = 'Failed to capture photo'
    console.error('Capture error:', err)
  } finally {
    isCapturing.value = false
  }
}

function retake() {
  if (capturedImage.value) {
    URL.revokeObjectURL(capturedImage.value)
  }
  capturedImage.value = null
  capturedBlob.value = null
  initCamera()
}

function confirmCapture() {
  if (capturedBlob.value) {
    const file = new File([capturedBlob.value], 'camera-capture.jpg', {
      type: 'image/jpeg'
    })
    emit('capture', file)
  }
}

function closeCamera() {
  cameraService.stopCamera()
  emit('close')
}

// Lifecycle
onMounted(() => {
  initCamera()
})

onUnmounted(() => {
  cameraService.stopCamera()
  if (capturedImage.value) {
    URL.revokeObjectURL(capturedImage.value)
  }
})
</script>

<style scoped>
.camera-capture {
  @apply w-full h-full bg-black;
}

.loading-state,
.error-state {
  @apply w-full h-full flex items-center justify-center bg-black;
}

.loading-content,
.error-content {
  @apply flex flex-col items-center justify-center px-6 text-center;
}

.camera-container {
  @apply relative w-full h-full flex flex-col items-center justify-center;
}

.camera-video {
  @apply w-full h-full object-cover;
}

.camera-video.mirror {
  @apply scale-x-[-1];
}

.camera-controls {
  @apply absolute bottom-8 left-0 right-0 flex items-center justify-center gap-8 px-4;
}

.control-btn {
  @apply w-14 h-14 rounded-full bg-white bg-opacity-30 backdrop-blur-sm flex items-center justify-center text-white transition-all duration-200 active:scale-95 disabled:opacity-50;
}

.capture-btn {
  @apply w-20 h-20 rounded-full bg-white bg-opacity-30 backdrop-blur-sm flex items-center justify-center transition-all duration-200 active:scale-95 disabled:opacity-50;
}

.capture-btn-inner {
  @apply w-16 h-16 rounded-full bg-white border-4 border-gray-300;
}

.camera-error {
  @apply absolute top-4 left-4 right-4 bg-red-500 text-white px-4 py-3 rounded-lg text-sm;
}

.preview-container {
  @apply relative w-full h-full bg-black flex flex-col;
}

.preview-image {
  @apply flex-1 w-full h-full object-contain;
}

.preview-controls {
  @apply absolute bottom-8 left-0 right-0 flex items-center justify-center gap-4 px-4;
}
</style>

