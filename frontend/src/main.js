import './index.css'
import App from './App.vue'
import router from './router'
import { createApp } from 'vue'
import utils from './utils'
import { userInfo } from './utils/users'
import { createToast } from './utils/toasts'
import {
	FrappeUI,
	Button,
	FeatherIcon,
	Input,
	onOutsideClickDirective,
	Popover,
	Dialog,
	ErrorMessage,
} from 'frappe-ui'

let app = createApp(App)
app.use(router)
app.use(FrappeUI)
app.component('Input', Input)
app.component('Button', Button)
app.component('Dialog', Dialog)
app.component('Popover', Popover)
app.component('ErrorMessage', ErrorMessage)
app.component('FeatherIcon', FeatherIcon)
app.directive('on-outside-click', onOutsideClickDirective)

app.provide('$utils', utils)
app.provide('$user', userInfo)
app.provide('$notify', createToast)
app.provide('$socket', app.config.globalProperties.$socket)
app.mount('#app')
