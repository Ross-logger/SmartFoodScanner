import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref([])
  let idCounter = 0

  function show(message, type = 'success', duration = 3000) {
    const id = ++idCounter
    const notification = {
      id,
      message,
      type, // 'success', 'error', 'info', 'warning'
    }
    
    notifications.value.push(notification)
    
    if (duration > 0) {
      setTimeout(() => {
        remove(id)
      }, duration)
    }
    
    return id
  }

  function success(message, duration = 3000) {
    return show(message, 'success', duration)
  }

  function error(message, duration = 4000) {
    return show(message, 'error', duration)
  }

  function info(message, duration = 3000) {
    return show(message, 'info', duration)
  }

  function warning(message, duration = 3500) {
    return show(message, 'warning', duration)
  }

  function remove(id) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }

  function clear() {
    notifications.value = []
  }

  return {
    notifications,
    show,
    success,
    error,
    info,
    warning,
    remove,
    clear
  }
})
