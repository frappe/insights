<script setup lang="tsx">
import {
	Badge,
	Breadcrumbs,
	ListEmptyState,
	ListHeader,
	ListRows,
	ListSelectBanner,
	ListView,
} from 'frappe-ui'
import { CircleHelp, SearchIcon } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { getErrorMessage } from '../helpers'
import { createToast } from '../helpers/toasts'
import { __ } from '../translation'
import MigrationDashboard from './MigrationDashboard.vue'
import useV2MigrationStore, {
	DashboardScan,
	VERDICT_LABELS,
	verdictSentence,
	verificationSentence,
} from './v2_migration'

const router = useRouter()
const store = useV2MigrationStore()

onMounted(() => {
	store.scan()
	store.startPolling()
})
onBeforeUnmount(() => store.stopPolling())

watchEffect(() => {
	document.title = 'Migrate from v2 | Insights'
})

/** What a row is right now. A verdict, except that a running job outranks the
 * verdict the scan recorded before the job started. */
type RowState = 'ready' | 'review' | 'blocked' | 'migrating' | 'migrated'

const STATE_LABELS: Record<RowState, string> = {
	...VERDICT_LABELS,
	migrating: __('Migrating'),
}

const STATE_THEMES: Record<RowState, string> = {
	ready: 'green',
	review: 'orange',
	blocked: 'red',
	migrating: 'blue',
	migrated: 'gray',
}

/** Only these two are a decision the user has yet to make. */
const MIGRATABLE: RowState[] = ['ready', 'review']

type Row = DashboardScan & { state: RowState; sentence: string }

function stateOf(dashboard: DashboardScan): RowState {
	const job = store.stateOf(dashboard.dashboard)
	if (job === 'queued' || job === 'in_progress') return 'migrating'
	if (dashboard.verdict === 'unreadable') return 'blocked'
	return dashboard.verdict as RowState
}

function sentenceOf(dashboard: DashboardScan, state: RowState) {
	if (state === 'migrating') return __('Migrating now...')
	if (state === 'migrated') {
		return verificationSentence(dashboard.verification) || __('Copied into a v3 workbook')
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
	...(['ready', 'review', 'blocked', 'migrating', 'migrated'] as RowState[]).map((state) => ({
		label: STATE_LABELS[state],
		value: state,
	})),
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

// -- opening one ------------------------------------------------------------

const opened = ref<DashboardScan | null>(null)
const showDialog = ref(false)
const showHelp = ref(false)

function openDashboard(row: DashboardScan) {
	opened.value = store.dashboards.find((d: DashboardScan) => d.dashboard === row.dashboard) || row
	showDialog.value = true
}

function openInV3(dashboard: DashboardScan) {
	if (!dashboard.migrated_workbook) return
	showDialog.value = false
	router.push(
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
		const result = await store.migrateDashboards(names)
		showConfirm.value = false
		showDialog.value = false
		selected.value = new Set()
		createToast({
			variant: 'success',
			title: __('Migration started'),
			message:
				result.accepted.length === 1
					? __('1 dashboard is being copied into v3.')
					: __(
							'{0} dashboards are being copied into v3.',
							String(result.accepted.length),
					  ),
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
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: __('Migrate from v2'), route: '/migration' }]" />
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
	</header>

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 pt-3">
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
				{{ __('Checking what will carry over...') }}
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
							'Each v2 dashboard is copied into a new v3 workbook. Your v2 dashboards stay untouched, so you can migrate one, look at it, and come back for the rest.',
						)
					}}
				</p>
				<p>
					<span class="font-medium text-ink-gray-8">{{ VERDICT_LABELS.ready }}</span>
					-
					{{ __('these carry over as they are.') }}
				</p>
				<p>
					<span class="font-medium text-ink-gray-8">{{ VERDICT_LABELS.review }}</span>
					-
					{{ __('open one to see what changes before you migrate it.') }}
				</p>
				<p>
					<span class="font-medium text-ink-gray-8">{{ VERDICT_LABELS.blocked }}</span>
					-
					{{
						__(
							'these read from a data source that is not set up in v3. Add it under Data Sources, then scan again.',
						)
					}}
				</p>
				<p>
					<span class="font-medium text-ink-gray-8">{{ VERDICT_LABELS.migrated }}</span>
					-
					{{
						__(
							'we run each migrated query against v2 and compare the numbers. Open one to see the result, or to see it in v3.',
						)
					}}
				</p>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button
					:label="__('Go to Data Sources')"
					variant="subtle"
					@click="router.push('/data-source')"
				/>
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
							? __(
									'1 more is already migrated or cannot migrate yet, and is skipped.',
							  )
							: __(
									'{0} more are already migrated or cannot migrate yet, and are skipped.',
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
