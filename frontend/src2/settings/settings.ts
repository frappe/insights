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
			setup_complete: false,
			telegram_api_token: '',
			fiscal_year_start: '',
		},
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
	setup_complete: boolean
	telegram_api_token: string
	fiscal_year_start: string
}
