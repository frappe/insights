import { call } from 'frappe-ui'
import '../../../frappe/frappe/public/js/lib/posthog.js'

const posthog = {
	init: (projectToken: string, options: any) => {},
	identify: (userId: string) => {},
	startSessionRecording: () => {},
	capture: (eventName: string, data?: any) => {},
}

declare global {
	interface Window {
		posthog: typeof posthog
	}
}

type PosthogSettings = {
	posthog_project_id: string
	posthog_host: string
	enable_telemetry: boolean
	telemetry_site_age: number
	record_session: boolean
	posthog_identifier: string
}

function init() {
	call('insights.api.telemetry.get_posthog_settings').then((posthogSettings: PosthogSettings) => {
		if (!posthogSettings.enable_telemetry || !posthogSettings.posthog_project_id) {
			return
		}
		window.posthog.init(posthogSettings.posthog_project_id, {
			api_host: posthogSettings.posthog_host,
			person_profiles: 'identified_only',
			autocapture: false,
			capture_pageview: false,
			capture_pageleave: false,
			enable_heatmaps: false,
			disable_session_recording: true,
			loaded: (ph: typeof posthog) => {
				ph.identify(posthogSettings.posthog_identifier || window.location.host)
				Object.assign(posthog, ph)
				if (posthogSettings.record_session) {
					ph.startSessionRecording()
				}
			},
		})
	})
}

export default { posthog, init }
