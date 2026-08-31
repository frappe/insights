<script setup lang="tsx">
import { Badge, ListEmptyState, ListHeader, ListRows, ListSelectBanner, ListView } from 'frappe-ui'
import { CircleHelp, SearchIcon } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getErrorMessage } from '../helpers'
import { createToast } from '../helpers/toasts'
import { useTelemetry } from '../telemetry'
import { __ } from '../translation'
import { settingsOpenedFrom, showSettingsDialog } from './settings'
import MigrationDashboard from '../migration/MigrationDashboard.vue'
import useV2MigrationStore, {
	DashboardScan,
	BadgeTheme,
	VERDICT_LABELS,
	VERDICT_THEMES,
	skipSentence,
	verdictSentence,
	verificationSentence,
} from '../migration/v2_migration'

const router = useRouter()
const store = useV2MigrationStore()
const { capture } = useTelemetry()

onMounted(() => {
	// Which surface brought the admin here decides whether the v2 nudge earned
	// its place. The server cannot answer it: one endpoint answers both apps.
	capture('v2_migration_page_opened', { from: settingsOpenedFrom.value || 'settings' })
	settingsOpenedFrom.value = ''
	store.scan()
	store.loadNudge()
	store.startPolling()
})
onBeforeUnmount(() => store.stopPolling())

// Hiding the reminder reaches every user on the site and is one click away in
// the sidebar. This is the way back, on the page that owns the migration.
const restoring = ref(false)
async function restoreNudge() {
	restoring.value = true
	try {
		await store.setNudgeHidden(false)
	} finally {
		restoring.value = false
	}
}

/** What a row is right now. A verdict, except that the job outranks the verdict
 * the scan recorded before the job started - it ran later, and it wrote. */
type RowState = 'ready' | 'review' | 'unreadable' | 'migrating' | 'failed' | 'migrated'

const STATE_LABELS: Record<RowState, string> = {
	...VERDICT_LABELS,
	migrating: __('Migrating'),
	failed: __('Could not migrate'),
}

const STATE_THEMES: Record<RowState, BadgeTheme> = {
	...VERDICT_THEMES,
	migrating: 'blue',
	failed: 'red',
}

/** What the user can still act on. A failure is one of them: nothing holds the
 * reason for long, so running it again is the only way to learn more. */
const MIGRATABLE: RowState[] = ['ready', 'review', 'failed']

type Row = DashboardScan & { state: RowState; sentence: string }

function stateOf(dashboard: DashboardScan): RowState {
	const job = store.stateOf(dashboard.dashboard)
	if (job === 'queued' || job === 'in_progress') return 'migrating'
	if (job === 'failed') return 'failed'
	return dashboard.verdict as RowState
}

function sentenceOf(dashboard: DashboardScan, state: RowState) {
	if (state === 'migrating') return __('Migrating now')
	if (state === 'failed') {
		// The job's own last line. It is the only account of the failure that
		// exists - RQ expires the record, and nothing else stored it.
		return (
			store.statuses[dashboard.dashboard]?.error ||
			__('The migration stopped before it wrote anything. Try it again.')
		)
	}
	if (state === 'migrated') {
		return verificationSentence(dashboard.verification) || __('Copied into a v3 workbook.')
	}
	return verdictSentence(dashboard)
}

const allRows = computed<Row[]>(() =>
	store.dashboards.map((d: DashboardScan) => {
		const state = stateOf(d)
		return { ...d, state, sentence: sentenceOf(d, state) }
	}),
)

// -- filtering --------------------------------------------------------------

const searchQuery = ref('')
const stateFilter = ref<RowState | 'all'>('all')

const filterOptions = computed(() => [
	{ label: __('All'), value: 'all' },
	...(['ready', 'review', 'unreadable', 'migrating', 'failed', 'migrated'] as RowState[]).map(
		(state) => ({
			label: STATE_LABELS[state],
			value: state,
		}),
	),
])

const rows = computed(() => {
	const term = searchQuery.value.toLowerCase().trim()
	return allRows.value.filter((row) => {
		if (stateFilter.value !== 'all' && row.state !== stateFilter.value) return false
		if (!term) return true
		return row.title.toLowerCase().includes(term)
	})
})

const emptyState = computed(() => {
	if (searchQuery.value.trim()) {
		return {
			title: __('No Matches'),
			description: __('No dashboard matches your search.'),
		}
	}
	if (stateFilter.value !== 'all') {
		return {
			title: __('Nothing Here'),
			description: __('No dashboard is {0}.', STATE_LABELS[stateFilter.value].toLowerCase()),
		}
	}
	return {
		title: __('No v2 Dashboards'),
		description: __('This site has no Insights v2 dashboards to migrate.'),
	}
})

const selected = ref<Set<string>>(new Set())

const listOptions = computed(() => ({
	columns: [
		{ label: __('Dashboard'), key: 'title', width: 2 },
		{
			label: __('Status'),
			key: 'state',
			// the badge carries the label; without this the cell prints it again
			// beside the badge, and dropping it falls back to the raw state key
			getLabel: () => '',
			prefix: (props: any) => {
				const state = props.row.state as RowState
				return (
					<Badge
						theme={STATE_THEMES[state]}
						variant="subtle"
						label={STATE_LABELS[state]}
					/>
				)
			},
		},
		{ label: __('What happens'), key: 'sentence', width: 3 },
	],
	rows: rows.value,
	rowKey: 'dashboard',
	options: {
		showTooltip: false,
		selectable: true,
		onRowClick: (row: Row) => openDashboard(row),
		selectionText: (count: number) =>
			count === 1 ? __('1 dashboard selected') : __('{0} dashboards selected', String(count)),
	},
}))

/** This tab lives inside the settings dialog, which owns the viewport. A route
 * pushed under it would open behind it, so the dialog closes first. */
function leaveSettings(path: string) {
	showSettingsDialog.value = false
	router.push(path)
}

// -- opening one ------------------------------------------------------------

const opened = ref<DashboardScan | null>(null)
const showDialog = ref(false)
const showHelp = ref(false)

function openDashboard(row: DashboardScan) {
	opened.value = store.dashboards.find((d: DashboardScan) => d.dashboard === row.dashboard) || row
	showDialog.value = true
	// The page is built on the bet that people read what happens before they
	// move anything. This is the only measure of whether they do.
	capture('v2_migration_dashboard_opened', { verdict: row.verdict })
}

function openInV3(dashboard: DashboardScan) {
	if (!dashboard.migrated_workbook) return
	// The end of the funnel: a migrated dashboard somebody actually looked at.
	capture('v2_migration_opened_in_v3', {
		different: dashboard.verification?.different ?? 0,
	})
	showDialog.value = false
	leaveSettings(
		dashboard.migrated_dashboard
			? `/workbook/${dashboard.migrated_workbook}/dashboard/${dashboard.migrated_dashboard}`
			: `/workbook/${dashboard.migrated_workbook}`,
	)
}

// -- migrating --------------------------------------------------------------

const showConfirm = ref(false)
const confirmTargets = ref<Row[]>([])

// One list means a selection can hold rows there is nothing left to do to. They
// are dropped here and counted in one line, rather than sorted into a taxonomy
// the user has to read.
const willMigrate = computed(() => confirmTargets.value.filter((d) => MIGRATABLE.includes(d.state)))
const willSkip = computed(() => confirmTargets.value.length - willMigrate.value.length)

function migrateSelected() {
	confirmTargets.value = allRows.value.filter((row) => selected.value.has(row.dashboard))
	showConfirm.value = true
}

/** The drill-down has already named every chart and what happens to it, so a
 * confirm on top of it would ask the same question twice. */
function migrateOne(dashboard: DashboardScan) {
	migrate(allRows.value.filter((row) => row.dashboard === dashboard.dashboard))
}

async function migrate(targets: Row[]) {
	const names = targets.filter((d) => MIGRATABLE.includes(d.state)).map((d) => d.dashboard)
	if (!names.length) return
	try {
		const { accepted, skipped } = await store.migrateDashboards(names)
		showConfirm.value = false
		showDialog.value = false
		selected.value = new Set()

		// The server decides what it takes, and it says why it refused the rest.
		// The page selected these rows, so it owes the user that answer.
		const refused = skipSentence(skipped)
		if (!accepted.length) {
			createToast({
				variant: 'info',
				title: __('Nothing to migrate'),
				message: refused || __('None of these could be started.'),
			})
			return
		}

		const started =
			accepted.length === 1
				? __('1 dashboard is being copied into v3.')
				: __('{0} dashboards are being copied into v3.', String(accepted.length))
		createToast({
			variant: 'success',
			title: __('Migration started'),
			message: refused ? `${started} ${refused}` : started,
		})
	} catch (err: any) {
		createToast({
			variant: 'error',
			title: __('Could not start the migration'),
			message: getErrorMessage(err),
		})
	}
}
</script>

<template>
	<div class="flex h-full w-full flex-col gap-3 overflow-x-hidden p-8 px-10">
		<div class="flex flex-shrink-0 items-center justify-between gap-2">
			<h1 class="text-xl font-semibold">{{ __('Migrate from v2') }}</h1>
			<div class="flex items-center gap-2">
				<Button variant="ghost" :tooltip="__('How this works')" @click="showHelp = true">
					<template #icon>
						<CircleHelp class="h-4 w-4" />
					</template>
				</Button>
				<Button
					:label="__('Scan again')"
					variant="outline"
					:loading="store.scanning"
					@click="store.scan(true)"
				/>
				<Button
					:label="__('Migrate')"
					variant="solid"
					:disabled="!selected.size"
					:tooltip="!selected.size ? __('Select the dashboards to migrate first') : ''"
					@click="migrateSelected"
				/>
			</div>
		</div>

		<div
			v-if="store.nudge.hidden"
			class="flex flex-shrink-0 items-center justify-between gap-2 rounded border border-outline-gray-2 bg-surface-gray-1 px-4 py-2.5"
		>
			<p class="text-p-sm text-ink-gray-6">
				{{ __('The reminder to move from v2 is hidden for everyone on this site.') }}
			</p>
			<Button
				:label="__('Show it again')"
				variant="outline"
				:loading="restoring"
				@click="restoreNudge"
			/>
		</div>

		<div
			v-if="store.scanError"
			class="rounded border border-outline-gray-2 bg-surface-gray-1 p-4"
		>
			<p class="text-p-base font-medium text-ink-red-5">
				{{ __('The v2 dashboards could not be read') }}
			</p>
			<p class="text-p-sm text-ink-gray-6">{{ store.scanError }}</p>
		</div>

		<div v-else-if="store.scanning && !store.dashboards.length" class="flex items-center gap-2">
			<LoadingIndicator class="h-4 w-4" />
			<span class="text-p-base text-ink-gray-6">
				{{ __('Checking what will carry over') }}
			</span>
		</div>

		<template v-else>
			<div class="flex items-center gap-2 overflow-visible py-1">
				<FormControl
					class="w-64"
					:placeholder="__('Search by title')"
					v-model="searchQuery"
					:debounce="300"
					autocomplete="off"
				>
					<template #prefix>
						<SearchIcon class="h-4 w-4 text-gray-500" />
					</template>
				</FormControl>
				<!-- FormControl drops layout classes on a select, so the width is on
				the wrapper -->
				<div class="w-44">
					<FormControl
						type="select"
						v-model="stateFilter"
						:options="filterOptions"
						autocomplete="off"
					/>
				</div>
			</div>
			<!-- flex parent so ListView (whose root is flex-1) fills the height, which
			lets the empty state center vertically instead of collapsing to the top -->
			<div class="flex w-full flex-1 flex-col">
				<ListView
					class="h-full"
					v-bind="listOptions"
					@update:selections="(s: Set<string>) => (selected = new Set(s))"
				>
					<ListHeader />
					<ListRows v-if="rows.length" />
					<!-- skip the empty state while a scan is in flight so it doesn't flash -->
					<!-- ListEmptyState already centers its slot content -->
					<ListEmptyState v-else-if="!store.scanning">
						<div class="text-xl font-medium text-ink-gray-8">
							{{ emptyState.title }}
						</div>
						<div class="mt-1 text-base text-ink-gray-5">
							{{ emptyState.description }}
						</div>
					</ListEmptyState>
					<ListSelectBanner />
				</ListView>
			</div>
		</template>
	</div>

	<MigrationDashboard
		v-model="showDialog"
		:dashboard="opened"
		@migrate="migrateOne"
		@open="openInV3"
	/>

	<Dialog v-model="showHelp" :options="{ title: __('How this works') }">
		<template #body-content>
			<div class="flex flex-col gap-3 text-p-base text-ink-gray-7">
				<p>
					{{
						__(
							'Each v2 dashboard is copied into a new v3 workbook. Your v2 dashboards stay as they are. Migrate one, look at it, then come back for the rest.',
						)
					}}
				</p>
				<p>
					<span class="font-medium text-ink-gray-8">{{ VERDICT_LABELS.ready }}</span>
					-
					{{ __('These carry over as they are.') }}
				</p>
				<p>
					<span class="font-medium text-ink-gray-8">{{ VERDICT_LABELS.review }}</span>
					-
					{{ __('Open one to see what changes. Then migrate it.') }}
				</p>
				<p>
					<span class="font-medium text-ink-gray-8">{{ VERDICT_LABELS.unreadable }}</span>
					-
					{{
						__(
							'Something in this one cannot be read. Migrate it on its own to see why.',
						)
					}}
				</p>
				<p>
					<span class="font-medium text-ink-gray-8">{{ STATE_LABELS.failed }}</span>
					-
					{{ __('The migration stopped. Nothing was written. Run it again.') }}
				</p>
				<p>
					<span class="font-medium text-ink-gray-8">{{ VERDICT_LABELS.migrated }}</span>
					-
					{{
						__(
							'Each migrated query runs against v2, and the numbers are compared. Open one to see the result, or to open it in v3.',
						)
					}}
				</p>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button :label="__('Close')" variant="solid" @click="showHelp = false" />
			</div>
		</template>
	</Dialog>

	<Dialog v-model="showConfirm" :options="{ title: __('Migrate to v3') }">
		<template #body-content>
			<div class="flex flex-col gap-2">
				<p class="text-p-base text-ink-gray-7">
					{{
						willMigrate.length === 1
							? __(
									'Create a v3 copy of this dashboard? Your v2 dashboard stays untouched.',
							  )
							: __(
									'Create v3 copies of these {0} dashboards? Your v2 dashboards stay untouched.',
									String(willMigrate.length),
							  )
					}}
				</p>
				<p v-if="willSkip" class="text-p-sm text-ink-gray-6">
					{{
						willSkip === 1
							? __('1 more cannot be migrated now. It is skipped.')
							: __(
									'{0} more cannot be migrated now. They are skipped.',
									String(willSkip),
							  )
					}}
				</p>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button :label="__('Cancel')" variant="subtle" @click="showConfirm = false" />
				<Button
					:label="__('Migrate')"
					variant="solid"
					:disabled="!willMigrate.length"
					:loading="store.migrating"
					@click="migrate(confirmTargets)"
				/>
			</div>
		</template>
	</Dialog>
</template>
