import { frappeRequest, setConfig, useColorScheme } from 'frappe-ui'
import { createPinia } from 'pinia'
import { createApp, watchEffect } from 'vue'
import App from './App.vue'
import { registerControllers } from './controllers.ts'
import { registerGlobalComponents } from './globals.ts'
import { setNavigationProvider } from './helpers/navigation.ts'
import './index.css'
import router from './router.ts'
import { translationPlugin } from './translation.ts'
import { telemetryPlugin } from '@framework/ui/telemetry/index.ts'
import session from './session.ts'

setConfig('resourceFetcher', frappeRequest)

// Default to light until charts are themed for dark (Phase 2); dark stays
// opt-in via the toggle so users aren't dropped into a half-themed UI.
if (!localStorage.getItem('theme')) localStorage.setItem('theme', 'light')
useColorScheme() // restores saved theme onto <html data-theme>, tracks system pref

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
setNavigationProvider({
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
