/**
 * Camera Service
 * Handles camera access and image capture for mobile and desktop
 */

class CameraService {
  constructor() {
    this.stream = null
    this.capabilities = {
      hasCamera: false,
      hasMultipleCameras: false,
      supportsCameraConstraints: false
    }
  }

  /**
   * Check if device has camera access
   */
  async checkCameraAvailability() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return false
    }

    try {
      const devices = await navigator.mediaDevices.enumerateDevices()
      const cameras = devices.filter(device => device.kind === 'videoinput')
      
      this.capabilities.hasCamera = cameras.length > 0
      this.capabilities.hasMultipleCameras = cameras.length > 1
      this.capabilities.supportsCameraConstraints = 'facingMode' in navigator.mediaDevices.getSupportedConstraints()
      
      return this.capabilities.hasCamera
    } catch (error) {
      console.error('Error checking camera availability:', error)
      return false
    }
  }

  /**
   * Request camera access with specific constraints
   * @param {string} facingMode - 'user' (front) or 'environment' (rear)
   */
  async requestCameraAccess(facingMode = 'environment') {
    try {
      const constraints = {
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        },
        audio: false
      }

      this.stream = await navigator.mediaDevices.getUserMedia(constraints)
      return this.stream
    } catch (error) {
      console.error('Error accessing camera:', error)
      throw new Error(this.getCameraErrorMessage(error))
    }
  }

  /**
   * Stop camera stream
   */
  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop())
      this.stream = null
    }
  }

  /**
   * Capture image from video element
   * @param {HTMLVideoElement} videoElement
   * @returns {Blob} Image blob
   */
  async captureImage(videoElement) {
    const canvas = document.createElement('canvas')
    canvas.width = videoElement.videoWidth
    canvas.height = videoElement.videoHeight

    const context = canvas.getContext('2d')
    context.drawImage(videoElement, 0, 0, canvas.width, canvas.height)

    return new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob)
          } else {
            reject(new Error('Failed to capture image'))
          }
        },
        'image/jpeg',
        0.9
      )
    })
  }

  /**
   * Compress image file
   * @param {File|Blob} file - Image file to compress
   * @param {number} maxWidth - Maximum width
   * @param {number} maxHeight - Maximum height
   * @param {number} quality - JPEG quality (0-1)
   * @returns {Promise<Blob>}
   */
  async compressImage(file, maxWidth = 1920, maxHeight = 1920, quality = 0.8) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      
      reader.onload = (e) => {
        const img = new Image()
        
        img.onload = () => {
          const canvas = document.createElement('canvas')
          let width = img.width
          let height = img.height

          // Calculate new dimensions
          if (width > height) {
            if (width > maxWidth) {
              height = (height * maxWidth) / width
              width = maxWidth
            }
          } else {
            if (height > maxHeight) {
              width = (width * maxHeight) / height
              height = maxHeight
            }
          }

          canvas.width = width
          canvas.height = height

          const ctx = canvas.getContext('2d')
          ctx.drawImage(img, 0, 0, width, height)

          canvas.toBlob(
            (blob) => {
              if (blob) {
                resolve(blob)
              } else {
                reject(new Error('Failed to compress image'))
              }
            },
            'image/jpeg',
            quality
          )
        }

        img.onerror = () => reject(new Error('Failed to load image'))
        img.src = e.target.result
      }

      reader.onerror = () => reject(new Error('Failed to read file'))
      reader.readAsDataURL(file)
    })
  }

  /**
   * Get user-friendly error message
   */
  getCameraErrorMessage(error) {
    if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
      return 'Camera access was denied. Please allow camera access in your browser settings.'
    }
    if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
      return 'No camera found on this device.'
    }
    if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
      return 'Camera is already in use by another application.'
    }
    if (error.name === 'OverconstrainedError') {
      return 'Camera does not support the requested settings.'
    }
    return 'Failed to access camera. Please try again.'
  }

  /**
   * Check if browser supports camera API
   */
  static isSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
  }
}

export default new CameraService()

