import { useTimeAgo } from '@vueuse/core'
import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { getUniqueId, showErrorToast } from '../helpers'
import useDocumentResource from '../helpers/resource'

export type InsightsAlert = {
	doctype: 'Insights Alert'
	disabled: 0 | 1
	title: string
	channel: 'Telegram' | 'Email'
	query: string
	frequency: 'Hourly' | 'Daily' | 'Weekly' | 'Monthly' | 'Cron'
	cron_format: string
	last_execution: string
	next_execution: string
	telegram_chat_id: string
	recipients: string
	condition: string
	custom_condition: 0 | 1
	message: string
	creation: string
	modified: string
	created_from_now: string
	modified_from_now: string
	owner: string
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
	condition: '',
	custom_condition: 0,
	message: '',
	creation: '',
	modified: '',
	created_from_now: '',
	modified_from_now: '',
	owner: '',
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
