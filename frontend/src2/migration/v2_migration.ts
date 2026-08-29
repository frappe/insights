import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { getErrorMessage } from '../helpers'
import { __ } from '../translation'

export type MigrationVerdict = 'ready' | 'review' | 'blocked' | 'migrated' | 'unreadable'

export type MigrationNote = {
	kind: string
	/** The docname the translator raised it against. */
	source: string
	/** The translator's own words. Kept for the copied report, not shown. */
	detail: string
	/** A loss the user will see in their numbers, as opposed to a note. */
	dropped: boolean
	/** Set when the note came from a query rather than from the item itself. */
	query: string
}

export type MigrationItem = {
	key: string
	title: string
	kind: 'chart' | 'filter' | 'text'
	state: 'ok' | 'changed' | 'dropped'
	notes: MigrationNote[]
}

export type QuerySection = {
	query: string
	title: string
	notes: MigrationNote[]
}

export type DashboardScan = {
	dashboard: string
	title: string
	verdict: MigrationVerdict
	converts_cleanly: boolean
	chart_count: number
	charts_carried: number
	items: MigrationItem[]
	queries: QuerySection[]
	counts: Record<string, any>
	unresolved_data_sources: string[]
	dropped_queries: string[]
	report: string
	migrated_workbook: string | null
	migrated_dashboard: string | null
	verification: VerificationSummary | null
}

export type MigrationState = 'not_started' | 'queued' | 'in_progress' | 'failed' | 'migrated'

export type VerificationSummary = {
	checked: number
	same: number
	expected: number
	different: number
	not_checked: number
	differing_charts: string[]
}

export type MigrationStatus = {
	status: MigrationState
	workbook: string | null
	dashboard: string | null
	error: string | null
	verification: VerificationSummary | null
}

export type VerifiedQuery = {
	query: string
	target: string | null
	charts: string[]
	verdict: string
	reason: string
	differences: { kind: string; detail: string; column: string }[]
}

export type Verification = VerificationSummary & {
	dashboard: string
	workbook: string | null
	checked_at: string
	queries: VerifiedQuery[]
	report: string
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

function makeStore() {
	const dashboards = ref<DashboardScan[]>([])
	const statuses = reactive<Record<string, MigrationStatus>>({})
	const scannedAt = ref('')

	const scanning = ref(false)
	const migrating = ref(false)

	/** Set when the site has no v2 doctype at all, which is not a failure. */
	const unavailable = ref(false)
	const scanError = ref('')

	let pollTimer: ReturnType<typeof setTimeout> | undefined

	async function scan(refresh = false) {
		scanning.value = true
		scanError.value = ''
		try {
			const data: any = await call('insights.api.v2_migration.scan_v2_dashboards', {
				refresh: refresh ? 1 : 0,
			})
			unavailable.value = !data?.available
			dashboards.value = (data?.dashboards || []) as DashboardScan[]
			scannedAt.value = data?.scanned_at || ''
			// A dashboard migrated by an earlier visit has no live job, so the scan
			// itself is what marks it done.
			dashboards.value.forEach((d) => {
				if (d.migrated_dashboard) {
					statuses[d.dashboard] = {
						status: 'migrated',
						workbook: d.migrated_workbook,
						dashboard: d.migrated_dashboard,
						error: null,
						verification: d.verification,
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
				scanError.value = message
			}
			return []
		} finally {
			scanning.value = false
		}
	}

	async function getVerification(dashboard: string): Promise<Verification | null> {
		return call('insights.api.v2_migration.get_v2_verification', { dashboard })
	}

	async function migrateDashboards(names: string[]) {
		const accepted: string[] = []
		const skipped: { dashboard: string; reason: string; detail: string }[] = []
		if (!names.length) return { accepted, skipped }

		migrating.value = true
		try {
			for (let i = 0; i < names.length; i += MIGRATION_BATCH_SIZE) {
				const batch = names.slice(i, i + MIGRATION_BATCH_SIZE)
				const data: any = await call('insights.api.v2_migration.migrate_v2_dashboards', {
					dashboards: batch,
				})
				accepted.push(...(data?.accepted || []))
				skipped.push(...(data?.skipped || []))
			}
			accepted.forEach((name) => {
				statuses[name] = {
					status: 'queued',
					workbook: null,
					dashboard: null,
					error: null,
					verification: null,
				}
			})
			startPolling()
			return { accepted, skipped }
		} finally {
			migrating.value = false
		}
	}

	function stateOf(dashboard: string): MigrationState {
		return statuses[dashboard]?.status || 'not_started'
	}

	function pendingNames() {
		return Object.keys(statuses).filter(
			(name) => statuses[name].status === 'queued' || statuses[name].status === 'in_progress',
		)
	}

	/** `get_v2_migration_status` bounds its list the same way the write does, so
	 * a poll over more than one batch has to ask in batches too. */
	async function refreshStatus(names?: string[]) {
		const wanted = names ?? pendingNames()
		for (let i = 0; i < wanted.length; i += MIGRATION_BATCH_SIZE) {
			const data: any = await call('insights.api.v2_migration.get_v2_migration_status', {
				dashboards: wanted.slice(i, i + MIGRATION_BATCH_SIZE),
			})
			Object.entries(data || {}).forEach(([name, status]) => {
				statuses[name] = status as MigrationStatus
			})
		}
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
				// The scan carries the verdict, and the queue just changed one of
				// them, so it has to be read again or the page stays stale.
				scan(true)
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
		scannedAt,
		scanning,
		migrating,
		unavailable,
		scanError,
		scan,
		stateOf,
		getVerification,
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

// -- saying it in words -----------------------------------------------------

export const VERDICT_LABELS: Record<MigrationVerdict, string> = {
	ready: __('Ready to migrate'),
	review: __('Needs review'),
	blocked: __("Can't migrate yet"),
	migrated: __('Migrated'),
	unreadable: __("Can't migrate yet"),
}

/** What one finding means for the dashboard, said as a whole sentence.
 *
 * The translators name a gap by what they hit - `missing_x_axis`,
 * `sql_floor` - which is a fact about the translation. A reader wants the
 * consequence, so every kind is spelled out here and nowhere else. A kind with
 * no sentence yet falls back to the translator's own detail, which is at least
 * true.
 */
const NOTE_SENTENCES: Record<string, string> = {
	// the chart itself
	unsupported_chart_type: __("this chart type doesn't exist in v3, so the chart is skipped"),
	chart_never_visualized: __('this item was never given a chart type, so there is nothing to carry over'),
	item_without_query: __('the query this reads was deleted, so the item is skipped'),
	missing_x_axis: __('no column was set for the horizontal axis, so the chart lands empty'),
	missing_y_axis: __('no column was set for the vertical axis, so the chart lands empty'),
	missing_label_or_value: __('no label or value column was set, so the chart lands empty'),
	missing_value_column: __('no value column was set, so the chart lands empty'),
	missing_columns: __('no columns were set, so the table lands empty'),
	extra_x_axis_columns: __('v3 draws one horizontal axis, so the extra columns are dropped'),
	extra_y_axis_columns: __('v3 draws one measure here, so the extra ones are dropped'),
	scatter_x_not_numeric: __('v3 plots a bubble chart over numbers, so this becomes a line chart'),
	trend_without_date_column: __("the trend line won't carry over: v3 compares over a date column"),
	progress_target_unsupported: __('v3 has no progress chart: the value carries over, the target does not'),
	reference_line_is_a_statistic: __('v3 draws a reference line at a fixed value, not at an average'),
	auto_type_guessed: __('v2 picked this chart type from the data, so v3 guesses it instead'),
	auto_type_needs_columns: __('v2 picked this chart type from the data, so it lands empty until you set it'),
	column_types_unknown: __('the column types are unknown, so numbers are added up by default'),
	column_not_in_query: __('a column it draws is no longer in the query, so that part lands empty'),
	filter_operator_unsupported: __('v3 has no such filter, so this filter starts empty'),
	filter_link_dangling: __('a filter points at an item this dashboard no longer has'),
	// the dashboard
	public_not_carried: __('the v2 dashboard was public; the v3 copy is private until you publish it'),
	circular_query_reference: __('its queries reference each other in a loop, so it cannot be migrated'),
	unresolved_data_source: __('its data source is not set up in v3 yet'),
	// the query behind it
	sql_floor: __('part of the query has no v3 form, so v3 runs the SQL v2 ran instead'),
	dropped_filter: __('a filter has no v3 form and is dropped, so this shows more rows than v2'),
	dropped_column: __('a column has no v3 form and is dropped'),
	dropped_transform: __('a step v2 ran after the query has no v3 form and is dropped'),
	untranslatable_expression: __('a formula has no v3 form, so v3 runs it as SQL instead'),
	expression_needs_sql: __('a formula has no v3 form, so v3 runs it as SQL instead'),
	unknown_operator: __('a filter uses an operator v3 does not have, so it is dropped'),
	unknown_aggregation: __('a column is summed up in a way v3 does not have'),
	unknown_granularity: __('a date is grouped by a period v3 does not have'),
	unknown_join_type: __('a join has no v3 form, so it is dropped'),
	no_source_table: __('the query names no table, so it returns nothing'),
	unreadable_json: __('the query is stored in a form v3 cannot read'),
	empty_script: __('the script is empty, so it returns nothing'),
	legacy_column_list: __('the query is in an old v2 format; its columns are read as written'),
}

export function noteSentence(note: MigrationNote) {
	const sentence = NOTE_SENTENCES[note.kind]
	if (!sentence) return note.detail
	if (note.query) return __('{0} (from the query {1})', sentence, note.query)
	return sentence
}

const ITEM_FALLBACK_TITLES: Record<MigrationItem['kind'], string> = {
	chart: __('Untitled chart'),
	filter: __('Filter'),
	text: __('Text'),
}

export function itemTitle(item: MigrationItem) {
	return item.title || ITEM_FALLBACK_TITLES[item.kind]
}

/** One sentence for the whole dashboard - the only headline the page shows. */
export function verdictSentence(scan: DashboardScan) {
	const total = scan.chart_count
	const carried = scan.charts_carried
	const attention = scan.items.filter((item) => item.state !== 'ok').length

	if (scan.verdict === 'blocked') {
		return __('Set up its data source in v3, then scan again.')
	}
	if (scan.verdict === 'unreadable') {
		return __('This dashboard could not be read. Migrate it on its own to see why.')
	}
	if (!total) {
		return __('This dashboard has no charts to carry over.')
	}
	if (carried < total) {
		return __(
			'{0} of {1} charts will carry over - {2} need your attention',
			String(carried),
			String(total),
			String(total - carried),
		)
	}
	if (attention) {
		return __(
			'All {0} charts will carry over - {1} need your attention',
			String(total),
			String(attention),
		)
	}
	return total === 1
		? __('The chart will carry over as it is')
		: __('All {0} charts will carry over', String(total))
}

/** What the numbers check found, said the way the page says everything else. */
export function verificationSentence(summary: VerificationSummary | null) {
	if (!summary || !summary.checked) return ''
	const agreed = summary.same + summary.expected
	if (summary.different) {
		return summary.different === 1
			? __('1 chart shows different numbers than v2 - open it to review')
			: __(
					'{0} charts show different numbers than v2 - open them to review',
					String(summary.different),
			  )
	}
	if (!agreed) {
		return __('The numbers could not be checked against v2.')
	}
	return __('We checked the numbers - {0} of {1} queries match v2', String(agreed), String(summary.checked))
}
