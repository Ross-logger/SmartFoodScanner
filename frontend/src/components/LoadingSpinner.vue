<template>
  <div class="loading-spinner" :class="sizeClass">
    <div class="spinner" :class="colorClass"></div>
    <p v-if="message" class="loading-message" :class="textSizeClass">
      {{ message }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: {
    type: String,
    default: ''
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },
  color: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'white', 'gray'].includes(value)
  }
})

const sizeClass = computed(() => {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16'
  }
  return sizes[props.size]
})

const colorClass = computed(() => {
  const colors = {
    primary: 'border-primary-600',
    white: 'border-white',
    gray: 'border-gray-600'
  }
  return colors[props.color]
})

const textSizeClass = computed(() => {
  const sizes = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg'
  }
  return sizes[props.size]
})
</script>

<style scoped>
.loading-spinner {
  @apply flex flex-col items-center justify-center gap-3;
}

.spinner {
  @apply rounded-full border-4 border-t-transparent animate-spin;
  width: inherit;
  height: inherit;
}

.loading-message {
  @apply text-gray-700 font-medium text-center;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

