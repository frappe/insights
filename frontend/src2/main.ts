import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { frappeRequest, setConfig } from 'frappe-ui'
import App from './App.vue'
import './index.css'
import router from './router.ts'
import { registerControllers, registerGlobalComponents } from './globals.ts'

setConfig('resourceFetcher', frappeRequest)

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

registerGlobalComponents(app)
registerControllers(app)

app.mount('#app')
