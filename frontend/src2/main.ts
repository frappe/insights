import { frappeRequest, setConfig, useTheme } from 'frappe-ui'
import { spritePlugin } from 'frappe-ui/icons'
import { GridItem, GridLayout } from 'grid-layout-plus'
import { createPinia } from 'pinia'
import { createApp, watchEffect } from 'vue'
import App from './App.vue'
import { registerControllers, registerGlobalComponents } from './globals.ts'
import './index.css'
import router from './router.ts'
import { translationPlugin } from './translation.ts'
import { telemetryPlugin } from 'frappe-ui/frappe'
import session from './session.ts'

setConfig('resourceFetcher', frappeRequest)

// Default to light until charts are themed for dark (Phase 2); dark stays
// opt-in via the toggle so users aren't dropped into a half-themed UI.
if (!localStorage.getItem('theme')) localStorage.setItem('theme', 'light')
useTheme() // restores saved theme onto <html data-theme>, tracks system pref

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(spritePlugin)
app.component('grid-layout', GridLayout)
app.component('grid-item', GridItem)

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
app.use(translationPlugin);
