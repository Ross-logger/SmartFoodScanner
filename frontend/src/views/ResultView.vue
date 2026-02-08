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

      <!-- Analysis Result -->
      <div v-if="scanResult.analysis_result" class="card mb-4">
        <div 
          class="analysis-result-banner"
          :class="scanResult.is_safe ? 'analysis-result-safe' : 'analysis-result-warning'"
        >
          <div class="analysis-result-icon">
            <svg v-if="scanResult.is_safe" class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <svg v-else class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div class="analysis-result-content">
            <h2 class="analysis-result-title">
              {{ scanResult.is_safe ? 'Product is safe' : 'Warning' }}
            </h2>
            <p class="analysis-result-text">{{ scanResult.analysis_result }}</p>
          </div>
        </div>
      </div>

      <!-- Detected Ingredients - Single Consolidated Section -->
      <div class="card mb-4">
        <div class="section-header">
          <h2 class="section-title">Detected Ingredients</h2>
          <button
            v-if="!isEditing"
            @click="startEditing"
            class="edit-button"
            title="Edit ingredients"
          >
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
            Edit
          </button>
        </div>

        <!-- Edit Mode -->
        <div v-if="isEditing" class="edit-mode">
          <p class="edit-hint">Fix misspellings, add or remove ingredients. Analysis will re-run on save.</p>
          <div class="edit-ingredients-list">
            <div
              v-for="(ingredient, index) in editableIngredients"
              :key="index"
              class="edit-ingredient-row"
            >
              <input
                type="text"
                v-model="editableIngredients[index]"
                class="edit-ingredient-input"
                placeholder="Ingredient name"
                @keydown.enter.prevent="addIngredient(index + 1)"
              />
              <button
                @click="removeIngredient(index)"
                class="remove-ingredient-button"
                title="Remove ingredient"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
          <button @click="addIngredient()" class="add-ingredient-button">
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Add Ingredient
          </button>
          <div class="edit-actions">
            <button @click="cancelEditing" class="btn-cancel" :disabled="isSaving">
              Cancel
            </button>
            <button @click="saveIngredients" class="btn-save" :disabled="isSaving">
              <svg v-if="isSaving" class="animate-spin w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              {{ isSaving ? 'Analyzing...' : 'Save & Re-analyze' }}
            </button>
          </div>
        </div>
        
        <!-- View Mode -->
        <div v-else>
          <div v-if="ingredients.length === 0" class="empty-state">
            <p class="text-gray-600">No ingredients detected</p>
          </div>

          <div v-else class="ingredients-list">
            <div
              v-for="(ingredient, index) in ingredients"
              :key="index"
              class="ingredient-item"
              :class="{ 'ingredient-warning': isProhibited(ingredient) || isAllergen(ingredient) }"
            >
              <div class="ingredient-content">
                <span class="ingredient-name">{{ ingredient }}</span>
                <div class="ingredient-badges">
                  <span v-if="isAllergen(ingredient)" class="ingredient-badge allergen-badge">
                    Allergen
                  </span>
                  <span v-if="isProhibited(ingredient)" class="ingredient-badge warning-badge">
                    Not suitable for you
                  </span>
                </div>
              </div>
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
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const scanStore = useScanStore()

const loading = ref(true)
const error = ref(null)
const isEditing = ref(false)
const isSaving = ref(false)
const editableIngredients = ref([])

const scanResult = computed(() => scanStore.currentScan)
const ingredients = computed(() => {
  if (!scanResult.value) return []
  
  // Get ingredients from various possible sources
  let allIngredients = []
  
  // Primary source: ingredients array
  if (scanResult.value.ingredients) {
    if (Array.isArray(scanResult.value.ingredients)) {
      allIngredients = [...scanResult.value.ingredients]
    } else if (typeof scanResult.value.ingredients === 'string') {
      // Handle string format - split by common delimiters
      allIngredients = scanResult.value.ingredients
        .split(/[,;]\s*|\n/)
        .map(ing => ing.trim())
        .filter(ing => ing.length > 0)
    }
  }
  
  // Fallback to corrected_ingredients
  if (allIngredients.length === 0 && scanResult.value.corrected_ingredients) {
    if (Array.isArray(scanResult.value.corrected_ingredients)) {
      allIngredients = [...scanResult.value.corrected_ingredients]
    } else if (typeof scanResult.value.corrected_ingredients === 'string') {
      allIngredients = scanResult.value.corrected_ingredients
        .split(/[,;]\s*|\n/)
        .map(ing => ing.trim())
        .filter(ing => ing.length > 0)
    }
  }
  
  // Add allergens from analysis if they exist and aren't already in the list
  if (scanResult.value.analysis?.allergens) {
    const allergenSet = new Set(allIngredients.map(ing => ing.toLowerCase()))
    scanResult.value.analysis.allergens.forEach(allergen => {
      if (!allergenSet.has(allergen.toLowerCase())) {
        allIngredients.push(allergen)
      }
    })
  }
  
  // Remove duplicates (case-insensitive)
  const uniqueIngredients = []
  const seen = new Set()
  allIngredients.forEach(ing => {
    const lower = ing.toLowerCase().trim()
    if (lower && !seen.has(lower)) {
      seen.add(lower)
      uniqueIngredients.push(ing.trim())
    }
  })
  
  return uniqueIngredients
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

function isAllergen(ingredient) {
  if (!scanResult.value?.analysis?.allergens) return false
  
  // Check if ingredient is in the allergens list (case-insensitive)
  return scanResult.value.analysis.allergens.some(allergen =>
    allergen.toLowerCase() === ingredient.toLowerCase()
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

function startEditing() {
  editableIngredients.value = [...ingredients.value]
  isEditing.value = true
}

function cancelEditing() {
  isEditing.value = false
  editableIngredients.value = []
}

function addIngredient(atIndex) {
  if (atIndex !== undefined) {
    editableIngredients.value.splice(atIndex, 0, '')
  } else {
    editableIngredients.value.push('')
  }
}

function removeIngredient(index) {
  editableIngredients.value.splice(index, 1)
}

async function saveIngredients() {
  // Filter out empty entries
  const cleaned = editableIngredients.value
    .map(ing => ing.trim())
    .filter(ing => ing.length > 0)

  if (cleaned.length === 0) {
    alert('Please add at least one ingredient.')
    return
  }

  isSaving.value = true
  try {
    const scanId = route.params.id
    await scanStore.updateIngredients(scanId, cleaned)
    isEditing.value = false
    editableIngredients.value = []
  } catch (err) {
    alert('Failed to update ingredients: ' + (err.message || 'Unknown error'))
  } finally {
    isSaving.value = false
  }
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

.section-header {
  @apply flex items-center justify-between mb-4;
}

.section-title {
  @apply text-lg font-semibold text-gray-900;
}

.edit-button {
  @apply flex items-center text-sm font-medium text-blue-600 hover:text-blue-800 
         bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-lg transition-colors;
}

.edit-mode {
  @apply mt-2;
}

.edit-hint {
  @apply text-sm text-gray-500 mb-3;
}

.edit-ingredients-list {
  @apply space-y-2 mb-3;
}

.edit-ingredient-row {
  @apply flex items-center gap-2;
}

.edit-ingredient-input {
  @apply flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm
         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
         bg-white;
}

.remove-ingredient-button {
  @apply text-gray-400 hover:text-red-500 p-1.5 rounded-lg hover:bg-red-50 transition-colors flex-shrink-0;
}

.add-ingredient-button {
  @apply flex items-center text-sm font-medium text-gray-600 hover:text-green-700
         bg-gray-50 hover:bg-green-50 border border-dashed border-gray-300 hover:border-green-400
         px-3 py-2 rounded-lg transition-colors w-full justify-center;
}

.edit-actions {
  @apply flex gap-3 mt-4 pt-4 border-t border-gray-200;
}

.btn-cancel {
  @apply flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 
         hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50;
}

.btn-save {
  @apply flex-1 flex items-center justify-center px-4 py-2.5 text-sm font-medium text-white 
         bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-70;
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
  @apply flex items-center justify-between gap-3 flex-wrap;
}

.ingredient-name {
  @apply text-gray-900 font-medium;
}

.ingredient-item.ingredient-warning .ingredient-name {
  @apply text-red-900 font-semibold;
}

.ingredient-badges {
  @apply flex gap-2 flex-wrap;
}

.ingredient-badge {
  @apply text-xs px-3 py-1 rounded-full font-medium;
}

.ingredient-badge.allergen-badge {
  @apply bg-red-600 text-white;
}

.ingredient-badge.warning-badge {
  @apply bg-orange-600 text-white;
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

.analysis-result-banner {
  @apply flex items-start gap-4 p-5 rounded-lg border-2;
}

.analysis-result-safe {
  @apply bg-green-50 border-green-300 text-green-900;
}

.analysis-result-warning {
  @apply bg-red-50 border-red-300 text-red-900;
}

.analysis-result-icon {
  @apply flex-shrink-0;
}

.analysis-result-content {
  @apply flex-1;
}

.analysis-result-title {
  @apply text-lg font-bold mb-2;
}

.analysis-result-text {
  @apply text-base leading-relaxed;
}
</style>

