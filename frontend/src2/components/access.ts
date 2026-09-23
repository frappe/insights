import { useStorage } from '@vueuse/core'
import { Building2, Lock, Users } from 'lucide-vue-next'
import { computed } from 'vue'
import session from '../session'
import { __ } from '../translation'

/** Where a listed document comes from, relative to the current user. */
export type AccessSource = 'created' | 'shared' | 'others'

const DEFAULT_SOURCES: AccessSource[] = ['created', 'shared']

/**
 * The Access quick filter. Nothing chosen means the default, created and
 * shared, like any other quick filter left empty; only admins get "others".
 * The choice is kept in the browser under `storageKey`.
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
	const sources = computed(() => (shown.value.length ? shown.value : DEFAULT_SOURCES))
	return { options, selected, shown, sources }
}

type Shared = { shared_with?: string[]; shared_with_organization?: boolean }

export function accessIcon(item: Shared) {
	if (item.shared_with_organization) return Building2
	return item.shared_with?.length ? Users : Lock
}

export function accessLabel(item: Shared, getName: (email: string) => string) {
	if (item.shared_with_organization) return __('Everyone')
	if (!item.shared_with?.length) return __('Private')
	return item.shared_with.length > 1
		? __('{0} people', String(item.shared_with.length))
		: getName(item.shared_with[0])
}
