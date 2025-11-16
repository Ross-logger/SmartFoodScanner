# Smart Food Scanner - Frontend

A modern, mobile-first Progressive Web App (PWA) for scanning food ingredient labels with AI-powered OCR and dietary analysis.

## 🚀 Features

- **📱 Mobile-First Design** - Optimized for smartphones with responsive layouts
- **📷 Camera Integration** - Native camera access for scanning labels
- **🔄 PWA Support** - Installable on mobile devices, works offline
- **⚡ Lightning Fast** - Built with Vite for optimal performance
- **🎨 Beautiful UI** - Tailwind CSS for modern, clean design
- **🔐 Authentication** - Secure user authentication and profiles
- **📊 Scan History** - Track and review previous scans
- **🌐 Real-time Analysis** - Instant ingredient recognition and dietary info

## 🛠️ Tech Stack

- **Framework**: Vue 3 (Composition API)
- **Build Tool**: Vite 5
- **Styling**: Tailwind CSS 3
- **State Management**: Pinia
- **Routing**: Vue Router 4
- **HTTP Client**: Axios
- **PWA**: vite-plugin-pwa

## 📋 Prerequisites

- Node.js 16+ and npm/yarn/pnpm
- Backend API running (see main project README)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your backend API URL:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### 3. Run Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### 4. Build for Production

```bash
npm run build
```

Build output will be in the `dist/` directory.

### 5. Preview Production Build

```bash
npm run preview
```

## 📁 Project Structure

```
frontend/
├── public/                 # Static assets
├── src/
│   ├── components/         # Reusable Vue components
│   │   ├── CameraCapture.vue
│   │   ├── ImageUpload.vue
│   │   ├── IngredientList.vue
│   │   └── LoadingSpinner.vue
│   ├── views/              # Page components
│   │   ├── HomeView.vue
│   │   ├── ScanView.vue
│   │   ├── ResultView.vue
│   │   ├── HistoryView.vue
│   │   ├── LoginView.vue
│   │   ├── RegisterView.vue
│   │   └── ProfileView.vue
│   ├── stores/             # Pinia state management
│   │   ├── auth.js
│   │   └── scan.js
│   ├── services/           # API and utilities
│   │   ├── api.js
│   │   └── camera.js
│   ├── router/             # Vue Router configuration
│   │   └── index.js
│   ├── App.vue             # Root component
│   ├── main.js             # App entry point
│   └── style.css           # Global styles
├── index.html              # HTML template
├── vite.config.js          # Vite configuration
├── tailwind.config.js      # Tailwind configuration
├── package.json            # Dependencies
└── README.md               # This file
```

## 🔑 Key Features Explained

### Camera Integration

The app uses the native browser Media API for camera access:

- **Mobile**: Opens device camera directly
- **Desktop**: Access webcam with permission
- **Rear Camera**: Defaults to back camera for scanning labels
- **Switch Camera**: Toggle between front/rear on mobile

### PWA Capabilities

- **Installable**: Add to home screen on mobile devices
- **Offline Support**: Service worker caching for offline functionality
- **App-like Experience**: Full-screen mode, native feel
- **Auto-updates**: Automatically updates when new version is available

### State Management

Using Pinia stores for:

- **Auth Store**: User authentication, login/logout
- **Scan Store**: Scan history, current scan results

### Routing

Protected routes require authentication:

- Public: Home, Login, Register
- Protected: Scan, Result, History, Profile

## 📱 Mobile Usage

### Installing on iOS (iPhone/iPad)

1. Open the app in Safari
2. Tap the Share button
3. Select "Add to Home Screen"
4. Tap "Add"

### Installing on Android

1. Open the app in Chrome
2. Tap the menu (three dots)
3. Select "Add to Home Screen" or "Install App"
4. Tap "Install"

### Camera Permissions

First time using the camera:

1. Browser will request camera permission
2. Select "Allow"
3. Permission persists for future uses

## 🎨 Customization

### Theme Colors

Edit `tailwind.config.js` to change the primary color:

```javascript
colors: {
  primary: {
    // Change these values
    500: '#10b981',
    600: '#059669',
    // ...
  }
}
```

### API Endpoint

Change the backend URL in `.env`:

```env
VITE_API_BASE_URL=https://your-api-domain.com/api
```

## 🔧 Development

### Code Style

- Use Vue 3 Composition API
- Follow Vue style guide
- Use Tailwind utility classes
- Keep components small and focused

### Adding New Pages

1. Create component in `src/views/`
2. Add route in `src/router/index.js`
3. Add navigation link if needed

### Adding New Components

1. Create component in `src/components/`
2. Export and import where needed
3. Use props for configuration
4. Emit events for parent communication

## 🐛 Troubleshooting

### Camera Not Working

- Ensure HTTPS (localhost is OK for dev)
- Check browser permissions
- Try different browser (Chrome recommended)

### API Connection Issues

- Verify backend is running
- Check `.env` configuration
- Check browser console for CORS errors

### Build Errors

- Clear node_modules and reinstall
- Check Node.js version (16+ required)
- Update dependencies: `npm update`

## 📦 Deployment

### Vercel (Recommended)

```bash
npm install -g vercel
vercel
```

### Netlify

```bash
npm run build
# Upload dist/ folder to Netlify
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "run", "preview"]
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

Part of the Smart Food Scanner FYP project.

## 👨‍💻 Author

Created as part of Final Year Project (FYP)

## 🙏 Acknowledgments

- Vue.js team for the amazing framework
- Tailwind CSS for utility-first styling
- Vite for blazing-fast build tool


