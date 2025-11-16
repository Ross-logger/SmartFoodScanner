<template>
  <div class="home-view">
    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-content">
        <div class="hero-icon">
          <svg class="w-20 h-20 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        
        <h1 class="hero-title">
          Smart Food Scanner
        </h1>
        
        <p class="hero-subtitle">
          Scan ingredient labels instantly with AI-powered OCR and get dietary analysis
        </p>

        <div v-if="!isAuthenticated" class="hero-actions">
          <router-link to="/login" class="btn-primary">
            Get Started
          </router-link>
          <router-link to="/register" class="btn-secondary">
            Sign Up
          </router-link>
        </div>

        <div v-else class="hero-actions">
          <router-link to="/scan" class="btn-primary text-lg px-8 py-4">
            <svg class="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Start Scanning
          </router-link>
        </div>
      </div>
    </div>

    <!-- Features Section -->
    <div class="features-section">
      <h2 class="section-title">How It Works</h2>
      
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon bg-blue-100 text-blue-600">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            </svg>
          </div>
          <h3 class="feature-title">1. Scan Label</h3>
          <p class="feature-description">
            Take a photo of any food ingredient label using your phone camera
          </p>
        </div>

        <div class="feature-card">
          <div class="feature-icon bg-green-100 text-green-600">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <h3 class="feature-title">2. AI Analysis</h3>
          <p class="feature-description">
            Advanced OCR and ML models extract and correct ingredient text
          </p>
        </div>

        <div class="feature-card">
          <div class="feature-icon bg-purple-100 text-purple-600">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
          </div>
          <h3 class="feature-title">3. Get Results</h3>
          <p class="feature-description">
            View organized ingredient list with dietary information and allergen warnings
          </p>
        </div>
      </div>
    </div>

    <!-- Stats Section (if authenticated) -->
    <div v-if="isAuthenticated" class="stats-section">
      <h2 class="section-title">Your Activity</h2>
      
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ recentScans }}</div>
          <div class="stat-label">Recent Scans</div>
        </div>
        
        <div class="stat-card">
          <div class="stat-value">{{ totalScans }}</div>
          <div class="stat-label">Total Scans</div>
        </div>
      </div>

      <router-link to="/history" class="view-history-link">
        View Full History →
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useScanStore } from '@/stores/scan'

const authStore = useAuthStore()
const scanStore = useScanStore()

const isAuthenticated = computed(() => authStore.isAuthenticated)
const recentScans = ref(0)
const totalScans = ref(0)

onMounted(async () => {
  if (isAuthenticated.value) {
    try {
      await scanStore.fetchScanHistory(5, 0)
      recentScans.value = scanStore.scanHistory.length
      totalScans.value = scanStore.scanHistory.length // In production, get from API
    } catch (error) {
      console.error('Failed to load scan stats:', error)
    }
  }
})
</script>

<style scoped>
.home-view {
  @apply min-h-screen bg-gradient-to-b from-white to-gray-50;
}

.hero-section {
  @apply px-4 py-16 max-w-4xl mx-auto text-center;
}

.hero-content {
  @apply space-y-6;
}

.hero-icon {
  @apply flex justify-center mb-6;
}

.hero-title {
  @apply text-4xl md:text-5xl font-bold text-gray-900;
}

.hero-subtitle {
  @apply text-lg md:text-xl text-gray-600 max-w-2xl mx-auto;
}

.hero-actions {
  @apply flex flex-col sm:flex-row gap-4 justify-center items-center pt-4;
}

.features-section {
  @apply px-4 py-12 max-w-6xl mx-auto;
}

.section-title {
  @apply text-3xl font-bold text-gray-900 text-center mb-12;
}

.features-grid {
  @apply grid grid-cols-1 md:grid-cols-3 gap-8;
}

.feature-card {
  @apply bg-white rounded-xl p-6 shadow-sm border border-gray-200 text-center hover:shadow-md transition-shadow duration-200;
}

.feature-icon {
  @apply w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4;
}

.feature-title {
  @apply text-xl font-semibold text-gray-900 mb-2;
}

.feature-description {
  @apply text-gray-600;
}

.stats-section {
  @apply px-4 py-12 max-w-4xl mx-auto text-center;
}

.stats-grid {
  @apply grid grid-cols-2 gap-6 mb-6;
}

.stat-card {
  @apply bg-white rounded-xl p-6 shadow-sm border border-gray-200;
}

.stat-value {
  @apply text-4xl font-bold text-primary-600 mb-2;
}

.stat-label {
  @apply text-gray-600 text-sm;
}

.view-history-link {
  @apply inline-block text-primary-600 font-medium hover:text-primary-700 transition-colors;
}
</style>

