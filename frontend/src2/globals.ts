import Autocomplete from './components/Autocomplete.vue'
import Checkbox from './components/Checkbox.vue'
import Popover from './components/Popover.vue'
import Switch from './components/Switch.vue'
import {
	Avatar,
	Badge,
	Button,
	Dialog,
	Dropdown,
	ErrorMessage,
	FeatherIcon,
	Input,
	LoadingIndicator,
	Tooltip,
	FormControl
} from 'frappe-ui'

import { App } from 'vue'
import dayjs from './helpers/dayjs.ts'
import { createToast } from './helpers/toasts'
import { initSocket } from './socket.ts'

export function registerGlobalComponents(app: App) {
	app.component('Input', Input)
	app.component('Badge', Badge)
	app.component('Button', Button)
	app.component('Dialog', Dialog)
	app.component('Avatar', Avatar)
	app.component('Switch', Switch)
	app.component('Popover', Popover)
	app.component('Tooltip', Tooltip)
	app.component('Checkbox', Checkbox)
	app.component('Dropdown', Dropdown)
	app.component('FormControl', FormControl)
	app.component('LoadingIndicator', LoadingIndicator)
	app.component('Autocomplete', Autocomplete)
	app.component('ErrorMessage', ErrorMessage)
	app.component('FeatherIcon', FeatherIcon)
}

export function registerControllers(app: App) {
	app.provide('$dayjs', dayjs)
	app.provide('$notify', createToast)
	app.provide('$socket', initSocket())
}
