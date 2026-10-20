import { useStorage } from '@vueuse/core'
import { Building2, Lock, ShieldCheck, Users } from 'lucide-vue-next'
import { computed } from 'vue'
import session from '../session'
import { __ } from '../translation'

/** Where a listed document comes from, relative to the current user. */
export type AccessSource = 'created' | 'shared' | 'others'

/**
 * The Access quick filter. Nothing chosen means every source the user has:
 * created and shared, and for an admin "others" too, so colleagues' work does
 * not look lost. The choice is kept in the browser under `storageKey`.
 */
export function useAccessSources(storageKey: string) {
	const options = computed(() => {
		const list: { label: string; value: AccessSource }[] = [
			{ label: __('Created'), value: 'created' },
			{ label: __('Shared'), value: 'shared' },
		]
		if (session.user.is_admin) list.push({ label: __('Others'), value: 'others' })
		return list
	})
	const selected = useStorage<AccessSource[]>(storageKey, [])
	const shown = computed(() =>
		selected.value.filter((source) => options.value.some((option) => option.value === source)),
	)
	const sources = computed(() =>
		shown.value.length ? shown.value : options.value.map((option) => option.value),
	)
	return { options, selected, shown, sources }
}

export type Shared = {
	shared_with?: string[]
	shared_with_organization?: boolean
	visible_to_roles?: string[]
}

/** The icon and label of who a listed document is shared with. */
export function access(item: Shared, getName: (email: string) => string) {
	if (item.shared_with_organization) return { icon: Building2, label: __('Everyone') }

	const shared = item.shared_with || []
	const people =
		shared.length > 1
			? __('{0} people', String(shared.length))
			: shared.length
			  ? getName(shared[0])
			  : ''
	const roles = item.visible_to_roles || []
	if (roles.length) {
		const label = roles.length > 1 ? __('{0} roles', String(roles.length)) : __(roles[0])
		return { icon: ShieldCheck, label: people ? __('{0}, {1}', label, people) : label }
	}
	if (people) return { icon: Users, label: people }
	return { icon: Lock, label: __('Private') }
}
