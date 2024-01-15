import { autoAnimatePlugin } from '@formkit/auto-animate/vue'
import { frappeRequest, setConfig } from 'frappe-ui'
import { GridItem, GridLayout } from 'grid-layout-plus'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import './index.css'
import router from './router'
import { initSocket } from './socket'
import { createToast } from './utils/toasts'

import { registerControllers, registerGlobalComponents } from './globals'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
setConfig('resourceFetcher', (options) => {
	return frappeRequest({
		...options,
		onError(err) {
			if (err.messages && err.messages[0]) {
				createToast({
					title: 'Error',
					variant: 'error',
					message: err.messages[0],
				})
			}
		},
	})
})

app.use(router)
app.use(autoAnimatePlugin)
app.component('grid-layout', GridLayout)
app.component('grid-item', GridItem)
app.provide('$socket', initSocket())

registerGlobalComponents(app)
registerControllers(app)

app.mount('#app')
