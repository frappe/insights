<script setup lang="ts">
import { Breadcrumbs, ListView } from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, ref, watchEffect } from 'vue'
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

function rowsOf(verdicts: string[]): Row[] {
	return store.dashboards
		.filter((d: DashboardScan) => verdicts.includes(d.verdict) && !isInFlight(d))
		.map((d: DashboardScan) => ({
			...d,
			sentence: verdictSentence(d),
			result: verificationSentence(d.verification),
		}))
}

function isInFlight(dashboard: DashboardScan) {
	const state = store.stateOf(dashboard.dashboard)
	return state === 'queued' || state === 'in_progress'
}

const ready = computed(() => rowsOf(['ready']))
const review = computed(() => rowsOf(['review']))
const blocked = computed(() => rowsOf(['blocked', 'unreadable']))
const migrated = computed(() => rowsOf(['migrated']))
const inFlight = computed(() =>
	store.dashboards
		.filter(isInFlight)
		.map((d: DashboardScan) => ({ ...d, sentence: __('Migrating now'), result: '' })),
)

const nothingToShow = computed(
	() => !store.scanning && !store.dashboards.length && !store.scanError,
)

// -- the groups -------------------------------------------------------------

const selectedForReview = ref<Set<string>>(new Set())

function listOptions(rows: Row[], label: string, key = 'sentence', selectable = false) {
	return {
		columns: [
			{ label: __('Dashboard'), key: 'title', width: 2 },
			{ label, key, width: 3 },
		],
		rows,
		rowKey: 'dashboard',
		options: {
			showTooltip: false,
			selectable,
			onRowClick: (row: Row) => openDashboard(row),
			selectionText: (count: number) =>
				count === 1
					? __('1 dashboard selected')
					: __('{0} dashboards selected', String(count)),
		},
	}
}

// -- opening one ------------------------------------------------------------

const opened = ref<DashboardScan | null>(null)
const showDialog = ref(false)

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
		selectedForReview.value = new Set()
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

function migrateSelectedForReview() {
	askToMigrate(review.value.filter((d) => selectedForReview.value.has(d.dashboard)))
}
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: __('Migrate from v2'), route: '/migration' }]" />
		<Button
			:label="__('Scan again')"
			variant="outline"
			:loading="store.scanning"
			@click="store.scan(true)"
		/>
	</header>

	<div class="mb-4 flex h-full flex-col gap-5 overflow-auto px-5 pt-4">
		<p class="max-w-3xl text-p-base text-ink-gray-6">
			{{
				__(
					'Each v2 dashboard is copied into a new v3 workbook. Your v2 dashboards stay untouched, so you can migrate one, look at it, and come back for the rest.',
				)
			}}
		</p>

		<div
			v-if="store.unavailable || nothingToShow"
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
			<section v-if="ready.length" class="flex flex-col gap-2">
				<div class="flex items-end justify-between gap-3">
					<div class="flex flex-col">
						<h2 class="text-lg font-semibold text-ink-gray-8">
							{{ __('Ready to migrate ({0})', String(ready.length)) }}
						</h2>
						<p class="text-p-sm text-ink-gray-6">
							{{ __('These carry over as they are.') }}
						</p>
					</div>
					<Button
						variant="solid"
						:loading="store.migrating"
						:label="
							ready.length === 1
								? __('Migrate 1 dashboard')
								: __('Migrate all {0}', String(ready.length))
						"
						@click="migrate(ready)"
					/>
				</div>
				<ListView v-bind="listOptions(ready, __('What happens'))" />
			</section>

			<section v-if="review.length" class="flex flex-col gap-2">
				<div class="flex items-end justify-between gap-3">
					<div class="flex flex-col">
						<h2 class="text-lg font-semibold text-ink-gray-8">
							{{ __('Needs review ({0})', String(review.length)) }}
						</h2>
						<p class="text-p-sm text-ink-gray-6">
							{{ __('Open one to see what changes before you migrate it.') }}
						</p>
					</div>
					<Button
						v-if="selectedForReview.size"
						variant="solid"
						:label="
							selectedForReview.size === 1
								? __('Migrate 1 dashboard')
								: __('Migrate {0} dashboards', String(selectedForReview.size))
						"
						@click="migrateSelectedForReview"
					/>
				</div>
				<ListView
					v-bind="listOptions(review, __('What happens'), 'sentence', true)"
					@update:selections="(s: Set<string>) => (selectedForReview = new Set(s))"
				/>
			</section>

			<section v-if="blocked.length" class="flex flex-col gap-2">
				<div class="flex flex-col">
					<h2 class="text-lg font-semibold text-ink-gray-8">
						{{ __("Can't migrate yet ({0})", String(blocked.length)) }}
					</h2>
					<p class="text-p-sm text-ink-gray-6">
						{{
							__(
								'Add the data sources these read from, then scan again. Open one to see which.',
							)
						}}
					</p>
				</div>
				<ListView v-bind="listOptions(blocked, __('What to do'))" />
				<Button
					class="self-start"
					variant="subtle"
					:label="__('Go to Data Sources')"
					@click="router.push('/data-source')"
				/>
			</section>

			<section v-if="inFlight.length" class="flex flex-col gap-2">
				<h2 class="text-lg font-semibold text-ink-gray-8">
					{{ __('Migrating now ({0})', String(inFlight.length)) }}
				</h2>
				<ListView v-bind="listOptions(inFlight as Row[], __('Status'))" />
			</section>

			<section v-if="migrated.length" class="flex flex-col gap-2">
				<div class="flex flex-col">
					<h2 class="text-lg font-semibold text-ink-gray-8">
						{{ __('Migrated ({0})', String(migrated.length)) }}
					</h2>
					<p class="text-p-sm text-ink-gray-6">
						{{ __('Open one to see it in v3.') }}
					</p>
				</div>
				<ListView v-bind="listOptions(migrated, __('Result'), 'result')" />
			</section>
		</template>
	</div>

	<MigrationDashboard
		v-model="showDialog"
		:dashboard="opened"
		@migrate="(d: DashboardScan) => (d.verdict === 'ready' ? migrate([d]) : askToMigrate([d]))"
		@open="openInV3"
	/>

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
