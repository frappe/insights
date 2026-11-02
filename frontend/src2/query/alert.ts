import { useTimeAgo } from '@vueuse/core'
import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { getErrorMessage, getUniqueId, showErrorToast } from '../helpers'
import useDocumentResource from '../helpers/resource'

export type InsightsAlert = {
	doctype: 'Insights Alert'
	disabled: 0 | 1
	title: string
	channel: 'Telegram' | 'Email' | 'Webhook'
	query: string
	frequency: 'Hourly' | 'Daily' | 'Weekly' | 'Monthly' | 'Cron'
	cron_format: string
	last_execution: string
	next_execution: string
	telegram_chat_id: string
	recipients: string
	webhook_url: string
	// Stored in __Auth; the server hands back a masked value it ignores on save.
	webhook_token: string
	condition: string
	custom_condition: 0 | 1
	message: string
	creation: string
	modified: string
	created_from_now: string
	modified_from_now: string
	owner: string
	// who the alert runs as: whoever last enabled it
	permission_user: string
	name: string
}

const alerts = ref<InsightsAlert[]>([])

const loading = ref(false)
async function loadAlerts(query: string) {
	loading.value = true
	alerts.value = await call('insights.api.alerts.get_alerts', { query })
	alerts.value = alerts.value.map((alert: any) => ({
		...alert,
		created_from_now: useTimeAgo(alert.creation),
		modified_from_now: useTimeAgo(alert.modified),
	}))
	loading.value = false
	return alerts.value
}

// A list row with a `disabled` field is inert in frappe-ui's ListView, so the
// alert's own field would make a disabled alert impossible to open and enable
export function alertRows(alerts: InsightsAlert[]) {
	return alerts.map(({ disabled, ...alert }) => ({ ...alert, enabled: !disabled }))
}

/** The server's refusal of a cron, to show under the Cron field. Any other failure is not one. */
export function cronRefusal(error: any): string | undefined {
	return error?.exc_type === 'CronUnreadable' ? getErrorMessage(error) : undefined
}

const EMPTY_ALERT: InsightsAlert = {
	doctype: 'Insights Alert',
	name: '',
	disabled: 0,
	title: '',
	channel: 'Email',
	query: '',
	frequency: 'Hourly',
	cron_format: '',
	last_execution: '',
	next_execution: '',
	telegram_chat_id: '',
	recipients: '',
	webhook_url: '',
	webhook_token: '',
	condition: '',
	custom_condition: 0,
	message: '',
	creation: '',
	modified: '',
	created_from_now: '',
	modified_from_now: '',
	owner: '',
	permission_user: '',
}

function getAlert(name: string) {
	return useDocumentResource<InsightsAlert>('Insights Alert', name, {
		initialDoc: { ...EMPTY_ALERT, name },
		enableAutoSave: false,
		disableLocalStorage: true,
	})
}

export type Alert = ReturnType<typeof getAlert>

export default function useAlertStore() {
	return reactive({
		alerts,
		loading,

		loadAlerts,
		getAlert,
	})
}
