import { createApp } from 'vue'
import { FrappeUI, Button, FeatherIcon, Input, onOutsideClickDirective, Popover } from 'frappe-ui'
import router from './router'
import App from './App.vue'
import './index.css'

let app = createApp(App)
app.use(router)
app.use(FrappeUI)
app.component('Input', Input)
app.component('Button', Button)
app.component('FeatherIcon', FeatherIcon)
app.component('Popover', Popover)
app.directive('on-outside-click', onOutsideClickDirective)
app.mount('#app')
