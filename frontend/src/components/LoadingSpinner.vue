<template>
  <div
    class="loading-spinner flex flex-col items-center justify-center gap-3 py-2"
    role="status"
    aria-live="polite"
  >
    <span class="sr-only">{{ message }}</span>
    <div
      class="shrink-0 rounded-full animate-spin"
      :class="spinnerClasses"
      aria-hidden="true"
    />
    <p :class="['text-center text-sm font-medium', textClasses]">{{ message }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: {
    type: String,
    default: 'Analyzing ingredients...',
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v),
  },
  color: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'white'].includes(v),
  },
  indicator: {
    type: String,
    default: 'ring',
  },
  messageClass: {
    type: String,
    default: '',
  },
})

const sizeClasses = {
  sm: 'h-8 w-8 border-2',
  md: 'h-10 w-10 border-2',
  lg: 'h-12 w-12 border-[3px]',
}

const trackAndAccent = {
  primary: 'border-gray-200 border-t-primary-600',
  white: 'border-white/30 border-t-white',
}

const spinnerClasses = computed(() => {
  const size = sizeClasses[props.size] || sizeClasses.md
  const colors = trackAndAccent[props.color] || trackAndAccent.primary
  return `${size} ${colors}`
})

const textClasses = computed(() => {
  if (props.messageClass) return props.messageClass
  return props.color === 'white' ? 'text-white/90' : 'text-gray-600'
})
</script>
