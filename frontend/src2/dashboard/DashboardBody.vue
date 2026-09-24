<script setup lang="ts">
import { computed, ref, type Component } from 'vue'
import { downloadImage } from '../helpers'
import { resolveHref } from '../helpers/navigation'
import { __ } from '../translation'
import type { BreakpointKey, Layout } from '../types/workbook.types'
import { BASE_BREAKPOINT, BREAKPOINTS } from './grid_placement'
import type { DashboardAction, DashboardView } from './view'

// A dashboard's content, on every surface that shows one: the grid of cards and
// the filters a reader moves, which are cells of that grid, and every state the
// page can be in before there is a grid to draw.
//
// It draws no header. Every surface has one of its own already, and draws it
// above this: the SPA page and the builder read the actions off a template ref,
// and the island reports the same list to its host. Nothing here asks which
// surface it is — a capability is either on the dashboard or it is not.
//
// The surface hands this a bounded box and it fills it. The grid then scrolls
// without the page around it scrolling too.
const props = defineProps<{
	// the dashboard to draw: `useDashboardView` on a view surface,
	// `useDashboardBuilder` in the builder
	dashboard: DashboardView
	// what draws it. A reader is given a grid that only draws, so the
	// drag-and-resize engine never reaches a surface that cannot use it
	grid: Component
	cell: Component
}>()

// An owner arranging a narrower breakpoint is given a box that width, rather
// than a wide grid told to pretend. The grid then measures the breakpoint it is
// arranging, the cards lay their contents out at the width they will really
// have, and a drag lands where the reader will see it.
const arrangedBox = computed(() => {
	const key = props.dashboard.builder?.arranging
	const breakpoint = BREAKPOINTS.find((item) => item.key === key)
	if (!breakpoint || breakpoint === BASE_BREAKPOINT) return undefined
	return { maxWidth: `${breakpoint.maxWidth}px` }
})

// Everything a reader may do with this dashboard, in one list. Every action is
// offered on the strength of what the dashboard carries, never of which surface
// this is, and the refresh is a member like any other — nothing outside adds to
// the list. A surface renders it and decides nothing.
//
// An action that leads somewhere carries the href its own surface resolves: the
// SPA's router and the island's Insights base answer the same route differently.
const actions = computed(() => {
	const builderRoute = props.dashboard.builderRoute
	// A dashboard being rearranged has nothing to re-run, and its half-placed
	// cards are not a picture anyone wants kept.
	const reading = !props.dashboard.builder?.editing
	return [
		reading ? { label: __('Refresh'), icon: 'refresh-cw', onClick: refresh } : null,
		reading && !props.dashboard.failed
			? { label: __('Export as PNG'), icon: 'download', onClick: exportImage }
			: null,
		builderRoute
			? { label: __('Edit'), icon: 'pencil', href: resolveHref(builderRoute) }
			: null,
		...(props.dashboard.builder?.menuOptions || []),
	].filter(Boolean) as DashboardAction[]
})

// the scrolling box the cards sit in, and the picture an export keeps
const scroller = ref<HTMLElement>()

// Re-run every card on the page. Forced, because the rows on screen already
// answer the question the cards would ask again.
function refresh() {
	props.dashboard.refresh(true)
}

// The one thing a surface reads off this component. A page reaches it through a
// template ref, and the island through the same ref before reporting it on.
defineExpose({ actions })

// the scrolling box of cards, which is what a reader means by the dashboard. The
// surface's header sits above this component and was never in the picture
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

		<!-- The one scroller on the page. An empty dashboard keeps it, because it
		     is also where a chart is dropped onto the grid. -->
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
