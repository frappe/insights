import './index.css'
import App from './App.vue'
import router from './router'
import { createApp } from 'vue'
import { socketio_port } from '../../../../sites/common_site_config.json'
import { setConfig, frappeRequest, initSocket } from 'frappe-ui'

import { registerGlobalComponents, registerControllers } from './globals'

let app = createApp(App)
setConfig('resourceFetcher', frappeRequest)

app.use(router)
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
