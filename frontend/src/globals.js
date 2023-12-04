import {
	Button,
	FeatherIcon,
	Input,
	onOutsideClickDirective,
	Dialog,
	ErrorMessage,
	Dropdown,
	Badge,
	Avatar,
	Tooltip,
	LoadingIndicator,
	FormControl,
} from 'frappe-ui'
import Checkbox from '@/components/Controls/Checkbox.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import Popover from '@/components/Popover.vue'

import utils from './utils'
import { createToast } from './utils/toasts'
import dayjs from './utils/dayjs'

export function registerGlobalComponents(app) {
	app.component('Input', Input)
	app.component('Badge', Badge)
	app.component('Button', Button)
	app.component('Dialog', Dialog)
	app.component('Avatar', Avatar)
	app.component('Popover', Popover)
	app.component('Tooltip', Tooltip)
	app.component('Checkbox', Checkbox)
	app.component('Dropdown', Dropdown)
	app.component('FormControl', FormControl)
	app.component('LoadingIndicator', LoadingIndicator)
	app.component('Autocomplete', Autocomplete)
	app.component('ErrorMessage', ErrorMessage)
	app.component('FeatherIcon', FeatherIcon)
	app.directive('on-outside-click', onOutsideClickDirective)
}

export function registerControllers(app) {
	app.provide('$utils', utils)
	app.provide('$dayjs', dayjs)
	app.provide('$notify', createToast)

	if (import.meta.env.DEV) {
		window.$utils = utils
		window.$dayjs = dayjs
		window.$notify = createToast
	}
}
