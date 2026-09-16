import { useTelemetry as useFrameworkTelemetry } from '@framework/ui/telemetry/index.ts'

import session from './session'

// The properties `docs/telemetry.md` puts on every event. The backend reads them
// from the site. The browser reads them from `insights.api.get_site_info`.
export function useTelemetry() {
	const telemetry = useFrameworkTelemetry()
	return {
		capture: (event: string, props: Record<string, any> = {}) =>
			telemetry.capture(event, {
				app_version: session.site.app_version,
				entry: session.site.entry,
				...props,
			}),
	}
}
