<script setup lang="tsx">
import { useTimeAgo } from '@vueuse/core'
import { Badge, ListView } from 'frappe-ui'
import { SearchIcon } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getErrorMessage } from '../helpers'
import { createToast } from '../helpers/toasts'
import { __ } from '../translation'
import V2MigrationPreviewDialog from './V2MigrationPreviewDialog.vue'
import useV2MigrationStore, { MigrationState, V2Dashboard } from './v2_migration'

const store = useV2MigrationStore()

onMounted(() => {
	store.getDashboards()
	store.startPolling()
})
onBeforeUnmount(() => store.stopPolling())

const searchQuery = ref('')
const selections = ref<Set<string>>(new Set())

const filteredDashboards = computed(() => {
	const query = searchQuery.value.toLowerCase().trim()
	if (!query) return store.dashboards
	return store.dashboards.filter(
		(d: V2Dashboard) =>
			d.title?.toLowerCase().includes(query) || d.name?.toLowerCase().includes(query),
	)
})

const STATE_BADGES: Record<MigrationState, { label: string; theme: string }> = {
	not_started: { label: __('Not migrated'), theme: 'gray' },
	queued: { label: __('Queued'), theme: 'blue' },
	in_progress: { label: __('Migrating'), theme: 'blue' },
	migrated: { label: __('Migrated'), theme: 'green' },
	failed: { label: __('Failed'), theme: 'red' },
}

function stateOf(row: V2Dashboard): MigrationState {
	const status = store.statuses[row.name]
	if (status) return status.status
	return row.migrated_dashboard ? 'migrated' : 'not_started'
}

function isMigrated(row: V2Dashboard) {
	return stateOf(row) === 'migrated'
}

function isInFlight(row: V2Dashboard) {
	const state = stateOf(row)
	return state === 'queued' || state === 'in_progress'
}

const rows = computed(() =>
	filteredDashboards.value.map((d: V2Dashboard) => ({
		...d,
		migration_state: stateOf(d),
		modified_from_now: d.modified ? useTimeAgo(d.modified).value : '',
	})),
)

const emptyState = computed(() => {
	if (store.unavailable) {
		return {
			title: __('No v2 data on this site'),
			description: __('This site has no Insights v2 dashboards to migrate.'),
		}
	}
	if (store.loadError) {
		return {
			title: __('Could not read v2 dashboards'),
			description: store.loadError,
		}
	}
	if (searchQuery.value.trim() && store.dashboards.length) {
		return {
			title: __('No matches'),
			description: __('No v2 dashboard matches your search.'),
		}
	}
	return {
		title: __('No v2 dashboards'),
		description: __('There are no Insights v2 dashboards on this site to migrate.'),
	}
})

const listOptions = computed(() => ({
	columns: [
		{ label: __('Dashboard'), key: 'title', width: 2 },
		{
			label: __('Status'),
			key: 'migration_state',
			// the badge carries the label; without this the cell prints it again
			// beside the badge, and dropping it falls back to the raw state key
			getLabel: () => '',
			prefix: (props: any) => {
				const badge = STATE_BADGES[props.row.migration_state as MigrationState]
				return <Badge theme={badge.theme} variant="subtle" label={badge.label} />
			},
		},
		{ label: __('Owner'), key: 'owner' },
		{ label: __('Items'), key: 'item_count', align: 'right' },
		{ label: __('Queries'), key: 'query_count', align: 'right' },
		{ label: __('Last Changed'), key: 'modified_from_now' },
	],
	rows: rows.value,
	rowKey: 'name',
	options: {
		showTooltip: false,
		selectable: true,
		onRowClick: (row: V2Dashboard) => openPreview(row),
		selectionText: (count: number) =>
			count === 1 ? __('1 dashboard selected') : __('{0} dashboards selected', String(count)),
		emptyState: emptyState.value,
	},
}))

// -- preview ----------------------------------------------------------------

const showPreview = ref(false)
const previewTarget = ref<V2Dashboard | null>(null)

function openPreview(row: V2Dashboard) {
	previewTarget.value = store.dashboards.find((d: V2Dashboard) => d.name === row.name) || row
	showPreview.value = true
}

function openWorkbook(target: { workbook: string | null; dashboard: string | null }) {
	if (!target.workbook) return
	const path = target.dashboard
		? `/insights/workbook/${target.workbook}/dashboard/${target.dashboard}`
		: `/insights/workbook/${target.workbook}`
	// The settings dialog owns the viewport here, so the workbook opens beside it
	// rather than under it.
	window.open(path, '_blank')
}

// -- migrating --------------------------------------------------------------

const showConfirm = ref(false)
const confirmTargets = ref<V2Dashboard[]>([])

const toMigrate = computed(() =>
	confirmTargets.value.filter((d) => !isMigrated(d) && !isInFlight(d)),
)
const alreadyDone = computed(() => confirmTargets.value.filter((d) => isMigrated(d)))
const inFlightTargets = computed(() => confirmTargets.value.filter((d) => isInFlight(d)))

function askToMigrate(targets: V2Dashboard[]) {
	confirmTargets.value = targets
	showConfirm.value = true
}

function migrateSelected() {
	askToMigrate(store.dashboards.filter((d: V2Dashboard) => selections.value.has(d.name)))
}

function migrateFromPreview(dashboard: V2Dashboard) {
	showPreview.value = false
	askToMigrate([dashboard])
}

async function confirmMigration() {
	const names = toMigrate.value.map((d) => d.name)
	if (!names.length) return
	try {
		const result = await store.migrateDashboards(names)
		showConfirm.value = false
		selections.value = new Set()
		createToast({
			variant: 'success',
			title: __('Migration Started'),
			message:
				result.accepted.length === 1
					? __('1 dashboard is being migrated in the background.')
					: __(
							'{0} dashboards are being migrated in the background.',
							String(result.accepted.length),
					  ),
		})
		if (result.skipped.length) {
			createToast({
				variant: 'warning',
				title: __('{0} skipped', String(result.skipped.length)),
				message: result.skipped.map((s) => s.detail).join('\n'),
			})
		}
	} catch (err: any) {
		createToast({
			variant: 'error',
			title: __('Could not start the migration'),
			message: getErrorMessage(err),
		})
	}
}

const failedCount = computed(
	() => store.dashboards.filter((d: V2Dashboard) => stateOf(d) === 'failed').length,
)
</script>

<template>
	<div class="flex h-full w-full flex-col gap-3 overflow-x-hidden p-8 px-10">
		<div class="flex flex-shrink-0 flex-col gap-1">
			<h1 class="text-xl font-semibold">{{ __('Migrate from v2') }}</h1>
			<p class="text-p-sm text-ink-gray-6">
				{{
					__(
						'Copy an Insights v2 dashboard into a new v3 workbook. Your v2 dashboards are left as they are. Open a dashboard to see what will not carry over before you migrate it.',
					)
				}}
			</p>
		</div>

		<div
			v-if="failedCount"
			class="flex flex-shrink-0 flex-col gap-1 rounded border border-outline-gray-2 bg-surface-gray-1 p-3"
		>
			<span class="text-p-base font-medium text-ink-red-5">
				{{
					failedCount === 1
						? __('1 dashboard failed to migrate')
						: __('{0} dashboards failed to migrate', String(failedCount))
				}}
			</span>
			<span class="text-p-sm text-ink-gray-6">
				{{ __('Open a failed dashboard to read why, and to try again.') }}
			</span>
		</div>

		<div class="flex w-full flex-1 flex-col gap-3 overflow-auto">
			<div class="flex justify-between gap-2 overflow-visible py-1">
				<FormControl v-model="searchQuery" :placeholder="__('Search')" :debounce="300">
					<template #prefix>
						<SearchIcon class="h-4 w-4 text-ink-gray-5" />
					</template>
				</FormControl>
				<div class="flex items-center gap-2">
					<Button
						:label="__('Refresh')"
						variant="outline"
						:loading="store.loading"
						@click="store.getDashboards(searchQuery)"
					/>
					<Button
						v-if="selections.size"
						:label="
							selections.size === 1
								? __('Migrate 1 Dashboard')
								: __('Migrate {0} Dashboards', String(selections.size))
						"
						variant="solid"
						@click="migrateSelected"
					/>
				</div>
			</div>

			<ListView
				class="h-full"
				v-bind="listOptions"
				@update:selections="(s: Set<string>) => (selections = new Set(s))"
			/>
		</div>
	</div>

	<V2MigrationPreviewDialog
		v-model="showPreview"
		:dashboard="previewTarget"
		:status="previewTarget ? store.statuses[previewTarget.name] : undefined"
		@migrate="migrateFromPreview"
		@open-workbook="openWorkbook"
	/>

	<Dialog v-model="showConfirm" :options="{ title: __('Migrate to v3'), size: 'lg' }">
		<template #body-content>
			<div class="flex flex-col gap-4 text-base">
				<p class="text-p-base text-ink-gray-7">
					{{
						__(
							'This creates a new v3 workbook for each dashboard below. It cannot be undone from here. Your v2 dashboards are not changed or removed.',
						)
					}}
				</p>

				<div v-if="toMigrate.length" class="flex flex-col gap-2">
					<h3 class="text-p-base font-medium text-ink-gray-8">
						{{ __('Will be migrated ({0})', String(toMigrate.length)) }}
					</h3>
					<ul
						class="max-h-56 divide-y divide-outline-gray-1 overflow-y-auto rounded border border-outline-gray-1"
					>
						<li
							v-for="dashboard in toMigrate"
							:key="dashboard.name"
							class="flex items-center justify-between gap-3 px-3 py-2"
						>
							<span class="truncate text-ink-gray-8">{{ dashboard.title }}</span>
							<span class="shrink-0 text-p-sm text-ink-gray-5">
								{{
									__(
										'{0} items, {1} queries',
										String(dashboard.item_count),
										String(dashboard.query_count),
									)
								}}
							</span>
						</li>
					</ul>
				</div>

				<div v-if="alreadyDone.length" class="flex flex-col gap-2">
					<h3 class="text-p-base font-medium text-ink-gray-8">
						{{
							__(
								'Already migrated, will be skipped ({0})',
								String(alreadyDone.length),
							)
						}}
					</h3>
					<p class="text-p-sm text-ink-gray-6">
						{{
							__(
								'These already have a v3 workbook. They are left untouched, so any edits you made in v3 are safe.',
							)
						}}
					</p>
					<ul class="flex flex-col gap-1">
						<li
							v-for="dashboard in alreadyDone"
							:key="dashboard.name"
							class="truncate text-p-sm text-ink-gray-5"
						>
							{{ dashboard.title }}
						</li>
					</ul>
				</div>

				<div v-if="inFlightTargets.length" class="flex flex-col gap-2">
					<h3 class="text-p-base font-medium text-ink-gray-8">
						{{
							__(
								'Already running, will be skipped ({0})',
								String(inFlightTargets.length),
							)
						}}
					</h3>
					<ul class="flex flex-col gap-1">
						<li
							v-for="dashboard in inFlightTargets"
							:key="dashboard.name"
							class="truncate text-p-sm text-ink-gray-5"
						>
							{{ dashboard.title }}
						</li>
					</ul>
				</div>

				<p v-if="!toMigrate.length" class="text-p-base text-ink-gray-6">
					{{ __('Nothing here is left to migrate.') }}
				</p>
			</div>
		</template>

		<template #actions>
			<div class="flex justify-end gap-2">
				<Button :label="__('Cancel')" variant="subtle" @click="showConfirm = false" />
				<Button
					:label="
						toMigrate.length === 1
							? __('Migrate 1 Dashboard')
							: __('Migrate {0} Dashboards', String(toMigrate.length))
					"
					variant="solid"
					:disabled="!toMigrate.length"
					:loading="store.migrating"
					@click="confirmMigration"
				/>
			</div>
		</template>
	</Dialog>
</template>
