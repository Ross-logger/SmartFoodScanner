# Frontend Setup Guide

Complete guide to setting up the Smart Food Scanner frontend.

## Prerequisites

Before starting, ensure you have:

- ✅ Node.js 16+ installed ([Download](https://nodejs.org/))
- ✅ npm, yarn, or pnpm package manager
- ✅ Backend API running (see main project setup)
- ✅ Modern browser (Chrome, Firefox, Safari, or Edge)

## Step-by-Step Setup

### Step 1: Navigate to Frontend Directory

```bash
cd frontend
```

### Step 2: Install Dependencies

Choose one package manager:

```bash
# Using npm
npm install

# Using yarn
yarn install

# Using pnpm
pnpm install
```

This will install all required packages listed in `package.json`.

### Step 3: Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Backend API URL
VITE_API_BASE_URL=http://localhost:8000/api

# App Info (optional)
VITE_APP_NAME=Smart Food Scanner
VITE_APP_VERSION=1.0.0
```

**Important**: If your backend runs on a different port, update the URL accordingly.

### Step 4: Start Development Server

```bash
npm run dev
```

You should see:

```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

### Step 5: Open in Browser

1. Open your browser
2. Navigate to `http://localhost:3000`
3. You should see the Smart Food Scanner home page

## Verification

Test that everything works:

### ✅ Homepage Loads
- Navigate to `http://localhost:3000`
- See the hero section with "Smart Food Scanner"

### ✅ Camera Access (Mobile)
- Open on mobile device or use Chrome DevTools mobile emulation
- Navigate to "Scan" page
- Browser should request camera permission

### ✅ API Connection
- Try to register/login
- Check browser console for errors
- If you see CORS errors, ensure backend CORS is configured

## Common Issues

### Issue: Port 3000 Already in Use

**Solution**: Change port in `vite.config.js`:

```javascript
server: {
  port: 3001, // Change to any available port
  // ...
}
```

### Issue: Camera Not Working

**Causes**:
- Not using HTTPS (except localhost)
- Browser doesn't support Media API
- Camera permission denied

**Solutions**:
1. Use localhost or HTTPS
2. Use modern browser (Chrome recommended)
3. Check browser settings and grant camera permission

### Issue: Cannot Connect to Backend

**Symptoms**:
- Login fails with "No response from server"
- API calls return CORS errors

**Solutions**:
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check `.env` has correct API URL
3. Ensure backend CORS allows frontend origin

### Issue: Build Errors

**Solution**:
```bash
# Clear node_modules
rm -rf node_modules package-lock.json

# Reinstall
npm install

# Clear Vite cache
rm -rf node_modules/.vite
```

### Issue: Blank White Page

**Solution**:
1. Open browser DevTools (F12)
2. Check Console for errors
3. Verify all routes are correctly configured
4. Try hard refresh (Ctrl+Shift+R / Cmd+Shift+R)

## Production Build

### Build

```bash
npm run build
```

Output will be in `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

Opens production build at `http://localhost:4173`

### Deploy

See deployment section in main README for platform-specific guides.

## Development Tips

### Hot Module Replacement (HMR)

Vite supports HMR - changes appear instantly without full page reload.

### Browser DevTools

Use Vue DevTools extension:
- [Chrome](https://chrome.google.com/webstore/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)

### Mobile Testing

**Option 1: Chrome DevTools**
1. Press F12
2. Click mobile icon (top-left)
3. Select device

**Option 2: Real Device**
1. Find your computer's local IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
2. On mobile, navigate to `http://YOUR_IP:3000`
3. Ensure both devices are on same network

### PWA Testing

**Test Installation**:
1. Build app: `npm run build`
2. Preview: `npm run preview`
3. Open DevTools → Application → Manifest
4. Check "Add to Home Screen" works

**Test Offline**:
1. Open DevTools → Application → Service Workers
2. Check "Offline" checkbox
3. Reload page - should still work (after first visit)

## Project Structure Overview

```
frontend/
├── public/              Static files (served as-is)
├── src/
│   ├── components/      Reusable UI components
│   ├── views/           Page components
│   ├── stores/          State management (Pinia)
│   ├── services/        API and utilities
│   ├── router/          Routing configuration
│   ├── App.vue          Root component
│   ├── main.js          Entry point
│   └── style.css        Global styles
├── .env                 Environment variables
├── vite.config.js       Vite configuration
├── tailwind.config.js   Tailwind configuration
└── package.json         Dependencies & scripts
```

## Next Steps

1. ✅ **Test Camera**: Go to Scan page and test camera
2. ✅ **Test Auth**: Register and login
3. ✅ **Test Scan**: Upload or capture an image
4. ✅ **Test History**: View scan history
5. ✅ **Test PWA**: Install on mobile device

## Getting Help

- Check browser console for errors
- Review main project README
- Check backend logs
- Verify all environment variables are set

## Useful Commands

```bash
# Development
npm run dev              # Start dev server

# Build
npm run build            # Build for production
npm run preview          # Preview production build

# Maintenance
npm update               # Update dependencies
npm audit                # Check for vulnerabilities
npm audit fix            # Fix vulnerabilities
```

---

**Setup Complete!** 🎉

Your frontend should now be running. Continue to testing or start development!


