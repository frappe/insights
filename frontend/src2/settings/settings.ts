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
	enable_permissions: boolean
}
