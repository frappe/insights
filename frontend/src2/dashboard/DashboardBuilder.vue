<script setup lang="ts">
import { useWindowSize } from '@vueuse/core'
import { Edit3, RefreshCcw, Share2 } from 'lucide-vue-next'
import { computed, provide, ref, watchEffect } from 'vue'
import ContentEditable from '../components/ContentEditable.vue'
import { safeJSONParse, waitUntil } from '../helpers'
import { WorkbookChart, WorkbookQuery } from '../types/workbook.types'
import useDashboard from './dashboard'
import DashboardChartSelectorDialog from './DashboardChartSelectorDialog.vue'
import DashboardItem from './DashboardItem.vue'
import DashboardShareDialog from './DashboardShareDialog.vue'
import VueGridLayout from './VueGridLayout.vue'

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
</script>

<template>
	<div class="relative flex h-full w-full overflow-hidden bg-gray-50">
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<div class="flex items-center justify-between p-4 pb-3">
				<ContentEditable
					class="cursor-text rounded-sm text-lg font-semibold !text-gray-800 focus:ring-2 focus:ring-gray-700 focus:ring-offset-4"
					v-model="dashboard.doc.title"
					placeholder="Untitled Dashboard"
				></ContentEditable>
				<div class="flex gap-2">
					<Button
						v-if="!dashboard.editing"
						variant="outline"
						@click="() => dashboard.refresh()"
						label="Refresh"
					>
						<template #prefix>
							<RefreshCcw class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
					<Button
						v-if="!dashboard.editing && !dashboard.doc.read_only"
						variant="outline"
						@click="showShareDialog = true"
						label="Share"
					>
						<template #prefix>
							<Share2 class="h-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
					<Button
						v-if="!dashboard.editing"
						variant="outline"
						@click="dashboard.editing = true"
						label="Edit"
					>
						<template #prefix>
							<Edit3 class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
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
						@click="dashboard.editing = false"
					>
						Done
					</Button>
				</div>
			</div>
			<div class="flex-1 overflow-y-auto p-2 pt-0" @dragover="onDragOver" @drop="onDrop">
				<VueGridLayout
					v-if="dashboard.doc.items.length > 0"
					class="h-fit w-full"
					:class="[dashboard.editing ? 'mb-[20rem] !select-none' : '']"
					:cols="20"
					:disabled="!dashboard.editing"
					:modelValue="dashboard.doc.items.map((item) => item.layout)"
					@update:modelValue="
						(newLayout) => {
							dashboard.doc.items.forEach((item, idx) => {
								item.layout = newLayout[idx]
							})
						}
					"
				>
					<template #item="{ index }">
						<DashboardItem :index="index" :item="dashboard.doc.items[index]" />
					</template>
				</VueGridLayout>
			</div>
		</div>
	</div>

	<DashboardChartSelectorDialog v-model="showChartSelectorDialog" :chartOptions="props.charts" />

	<DashboardShareDialog v-if="showShareDialog" v-model="showShareDialog" />
</template>
