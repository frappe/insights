<script setup lang="ts">
import { Breadcrumbs } from 'frappe-ui'
import { MoreHorizontal, RefreshCcw } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import ContentEditable from '../components/ContentEditable.vue'
import { downloadImage } from '../helpers'
import dayjs from '../helpers/dayjs'
import { __ } from '../translation'
import type {
	DashboardSource,
	ViewerDashboardItem,
	ViewerFilters,
	ViewerFilterState,
} from './viewer'
import VueGridLayout from './VueGridLayout.vue'

// A saved dashboard. This is the whole of what a dashboard page shows — the
// trail, the title, the freshness, the actions and the grid — on every surface
// that shows one: the desk island, the public link, the SPA's own page and the
// builder. Each of those is a mount shim around this component, carrying nothing
// but the feed it reads from and the navigation context of where it sits.
//
// Everything that changes between them arrives on the feed, as a capability that
// is either there or not. Nothing here asks which surface it is, and an
// ungranted capability draws nothing at all — no disabled button, no action that
// answers with a refusal.
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
	// where the page's content comes from: `useSavedDashboard` on a read surface,
	// `useDashboardAuthoring` in the builder
	source: DashboardSource
	// where the reader starts. What they last chose on this dashboard wins over it
	filters?: ViewerFilters
	// ancestors of this page, never the page itself — the last crumb is ours
	breadcrumbs?: PageCrumb[]
}>()

// what this page is called, for whoever names the browser tab
const emit = defineEmits<{ title: [title: string] }>()

const GRID_COLS = 20

const filters = ref<ViewerFilters>({})
const refreshToken = ref(0)
const executedAt = ref<Record<string, Date>>({})

// what the surface mounted us with is the starting point; where the feed says
// the filters start wins over it — a reader's last choice on a read surface, the
// document's own defaults in the builder.
watch(
	() => props.source.name,
	(name) => {
		executedAt.value = {}
		if (!name) return
		filters.value = { ...(props.filters || {}), ...props.source.filters }
	},
	{ immediate: true },
)

watch(filters, (value) => props.source.saveFilters?.(value), { deep: true })

// Which cards a filter reaches is the server's answer, carried on the item. A
// card is handed only the filters that land on it, so moving one filter refetches
// its cards and leaves the rest of the page alone.
const filtersByChart = computed(() => {
	const byChart: Record<string, ViewerFilters> = {}
	props.source.items.forEach((item) => {
		if (item.type !== 'filter') return
		const state = filters.value[item.filter_name!]
		if (!state) return
		item.charts?.forEach((chart) => {
			byChart[chart] = { ...byChart[chart], [item.filter_name!]: state }
		})
	})
	return byChart
})

// A card gets the filters that land on it. A filter cell gets the page's state
// and finds itself in it by name — the page owns it, so a reset from anywhere on
// the page reaches every control.
function cellFilters(item: ViewerDashboardItem) {
	return item.type === 'filter' ? filters.value : filtersByChart.value[item.chart!]
}

// where a filter cell says it has been moved to
function setFilter(item: ViewerDashboardItem, state?: ViewerFilterState) {
	const moved = { ...filters.value }
	if (state) moved[item.filter_name!] = state
	else delete moved[item.filter_name!]
	filters.value = moved
}

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
const pageTitle = computed(() => props.source.title || __('Dashboard'))

// The trail that led here, drawn in this header because a page box is all a
// surface gives us: the shim hands down the ancestors it can vouch for.
const crumbs = computed(() => [...(props.breadcrumbs || []), { label: pageTitle.value }])

watch(pageTitle, (title) => emit('title', title), { immediate: true })

// Every action is offered on the strength of what the feed carries, never of
// which surface this is.
const menuOptions = computed(() => {
	const duplicate = props.source.duplicate
	return [
		{
			label: __('Export as PNG'),
			icon: 'lucide-download',
			onClick: exportImage,
		},
		props.source.openBuilder
			? {
					label: __('Edit in Insights'),
					icon: 'lucide-external-link',
					onClick: props.source.openBuilder,
			  }
			: null,
		// shipped content is read-only, so a copy is the only way to change it
		duplicate
			? {
					label: duplicate.running ? __('Duplicating...') : __('Duplicate to edit'),
					icon: 'lucide-copy',
					onClick: duplicate.run,
			  }
			: null,
		...(props.source.authoring?.menuOptions || []),
	].filter(Boolean)
})

const grid = ref<HTMLElement>()

// the grid, not the page: the header band belongs to the reader's session, not
// to the picture they want to keep
function exportImage() {
	if (!grid.value) return
	return downloadImage(grid.value, `${props.source.title}.png`)
}
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden">
		<!-- The page's one header, so it is drawn in every state — a reader who
		     may not see this dashboard still gets a way back. It sits outside the
		     scrolling body rather than sticking to the top of it, so the grid
		     scrolls under it and the page around it does not move. -->
		<div
			class="flex flex-shrink-0 items-center justify-between gap-2 border-b border-outline-gray-1 px-4 py-3"
		>
			<div class="flex min-w-0 items-center gap-2">
				<!-- renaming is a capability like any other: where it is granted
				     the title is the control, and where it is not there is a
				     trail with the title at the end of it -->
				<ContentEditable
					v-if="source.authoring?.rename"
					class="cursor-text rounded-sm text-lg-semibold !text-ink-gray-7 focus:ring-2 focus:ring-outline-gray-6 focus:ring-offset-4"
					:modelValue="source.title"
					@returned="source.authoring.rename($event)"
					@blur="source.authoring.rename($event)"
					:placeholder="__('Untitled Dashboard')"
				/>
				<Breadcrumbs v-else :items="crumbs" />

				<span
					v-if="source.duplicate?.running"
					class="flex-shrink-0 text-p-sm text-ink-gray-5"
				>
					{{ __('Duplicating...') }}
				</span>
				<span
					v-else-if="source.duplicate?.failed"
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
			<div
				v-if="!source.loading && !source.unavailable"
				class="flex flex-shrink-0 items-center gap-1"
			>
				<component v-if="source.authoring" :is="source.authoring.actions" />
				<Button
					v-if="!source.authoring?.editing"
					variant="ghost"
					:label="__('Refresh')"
					@click="refreshToken++"
				>
					<template #prefix>
						<RefreshCcw class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
					</template>
				</Button>
				<Dropdown v-if="menuOptions.length" placement="right" :options="menuOptions">
					<Button variant="ghost">
						<template #icon>
							<MoreHorizontal class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
						</template>
					</Button>
				</Dropdown>
			</div>
		</div>

		<div
			v-if="source.unavailable"
			class="flex w-full flex-1 items-center justify-center p-4 text-p-base text-ink-gray-5"
		>
			{{ __('This dashboard is not available') }}
		</div>

		<div v-else-if="source.loading" class="flex-1 p-4">
			<div class="h-8 w-64 animate-pulse rounded bg-surface-gray-2" />
		</div>

		<!-- The one scroller on the page. The padding belongs here and not on
		     the grid: vue-grid-layout reads its own `offsetWidth` to size a
		     column, which is the padding box, and then lays the columns out
		     inside the padding — so the rightmost card ended 16px past the
		     page. An empty dashboard keeps the scroller, because it is also
		     where a chart is dropped onto the grid. -->
		<div
			v-else
			ref="grid"
			class="flex-1 overflow-y-auto p-4"
			@dragover="source.authoring?.dragOver($event)"
			@drop="source.authoring?.drop($event)"
		>
			<div
				v-if="!source.items.length"
				class="flex h-full w-full items-center justify-center text-p-base text-ink-gray-5"
			>
				{{ __('This dashboard is empty') }}
			</div>

			<VueGridLayout
				v-else
				class="h-fit w-full"
				:class="source.authoring?.editing ? 'mb-[20rem] !select-none' : ''"
				:cols="GRID_COLS"
				:disabled="!source.authoring?.editing"
				:verticalCompact="source.verticalCompact"
				:modelValue="source.items.map((item) => item.layout)"
				@update:modelValue="(layouts) => layouts && source.authoring?.moveItems(layouts)"
			>
				<template #item="{ index }">
					<component
						:is="source.cell"
						:item="source.items[index]"
						:index="index"
						:dashboard="source.name"
						:filters="cellFilters(source.items[index])"
						:priority="layoutRank(source.items[index])"
						:refresh-token="refreshToken"
						@loaded="executedAt[source.items[index].layout.i] = $event"
						@filter="setFilter(source.items[index], $event)"
						@reset-filters="filters = {}"
					/>
				</template>
			</VueGridLayout>
		</div>
	</div>
</template>
