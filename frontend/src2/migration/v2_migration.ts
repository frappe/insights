import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { getErrorMessage } from '../helpers'
import { __ } from '../translation'

export type MigrationVerdict = 'ready' | 'review' | 'migrated' | 'unreadable'

export type MigrationNote = {
	kind: string
	/** The docname the translator raised it against. */
	source: string
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
	chart_count: number
	charts_carried: number
	items: MigrationItem[]
	queries: QuerySection[]
	migrated_workbook: string | null
	migrated_dashboard: string | null
	verification: VerificationSummary | null
}

export type MigrationState = 'not_started' | 'queued' | 'in_progress' | 'failed' | 'migrated'

/** One dashboard the server would not take, and why. */
export type MigrationSkip = { dashboard: string; reason: string; detail: string }

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

/** What v3 says about offering the migration. The rule is the server's - see
 * `get_v2_migration_nudge` - and this is where both v3 surfaces read it, so the
 * banner and the migration page cannot disagree about it inside one session. */
export type MigrationNudge = {
	show: boolean
	waiting: number
	canMigrate: boolean
	hidden: boolean
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
	let scanTimer: ReturnType<typeof setTimeout> | undefined

	const nudge = reactive<MigrationNudge>({
		show: false,
		waiting: 0,
		canMigrate: false,
		hidden: false,
	})

	async function loadNudge() {
		try {
			const data: any = await call('insights.api.v2_migration.get_v2_migration_nudge')
			nudge.show = Boolean(data?.show)
			nudge.waiting = data?.waiting || 0
			nudge.canMigrate = Boolean(data?.can_migrate)
			nudge.hidden = Boolean(data?.hidden)
		} catch {
			// An Insights without the migrator answers 404, which is not a
			// failure: nothing is offered, and the surfaces render nothing.
		}
		return nudge
	}

	/** Hiding reaches every user on the site, so the way back has to reach them
	 * too. Both directions are the one endpoint. */
	async function setNudgeHidden(hidden: boolean) {
		// A real boolean, not 1/0: `call` posts JSON, and frappe reads a JSON
		// `false` as False. A string "0" would come back True.
		await call('insights.api.v2_migration.set_v2_migration_nudge', { hidden })
		nudge.hidden = hidden
		if (hidden) nudge.show = false
		else await loadNudge()
	}

	/** The server builds the triage on a worker, so this asks and then keeps
	 * asking until it is built. A refresh serves the rows it already has while
	 * the new ones are built, so the page dims instead of emptying. */
	function scan(refresh = false) {
		stopScanPolling()
		scanning.value = true
		scanError.value = ''
		return readScan(refresh)
	}

	async function readScan(refresh: boolean) {
		try {
			const data: any = await call('insights.api.v2_migration.scan_v2_dashboards', {
				refresh: refresh ? 1 : 0,
			})
			unavailable.value = !data?.available
			applyScan((data?.dashboards || []) as DashboardScan[])
			scannedAt.value = data?.scanned_at || ''

			if (data?.status === 'scanning') {
				scanTimer = setTimeout(() => readScan(false), POLL_INTERVAL)
				return dashboards.value
			}

			scanning.value = false
			if (data?.status === 'failed') scanError.value = data?.error || ''
			return dashboards.value
		} catch (err: any) {
			scanning.value = false
			const message = getErrorMessage(err)
			dashboards.value = []
			if (isMissingDoctype(message)) {
				unavailable.value = true
			} else {
				scanError.value = message
			}
			return []
		}
	}

	function applyScan(rows: DashboardScan[]) {
		dashboards.value = rows
		// A dashboard migrated by an earlier visit has no live job, so the scan
		// itself is what marks it done.
		rows.forEach((d) => {
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
	}

	function stopScanPolling() {
		if (scanTimer) clearTimeout(scanTimer)
		scanTimer = undefined
	}

	async function getVerification(dashboard: string): Promise<Verification | null> {
		return call('insights.api.v2_migration.get_v2_verification', { dashboard })
	}

	async function migrateDashboards(names: string[]) {
		const accepted: string[] = []
		const skipped: MigrationSkip[] = []
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
		nudge,
		loadNudge,
		setNudgeHidden,
		scan,
		stopScanPolling,
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
	migrated: __('Migrated'),
	unreadable: __('Could not be read'),
}

/** Badge only accepts its own themes, so a plain `string` will not type-check. */
export type BadgeTheme = 'green' | 'orange' | 'red' | 'gray' | 'blue'

export const VERDICT_THEMES: Record<MigrationVerdict, BadgeTheme> = {
	ready: 'green',
	review: 'orange',
	migrated: 'gray',
	unreadable: 'red',
}

/** Why the server would not take a dashboard the user selected.
 *
 * `migrate_v2_dashboards` answers per dashboard so the caller can say what
 * happened to a selection. The reasons are its own vocabulary, so they are
 * spelled out here beside every other kind rather than in the page.
 */
const SKIP_PHRASES: Record<string, (count: number) => string> = {
	not_found: (n) =>
		n === 1 ? __('1 is no longer in v2.') : __('{0} are no longer in v2.', String(n)),
	already_migrated: (n) =>
		n === 1 ? __('1 is already migrated.') : __('{0} are already migrated.', String(n)),
	in_progress: (n) =>
		n === 1
			? __('1 is already being migrated.')
			: __('{0} are already being migrated.', String(n)),
	unknown: (n) =>
		n === 1 ? __('1 could not be started.') : __('{0} could not be started.', String(n)),
}

export function skipSentence(skipped: MigrationSkip[]) {
	if (!skipped.length) return ''
	const counts: Record<string, number> = {}
	skipped.forEach((entry) => {
		const reason = entry.reason in SKIP_PHRASES ? entry.reason : 'unknown'
		counts[reason] = (counts[reason] || 0) + 1
	})
	return Object.entries(counts)
		.map(([reason, count]) => SKIP_PHRASES[reason](count))
		.join(' ')
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
	unsupported_chart_type: __("v3 has no such chart type. The chart is skipped."),
	chart_never_visualized: __('This item has no chart type. There is nothing to carry over.'),
	item_without_query: __('The query it reads was deleted. The item is skipped.'),
	missing_x_axis: __('The horizontal axis has no column. The chart lands empty.'),
	missing_y_axis: __('The vertical axis has no column. The chart lands empty.'),
	missing_label_or_value: __('The label and value columns are not set. The chart lands empty.'),
	missing_value_column: __('The value column is not set. The chart lands empty.'),
	missing_columns: __('The table has no columns. It lands empty.'),
	extra_x_axis_columns: __('v3 draws one horizontal axis. The extra columns are dropped.'),
	extra_y_axis_columns: __('v3 draws one measure here. The extra ones are dropped.'),
	scatter_x_not_numeric: __('A bubble chart needs numbers on both axes. This becomes a line chart.'),
	trend_without_date_column: __('A trend line needs a date column in v3. The trend line is dropped.'),
	progress_target_unsupported: __('v3 has no progress chart. The value carries over, the target does not.'),
	auto_type_guessed: __('v2 picked this chart type from the data. v3 guesses it instead.'),
	auto_type_needs_columns: __('v2 picked this chart type from the data. Set it in v3, or the chart lands empty.'),
	column_types_unknown: __('The column types are unknown. v3 adds the numbers up by default.'),
	column_not_in_query: __('A column it draws is no longer in the query. That part lands empty.'),
	filter_operator_unsupported: __('v3 has no such filter. This filter starts empty.'),
	filter_link_dangling: __('A filter points at an item this dashboard no longer has.'),
	// the dashboard
	public_not_carried: __('The v2 dashboard was public. The v3 copy stays private until you publish it.'),
	circular_query_reference: __('Its queries reference each other in a loop. It cannot be migrated.'),
	// the query behind it
	sql_floor: __('Part of the query has no v3 form. v3 runs the SQL that v2 ran.'),
	dropped_filter: __('A filter has no v3 form and is dropped. This shows more rows than v2.'),
	dropped_column: __('A column has no v3 form and is dropped.'),
	dropped_transform: __('A step that v2 ran after the query has no v3 form. It is dropped.'),
	untranslatable_expression: __('A formula has no v3 form. v3 runs it as SQL.'),
	expression_needs_sql: __('A formula has no v3 form. v3 runs it as SQL.'),
	unknown_operator: __('A filter uses an operator that v3 does not have. It is dropped.'),
	unknown_aggregation: __('A column is summed up in a way that v3 does not have.'),
	unknown_granularity: __('A date is grouped by a period that v3 does not have.'),
	unknown_join_type: __('A join has no v3 form. It is dropped.'),
	no_source_table: __('The query names no table. It returns nothing.'),
	unreadable_json: __('The query is stored in a form that v3 cannot read.'),
	empty_script: __('The script is empty. It returns nothing.'),
	legacy_column_list: __('The query is in an old v2 format. Its columns are read as written.'),
	legacy_query: __("This query is in v2's oldest format. v3 runs the SQL that v2 ran."),
	no_compiled_sql: __(
		'This query has no v3 form, and v2 kept no SQL to fall back on. It returns nothing.',
	),
	unresolved_query_reference: __(
		'It reads another v2 query that is not part of this migration. That part returns nothing.',
	),
	invalid_join: __('A join names no table or no column. v2 skipped it too, so nothing changes.'),
	broken_filter: __(
		'A filter value does not fit its column. The filter is dropped, so this shows more rows than v2.',
	),
	broken_in_v2: __('A formula that did not work in v2 either. It is dropped.'),
	ambiguous_fragment: __(
		'A formula names a column that more than one table has. v3 picks one, which may be the wrong one.',
	),
	grouped_loose_column: __(
		'v2 showed this column without grouping by it. v3 groups by it, so there may be fewer rows.',
	),
	ignored_granularity: __('A date grouping that v2 did not apply. v3 does not apply it either.'),
	granularity_part_type: __('This date part shows as a number in v3, where v2 showed text.'),
	unsupported_transform: __('v3 has no such step. The query carries over without it.'),
	cumulative_without_order: __(
		'The running total has no sort order, so its numbers can come out in a different order.',
	),
	cumulative_column_renamed: __(
		'The running total lands in a new column in v3, beside the original.',
	),
	script_result_shape: __(
		'If the script returns a list of lists, its first row becomes data in v3. Return a DataFrame instead.',
	),
	script_calls_get_query_results: __(
		'The script reads another v2 query with `get_query_results`, which v3 does not have. Point it at the migrated query.',
	),
	variable_value_unreadable: __(
		'A script variable has no readable value in v2. It is not carried, and the script fails on its name.',
	),
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

	if (scan.verdict === 'unreadable') {
		return __('This dashboard could not be read. Migrate it on its own to see why.')
	}
	if (!total) {
		return __('This dashboard has no charts to carry over.')
	}
	if (carried < total) {
		return __(
			'{0} of {1} charts will carry over. {2} will not.',
			String(carried),
			String(total),
			String(total - carried),
		)
	}
	if (attention) {
		return attention === 1
			? __('All {0} charts will carry over. 1 will look different.', String(total))
			: __(
					'All {0} charts will carry over. {1} will look different.',
					String(total),
					String(attention),
			  )
	}
	return total === 1
		? __('The chart will carry over as it is.')
		: __('All {0} charts will carry over.', String(total))
}

/** What the numbers check found, said the way the page says everything else. */
export function verificationSentence(summary: VerificationSummary | null) {
	if (!summary || !summary.checked) return ''
	const agreed = summary.same + summary.expected
	if (summary.different) {
		return summary.different === 1
			? __('1 chart shows different numbers than v2. Open it to review.')
			: __(
					'{0} charts show different numbers than v2. Open them to review.',
					String(summary.different),
			  )
	}
	if (!agreed) {
		return __('The numbers could not be compared with v2.')
	}
	return __(
		'{0} of {1} queries return the same numbers as v2.',
		String(agreed),
		String(summary.checked),
	)
}
