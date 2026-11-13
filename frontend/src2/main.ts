import { frappeRequest, setConfig, useColorScheme } from 'frappe-ui'
import { createPinia } from 'pinia'
import { createApp, watchEffect } from 'vue'
import App from './App.vue'
import { registerControllers } from './controllers.ts'
import { registerGlobalComponents } from './globals.ts'
import { setRouter } from './helpers/navigation.ts'
import './index.css'
import router from './router.ts'
import { translationPlugin } from './translation.ts'
import { telemetryPlugin } from '@framework/ui/telemetry/index.ts'
import session from './session.ts'

setConfig('resourceFetcher', frappeRequest)

// A deploy replaces the hashed chunks, so a tab opened before it fails to load
// one. Reload to fetch the new build, but not again within a minute, so a chunk
// that is missing from the new build too does not reload the page in a loop.
window.addEventListener('vite:preloadError', (event) => {
	const lastReload = Number(sessionStorage.getItem('insights:chunk-reload'))
	if (Date.now() - lastReload < 60_000) return
	sessionStorage.setItem('insights:chunk-reload', String(Date.now()))
	event.preventDefault()
	window.location.reload()
})

// Default to light until charts are themed for dark (Phase 2); dark stays
// opt-in via the toggle so users aren't dropped into a half-themed UI.
if (!localStorage.getItem('theme')) localStorage.setItem('theme', 'light')
useColorScheme()

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
setRouter({
	resolveHref: (to) => router.resolve(to).href,
	navigate: (to) => router.push(to),
})

const stop = watchEffect(() => {
	if (session.isLoggedIn) {
		app.use(telemetryPlugin, { app_name: 'insights' })
		stop()
	}
})

app.config.errorHandler = (err, vm, info) => {
	console.groupCollapsed('Unhandled Error in: ', info)
	console.error('Context:', vm)
	console.error('Error:', err)
	console.groupEnd()
	return false
}

registerGlobalComponents(app)
registerControllers(app)

app.mount('#app')
app.use(translationPlugin)
