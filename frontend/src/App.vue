<template>
  <div id="app" class="min-h-screen flex flex-col">
    <!-- Main Content -->
    <main class="flex-1 pb-20">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Bottom Navigation (Mobile) -->
    <nav class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 safe-area-bottom z-50">
      <div class="max-w-md mx-auto px-4">
        <div class="flex justify-around items-center h-16">
          <router-link
            to="/"
            class="nav-item"
            :class="{ active: $route.path === '/' }"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            <span class="text-xs mt-1">Home</span>
          </router-link>

          <router-link
            to="/scan"
            class="nav-item-scan"
          >
            <div class="bg-primary-600 rounded-full p-4 -mt-6 shadow-lg">
              <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
          </router-link>

          <router-link
            to="/history"
            class="nav-item"
            :class="{ active: $route.path === '/history' }"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-xs mt-1">History</span>
          </router-link>
        </div>
      </div>
    </nav>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

onMounted(() => {
  // Initialize auth from localStorage
  authStore.initAuth()
})
</script>

<style scoped>
.nav-item {
  @apply flex flex-col items-center justify-center text-gray-500 transition-colors duration-200 py-2 px-4;
}

.nav-item.active {
  @apply text-primary-600;
}

.nav-item-scan {
  @apply flex items-center justify-center;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* iOS safe area support */
.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
}
</style>

