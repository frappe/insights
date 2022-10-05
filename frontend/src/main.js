import './index.css'
import App from './App.vue'
import router from './router'
import { createApp } from 'vue'
import { socketio_port } from '../../../../sites/common_site_config.json'
import { FrappeUI } from 'frappe-ui'

import { registerGlobalComponents, registerControllers } from './globals'

let app = createApp(App)
app.use(router)
app.use(FrappeUI, {
	socketio: {
		port: socketio_port,
	},
})

registerGlobalComponents(app)
registerControllers(app)

app.mount('#app')
