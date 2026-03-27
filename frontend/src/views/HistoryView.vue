<template>
  <div class="history-view">
    <!-- Header -->
    <div class="header">
      <h1 class="page-title">Scan History</h1>
      <p class="page-subtitle">View your previous scans</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading && !scanHistory.length" class="loading-container">
      <LoadingSpinner size="lg" message="Loading history..." />
    </div>

    <!-- Empty State -->
    <div v-else-if="!loading && !scanHistory.length" class="empty-state">
      <svg class="w-24 h-24 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <h2 class="text-xl font-semibold text-gray-900 mb-2">No Scans Yet</h2>
      <p class="text-gray-600 mb-6">Start scanning ingredient labels to see your history</p>
      <router-link to="/scan" class="btn-primary">
        Start Scanning
      </router-link>
    </div>

    <!-- History List -->
    <div v-else class="history-container">
      <div class="history-list">
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

            <div v-if="scan.analysis" class="history-tags">
              <span v-if="scan.analysis.is_vegan" class="tag tag-green">Vegan</span>
              <span v-if="scan.analysis.is_vegetarian" class="tag tag-blue">Vegetarian</span>
              <span v-if="scan.analysis.allergens?.length" class="tag tag-red">
                Contains Allergens
              </span>
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
      </div>

      <!-- Load More Button -->
      <div v-if="hasMore" class="load-more-container">
        <button
          @click="loadMore"
          :disabled="loading"
          class="btn-secondary"
        >
          {{ loading ? 'Loading...' : 'Load More' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useScanStore } from '@/stores/scan'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const router = useRouter()
const scanStore = useScanStore()

const loading = ref(false)
const hasMore = ref(true)
const currentOffset = ref(0)
const pageSize = 20

const scanHistory = computed(() => scanStore.scanHistory)

onMounted(async () => {
  await loadHistory()
})

async function loadHistory() {
  loading.value = true
  try {
    const results = await scanStore.fetchScanHistory(pageSize, currentOffset.value)
    if (results.length < pageSize) {
      hasMore.value = false
    }
  } catch (error) {
    console.error('Failed to load history:', error)
  } finally {
    loading.value = false
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
  if (!ingredients?.length) return 0
  if (ingredients.length === 1 && typeof ingredients[0] === 'string') {
    const raw = ingredients[0]
    const m = raw.match(/^INGREDIENTS:\s*(.*)$/i)
    const body = (m ? m[1] : raw).trim()
    const parts = body.split(',').map((s) => s.trim()).filter(Boolean)
    return parts.length || 1
  }
  return ingredients.length
}
</script>

<style scoped>
.history-view {
  @apply min-h-screen bg-gray-50 pb-20;
}

.header {
  @apply bg-white border-b border-gray-200 px-4 py-6;
}

.page-title {
  @apply text-2xl font-bold text-gray-900 mb-2;
}

.page-subtitle {
  @apply text-gray-600;
}

.loading-container {
  @apply flex items-center justify-center min-h-screen;
}

.empty-state {
  @apply flex flex-col items-center justify-center min-h-screen px-4 text-center;
}

.history-container {
  @apply max-w-4xl mx-auto px-4 py-6;
}

.history-list {
  @apply space-y-4;
}

.history-item {
  @apply bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex gap-4 cursor-pointer hover:shadow-md transition-all duration-200 active:scale-95;
}

.history-image {
  @apply w-20 h-20 rounded-lg overflow-hidden bg-gray-100 flex-shrink-0;
}

.image-placeholder {
  @apply w-full h-full flex items-center justify-center;
}

.history-content {
  @apply flex-1 min-w-0;
}

.history-meta {
  @apply flex items-center gap-2 mb-2;
}

.history-date {
  @apply text-sm text-gray-500;
}

.history-badge {
  @apply text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full;
}

.history-text {
  @apply text-sm text-gray-700 mb-2 line-clamp-2;
}

.history-tags {
  @apply flex flex-wrap gap-2;
}

.tag {
  @apply text-xs px-2 py-1 rounded-full font-medium;
}

.tag-green {
  @apply bg-green-100 text-green-700;
}

.tag-blue {
  @apply bg-blue-100 text-blue-700;
}

.tag-red {
  @apply bg-red-100 text-red-700;
}

.delete-button {
  @apply text-gray-400 hover:text-red-600 transition-colors flex-shrink-0 p-2 -mr-2;
}

.load-more-container {
  @apply flex justify-center mt-8;
}
</style>

