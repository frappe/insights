import useDocumentResource from '../helpers/resource'
import { createToast } from '../helpers/toasts'

let settings = undefined as Settings | undefined
export default function useSettings() {
	if (settings) return settings
	return makeSettings()
}

function makeSettings() {
	const doctype = 'Insights Settings'
	const _settings = useDocumentResource<InsightsSettings>(doctype, doctype, {
		initialDoc: {
			name: '',
			enable_permissions: false,
			allowed_origins: '',
			max_records_to_sync: 10_00_000,
			max_memory_usage: 512,
			fiscal_year_start: '2024-04-01',
			week_starts_on: 'Monday',
			enable_data_store: false,
			apply_user_permissions: false,
		},
		disableLocalStorage: true,
	})
	_settings.onAfterSave(() =>
		createToast({
			title: 'Settings Updated',
			message: 'Your settings have been updated successfully',
			variant: 'success',
		})
	)
	settings = _settings
	return _settings
}

type Settings = ReturnType<typeof makeSettings>

type InsightsSettings = {
	name: string
	enable_permissions: boolean
	allowed_origins: string
	max_records_to_sync: number
	max_memory_usage: number
	fiscal_year_start: string
	week_starts_on: string
	enable_data_store: boolean
	apply_user_permissions: boolean
}
