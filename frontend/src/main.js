import './index.css'
import App from './App.vue'
import router from './router'
import { createApp } from 'vue'
import { socketio_port } from '../../../../sites/common_site_config.json'
import { setConfig, frappeRequest, initSocket } from 'frappe-ui'
import { createToast } from './utils/toasts'
import VueGridLayout from 'vue3-drr-grid-layout'
import 'vue3-drr-grid-layout/dist/style.css'

import { registerGlobalComponents, registerControllers } from './globals'

let app = createApp(App)
setConfig('resourceFetcher', (options) => {
	return frappeRequest({
		...options,
		onError(err) {
			if (err.error.messages && err.error.messages[0]) {
				createToast({
					title: 'Error',
					appearance: 'error',
					message: err.error.messages[0],
				})
			}
		},
	})
})

app.use(router)
app.use(VueGridLayout)
app.config.unwrapInjectedRef = true
app.provide(
	'$socket',
	initSocket({
		port: socketio_port,
	})
)

registerGlobalComponents(app)
registerControllers(app)

app.mount('#app')
