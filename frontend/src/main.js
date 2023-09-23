import { frappeRequest, initSocket, setConfig } from 'frappe-ui'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { GridLayout, GridItem } from 'grid-layout-plus'
import { socketio_port } from '../../../../sites/common_site_config.json'
import App from './App.vue'
import './index.css'
import router from './router'
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
app.component('grid-layout', GridLayout)
app.component('grid-item', GridItem)
app.provide(
	'$socket',
	initSocket({
		port: socketio_port,
	})
)

registerGlobalComponents(app)
registerControllers(app)

app.mount('#app')
