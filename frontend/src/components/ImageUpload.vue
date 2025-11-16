<template>
  <div class="image-upload">
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      capture="environment"
      @change="handleFileSelect"
      class="hidden"
    />

    <div
      v-if="!preview"
      @click="triggerFileInput"
      class="upload-area"
      :class="{ 'drag-over': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <svg class="w-16 h-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>

      <p class="text-lg font-medium text-gray-700 mb-2">
        {{ isMobile ? 'Tap to take photo or choose from gallery' : 'Click to upload or drag image here' }}
      </p>
      <p class="text-sm text-gray-500">
        Supports: JPG, PNG, WebP
      </p>
    </div>

    <div v-else class="preview-container">
      <img :src="preview" alt="Preview" class="preview-image" />

      <div class="preview-actions">
        <button @click="clearImage" class="btn-secondary">
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          Remove
        </button>

        <button @click="confirmUpload" class="btn-primary">
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Scan This Image
        </button>
      </div>
    </div>

    <p v-if="error" class="text-red-600 text-sm mt-2">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import cameraService from '@/services/camera'

const emit = defineEmits(['upload'])

// State
const fileInput = ref(null)
const preview = ref(null)
const selectedFile = ref(null)
const isDragging = ref(false)
const error = ref(null)

// Computed
const isMobile = computed(() => {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
})

// Methods
function triggerFileInput() {
  fileInput.value?.click()
}

async function handleFileSelect(event) {
  const file = event.target.files?.[0]
  if (file) {
    await processFile(file)
  }
}

async function handleDrop(event) {
  isDragging.value = false
  const file = event.dataTransfer.files?.[0]
  if (file) {
    await processFile(file)
  }
}

async function processFile(file) {
  error.value = null

  // Validate file type
  if (!file.type.startsWith('image/')) {
    error.value = 'Please select a valid image file'
    return
  }

  // Validate file size (max 10MB)
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    error.value = 'Image size must be less than 10MB'
    return
  }

  try {
    // Compress image if needed
    const compressedBlob = await cameraService.compressImage(file)
    const compressedFile = new File([compressedBlob], file.name, {
      type: 'image/jpeg'
    })

    selectedFile.value = compressedFile
    preview.value = URL.createObjectURL(compressedFile)
  } catch (err) {
    error.value = 'Failed to process image'
    console.error('Image processing error:', err)
  }
}

function clearImage() {
  if (preview.value) {
    URL.revokeObjectURL(preview.value)
  }
  preview.value = null
  selectedFile.value = null
  error.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function confirmUpload() {
  if (selectedFile.value) {
    emit('upload', selectedFile.value)
  }
}

// Cleanup
onUnmounted(() => {
  if (preview.value) {
    URL.revokeObjectURL(preview.value)
  }
})
</script>

<style scoped>
.image-upload {
  @apply w-full;
}

.upload-area {
  @apply w-full p-8 border-2 border-dashed border-gray-300 rounded-xl flex flex-col items-center justify-center cursor-pointer transition-all duration-200 hover:border-primary-500 hover:bg-primary-50 active:scale-95;
  min-height: 300px;
}

.upload-area.drag-over {
  @apply border-primary-500 bg-primary-50;
}

.preview-container {
  @apply w-full space-y-4;
}

.preview-image {
  @apply w-full rounded-xl shadow-lg object-contain;
  max-height: 500px;
}

.preview-actions {
  @apply flex gap-3 justify-center;
}

@media (max-width: 640px) {
  .preview-actions {
    @apply flex-col;
  }
}
</style>

