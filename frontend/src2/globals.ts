import {
	Avatar,
	Badge,
	Button,
	Combobox,
	Dialog,
	Dropdown,
	ErrorMessage,
	FormControl,
	Input,
	LoadingIndicator,
	MultiSelect,
	Popover,
	Switch,
	TabButtons,
	Tooltip,
} from 'frappe-ui'
import Checkbox from './components/Checkbox.vue'

import { App } from 'vue'
import dayjs from './helpers/dayjs.ts'
import { createToast } from './helpers/toasts'
import { getSocket } from './socket.ts'

export function registerGlobalComponents(app: App) {
	app.component('Input', Input)
	app.component('Badge', Badge)
	app.component('Button', Button)
	app.component('Dialog', Dialog)
	app.component('Avatar', Avatar)
	app.component('Switch', Switch)
	app.component('TabButtons', TabButtons)
	app.component('Popover', Popover)
	app.component('Tooltip', Tooltip)
	app.component('Toggle', Checkbox)
	app.component('Dropdown', Dropdown)
	app.component('FormControl', FormControl)
	app.component('LoadingIndicator', LoadingIndicator)
	app.component('Combobox', Combobox)
	app.component('MultiSelect', MultiSelect)
	app.component('ErrorMessage', ErrorMessage)
}

export function registerControllers(app: App) {
	app.provide('$dayjs', dayjs)
	app.provide('$notify', createToast)
	app.provide('$socket', getSocket())
}
