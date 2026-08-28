import type { Credentials } from './auth'
import type { FrappeApi } from './frappe'
import { DOCTYPE } from './insights'

/**
 * Create or repair the fixture user, and give it the Insights User role.
 *
 * Insights invites people as Website Users, and `Insights User` has no desk
 * access, so the fixture user matches an invited member rather than a System
 * User. The password is set only when the account is created. Frappe clears a
 * user's sessions whenever `new_password` is written, so resetting it on every
 * run invalidates a saved `storageState` that another worker is still using.
 */
export async function ensureInsightsUser(
	api: FrappeApi,
	credentials: Credentials,
	role = 'Insights User',
): Promise<void> {
	const email = credentials.usr
	const profile = {
		enabled: 1,
		user_type: 'Website User',
		send_welcome_email: 0,
		roles: [{ role }],
	}

	if (await api.docExists(DOCTYPE.USER, email)) {
		await api.updateDoc(DOCTYPE.USER, email, profile)
		return
	}

	await api.createDoc(DOCTYPE.USER, {
		email,
		first_name: 'E2E',
		last_name: 'Viewer',
		new_password: credentials.pwd,
		...profile,
	})
}
