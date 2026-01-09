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

      <!-- Dietary Preferences -->
      <div class="card mb-6">
        <h3 class="section-title mb-4">Dietary Preferences</h3>
        <p class="text-gray-600 text-sm mb-4">
          Set your dietary preferences to get personalized alerts when scanning ingredients
        </p>

        <div v-if="isLoadingDietary" class="loading-state">
          <LoadingSpinner :message="'Loading dietary preferences...'" />
        </div>

        <form v-else @submit.prevent="handleUpdateDietaryProfile" class="dietary-form">
          <!-- Dietary Restrictions Grid -->
          <div class="preferences-grid mb-6">
            <label class="preference-item">
              <input 
                type="checkbox" 
                v-model="dietaryProfile.vegan" 
                class="preference-checkbox" 
              />
              <span>Vegan</span>
            </label>

            <label class="preference-item">
              <input 
                type="checkbox" 
                v-model="dietaryProfile.vegetarian" 
                class="preference-checkbox" 
              />
              <span>Vegetarian</span>
            </label>

            <label class="preference-item">
              <input 
                type="checkbox" 
                v-model="dietaryProfile.gluten_free" 
                class="preference-checkbox" 
              />
              <span>Gluten-Free</span>
            </label>

            <label class="preference-item">
              <input 
                type="checkbox" 
                v-model="dietaryProfile.dairy_free" 
                class="preference-checkbox" 
              />
              <span>Dairy-Free</span>
            </label>

            <label class="preference-item">
              <input 
                type="checkbox" 
                v-model="dietaryProfile.nut_free" 
                class="preference-checkbox" 
              />
              <span>Nut-Free</span>
            </label>

            <label class="preference-item">
              <input 
                type="checkbox" 
                v-model="dietaryProfile.halal" 
                class="preference-checkbox" 
              />
              <span>Halal</span>
            </label>
          </div>

          <!-- Allergens Section -->
          <div class="form-group mb-6">
            <label class="form-label">Allergens</label>
            <p class="text-gray-500 text-xs mb-2">
              List any allergens you need to avoid (e.g., "peanuts", "shellfish", "soy")
            </p>
            <div class="tags-container">
              <div 
                v-for="(allergen, index) in dietaryProfile.allergens" 
                :key="index"
                class="tag"
              >
                <span>{{ allergen }}</span>
                <button 
                  type="button"
                  @click="removeAllergen(index)"
                  class="tag-remove"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div class="tag-input-container">
                <input
                  v-model="newAllergen"
                  type="text"
                  class="tag-input"
                  placeholder="Add allergen..."
                  @keydown.enter.prevent="addAllergen"
                />
                <button
                  type="button"
                  @click="addAllergen"
                  class="tag-add-btn"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- Custom Restrictions Section -->
          <div class="form-group mb-6">
            <label class="form-label">Custom Restrictions</label>
            <p class="text-gray-500 text-xs mb-2">
              Add any other dietary restrictions or preferences
            </p>
            <div class="tags-container">
              <div 
                v-for="(restriction, index) in dietaryProfile.custom_restrictions" 
                :key="index"
                class="tag"
              >
                <span>{{ restriction }}</span>
                <button 
                  type="button"
                  @click="removeCustomRestriction(index)"
                  class="tag-remove"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div class="tag-input-container">
                <input
                  v-model="newCustomRestriction"
                  type="text"
                  class="tag-input"
                  placeholder="Add restriction..."
                  @keydown.enter.prevent="addCustomRestriction"
                />
                <button
                  type="button"
                  @click="addCustomRestriction"
                  class="tag-add-btn"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- Success/Error Messages -->
          <div v-if="dietaryUpdateSuccess" class="success-alert">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            Dietary preferences updated successfully!
          </div>

          <div v-if="dietaryUpdateError" class="error-alert">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
            {{ dietaryUpdateError }}
          </div>

          <button
            type="submit"
            :disabled="isUpdatingDietary"
            class="btn-primary w-full"
          >
            {{ isUpdatingDietary ? 'Saving...' : 'Save Dietary Preferences' }}
          </button>
        </form>
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
import api from '@/services/api'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const router = useRouter()
const authStore = useAuthStore()

const user = computed(() => authStore.user)

const profileData = ref({
  fullName: '',
  email: '',
  username: ''
})

const dietaryProfile = ref({
  halal: false,
  gluten_free: false,
  vegetarian: false,
  vegan: false,
  nut_free: false,
  dairy_free: false,
  allergens: [],
  custom_restrictions: []
})

const newAllergen = ref('')
const newCustomRestriction = ref('')

const isUpdating = ref(false)
const updateSuccess = ref(false)
const updateError = ref(null)

const isUpdatingDietary = ref(false)
const dietaryUpdateSuccess = ref(false)
const dietaryUpdateError = ref(null)
const isLoadingDietary = ref(false)

onMounted(async () => {
  if (user.value) {
    profileData.value = {
      fullName: user.value.full_name || '',
      email: user.value.email || '',
      username: user.value.username || ''
    }
  }
  
  // Load dietary profile
  await loadDietaryProfile()
})

async function loadDietaryProfile() {
  isLoadingDietary.value = true
  dietaryUpdateError.value = null
  
  try {
    const profile = await api.get('/dietary-profiles')
    dietaryProfile.value = {
      halal: profile.halal || false,
      gluten_free: profile.gluten_free || false,
      vegetarian: profile.vegetarian || false,
      vegan: profile.vegan || false,
      nut_free: profile.nut_free || false,
      dairy_free: profile.dairy_free || false,
      allergens: profile.allergens || [],
      custom_restrictions: profile.custom_restrictions || []
    }
  } catch (err) {
    dietaryUpdateError.value = err.message || 'Failed to load dietary profile'
  } finally {
    isLoadingDietary.value = false
  }
}

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

async function handleUpdateDietaryProfile() {
  isUpdatingDietary.value = true
  dietaryUpdateSuccess.value = false
  dietaryUpdateError.value = null

  try {
    const profileData = {
      halal: dietaryProfile.value.halal,
      gluten_free: dietaryProfile.value.gluten_free,
      vegetarian: dietaryProfile.value.vegetarian,
      vegan: dietaryProfile.value.vegan,
      nut_free: dietaryProfile.value.nut_free,
      dairy_free: dietaryProfile.value.dairy_free,
      allergens: dietaryProfile.value.allergens,
      custom_restrictions: dietaryProfile.value.custom_restrictions
    }

    await api.post('/dietary-profiles/custom', profileData)
    
    dietaryUpdateSuccess.value = true
    setTimeout(() => {
      dietaryUpdateSuccess.value = false
    }, 3000)
  } catch (err) {
    dietaryUpdateError.value = err.message || 'Failed to update dietary preferences'
  } finally {
    isUpdatingDietary.value = false
  }
}

function addAllergen() {
  const allergen = newAllergen.value.trim()
  if (allergen && !dietaryProfile.value.allergens.includes(allergen)) {
    dietaryProfile.value.allergens.push(allergen)
    newAllergen.value = ''
  }
}

function removeAllergen(index) {
  dietaryProfile.value.allergens.splice(index, 1)
}

function addCustomRestriction() {
  const restriction = newCustomRestriction.value.trim()
  if (restriction && !dietaryProfile.value.custom_restrictions.includes(restriction)) {
    dietaryProfile.value.custom_restrictions.push(restriction)
    newCustomRestriction.value = ''
  }
}

function removeCustomRestriction(index) {
  dietaryProfile.value.custom_restrictions.splice(index, 1)
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
  @apply flex items-center gap-2 cursor-pointer p-2 rounded-lg hover:bg-gray-50 transition-colors;
}

.preference-checkbox {
  @apply w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500 cursor-pointer;
}

.dietary-form {
  @apply space-y-4;
}

.tags-container {
  @apply flex flex-wrap gap-2 p-3 border border-gray-300 rounded-lg bg-gray-50 min-h-[60px];
}

.tag {
  @apply inline-flex items-center gap-2 px-3 py-1.5 bg-primary-100 text-primary-800 rounded-full text-sm font-medium;
}

.tag-remove {
  @apply hover:text-primary-900 transition-colors cursor-pointer;
}

.tag-input-container {
  @apply flex items-center gap-2 flex-1 min-w-[200px];
}

.tag-input {
  @apply flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent;
}

.tag-add-btn {
  @apply p-1.5 text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded-lg transition-colors;
}

.loading-state {
  @apply py-8 flex items-center justify-center;
}

.logout-button {
  @apply w-full flex items-center justify-center gap-2 px-6 py-3 bg-red-50 text-red-600 font-medium rounded-lg hover:bg-red-100 transition-colors;
}
</style>

