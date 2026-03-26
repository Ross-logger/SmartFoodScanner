<template>
  <!-- Full-screen overlay mode -->
  <Transition name="fade">
    <div v-if="overlay && isLoading" class="loading-overlay">
      <div class="loading-content">
        <!-- Animated spinner -->
        <div class="spinner-container" :class="sizeClass">
          <div class="spinner-ring"></div>
          <div class="spinner-ring spinner-ring-2"></div>
          <div class="spinner-dot"></div>
        </div>
        
        <!-- Main text -->
        <p class="loading-text" :class="overlayMessageColorClass">{{ message || 'Processing your request...' }}</p>
        
        <!-- Subtext -->
        <p v-if="showSubtext" class="loading-subtext">
          {{ subtext || 'Please do not refresh the page' }}
        </p>
      </div>
    </div>
  </Transition>

  <!-- Inline spinner mode (original behavior) -->
  <div v-if="!overlay" class="loading-spinner" :class="sizeClass">
    <div
      v-if="indicator === 'ring'"
      class="ring-indicator"
      :class="colorClass"
    />
    <div v-else class="circle-loader" :class="colorClass">
      <div class="circle-dot" v-for="n in 12" :key="n" :style="getDotStyle(n)"></div>
    </div>
    <p
      v-if="message"
      class="loading-message"
      :class="[textSizeClass, inlineMessageColorClass]"
    >
      {{ message }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isLoading: {
    type: Boolean,
    default: true
  },
  overlay: {
    type: Boolean,
    default: false
  },
  message: {
    type: String,
    default: ''
  },
  subtext: {
    type: String,
    default: ''
  },
  showSubtext: {
    type: Boolean,
    default: true
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg', 'xl'].includes(value)
  },
  color: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'white', 'gray'].includes(value)
  },
  /** Inline mode: `dots` (default) or a single animated circle (`ring`). */
  indicator: {
    type: String,
    default: 'dots',
    validator: (value) => ['dots', 'ring'].includes(value)
  },
  /** Extra classes for the message line (e.g. text color on dark overlays). */
  messageClass: {
    type: String,
    default: ''
  }
})

const sizeClass = computed(() => {
  const sizes = {
    sm: 'size-sm',
    md: 'size-md',
    lg: 'size-lg',
    xl: 'size-xl'
  }
  return sizes[props.size]
})

const colorClass = computed(() => {
  const colors = {
    primary: 'color-primary',
    white: 'color-white',
    gray: 'color-gray'
  }
  return colors[props.color]
})

const textSizeClass = computed(() => {
  const sizes = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
    xl: 'text-xl'
  }
  return sizes[props.size]
})

/** Scoped `.loading-message` must not set color — it beat Tailwind utilities. */
const inlineMessageColorClass = computed(() =>
  props.messageClass?.trim() ? props.messageClass : 'text-gray-700'
)

const overlayMessageColorClass = computed(() =>
  props.messageClass?.trim() ? props.messageClass : 'text-white'
)

const getDotStyle = (index) => {
  const angle = (index - 1) * 30 - 90
  const radius = 50
  const x = 50 + radius * Math.cos((angle * Math.PI) / 180)
  const y = 50 + radius * Math.sin((angle * Math.PI) / 180)
  const delay = (index - 1) * 0.1
  
  return {
    left: `${x}%`,
    top: `${y}%`,
    transform: 'translate(-50%, -50%)',
    animationDelay: `${delay}s`
  }
}
</script>

<style scoped>
/* ===== FULL-SCREEN OVERLAY MODE ===== */
.loading-overlay {
  @apply fixed inset-0 z-50 flex items-center justify-center;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%);
  backdrop-filter: blur(8px);
}

.loading-content {
  @apply flex flex-col items-center gap-6 p-8;
}

/* Spinner container */
.spinner-container {
  @apply relative;
}

.spinner-container.size-sm {
  @apply w-12 h-12;
}

.spinner-container.size-md {
  @apply w-16 h-16;
}

.spinner-container.size-lg {
  @apply w-20 h-20;
}

.spinner-container.size-xl {
  @apply w-24 h-24;
}

/* Spinning rings */
.spinner-ring {
  @apply absolute inset-0 rounded-full;
  border: 3px solid transparent;
  border-top-color: #3b82f6;
  border-right-color: #3b82f6;
  animation: spin 1.2s linear infinite;
}

.spinner-ring-2 {
  @apply inset-2;
  border-top-color: #60a5fa;
  border-right-color: transparent;
  border-bottom-color: #60a5fa;
  animation: spin-reverse 1s linear infinite;
}

/* Center dot with pulse */
.spinner-dot {
  @apply absolute rounded-full bg-blue-400;
  top: 50%;
  left: 50%;
  width: 20%;
  height: 20%;
  transform: translate(-50%, -50%);
  animation: pulse-dot 1.5s ease-in-out infinite;
}

/* Text styles */
.loading-text {
  @apply text-xl font-semibold tracking-wide;
  animation: fade-in-up 0.5s ease-out 0.2s both;
}

.loading-subtext {
  @apply text-sm text-slate-400 font-medium;
  animation: fade-in-up 0.5s ease-out 0.4s both;
}

/* ===== INLINE SPINNER MODE (original) ===== */
.loading-spinner {
  @apply flex flex-col items-center justify-center gap-3;
}

.circle-loader {
  position: relative;
  width: 100%;
  height: 100%;
}

.loading-spinner.size-sm {
  width: 2rem;
  height: 2rem;
}

.loading-spinner.size-md {
  width: 3rem;
  height: 3rem;
}

.loading-spinner.size-lg {
  width: 4rem;
  height: 4rem;
}

.loading-spinner.size-xl {
  width: 5rem;
  height: 5rem;
}

/* Single circle / ring loader (inline) */
.ring-indicator {
  flex-shrink: 0;
  border-radius: 50%;
  box-sizing: border-box;
  animation: spin 0.75s linear infinite;
}

.loading-spinner.size-sm .ring-indicator {
  width: 2rem;
  height: 2rem;
  border-width: 2px;
  border-style: solid;
}

.loading-spinner.size-md .ring-indicator {
  width: 3rem;
  height: 3rem;
  border-width: 3px;
  border-style: solid;
}

.loading-spinner.size-lg .ring-indicator {
  width: 4rem;
  height: 4rem;
  border-width: 3px;
  border-style: solid;
}

.loading-spinner.size-xl .ring-indicator {
  width: 5rem;
  height: 5rem;
  border-width: 4px;
  border-style: solid;
}

.ring-indicator.color-primary {
  border-color: rgba(59, 130, 246, 0.22);
  border-top-color: rgb(59, 130, 246);
}

.ring-indicator.color-white {
  border-color: rgba(255, 255, 255, 0.28);
  border-top-color: white;
}

.ring-indicator.color-gray {
  border-color: rgba(75, 85, 99, 0.25);
  border-top-color: rgb(75, 85, 99);
}

.circle-dot {
  position: absolute;
  border-radius: 50%;
  animation: circle-fade 1.2s infinite ease-in-out;
}

.loading-spinner.size-sm .circle-dot {
  width: 0.25rem;
  height: 0.25rem;
}

.loading-spinner.size-md .circle-dot {
  width: 0.375rem;
  height: 0.375rem;
}

.loading-spinner.size-lg .circle-dot {
  width: 0.5rem;
  height: 0.5rem;
}

.loading-spinner.size-xl .circle-dot {
  width: 0.625rem;
  height: 0.625rem;
}

.color-primary .circle-dot {
  background-color: rgb(59 130 246);
}

.color-white .circle-dot {
  background-color: white;
}

.color-gray .circle-dot {
  background-color: rgb(75 85 99);
}

.loading-message {
  @apply font-medium text-center;
}

/* ===== ANIMATIONS ===== */
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes spin-reverse {
  to {
    transform: rotate(-360deg);
  }
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 0.6;
    transform: translate(-50%, -50%) scale(0.8);
  }
  50% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1.2);
  }
}

@keyframes circle-fade {
  0%, 100% {
    opacity: 0.3;
    transform: translate(-50%, -50%) scale(0.8);
  }
  50% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

@keyframes fade-in-up {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Fade transition for overlay */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
