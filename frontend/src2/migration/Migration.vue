<script setup lang="ts">
import { Breadcrumbs, ListView, TabButtons } from 'frappe-ui'
import { CircleHelp } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { getErrorMessage } from '../helpers'
import { createToast } from '../helpers/toasts'
import { __ } from '../translation'
import MigrationDashboard from './MigrationDashboard.vue'
import useV2MigrationStore, {
	DashboardScan,
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

type Row = DashboardScan & { sentence: string; result: string }

function isInFlight(dashboard: DashboardScan) {
	const state = store.stateOf(dashboard.dashboard)
	return state === 'queued' || state === 'in_progress'
}

function rowsOf(verdicts: string[]): Row[] {
	return store.dashboards
		.filter((d: DashboardScan) => verdicts.includes(d.verdict) && !isInFlight(d))
		.map((d: DashboardScan) => ({
			...d,
			sentence: verdictSentence(d),
			result: verificationSentence(d.verification),
		}))
}

const ready = computed(() => rowsOf(['ready']))
const review = computed(() => rowsOf(['review']))
const blocked = computed(() => rowsOf(['blocked', 'unreadable']))
const migrated = computed(() => rowsOf(['migrated']))

// A dashboard whose job is running is out of every other tab: it is no longer
// waiting on a decision, and `ListView` selects whole rows or none, so leaving
// it among the reviewable ones is what would make it selectable.
const inFlight = computed<Row[]>(() =>
	store.dashboards.filter(isInFlight).map((d: DashboardScan) => ({
		...d,
		sentence: __('Migrating now...'),
		result: __('Migrating now...'),
	})),
)

type TabValue = 'ready' | 'review' | 'blocked' | 'migrating' | 'migrated'

const tab = ref<TabValue>('ready')
const tabRows: Record<TabValue, () => Row[]> = {
	ready: () => ready.value,
	review: () => review.value,
	blocked: () => blocked.value,
	migrating: () => inFlight.value,
	migrated: () => migrated.value,
}

const tabs = computed(() => {
	const defined: { label: string; value: TabValue; count: number; always: boolean }[] = [
		{ label: __('Ready'), value: 'ready', count: ready.value.length, always: true },
		{ label: __('Needs review'), value: 'review', count: review.value.length, always: true },
		{ label: __('Blocked'), value: 'blocked', count: blocked.value.length, always: false },
		{
			label: __('Migrating'),
			value: 'migrating',
			count: inFlight.value.length,
			always: false,
		},
		{ label: __('Migrated'), value: 'migrated', count: migrated.value.length, always: true },
	]
	return defined
		.filter((t) => t.always || t.count)
		.map((t) => ({ label: `${t.label} · ${t.count}`, value: t.value }))
})

// A tab that empties - the last migration left the queue - would otherwise
// leave the page on a tab that no longer exists.
watch(tabs, (available) => {
	if (!available.some((t) => t.value === tab.value)) tab.value = 'ready'
})

const rows = computed(() => tabRows[tab.value]())

const EMPTY_STATES: Record<TabValue, string> = {
	ready: __('Nothing is ready to migrate.'),
	review: __('Nothing needs review.'),
	blocked: __('Nothing is blocked.'),
	migrating: __('Nothing is migrating.'),
	migrated: __('Nothing is migrated yet.'),
}

const COLUMN_LABELS: Record<TabValue, string> = {
	ready: __('What happens'),
	review: __('What happens'),
	blocked: __('What to do'),
	migrating: __('Status'),
	migrated: __('Result'),
}

const noV2 = computed(
	() => store.unavailable || (!store.scanning && !store.dashboards.length && !store.scanError),
)

const selected = ref<Set<string>>(new Set())
watch(tab, () => (selected.value = new Set()))

const listOptions = computed(() => ({
	columns: [
		{ label: __('Dashboard'), key: 'title', width: 2 },
		{
			label: COLUMN_LABELS[tab.value],
			key: tab.value === 'migrated' ? 'result' : 'sentence',
			width: 3,
		},
	],
	rows: rows.value,
	rowKey: 'dashboard',
	options: {
		showTooltip: false,
		selectable: tab.value === 'review',
		onRowClick: (row: Row) => openDashboard(row),
		selectionText: (count: number) =>
			count === 1 ? __('1 dashboard selected') : __('{0} dashboards selected', String(count)),
		emptyState: { title: EMPTY_STATES[tab.value], description: '' },
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
const confirmTargets = ref<DashboardScan[]>([])

async function migrate(targets: DashboardScan[]) {
	const names = targets.map((d) => d.dashboard)
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

function askToMigrate(targets: DashboardScan[]) {
	confirmTargets.value = targets
	showConfirm.value = true
}

function migrateSelected() {
	askToMigrate(review.value.filter((d) => selected.value.has(d.dashboard)))
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
				v-if="tab === 'review' && selected.size"
				variant="solid"
				:label="
					selected.size === 1
						? __('Migrate 1 selected')
						: __('Migrate {0} selected', String(selected.size))
				"
				@click="migrateSelected"
			/>
			<Button
				v-else-if="ready.length"
				variant="solid"
				:loading="store.migrating"
				:label="
					ready.length === 1
						? __('Migrate 1 ready')
						: __('Migrate all {0} ready', String(ready.length))
				"
				@click="migrate(ready)"
			/>
		</div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 pt-3">
		<div
			v-if="noV2"
			class="rounded border border-outline-gray-1 p-4 text-p-base text-ink-gray-6"
		>
			{{ __('This site has no Insights v2 dashboards to migrate.') }}
		</div>

		<div
			v-else-if="store.scanError"
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
			<div class="flex overflow-visible py-1">
				<TabButtons :buttons="tabs" v-model="tab" />
			</div>
			<!-- flex parent so ListView (whose root is flex-1) fills the height, which
			lets the empty state center vertically instead of collapsing to the top -->
			<div class="flex w-full flex-1 flex-col">
				<ListView
					class="h-full"
					v-bind="listOptions"
					@update:selections="(s: Set<string>) => (selected = new Set(s))"
				/>
			</div>
		</template>
	</div>

	<MigrationDashboard
		v-model="showDialog"
		:dashboard="opened"
		@migrate="(d: DashboardScan) => (d.verdict === 'ready' ? migrate([d]) : askToMigrate([d]))"
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
					<span class="font-medium text-ink-gray-8">{{ __('Ready') }}</span>
					-
					{{ __('these carry over as they are.') }}
				</p>
				<p>
					<span class="font-medium text-ink-gray-8">{{ __('Needs review') }}</span>
					-
					{{ __('open one to see what changes before you migrate it.') }}
				</p>
				<p>
					<span class="font-medium text-ink-gray-8">{{ __('Blocked') }}</span>
					-
					{{
						__(
							'these read from a data source that is not set up in v3. Add it under Data Sources, then scan again.',
						)
					}}
				</p>
				<p>
					<span class="font-medium text-ink-gray-8">{{ __('Migrated') }}</span>
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
			<p class="text-p-base text-ink-gray-7">
				{{
					confirmTargets.length === 1
						? __(
								'Create a v3 copy of this dashboard? Your v2 dashboard stays untouched.',
						  )
						: __(
								'Create v3 copies of these {0} dashboards? Your v2 dashboards stay untouched.',
								String(confirmTargets.length),
						  )
				}}
			</p>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button :label="__('Cancel')" variant="subtle" @click="showConfirm = false" />
				<Button
					:label="__('Migrate')"
					variant="solid"
					:loading="store.migrating"
					@click="migrate(confirmTargets)"
				/>
			</div>
		</template>
	</Dialog>
</template>
