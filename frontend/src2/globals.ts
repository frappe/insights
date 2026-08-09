import {
	Avatar,
	Badge,
	Button,
	Combobox,
	Dialog,
	Dropdown,
	ErrorMessage,
	FormControl,
	LoadingIndicator,
	MultiSelect,
	Popover,
	Switch,
	TabButtons,
	Tooltip,
} from 'frappe-ui'
import Checkbox from './components/Checkbox.vue'

import { App } from 'vue'

// Islands import this module too, so keep it free of anything the SPA alone
// needs — the injections live in `controllers.ts`.
export function registerGlobalComponents(app: App) {
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
