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
              class="input-field input-disabled"
              placeholder="username"
              disabled
            />
            <p class="text-gray-500 text-xs mt-1">Username cannot be changed</p>
          </div>

          <!-- Error Message -->
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

      <!-- View Scan History -->
      <router-link to="/scan" class="history-button-card">
        <div class="history-button-icon">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div class="history-button-text">
          <span class="history-button-label">View Scan History</span>
          <span class="history-button-desc">See all your previous scans and results</span>
        </div>
        <svg class="w-5 h-5 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </router-link>

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
                @change="saveDietaryProfile"
                class="preference-checkbox" 
              />
              <span>Vegan</span>
            </label>

            <label class="preference-item">
              <input 
                type="checkbox" 
                v-model="dietaryProfile.vegetarian" 
                @change="saveDietaryProfile"
                class="preference-checkbox" 
              />
              <span>Vegetarian</span>
            </label>

            <label class="preference-item">
              <input 
                type="checkbox" 
                v-model="dietaryProfile.gluten_free" 
                @change="saveDietaryProfile"
                class="preference-checkbox" 
              />
              <span>Gluten-Free</span>
            </label>

            <label class="preference-item">
              <input 
                type="checkbox" 
                v-model="dietaryProfile.dairy_free" 
                @change="saveDietaryProfile"
                class="preference-checkbox" 
              />
              <span>Dairy-Free</span>
            </label>

            <label class="preference-item">
              <input 
                type="checkbox" 
                v-model="dietaryProfile.nut_free" 
                @change="saveDietaryProfile"
                class="preference-checkbox" 
              />
              <span>Nut-Free</span>
            </label>

            <label class="preference-item">
              <input 
                type="checkbox" 
                v-model="dietaryProfile.halal" 
                @change="saveDietaryProfile"
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

          <!-- Error Message -->
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

      <!-- Options -->
      <div class="card mb-6">
        <h3 class="section-title mb-4">Options</h3>

        <div class="llm-toggle-container space-y-4">
          <!-- LLM Ingredient Extractor -->
          <label class="llm-toggle-item">
            <input 
              type="checkbox" 
              v-model="dietaryProfile.use_llm_ingredient_extractor" 
              @change="handleOptionsToggleChange"
              class="preference-checkbox" 
              :disabled="isSavingOptions"
            />
            <div class="toggle-content">
              <span class="toggle-label">Enable LLM Ingredient Extractor</span>
              <span class="toggle-description">Use AI to extract and translate ingredients from scanned text</span>
            </div>
          </label>

          <!-- Mistral OCR -->
          <label class="llm-toggle-item">
            <input 
              type="checkbox" 
              v-model="dietaryProfile.use_mistral_ocr" 
              @change="handleOptionsToggleChange"
              class="preference-checkbox" 
              :disabled="isSavingOptions"
            />
            <div class="toggle-content">
              <span class="toggle-label">Enable Mistral OCR</span>
              <span class="toggle-description">Use cloud-based Mistral OCR for higher-quality text recognition</span>
            </div>
          </label>

          <!-- HF Section Detection -->
          <label class="llm-toggle-item">
            <input 
              type="checkbox" 
              v-model="dietaryProfile.use_hf_section_detection" 
              @change="handleOptionsToggleChange"
              class="preference-checkbox" 
              :disabled="isSavingOptions"
            />
            <div class="toggle-content">
              <span class="toggle-label">Enable HF Ingredient Detection</span>
              <span class="toggle-description">Use a NER model to detect ingredient sections instead of regex patterns</span>
            </div>
          </label>

          <div v-if="isSavingOptions" class="saving-indicator">
            <svg class="animate-spin h-4 w-4 text-primary-600" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span class="text-sm text-gray-500">Saving...</span>
          </div>
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
import { useNotificationStore } from '@/stores/notification'
import api from '@/services/api'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const router = useRouter()
const authStore = useAuthStore()
const notification = useNotificationStore()

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
  custom_restrictions: [],
  use_llm_ingredient_extractor: false,
  use_mistral_ocr: false,
  use_hf_section_detection: false
})

const newAllergen = ref('')
const newCustomRestriction = ref('')

// Options auto-save state
const isSavingOptions = ref(false)

const isUpdating = ref(false)
const updateError = ref(null)

const isUpdatingDietary = ref(false)
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
      custom_restrictions: profile.custom_restrictions || [],
      use_llm_ingredient_extractor: profile.use_llm_ingredient_extractor || false,
      use_mistral_ocr: profile.use_mistral_ocr || false,
      use_hf_section_detection: profile.use_hf_section_detection || false
    }
  } catch (err) {
    dietaryUpdateError.value = err.message || 'Failed to load dietary profile'
  } finally {
    isLoadingDietary.value = false
  }
}

async function handleUpdateProfile() {
  isUpdating.value = true
  updateError.value = null

  try {
    const success = await authStore.updateProfile({
      full_name: profileData.value.fullName,
      email: profileData.value.email
    })

    if (success) {
      notification.success('Profile updated successfully')
    } else {
      updateError.value = authStore.error || 'Failed to update profile'
      notification.error(updateError.value)
    }
  } catch (err) {
    updateError.value = err.message || 'Failed to update profile'
    notification.error(updateError.value)
  } finally {
    isUpdating.value = false
  }
}

async function handleUpdateDietaryProfile() {
  isUpdatingDietary.value = true
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
      custom_restrictions: dietaryProfile.value.custom_restrictions,
      use_llm_ingredient_extractor: dietaryProfile.value.use_llm_ingredient_extractor,
      use_mistral_ocr: dietaryProfile.value.use_mistral_ocr,
      use_hf_section_detection: dietaryProfile.value.use_hf_section_detection
    }

    await api.post('/dietary-profiles/custom', profileData)
    notification.success('Dietary preferences saved')
  } catch (err) {
    dietaryUpdateError.value = err.message || 'Failed to update dietary preferences'
    notification.error(dietaryUpdateError.value)
  } finally {
    isUpdatingDietary.value = false
  }
}

function addAllergen() {
  const allergen = newAllergen.value.trim()
  if (allergen && !dietaryProfile.value.allergens.includes(allergen)) {
    dietaryProfile.value.allergens.push(allergen)
    newAllergen.value = ''
    saveDietaryProfile()
  }
}

function removeAllergen(index) {
  dietaryProfile.value.allergens.splice(index, 1)
  saveDietaryProfile()
}

function addCustomRestriction() {
  const restriction = newCustomRestriction.value.trim()
  if (restriction && !dietaryProfile.value.custom_restrictions.includes(restriction)) {
    dietaryProfile.value.custom_restrictions.push(restriction)
    newCustomRestriction.value = ''
    saveDietaryProfile()
  }
}

function removeCustomRestriction(index) {
  dietaryProfile.value.custom_restrictions.splice(index, 1)
  saveDietaryProfile()
}

async function saveDietaryProfile() {
  try {
    const profileData = {
      halal: dietaryProfile.value.halal,
      gluten_free: dietaryProfile.value.gluten_free,
      vegetarian: dietaryProfile.value.vegetarian,
      vegan: dietaryProfile.value.vegan,
      nut_free: dietaryProfile.value.nut_free,
      dairy_free: dietaryProfile.value.dairy_free,
      allergens: dietaryProfile.value.allergens,
      custom_restrictions: dietaryProfile.value.custom_restrictions,
      use_llm_ingredient_extractor: dietaryProfile.value.use_llm_ingredient_extractor,
      use_mistral_ocr: dietaryProfile.value.use_mistral_ocr,
      use_hf_section_detection: dietaryProfile.value.use_hf_section_detection
    }

    await api.post('/dietary-profiles/custom', profileData)
    notification.success('Changes saved')
  } catch (err) {
    notification.error('Failed to save changes')
  }
}

async function handleOptionsToggleChange() {
  isSavingOptions.value = true

  // Snapshot current toggle values so we can revert on failure
  const prevLlm = dietaryProfile.value.use_llm_ingredient_extractor
  const prevMistralOcr = dietaryProfile.value.use_mistral_ocr
  const prevHfSection = dietaryProfile.value.use_hf_section_detection

  try {
    const profileData = {
      halal: dietaryProfile.value.halal,
      gluten_free: dietaryProfile.value.gluten_free,
      vegetarian: dietaryProfile.value.vegetarian,
      vegan: dietaryProfile.value.vegan,
      nut_free: dietaryProfile.value.nut_free,
      dairy_free: dietaryProfile.value.dairy_free,
      allergens: dietaryProfile.value.allergens,
      custom_restrictions: dietaryProfile.value.custom_restrictions,
      use_llm_ingredient_extractor: dietaryProfile.value.use_llm_ingredient_extractor,
      use_mistral_ocr: dietaryProfile.value.use_mistral_ocr,
      use_hf_section_detection: dietaryProfile.value.use_hf_section_detection
    }

    await api.post('/dietary-profiles/custom', profileData)
    notification.success('Changes saved')
  } catch (err) {
    dietaryProfile.value.use_llm_ingredient_extractor = prevLlm
    dietaryProfile.value.use_mistral_ocr = prevMistralOcr
    dietaryProfile.value.use_hf_section_detection = prevHfSection
    notification.error('Failed to save changes')
  } finally {
    isSavingOptions.value = false
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

.input-disabled {
  @apply bg-gray-100 text-gray-500 cursor-not-allowed;
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

.history-button-card {
  @apply flex items-center gap-4 w-full mb-6 px-5 py-4 bg-gradient-to-r from-primary-50 to-blue-50 
         rounded-xl shadow-sm border-2 border-primary-200 hover:border-primary-400 hover:shadow-md 
         transition-all duration-200 no-underline;
}

.history-button-icon {
  @apply flex-shrink-0 w-11 h-11 rounded-full bg-primary-600 text-white flex items-center justify-center shadow;
}

.history-button-text {
  @apply flex-1 flex flex-col;
}

.history-button-label {
  @apply text-base font-semibold text-gray-900;
}

.history-button-desc {
  @apply text-xs text-gray-500 mt-0.5;
}

.logout-button {
  @apply w-full flex items-center justify-center gap-2 px-6 py-3 bg-red-50 text-red-600 font-medium rounded-lg hover:bg-red-100 transition-colors;
}

/* LLM Extractor Styles */
.llm-toggle-container {
  @apply bg-gray-50 rounded-lg p-4;
}

.saving-indicator {
  @apply flex items-center gap-2 mt-2;
}

.llm-toggle-item {
  @apply flex items-start gap-3 cursor-pointer;
}

.toggle-content {
  @apply flex flex-col;
}

.toggle-label {
  @apply font-medium text-gray-900;
}

.toggle-description {
  @apply text-sm text-gray-500 mt-0.5;
}

</style>

