<script setup lang="ts">
import { Breadcrumbs } from 'frappe-ui'
import { MoreHorizontal, RefreshCcw } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import ViewerChart from '../charts/ViewerChart.vue'
import { downloadImage } from '../helpers'
import dayjs from '../helpers/dayjs'
import { navigate } from '../helpers/navigation'
import { __ } from '../translation'
import { readFilters, writeFilters } from './filter_storage'
import {
	duplicateDashboard,
	fetchDashboard,
	ViewerDashboard,
	ViewerDashboardItem,
	ViewerFilters,
} from './viewer'
import ViewerFilterBar from './ViewerFilterBar.vue'
import VueGridLayout from './VueGridLayout.vue'

// A saved dashboard, read. This is the whole of what a dashboard page shows —
// the trail, the title, the freshness, the actions, the filter bar and the grid
// — on every surface that shows one: the desk island, the public link and the
// SPA's own page. Each of those is a mount shim around this component, carrying
// nothing but the navigation context of where it sits.
//
// The layout arrives in one request and is drawn straight away; every card then
// fetches on its own, so one slow or failing card never holds up the rest.
//
// A surface hands this a bounded box and it fills it: a header band that stays,
// one scrolling body under it. That is what lets the grid scroll without the
// page around it scrolling too.
type PageCrumb = {
	label: string
	/** an SPA route. A surface without a router passes `onClick` instead. */
	route?: string
	onClick?: () => void
}

const props = defineProps<{
	dashboard: string
	// where the reader starts. What they last chose on this dashboard wins over it
	filters?: ViewerFilters
	// ancestors of this page, never the page itself — the last crumb is ours
	breadcrumbs?: PageCrumb[]
}>()

// what this page is called, for whoever names the browser tab
const emit = defineEmits<{ title: [title: string] }>()

const GRID_COLS = 20

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
		// what the surface mounted us with is the starting point; what this reader
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

// Cards reach the execution queue in whatever order they mount, so rank them by
// grid position instead: top row first, left to right within a row.
function layoutRank(item: ViewerDashboardItem) {
	return item.layout.y * GRID_COLS + item.layout.x
}

// when what is on screen was produced. Cards fetch on their own, so the honest
// stamp for the page is the oldest of them.
const freshness = computed(() => {
	const times = Object.values(executedAt.value).map((date) => date.getTime())
	return times.length ? dayjs(Math.min(...times)).format('h:mm a') : ''
})

// A dashboard that is loading and one the reader may not see answer the same
// name, so the header never says whether the content exists.
const pageTitle = computed(() => doc.value?.title || __('Dashboard'))

// The trail that led here, drawn in this header because a page box is all a
// surface gives us: the shim hands down the ancestors it can vouch for.
const crumbs = computed(() => [...(props.breadcrumbs || []), { label: pageTitle.value }])

watch(pageTitle, (title) => emit('title', title), { immediate: true })

const duplicating = ref(false)
const duplicateFailed = ref(false)

// Every action is offered on the strength of what the server granted, never of
// which surface this is. A capability the reader does not hold renders nothing:
// no disabled button, no action that answers with a refusal.
const menuOptions = computed(() => {
	return [
		{
			label: __('Export as PNG'),
			icon: 'lucide-download',
			onClick: exportImage,
		},
		doc.value?.can_edit && doc.value?.workbook
			? {
					label: __('Edit in Insights'),
					icon: 'lucide-external-link',
					onClick: openBuilder,
			  }
			: null,
		// shipped content is read-only, so a copy is the only way to change it
		doc.value?.can_duplicate
			? {
					label: duplicating.value ? __('Duplicating...') : __('Duplicate to edit'),
					icon: 'lucide-copy',
					onClick: duplicate,
			  }
			: null,
	].filter(Boolean)
})

const grid = ref<HTMLElement>()

// the grid, not the page: the header band belongs to the reader's session, not
// to the picture they want to keep
function exportImage() {
	if (!grid.value || !doc.value) return
	return downloadImage(grid.value, `${doc.value.title}.png`)
}

function openBuilder() {
	if (!doc.value?.workbook) return
	navigate(`/workbook/${doc.value.workbook}/dashboard/${doc.value.name}`)
}

// The copy is the caller's own document in a workbook of their own, so it lands
// in the builder rather than here. Copying a closure is a handful of inserts,
// but it is a round trip either way: the title row says so while it runs, and
// says so if it failed — the menu is closed by then and there is nowhere else
// on this page for the answer to go.
async function duplicate() {
	if (!doc.value || duplicating.value) return
	duplicating.value = true
	duplicateFailed.value = false
	try {
		const copy = await duplicateDashboard(doc.value.name)
		navigate(`/workbook/${copy.workbook}/dashboard/${copy.dashboard}`)
	} catch (error) {
		duplicateFailed.value = true
	} finally {
		duplicating.value = false
	}
}
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden">
		<!-- The page's one header, so it is drawn in every state — a reader who
		     may not see this dashboard still gets a way back. It sits outside the
		     scrolling body rather than sticking to the top of it: a `sticky` bar
		     sticks to whichever ancestor scrolls, which on a desk page was the
		     page itself, so the filters slid under desk's own head while the grid
		     moved beneath them. -->
		<div class="flex flex-shrink-0 flex-col gap-3 border-b border-outline-gray-1 px-4 py-3">
			<div class="flex items-center justify-between gap-2">
				<div class="flex min-w-0 items-center gap-2">
					<Breadcrumbs :items="crumbs" />
					<span v-if="duplicating" class="flex-shrink-0 text-p-sm text-ink-gray-5">
						{{ __('Duplicating...') }}
					</span>
					<span
						v-else-if="duplicateFailed"
						class="flex-shrink-0 text-p-sm text-ink-red-6"
					>
						{{ __('Could not duplicate this dashboard') }}
					</span>
					<span v-else-if="freshness" class="flex-shrink-0 text-p-sm text-ink-gray-5">
						{{ __('as of') }} {{ freshness }}
					</span>
				</div>
				<!-- Nothing to refresh and nothing to act on until the dashboard
				     is there, and a denied page offers neither. -->
				<div v-if="doc" class="flex flex-shrink-0 items-center gap-1">
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
				v-if="doc && filterItems.length"
				ref="filterBar"
				:key="doc.name"
				v-model="filters"
				:dashboard="doc.name"
				:items="filterItems"
			/>
		</div>

		<div
			v-if="unavailable"
			class="flex w-full flex-1 items-center justify-center p-4 text-p-base text-ink-gray-5"
		>
			{{ __('This dashboard is not available') }}
		</div>

		<div v-else-if="loading" class="flex-1 p-4">
			<div class="h-8 w-64 animate-pulse rounded bg-surface-gray-2" />
		</div>

		<template v-else-if="doc">
			<div
				v-if="!items.length"
				class="flex w-full flex-1 items-center justify-center p-4 text-p-base text-ink-gray-5"
			>
				{{ __('This dashboard is empty') }}
			</div>

			<!-- The one scroller on the page. The padding belongs here and not on
			     the grid: vue-grid-layout reads its own `offsetWidth` to size a
			     column, which is the padding box, and then lays the columns out
			     inside the padding — so the rightmost card ended 16px past the
			     page. -->
			<div v-else ref="grid" class="flex-1 overflow-y-auto p-4">
				<VueGridLayout
					class="h-fit w-full"
					:cols="GRID_COLS"
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
								:priority="layoutRank(items[index])"
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
			</div>
		</template>
	</div>
</template>
