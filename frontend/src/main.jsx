import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

const savedTheme = localStorage.getItem('theme') || 'orange'
document.documentElement.dataset.theme = savedTheme
window.__setTheme = (themeName) => {
  document.documentElement.dataset.theme = themeName
  localStorage.setItem('theme', themeName)
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
