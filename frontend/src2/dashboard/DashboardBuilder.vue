<script setup lang="ts">
import { useStorage, useWindowSize } from '@vueuse/core'
import { TabButtons } from 'frappe-ui'
import { Edit3, RefreshCcw, Share2 } from 'lucide-vue-next'
import { computed, provide, ref, watchEffect } from 'vue'
import ContentEditable from '../components/ContentEditable.vue'
import { downloadImage, safeJSONParse, waitUntil } from '../helpers'
import { BreakpointKey, Layout, WorkbookChart, WorkbookQuery } from '../types/workbook.types'
import useDashboard from './dashboard'
import DashboardChartSelectorDialog from './DashboardChartSelectorDialog.vue'
import DashboardItem from './DashboardItem.vue'
import DashboardShareDialog from './DashboardShareDialog.vue'
import EditableGridLayout from './EditableGridLayout.vue'
import { BASE_BREAKPOINT, BREAKPOINTS } from './grid_placement'
import { __ } from '../translation'

const props = defineProps<{
	dashboard_name: string
	charts: WorkbookChart[]
	queries: WorkbookQuery[]
}>()

const dashboard = useDashboard(props.dashboard_name)
provide('dashboard', dashboard)

const { width } = useWindowSize()
const isMobile = computed(() => width.value < 1058)

watchEffect(() => {
	if (dashboard.editing || isMobile.value) {
		dashboard.autoSave = false
	} else {
		dashboard.autoSave = true
	}
})

await waitUntil(() => dashboard.isloaded)

const showChartSelectorDialog = ref(false)

function onDragOver(event: DragEvent) {
	if (!event.dataTransfer) return
	event.preventDefault()
	event.dataTransfer.dropEffect = 'copy'
}
function onDrop(event: DragEvent) {
	if (!event.dataTransfer) return
	event.preventDefault()
	const data = safeJSONParse(event.dataTransfer.getData('text/plain'))
	const chartName = data.item.name
	const chart = props.charts.find((c) => c.name === chartName)
	if (!chart) return
	if (!dashboard.editing) {
		dashboard.editing = true
	}
	dashboard.addChart([chart])
}

const showShareDialog = ref(false)

const verticalCompact = useStorage('dashboard_vertical_compact', true)

// One entry per breakpoint, widest first — the layout an author arranges first
// reads first. A new width is a row in `BREAKPOINTS` and turns up here on its
// own, so this switch cannot fall behind the layouts the grid can draw.
const widths = computed(() =>
	[...BREAKPOINTS].reverse().map((breakpoint) => ({
		value: breakpoint.key,
		icon: breakpoint.icon,
		label: __(breakpoint.label),
		tooltip: __('Arrange the {0} layout').replace('{0}', __(breakpoint.label).toLowerCase()),
	})),
)

// An author arranging a narrower breakpoint is given a box that width, rather
// than a wide grid told to pretend. The grid then measures the breakpoint it is
// arranging, the cards lay their contents out at the width they will really
// have, and a drag lands where the reader will see it.
const arrangedBox = computed(() => {
	const breakpoint = BREAKPOINTS.find((item) => item.key === dashboard.arranging)
	if (!breakpoint || breakpoint === BASE_BREAKPOINT) return undefined
	return { maxWidth: `${breakpoint.maxWidth}px` }
})

const dashboardContainer = ref<HTMLElement | null>(null)
async function downloadDashboardImage() {
	if (!dashboardContainer.value) return
	await downloadImage(dashboardContainer.value, `${dashboard.doc.title}.png`)
}
</script>

<template>
	<div class="relative flex h-full w-full overflow-hidden">
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<!-- the first card's own 8px inset completes the query view's 12px gap -->
			<div class="flex h-7 items-center justify-between mx-4 mt-3 mb-1">
				<ContentEditable
					class="-ml-2 cursor-text text-lg-semibold !text-ink-gray-7"
					:modelValue="dashboard.doc.title"
					@returned="dashboard.doc.title = $event"
					@blur="dashboard.doc.title = $event"
					placeholder="Untitled Dashboard"
				></ContentEditable>
				<div class="flex gap-2">
					<Button
						v-if="!dashboard.editing"
						variant="outline"
						@click="() => dashboard.refresh(true)"
						label="Refresh"
					>
						<template #prefix>
							<RefreshCcw class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
						</template>
					</Button>
					<Button
						v-if="!dashboard.editing && !dashboard.doc.read_only"
						variant="outline"
						@click="showShareDialog = true"
						label="Share"
					>
						<template #prefix>
							<Share2 class="h-4 text-ink-gray-6" stroke-width="1.5" />
						</template>
					</Button>
					<Button
						v-if="!dashboard.editing"
						variant="outline"
						@click="dashboard.editing = true"
						label="Edit"
					>
						<template #prefix>
							<Edit3 class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
						</template>
					</Button>
					<TabButtons
						v-if="dashboard.editing"
						v-model="dashboard.arranging"
						:options="widths"
					/>
					<Button
						v-if="dashboard.editing"
						variant="outline"
						icon-left="plus"
						@click="showChartSelectorDialog = true"
					>
						Chart
					</Button>
					<Button
						v-if="dashboard.editing"
						variant="outline"
						icon-left="plus"
						@click="() => dashboard.addFilter()"
					>
						Filter
					</Button>
					<Button
						v-if="dashboard.editing"
						variant="outline"
						icon-left="plus"
						@click="() => dashboard.addText()"
					>
						Text
					</Button>
					<Button
						v-if="dashboard.editing"
						variant="solid"
						icon-left="check"
						@click="
							() => {
								dashboard.save()
								dashboard.editing = false
							}
						"
					>
						Done
					</Button>
					<Dropdown
						:button="{ icon: 'lucide-more-horizontal', variant: 'outline' }"
						:options="[
							{
								label: __('Force Refresh'),
								icon: RefreshCcw,
								onClick: () => dashboard.refresh(true),
							},
							{
								label: __('Export as PNG'),
								variant: 'outline',
								icon: 'lucide-download',
								onClick: downloadDashboardImage,
							},
							dashboard.editing
								? {
										label: __('Compact Layout'),
										icon: verticalCompact ? 'check-square' : 'square',
										onClick: () => (verticalCompact = !verticalCompact),
								  }
								: null,
							dashboard.editing
								? {
										label: __('Reset Layout'),
										icon: 'lucide-refresh-ccw',
										onClick: () => (
											dashboard.discard(), (dashboard.editing = false)
										),
								  }
								: null,
						]"
					/>
				</div>
			</div>
			<div
				ref="dashboardContainer"
				class="flex-1 overflow-y-auto p-2 pt-0"
				@dragover="onDragOver"
				@drop="onDrop"
			>
				<EditableGridLayout
					v-if="dashboard.doc.items.length > 0"
					class="mx-auto h-fit w-full"
					:class="[dashboard.editing ? 'mb-[20rem] !select-none' : '']"
					:style="arrangedBox"
					:breakpoint="dashboard.arranging"
					:disabled="!dashboard.editing"
					:verticalCompact="verticalCompact"
					:items="dashboard.doc.items"
					:rules="dashboard.cellRules"
					@move="
						(key: BreakpointKey, layouts: Layout[]) => dashboard.moveItems(key, layouts)
					"
				>
					<template #item="{ index }">
						<DashboardItem :index="index" :item="dashboard.doc.items[index]" />
					</template>
				</EditableGridLayout>
			</div>
		</div>
	</div>

	<DashboardChartSelectorDialog v-model="showChartSelectorDialog" :chartOptions="props.charts" />

	<DashboardShareDialog v-if="showShareDialog" v-model="showShareDialog" />
</template>
