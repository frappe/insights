import './index.css'
import App from './App.vue'
import router from './router'
import { createApp } from 'vue'
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
} from 'frappe-ui'

let app = createApp(App)
app.use(router)
app.use(FrappeUI)
app.component('Input', Input)
app.component('Button', Button)
app.component('Dialog', Dialog)
app.component('Popover', Popover)
app.component('FeatherIcon', FeatherIcon)
app.directive('on-outside-click', onOutsideClickDirective)

app.config.globalProperties.$user = userInfo
app.config.globalProperties.$notify = createToast
app.mount('#app')
