<template>
  <div class="ingredient-list">
    <div class="mb-4 flex items-center justify-between">
      <h3 class="text-lg font-semibold text-gray-900">
        Detected Ingredients
      </h3>
      <span class="text-sm text-gray-500">
        {{ ingredients.length }} items
      </span>
    </div>

    <div v-if="ingredients.length === 0" class="empty-state">
      <svg class="w-12 h-12 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
      </svg>
      <p class="text-gray-600">No ingredients detected</p>
    </div>

    <div v-else class="ingredients-grid">
      <div
        v-for="(ingredient, index) in ingredients"
        :key="index"
        class="ingredient-item"
        :class="getIngredientClass(ingredient)"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="font-medium text-gray-900">
              {{ ingredient.name || ingredient }}
            </p>
            <p v-if="ingredient.confidence" class="text-xs text-gray-500 mt-1">
              {{ (ingredient.confidence * 100).toFixed(0) }}% confidence
            </p>
          </div>

          <div v-if="showWarnings && ingredient.warning" class="ml-2">
            <span
              class="inline-flex items-center justify-center w-6 h-6 rounded-full"
              :class="getWarningClass(ingredient.warning)"
              :title="ingredient.warning"
            >
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
            </span>
          </div>
        </div>

        <p v-if="ingredient.alternatives && ingredient.alternatives.length" class="text-xs text-gray-500 mt-2">
          Alternatives: {{ ingredient.alternatives.join(', ') }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  ingredients: {
    type: Array,
    default: () => []
  },
  showWarnings: {
    type: Boolean,
    default: true
  },
  highlightAllergens: {
    type: Boolean,
    default: false
  }
})

function getIngredientClass(ingredient) {
  if (!props.highlightAllergens) return ''
  
  const name = typeof ingredient === 'string' ? ingredient : ingredient.name
  const allergens = ['milk', 'egg', 'peanut', 'tree nut', 'soy', 'wheat', 'fish', 'shellfish']
  
  const isAllergen = allergens.some(allergen => 
    name.toLowerCase().includes(allergen)
  )
  
  return isAllergen ? 'border-l-4 border-red-500 bg-red-50' : ''
}

function getWarningClass(warningLevel) {
  const classes = {
    high: 'bg-red-100 text-red-600',
    medium: 'bg-yellow-100 text-yellow-600',
    low: 'bg-blue-100 text-blue-600'
  }
  return classes[warningLevel] || classes.medium
}
</script>

<style scoped>
.ingredient-list {
  @apply w-full;
}

.empty-state {
  @apply flex flex-col items-center justify-center py-12 text-center;
}

.ingredients-grid {
  @apply space-y-2;
}

.ingredient-item {
  @apply bg-white border border-gray-200 rounded-lg p-3 transition-all duration-200 hover:shadow-md;
}
</style>

