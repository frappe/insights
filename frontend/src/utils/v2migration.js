import sessionStore from '@/stores/sessionStore'
import { call } from 'frappe-ui'
import { ref } from 'vue'

const waiting = ref(0)
const canMigrate = ref(false)
let asked = false

/** What v3 says about migrating this site's v2 dashboards.
 *
 * v3 owns the rule and answers it for both apps - see `get_v2_migration_nudge`.
 * Its `show` is not read here: a caller in v2 is already the audience, which is
 * the whole of what `show` asks.
 *
 * Shared and asked once, because two surfaces in v2 offer the migration and a
 * second copy of the call would be a second chance to word the rule differently.
 */
export function useV2MigrationNudge() {
	if (!asked) {
		asked = true
		call('insights.api.v2_migration.get_v2_migration_nudge')
			.then((nudge) => {
				waiting.value = nudge?.waiting || 0
				canMigrate.value = Boolean(nudge?.can_migrate)
			})
			.catch(() => {
				// An Insights without the migrator answers 404. Both surfaces then
				// say what they always said, minus the migration offer.
			})
	}
	return { waiting, canMigrate }
}

/** v3 keeps its settings in a dialog and not on a route, so `?settings` is the
 * only way to open one from here. `/dashboards` and not `/`, because the root
 * route redirects and a redirect drops the query. */
export const MIGRATION_URL = '/insights/dashboards?settings=v2-migration'

export function openInsightsV3(target = '/insights') {
	const session = sessionStore()
	return session
		.updateDefaultVersion(
			// if default version is v2, then /insights always redirects to /insights_v2
			// so it is not possible to switch to v3 from v2
			// so we need to remove the default_version
			session.user.default_version === 'v2' ? '' : session.user.default_version,
		)
		.then(() => {
			window.location.href = target
		})
}
