import { frappeRequest, setConfig } from 'frappe-ui'
import { GridItem, GridLayout } from 'grid-layout-plus'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { registerControllers, registerGlobalComponents } from './globals.ts'
import './index.css'
import router from './router.ts'
import { translationPlugin } from './translation.ts'
import { spritePlugin } from 'frappe-ui/icons'

setConfig('resourceFetcher', frappeRequest)

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(spritePlugin)
app.component('grid-layout', GridLayout)
app.component('grid-item', GridItem)

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
