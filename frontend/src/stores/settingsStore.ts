import * as api from '@/api'
import { createToast } from '@/utils/toasts'
import { defineStore } from 'pinia'
import { computed } from 'vue'

type InsightsSettings = {
	setup_complete: boolean
	enable_permissions: boolean
	allow_subquery: boolean
	auto_execute_query: boolean
	query_result_expiry: number
	query_result_limit: number
	telegram_api_token: string
	fiscal_year_start: string
}

const settingsStore = defineStore('insights:settings', () => {
	const insightsSettings = api.getDocumentResource('Insights Settings')
	const initialized = computed(() => insightsSettings.doc?.name)
	async function initialize() {
		if (initialized.value) return
		await insightsSettings.get.fetch()
	}

	const loading = computed(() => insightsSettings.loading)
	const settings = computed({
		get: () => insightsSettings.doc,
		set(value: InsightsSettings) {
			insightsSettings.doc = value
		},
	})

	function update(settings: InsightsSettings, showToast: boolean = true) {
		return insightsSettings.setValue.submit({ ...settings }).then(() => {
			showToast &&
				createToast({
					title: 'Settings Updated',
					message: 'Your settings have been updated successfully',
					variant: 'success',
				})
		})
	}

	return {
		initialized,
		settings,
		loading,
		initialize,
		update,
	}
})

export default settingsStore
export type SettingsStore = ReturnType<typeof settingsStore>
