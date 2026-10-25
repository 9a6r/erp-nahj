import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import './lib/namespace'
import { DirectionProvider } from './components/ui/direction.tsx'

async function start() {
  if (import.meta.env.DEV) {
    const response = await fetch('/api/method/erpnext.www.banking.get_context_for_dev', { method: 'POST' })
    if (!response.ok) throw new Error('Could not load session')
    const { message } = await response.json()
    if (!window.frappe) window.frappe = {}
    window.frappe.boot = typeof message.boot === 'string' ? JSON.parse(message.boot) : message.boot
    document.documentElement.lang = message.lang || 'en'
    document.dir = message.layout_direction
    window.frappe.boot.layout_direction = message.layout_direction
    const translations = await fetch(`/api/method/frappe.translate.get_boot_translations?lang=${document.documentElement.lang}`)
    if (!translations.ok) throw new Error('Could not load translations')
    window.frappe._messages = (await translations.json()).message || {}
  } else {
    // Avoid rendering untranslated labels before the catalogue has arrived.
    await window.frappe?._translations_loaded
  }
  window.frappe.model.sync(window.frappe.boot.docs)
  createRoot(document.getElementById('root') as HTMLElement).render(
    <StrictMode>
      <DirectionProvider dir={window.frappe.boot.layout_direction ?? 'ltr'}>
        <App />
      </DirectionProvider>
    </StrictMode>,
  )
}

void start().catch(() => {
  createRoot(document.getElementById('root') as HTMLElement).render(
    <div role="alert" style={{ padding: '3rem', textAlign: 'center' }}>
      <p>تعذر تحميل مساحة العمل. تحقق من الاتصال وتسجيل الدخول، ثم أعد تحميل الصفحة.</p>
      <p>Could not load the workspace. Check your connection and sign-in, then reload.</p>
      <button onClick={() => window.location.reload()}>إعادة المحاولة · Retry</button>
    </div>,
  )
})
