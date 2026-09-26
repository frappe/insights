<script setup lang="ts">
import { computed, ref, type Component } from 'vue'
import { downloadImage } from '../helpers'
import { resolveHref } from '../helpers/navigation'
import { __ } from '../translation'
import type { BreakpointKey, Layout } from '../types/workbook.types'
import { BASE_BREAKPOINT, BREAKPOINTS } from './grid_placement'
import type { DashboardAction, DashboardView } from './view'

// A dashboard's content on every page that shows one: the grid, with its filter
// cells, and the loading, Not Found and error states.
//
// It renders no header. Each page renders its own header above this. The SPA
// page and the builder read the actions through a template ref, and the island
// reports the same list to its host. Nothing here checks which page it is on.
//
// The page gives this a box of fixed size, and this fills it. So the grid
// scrolls and the page around it does not.
const props = defineProps<{
	// `useDashboardView` on a view page, `useDashboardBuilder` in the builder
	dashboard: DashboardView
	// A reader gets a read-only grid, so the drag-and-resize code never loads on
	// a page that cannot use it
	grid: Component
	cell: Component
}>()

// When an owner arranges a narrower breakpoint, the box gets that real width.
// The grid then measures the breakpoint itself, the cards lay out at their real
// width, and a drag lands where the reader will see it.
const arrangedBox = computed(() => {
	const key = props.dashboard.builder?.arranging
	const breakpoint = BREAKPOINTS.find((item) => item.key === key)
	if (!breakpoint || breakpoint === BASE_BREAKPOINT) return undefined
	return { maxWidth: `${breakpoint.maxWidth}px` }
})

// Every action a reader may take, in one list. An action shows only if the
// dashboard has the capability for it, never because of which page this is.
// Nothing outside adds to the list. A page only renders it.
//
// An `href` is resolved for the current page, because the SPA's router and the
// island's Insights base resolve the same route differently.
const actions = computed(() => {
	const builderRoute = props.dashboard.builderRoute
	// While the owner rearranges the grid, there is nothing to re-run, and a PNG
	// of half-placed cards is not useful.
	const reading = !props.dashboard.builder?.editing
	return [
		reading ? { label: __('Refresh'), icon: 'refresh-cw', onClick: refresh } : null,
		reading && !props.dashboard.failed
			? { label: __('Export as PNG'), icon: 'download', onClick: exportImage }
			: null,
		builderRoute
			? { label: __('Edit'), icon: 'pencil', href: resolveHref(builderRoute) }
			: null,
		reading && props.dashboard.duplicate
			? { label: __('Duplicate'), icon: 'copy', onClick: props.dashboard.duplicate }
			: null,
		...(props.dashboard.builder?.menuOptions || []),
	].filter(Boolean) as DashboardAction[]
})

// the scrolling box of cards, which is also what an export captures
const scroller = ref<HTMLElement>()

// Forced, because each card's request is unchanged and a normal load would skip.
function refresh() {
	props.dashboard.refresh(true)
}

// A page reads this through a template ref. The island reads the same ref and
// reports the actions to its host.
defineExpose({ actions })

// Only the cards are exported. The page's header is outside this component.
function exportImage() {
	if (!scroller.value) return
	return downloadImage(scroller.value, `${props.dashboard.title}.png`)
}
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden">
		<div
			v-if="dashboard.notFound"
			class="flex w-full flex-1 items-center justify-center p-4 text-p-base text-ink-gray-5"
		>
			{{ __('Dashboard not found') }}
		</div>

		<div
			v-else-if="dashboard.failed"
			class="flex w-full flex-1 items-center justify-center p-4 text-p-base text-ink-gray-5"
		>
			{{ __('Could not load the dashboard. Refresh to try again.') }}
		</div>

		<div v-else-if="dashboard.loading" class="flex-1 p-4">
			<div class="h-8 w-64 animate-pulse rounded-4 bg-surface-gray-2" />
		</div>

		<!-- The only scroller on the page. An empty dashboard keeps it, because a
		     chart is dropped onto the grid here. -->
		<div
			v-else
			ref="scroller"
			class="flex-1 overflow-y-auto p-2"
			@dragover="dashboard.builder?.dragOver($event)"
			@drop="dashboard.builder?.drop($event)"
		>
			<div
				v-if="!dashboard.items.length"
				class="flex h-full w-full items-center justify-center text-p-base text-ink-gray-5"
			>
				{{ __('This dashboard is empty') }}
			</div>

			<component
				:is="props.grid"
				v-else
				class="mx-auto h-fit w-full"
				:style="arrangedBox"
				:breakpoint="dashboard.builder?.arranging"
				:class="dashboard.builder?.editing ? 'mb-[20rem] !select-none' : ''"
				:disabled="!dashboard.builder?.editing"
				:verticalCompact="dashboard.verticalCompact"
				:items="dashboard.items"
				:rules="dashboard.cellRules"
				@move="
					(key: BreakpointKey, layouts: Layout[], before: Layout[]) =>
						layouts && dashboard.builder?.moveItems(key, layouts, before)
				"
			>
				<template #item="{ index }">
					<component
						:is="props.cell"
						:dashboard="dashboard"
						:item="dashboard.items[index]"
						:index="index"
					/>
				</template>
			</component>
		</div>
	</div>
</template>
