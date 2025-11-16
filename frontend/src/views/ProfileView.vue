<template>
  <div class="profile-view">
    <!-- Header -->
    <div class="header">
      <h1 class="page-title">Profile</h1>
      <p class="page-subtitle">Manage your account settings</p>
    </div>

    <div class="profile-container">
      <!-- User Info Card -->
      <div class="card mb-6">
        <div class="profile-header">
          <div class="avatar">
            <svg class="w-16 h-16 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd" />
            </svg>
          </div>
          <div class="profile-info">
            <h2 class="profile-name">{{ user?.full_name || user?.username || 'User' }}</h2>
            <p class="profile-email">{{ user?.email }}</p>
          </div>
        </div>
      </div>

      <!-- Edit Profile Form -->
      <div class="card mb-6">
        <h3 class="section-title mb-4">Account Information</h3>
        
        <form @submit.prevent="handleUpdateProfile" class="profile-form">
          <div class="form-group">
            <label class="form-label">Full Name</label>
            <input
              v-model="profileData.fullName"
              type="text"
              class="input-field"
              placeholder="Your full name"
            />
          </div>

          <div class="form-group">
            <label class="form-label">Email</label>
            <input
              v-model="profileData.email"
              type="email"
              class="input-field"
              placeholder="your.email@example.com"
            />
          </div>

          <div class="form-group">
            <label class="form-label">Username</label>
            <input
              v-model="profileData.username"
              type="text"
              class="input-field"
              placeholder="username"
            />
          </div>

          <!-- Success/Error Messages -->
          <div v-if="updateSuccess" class="success-alert">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            Profile updated successfully!
          </div>

          <div v-if="updateError" class="error-alert">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
            {{ updateError }}
          </div>

          <button
            type="submit"
            :disabled="isUpdating"
            class="btn-primary w-full"
          >
            {{ isUpdating ? 'Saving...' : 'Save Changes' }}
          </button>
        </form>
      </div>

      <!-- Dietary Preferences (Optional for future) -->
      <div class="card mb-6">
        <h3 class="section-title mb-4">Dietary Preferences</h3>
        <p class="text-gray-600 text-sm mb-4">
          Set your dietary preferences to get personalized alerts
        </p>

        <div class="preferences-grid">
          <label class="preference-item">
            <input type="checkbox" v-model="preferences.vegan" class="preference-checkbox" />
            <span>Vegan</span>
          </label>

          <label class="preference-item">
            <input type="checkbox" v-model="preferences.vegetarian" class="preference-checkbox" />
            <span>Vegetarian</span>
          </label>

          <label class="preference-item">
            <input type="checkbox" v-model="preferences.glutenFree" class="preference-checkbox" />
            <span>Gluten-Free</span>
          </label>

          <label class="preference-item">
            <input type="checkbox" v-model="preferences.dairyFree" class="preference-checkbox" />
            <span>Dairy-Free</span>
          </label>
        </div>
      </div>

      <!-- Logout Button -->
      <div class="card">
        <button
          @click="handleLogout"
          class="logout-button"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Sign Out
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const user = computed(() => authStore.user)

const profileData = ref({
  fullName: '',
  email: '',
  username: ''
})

const preferences = ref({
  vegan: false,
  vegetarian: false,
  glutenFree: false,
  dairyFree: false
})

const isUpdating = ref(false)
const updateSuccess = ref(false)
const updateError = ref(null)

onMounted(() => {
  if (user.value) {
    profileData.value = {
      fullName: user.value.full_name || '',
      email: user.value.email || '',
      username: user.value.username || ''
    }
  }
})

async function handleUpdateProfile() {
  isUpdating.value = true
  updateSuccess.value = false
  updateError.value = null

  try {
    const success = await authStore.updateProfile({
      full_name: profileData.value.fullName,
      email: profileData.value.email,
      username: profileData.value.username
    })

    if (success) {
      updateSuccess.value = true
      setTimeout(() => {
        updateSuccess.value = false
      }, 3000)
    } else {
      updateError.value = authStore.error || 'Failed to update profile'
    }
  } catch (err) {
    updateError.value = err.message || 'Failed to update profile'
  } finally {
    isUpdating.value = false
  }
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.profile-view {
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

.profile-container {
  @apply max-w-2xl mx-auto px-4 py-6;
}

.card {
  @apply bg-white rounded-xl shadow-sm border border-gray-200 p-6;
}

.profile-header {
  @apply flex items-center gap-4;
}

.avatar {
  @apply w-20 h-20 rounded-full bg-gray-100 flex items-center justify-center;
}

.profile-info {
  @apply flex-1;
}

.profile-name {
  @apply text-xl font-semibold text-gray-900 mb-1;
}

.profile-email {
  @apply text-gray-600;
}

.section-title {
  @apply text-lg font-semibold text-gray-900;
}

.profile-form {
  @apply space-y-4;
}

.form-group {
  @apply space-y-2;
}

.form-label {
  @apply block text-sm font-medium text-gray-700;
}

.success-alert {
  @apply flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm;
}

.error-alert {
  @apply flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm;
}

.preferences-grid {
  @apply grid grid-cols-2 gap-3;
}

.preference-item {
  @apply flex items-center gap-2 cursor-pointer;
}

.preference-checkbox {
  @apply w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500;
}

.logout-button {
  @apply w-full flex items-center justify-center gap-2 px-6 py-3 bg-red-50 text-red-600 font-medium rounded-lg hover:bg-red-100 transition-colors;
}
</style>

