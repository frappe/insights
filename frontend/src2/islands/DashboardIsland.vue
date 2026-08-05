<script setup lang="ts">
import { MoreHorizontal, RefreshCcw } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import VueGridLayout from '../dashboard/VueGridLayout.vue'
import dayjs from '../helpers/dayjs'
import { navigate } from '../helpers/navigation'
import { __ } from '../translation'
import { readFilters, writeFilters } from './filter_storage'
import { fetchDashboard, ViewerDashboard, ViewerFilters } from './viewer'
import ViewerChart from './ViewerChart.vue'
import ViewerFilterBar from './ViewerFilterBar.vue'

// The whole page body of a desk dashboard page. The layout arrives in one
// request and is drawn straight away; every card then fetches on its own, so
// one slow or failing card never holds up the rest.
//
// A reader gets two things to do here: filter, and click a chart. Everything
// else on the page reports state.
const props = defineProps<{ dashboard: string; filters?: ViewerFilters }>()

const doc = ref<ViewerDashboard>()
const loading = ref(true)
const unavailable = ref(false)
const filters = ref<ViewerFilters>({})
const filterBar = ref<InstanceType<typeof ViewerFilterBar>>()
const refreshToken = ref(0)
const executedAt = ref<Record<string, Date>>({})

// A dashboard that is missing and one the viewer may not read answer the same,
// so there is one page state for both.
async function load() {
	loading.value = true
	unavailable.value = false
	executedAt.value = {}
	try {
		doc.value = await fetchDashboard(props.dashboard)
		// what the host mounted us with is the starting point; what this reader
		// last chose on this dashboard wins over it
		filters.value = { ...(props.filters || {}), ...readFilters(doc.value.name) }
	} catch (error) {
		doc.value = undefined
		unavailable.value = true
	} finally {
		loading.value = false
	}
}

watch(() => props.dashboard, load, { immediate: true })

watch(filters, (value) => doc.value && writeFilters(doc.value.name, value), { deep: true })

// Filter items hold their place in the saved layout, but the filter bar is its
// own surface above the grid, not a grid cell. Dropping them lets the grid
// compact the gap away.
const items = computed(() => (doc.value?.items || []).filter((item) => item.type !== 'filter'))
const filterItems = computed(() =>
	(doc.value?.items || []).filter((item) => item.type === 'filter'),
)

// Which cards a filter reaches is the server's answer, carried on the item. A
// card is handed only the filters that land on it, so moving one filter refetches
// its cards and leaves the rest of the page alone.
const filtersByChart = computed(() => {
	const byChart: Record<string, ViewerFilters> = {}
	filterItems.value.forEach((item) => {
		const state = filters.value[item.filter_name!]
		if (!state) return
		item.charts?.forEach((chart) => {
			byChart[chart] = { ...byChart[chart], [item.filter_name!]: state }
		})
	})
	return byChart
})

// when what is on screen was produced. Cards fetch on their own, so the honest
// stamp for the page is the oldest of them.
const freshness = computed(() => {
	const times = Object.values(executedAt.value).map((date) => date.getTime())
	return times.length ? dayjs(Math.min(...times)).format('h:mm a') : ''
})

const menuOptions = computed(() => {
	// ticket 22 adds "Duplicate to edit" here, on `doc.can_duplicate`
	return [
		doc.value?.can_edit && doc.value?.workbook
			? {
					label: __('Edit in Insights'),
					icon: 'lucide-external-link',
					onClick: openBuilder,
			  }
			: null,
	].filter(Boolean)
})

function openBuilder() {
	if (!doc.value?.workbook) return
	// the island has no router: the navigation adapter opens Insights in a new tab
	navigate(`/workbook/${doc.value.workbook}/dashboard/${doc.value.name}`)
}
</script>

<template>
	<div class="w-full">
		<div
			v-if="unavailable"
			class="flex min-h-64 w-full items-center justify-center p-4 text-p-base text-ink-gray-5"
		>
			{{ __('This dashboard is not available') }}
		</div>

		<div v-else-if="loading" class="p-4">
			<div class="h-8 w-64 animate-pulse rounded bg-surface-gray-2" />
		</div>

		<template v-else-if="doc">
			<div class="flex items-center justify-between gap-2 px-4 pt-4">
				<div class="flex items-baseline gap-2 overflow-hidden">
					<h1 class="truncate text-lg font-medium text-ink-gray-8">{{ doc.title }}</h1>
					<span v-if="freshness" class="flex-shrink-0 text-p-sm text-ink-gray-5">
						{{ __('as of') }} {{ freshness }}
					</span>
				</div>
				<div class="flex flex-shrink-0 items-center gap-1">
					<Button variant="ghost" :label="__('Refresh')" @click="refreshToken++">
						<template #prefix>
							<RefreshCcw class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
						</template>
					</Button>
					<Dropdown v-if="menuOptions.length" placement="right" :options="menuOptions">
						<Button variant="ghost">
							<template #icon>
								<MoreHorizontal
									class="h-4 w-4 text-ink-gray-6"
									stroke-width="1.5"
								/>
							</template>
						</Button>
					</Dropdown>
				</div>
			</div>

			<ViewerFilterBar
				v-if="filterItems.length"
				ref="filterBar"
				:key="doc.name"
				v-model="filters"
				:dashboard="doc.name"
				:items="filterItems"
			/>

			<div
				v-if="!items.length"
				class="flex min-h-64 w-full items-center justify-center p-4 text-p-base text-ink-gray-5"
			>
				{{ __('This dashboard is empty') }}
			</div>

			<VueGridLayout
				v-else
				class="h-fit w-full px-4 pb-4"
				:cols="20"
				:disabled="true"
				:verticalCompact="doc.vertical_compact_layout"
				:modelValue="items.map((item) => item.layout)"
			>
				<template #item="{ index }">
					<div class="flex h-full w-full items-center justify-start p-2">
						<ViewerChart
							v-if="items[index].type === 'chart'"
							:chart="items[index].chart!"
							:dashboard="doc.name"
							:filters="filtersByChart[items[index].chart!]"
							:refresh-token="refreshToken"
							@loaded="executedAt[items[index].chart!] = $event"
							@reset-filters="filterBar?.reset()"
						/>
						<div
							v-else-if="items[index].type === 'text'"
							class="prose prose-v3 h-full w-full max-w-none overflow-auto text-ink-gray-7"
							v-html="items[index].text"
						/>
					</div>
				</template>
			</VueGridLayout>
		</template>
	</div>
</template>
