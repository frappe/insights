import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { getErrorMessage } from '../helpers'
import { __ } from '../translation'

export type V2Dashboard = {
	name: string
	title: string
	owner: string
	modified: string
	item_count: number
	query_count: number
	migrated_workbook: string | null
	migrated_dashboard: string | null
}

export type MigrationGap = {
	/** Which translator raised it: the dashboard, an item, or a named query. */
	origin: string
	kind: string
	source: string
	detail: string
	/** A loss the user will see in their numbers, as opposed to a note. */
	dropped: boolean
}

export type DashboardPreview = {
	converts_cleanly: boolean
	counts: Record<string, any>
	gaps: MigrationGap[]
	unresolved_data_sources: string[]
	dropped_queries: string[]
	report: string
}

export type MigrationState = 'not_started' | 'queued' | 'in_progress' | 'failed' | 'migrated'

export type MigrationStatus = {
	status: MigrationState
	workbook: string | null
	dashboard: string | null
	error: string | null
}

export type MigrationSkip = {
	dashboard: string
	reason: 'not_found' | 'already_migrated' | 'in_progress' | string
	detail: string
}

const POLL_INTERVAL = 2000

/** `migrate_v2_dashboards` throws above this, so the store batches rather than
 * making the caller count. */
export const MIGRATION_BATCH_SIZE = 50

/** The v2 doctype is removed code on a site that upgraded, so its absence is a
 * normal answer and not a failure worth a toast. */
function isMissingDoctype(message: string) {
	return /DoesNotExist|1146|doesn't exist|does not exist|no such table/i.test(message)
}

/** A gap arrives flat with an `origin`, but tolerate the `(origin, gap)` pair
 * `all_gaps()` builds in case it is ever passed straight through. */
function normalizeGap(raw: any): MigrationGap {
	const gap = Array.isArray(raw) ? raw[1] : raw
	const origin = Array.isArray(raw) ? raw[0] : (gap?.origin ?? '')
	return {
		origin: String(origin || ''),
		kind: String(gap?.kind || 'unknown'),
		source: String(gap?.source || ''),
		detail: String(gap?.detail || ''),
		dropped: Boolean(gap?.dropped),
	}
}

function makeStore() {
	const dashboards = ref<V2Dashboard[]>([])
	const statuses = reactive<Record<string, MigrationStatus>>({})

	const loading = ref(false)
	const previewing = ref(false)
	const migrating = ref(false)

	/** Set when the site has no v2 doctype at all, which is not a failure. */
	const unavailable = ref(false)
	const loadError = ref('')

	let pollTimer: ReturnType<typeof setTimeout> | undefined

	async function getDashboards(search?: string) {
		loading.value = true
		loadError.value = ''
		try {
			const rows = await call('insights.api.v2_migration.get_v2_dashboards', {
				search: search || undefined,
			})
			dashboards.value = (rows || []) as V2Dashboard[]
			unavailable.value = false
			// A dashboard migrated by an earlier visit has no live job, so the list
			// itself is what marks it done.
			dashboards.value.forEach((d) => {
				if (d.migrated_dashboard) {
					statuses[d.name] = {
						status: 'migrated',
						workbook: d.migrated_workbook,
						dashboard: d.migrated_dashboard,
						error: null,
					}
				}
			})
			return dashboards.value
		} catch (err: any) {
			const message = getErrorMessage(err)
			dashboards.value = []
			if (isMissingDoctype(message)) {
				unavailable.value = true
			} else {
				loadError.value = message
			}
			return []
		} finally {
			loading.value = false
		}
	}

	async function previewDashboard(dashboard: string): Promise<DashboardPreview> {
		previewing.value = true
		try {
			const data: any = await call('insights.api.v2_migration.preview_v2_dashboard', {
				dashboard,
			})
			return {
				converts_cleanly: Boolean(data?.converts_cleanly),
				counts: data?.counts || {},
				gaps: (data?.gaps || []).map(normalizeGap),
				unresolved_data_sources: data?.unresolved_data_sources || [],
				dropped_queries: data?.dropped_queries || [],
				report: String(data?.report || ''),
			}
		} finally {
			previewing.value = false
		}
	}

	async function migrateDashboards(names: string[]) {
		const accepted: string[] = []
		const skipped: MigrationSkip[] = []
		if (!names.length) return { accepted, skipped }

		migrating.value = true
		try {
			for (let i = 0; i < names.length; i += MIGRATION_BATCH_SIZE) {
				const batch = names.slice(i, i + MIGRATION_BATCH_SIZE)
				const data: any = await call(
					'insights.api.v2_migration.migrate_v2_dashboards',
					{ dashboards: batch },
				)
				accepted.push(...(data?.accepted || []))
				skipped.push(...(data?.skipped || []))
			}
			accepted.forEach((name) => {
				statuses[name] = {
					status: 'queued',
					workbook: null,
					dashboard: null,
					error: null,
				}
			})
			startPolling()
			return { accepted, skipped }
		} finally {
			migrating.value = false
		}
	}

	function pendingNames() {
		return Object.keys(statuses).filter(
			(name) => statuses[name].status === 'queued' || statuses[name].status === 'in_progress',
		)
	}

	async function refreshStatus(names?: string[]) {
		const wanted = names ?? pendingNames()
		if (!wanted.length) return
		const data: any = await call('insights.api.v2_migration.get_v2_migration_status', {
			dashboards: wanted,
		})
		Object.entries(data || {}).forEach(([name, status]) => {
			statuses[name] = status as MigrationStatus
		})
	}

	function startPolling() {
		stopPolling()
		const tick = async () => {
			if (!pendingNames().length) return
			try {
				await refreshStatus()
			} catch {
				// A single failed poll is not worth interrupting the user over; the
				// next tick asks again.
			}
			if (pendingNames().length) {
				pollTimer = setTimeout(tick, POLL_INTERVAL)
			} else {
				// The rows carry `migrated_workbook`, so the list has to be re-read
				// once the queue drains or it stays stale.
				getDashboards()
			}
		}
		pollTimer = setTimeout(tick, POLL_INTERVAL)
	}

	function stopPolling() {
		if (pollTimer) clearTimeout(pollTimer)
		pollTimer = undefined
	}

	return reactive({
		dashboards,
		statuses,
		loading,
		previewing,
		migrating,
		unavailable,
		loadError,
		getDashboards,
		previewDashboard,
		migrateDashboards,
		refreshStatus,
		startPolling,
		stopPolling,
	})
}

let store: ReturnType<typeof makeStore> | undefined
export default function useV2MigrationStore() {
	if (!store) store = makeStore()
	return store
}

// -- reading the numbers ----------------------------------------------------

export type CountCard = {
	label: string
	value: string
	detail: string
}

const QUERY_KIND_LABELS: Record<string, string> = {
	builder: __('builder'),
	sql: __('SQL'),
	code: __('script'),
	none: __('unconvertible'),
}

function humanize(key: string) {
	return key.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
}

/** `counts` arrives nested - `{queries: {...}, items: {...}}` - so it is read
 * into cards rather than printed as it is. */
export function summarizeCounts(counts: Record<string, any>): CountCard[] {
	const cards: CountCard[] = []

	const queries = counts?.queries
	if (queries && typeof queries === 'object') {
		const kinds = Object.entries(QUERY_KIND_LABELS)
			.filter(([kind]) => Number(queries[kind]) > 0)
			.map(([kind, label]) => `${queries[kind]} ${label}`)
		cards.push({
			label: __('Queries'),
			value: String(queries.total ?? 0),
			detail: kinds.join(', '),
		})
	} else if (queries !== undefined) {
		cards.push({ label: __('Queries'), value: String(queries), detail: '' })
	}

	const items = counts?.items
	if (items && typeof items === 'object') {
		const total = Number(items.total ?? 0)
		const converted = Number(items.converted ?? 0)
		const dropped = Number(items.dropped ?? 0)
		cards.push({
			label: __('Dashboard items'),
			value: __('{0} of {1}', String(converted), String(total)),
			detail: dropped ? __('{0} dropped', String(dropped)) : __('all converted'),
		})
	} else if (items !== undefined) {
		cards.push({ label: __('Dashboard items'), value: String(items), detail: '' })
	}

	Object.entries(counts || {}).forEach(([key, value]) => {
		if (key === 'queries' || key === 'items') return
		if (typeof value !== 'number' && typeof value !== 'string') return
		cards.push({ label: humanize(key), value: String(value), detail: '' })
	})

	return cards
}

const GAP_LABELS: Record<string, string> = {
	missing_x_axis: __('Chart has no X axis'),
	missing_y_axis: __('Chart has no Y axis'),
	missing_label_or_value: __('Chart has no label or value'),
	missing_value_column: __('Chart has no value column'),
	extra_y_axis_columns: __('Extra measures dropped'),
	unresolved_data_source: __('Data source not found in v3'),
}

/** A gap kind reads as a slug; a person reads a phrase. */
export function gapLabel(kind: string) {
	return GAP_LABELS[kind] || humanize(kind)
}

const ORIGIN_LABELS: Record<string, string> = {
	dashboard: __('Dashboard'),
	item: __('Dashboard item'),
}

export function originLabel(origin: string) {
	if (!origin) return __('Dashboard')
	if (ORIGIN_LABELS[origin]) return ORIGIN_LABELS[origin]
	if (origin.startsWith('query ')) return `${__('Query')} ${origin.slice(6)}`
	return humanize(origin)
}
