import './index.css'
import App from './App.vue'
import router from './router'
import { createApp } from 'vue'
import { createToast } from './utils/toasts'
import { FrappeUI, Button, FeatherIcon, Input, onOutsideClickDirective, Popover } from 'frappe-ui'

let app = createApp(App)
app.use(router)
app.use(FrappeUI)
app.component('Input', Input)
app.component('Button', Button)
app.component('FeatherIcon', FeatherIcon)
app.component('Popover', Popover)
app.directive('on-outside-click', onOutsideClickDirective)

app.config.globalProperties.$notify = createToast
app.mount('#app')
