<template>
  <div class="result-view">
    <LoadingSpinner v-if="loading" size="lg" message="Loading results..." />

    <div v-else-if="error" class="error-container">
      <svg class="w-16 h-16 text-red-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <h2 class="text-xl font-semibold text-gray-900 mb-2">Error Loading Results</h2>
      <p class="text-gray-600 mb-6">{{ error }}</p>
      <router-link to="/scan" class="btn-primary">
        Try Again
      </router-link>
    </div>

    <div v-else-if="scanResult" class="result-container">
      <!-- Header -->
      <div class="result-header">
        <button @click="$router.back()" class="back-button">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 class="page-title">Scan Results</h1>
        <div class="w-6"></div>
      </div>

      <!-- Scanned Image -->
      <div class="image-section">
        <img
          v-if="scanResult.image_url"
          :src="scanResult.image_url"
          alt="Scanned label"
          class="scanned-image"
        />
      </div>

      <!-- Detected Ingredients -->
      <div class="card mb-4">
        <h2 class="section-title mb-4">Detected Ingredients</h2>
        
        <div v-if="ingredients.length === 0" class="empty-state">
          <p class="text-gray-600">No ingredients detected</p>
        </div>

        <div v-else class="ingredients-list">
          <div
            v-for="(ingredient, index) in ingredients"
            :key="index"
            class="ingredient-item"
            :class="{ 'ingredient-warning': isProhibited(ingredient) }"
          >
            <div class="ingredient-content">
              <span class="ingredient-name">{{ ingredient }}</span>
              <span v-if="isProhibited(ingredient)" class="ingredient-badge">
                Not suitable for you
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Analysis Summary -->
      <div v-if="scanResult.analysis" class="card mb-4">
        <h2 class="section-title mb-4">Dietary Analysis</h2>
        
        <div class="analysis-grid">
          <div class="analysis-item">
            <div class="analysis-label">Allergens Detected</div>
            <div class="analysis-value text-red-600">
              {{ scanResult.analysis.allergens?.length || 0 }}
            </div>
          </div>

          <div class="analysis-item">
            <div class="analysis-label">Vegan Friendly</div>
            <div class="analysis-value" :class="scanResult.analysis.is_vegan ? 'text-green-600' : 'text-gray-600'">
              {{ scanResult.analysis.is_vegan ? 'Yes' : 'No' }}
            </div>
          </div>

          <div class="analysis-item">
            <div class="analysis-label">Vegetarian</div>
            <div class="analysis-value" :class="scanResult.analysis.is_vegetarian ? 'text-green-600' : 'text-gray-600'">
              {{ scanResult.analysis.is_vegetarian ? 'Yes' : 'No' }}
            </div>
          </div>

          <div class="analysis-item">
            <div class="analysis-label">Gluten Free</div>
            <div class="analysis-value" :class="scanResult.analysis.is_gluten_free ? 'text-green-600' : 'text-gray-600'">
              {{ scanResult.analysis.is_gluten_free ? 'Yes' : 'No' }}
            </div>
          </div>
        </div>

        <div v-if="scanResult.analysis.allergens?.length" class="allergen-list mt-4">
          <h3 class="font-semibold text-red-600 mb-2">⚠️ Allergen Warning</h3>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="allergen in scanResult.analysis.allergens"
              :key="allergen"
              class="allergen-badge"
            >
              {{ allergen }}
            </span>
          </div>
        </div>
      </div>

      <!-- Scan Info -->
      <div class="card mb-4">
        <h2 class="section-title mb-4">Scan Information</h2>
        <div class="scan-info">
          <div class="info-row">
            <span class="info-label">Scan Date:</span>
            <span class="info-value">{{ formatDate(scanResult.created_at) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Processing Time:</span>
            <span class="info-value">{{ scanResult.processing_time || 'N/A' }}</span>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="action-buttons">
        <button @click="shareScan" class="btn-secondary">
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
          Share
        </button>

        <router-link to="/scan" class="btn-primary">
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
          </svg>
          Scan Another
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useScanStore } from '@/stores/scan'
import IngredientList from '@/components/IngredientList.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const scanStore = useScanStore()

const loading = ref(true)
const error = ref(null)

const scanResult = computed(() => scanStore.currentScan)
const ingredients = computed(() => {
  if (!scanResult.value) return []
  return scanResult.value.ingredients || scanResult.value.corrected_ingredients || []
})

onMounted(async () => {
  const scanId = route.params.id
  
  try {
    await scanStore.getScanById(scanId)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})

function isProhibited(ingredient) {
  if (!scanResult.value?.warnings) return false
  
  // Check if any warning mentions this ingredient
  return scanResult.value.warnings.some(warning => 
    warning.toLowerCase().includes(ingredient.toLowerCase())
  )
}

function formatDate(dateString) {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function shareScan() {
  if (navigator.share) {
    try {
      await navigator.share({
        title: 'Food Scan Results',
        text: `Scanned ${ingredients.value.length} ingredients`,
        url: window.location.href
      })
    } catch (err) {
      console.log('Share cancelled or failed:', err)
    }
  } else {
    // Fallback: copy link
    navigator.clipboard.writeText(window.location.href)
    alert('Link copied to clipboard!')
  }
}
</script>

<style scoped>
.result-view {
  @apply min-h-screen bg-gray-50 pb-20;
}

.error-container {
  @apply flex flex-col items-center justify-center min-h-screen px-4 text-center;
}

.result-container {
  @apply max-w-4xl mx-auto;
}

.result-header {
  @apply bg-white border-b border-gray-200 px-4 py-4 flex items-center justify-between sticky top-0 z-10;
}

.back-button {
  @apply text-gray-600 hover:text-gray-900 transition-colors;
}

.page-title {
  @apply text-xl font-bold text-gray-900;
}

.image-section {
  @apply px-4 py-6;
}

.scanned-image {
  @apply w-full rounded-xl shadow-lg object-contain;
  max-height: 400px;
}

.card {
  @apply bg-white rounded-xl shadow-sm border border-gray-200 mx-4 p-6;
}

.section-title {
  @apply text-lg font-semibold text-gray-900;
}

.empty-state {
  @apply text-center py-8;
}

.ingredients-list {
  @apply space-y-2;
}

.ingredient-item {
  @apply bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 transition-all duration-200;
}

.ingredient-item.ingredient-warning {
  @apply bg-red-50 border-2 border-red-400;
}

.ingredient-content {
  @apply flex items-center justify-between gap-3;
}

.ingredient-name {
  @apply text-gray-900 font-medium;
}

.ingredient-item.ingredient-warning .ingredient-name {
  @apply text-red-900 font-semibold;
}

.ingredient-badge {
  @apply text-xs bg-red-600 text-white px-3 py-1 rounded-full font-medium;
}

.ocr-text {
  @apply mt-3 p-4 bg-gray-50 rounded-lg text-sm text-gray-700 whitespace-pre-wrap font-mono;
}

.analysis-grid {
  @apply grid grid-cols-2 gap-4;
}

.analysis-item {
  @apply text-center;
}

.analysis-label {
  @apply text-sm text-gray-600 mb-1;
}

.analysis-value {
  @apply text-2xl font-bold;
}

.allergen-list {
  @apply pt-4 border-t border-gray-200;
}

.allergen-badge {
  @apply px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-medium;
}

.scan-info {
  @apply space-y-2;
}

.info-row {
  @apply flex justify-between items-center py-2 border-b border-gray-100 last:border-0;
}

.info-label {
  @apply text-gray-600;
}

.info-value {
  @apply font-medium text-gray-900;
}

.action-buttons {
  @apply px-4 py-6 flex gap-3;
}
</style>

