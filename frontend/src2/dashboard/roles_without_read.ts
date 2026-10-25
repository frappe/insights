import { __ } from '../translation'
import { listOf } from '../upgrade/upgrade_steps'

/** Each role chosen to share a dashboard with that can't read what its charts read, and the doctypes it needs. */
export type RolesWithoutRead = Record<string, string[]>

/** One line per role, as the share dialog warns of them before it saves. */
export function rolesWithoutReadLines(roles: RolesWithoutRead): string[] {
	return Object.entries(roles).map(([role, doctypes]) =>
		__('{0} can’t read {1}.', role, listOf(doctypes)),
	)
}
