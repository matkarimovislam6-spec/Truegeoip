import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/signin': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/signup': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/verify': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/signout': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
