<script setup lang="ts">
import { inject, ref } from 'vue'

import {
	WorkbookDashboardChart,
	WorkbookDashboardFilter,
	WorkbookDashboardItem,
	WorkbookDashboardText,
} from '../types/workbook.types'
import { Dashboard } from './dashboard'
import DashboardChart from './DashboardChart.vue'
import DashboardFilter from './DashboardFilter.vue'
import DashboardItemActions from './DashboardItemActions.vue'
import DashboardText from './DashboardText.vue'

const props = defineProps<{
	index: number
	item: WorkbookDashboardItem
}>()

const dashboard = inject('dashboard') as Dashboard

let timer: any
const wasDragging = ref(false)
const showPopover = ref(false)
const popoverDelay = 300
document.addEventListener('mousemove', (event) => {
	if (!dashboard.editing) return
	if (dashboard.isEditingItem(props.item)) {
		showPopover.value = false
		return
	}
	// if mouse moves while the button is pressed, it's dragging
	// once the button is released, it's not dragging
	// if not dragging then show popover after delay
	if (wasDragging.value && event.buttons == 0) {
		clearTimeout(timer)
		timer = setTimeout(() => (showPopover.value = true), popoverDelay)
		wasDragging.value = false
	}
	if (event.buttons == 1) {
		wasDragging.value = true
		showPopover.value = false
		clearTimeout(timer)
	}
})
</script>

<template>
	<div class="relative h-full w-full p-2 [&>div:first-child]:h-full">
		<Popover
			class="h-full"
			:show="dashboard.editing && dashboard.isActiveItem(index) && showPopover"
			placement="top-start"
		>
			<template #target>
				<div
					class="flex h-full w-full items-center rounded"
					:class="[
						dashboard.editing && dashboard.isActiveItem(index)
							? 'outline outline-gray-700'
							: '',
					]"
					@click="dashboard.setActiveItem(index)"
				>
					<div
						class="group relative flex h-full w-full flex-col justify-center"
						:class="dashboard.editing ? 'pointer-events-none' : ''"
					>
						<DashboardChart
							v-if="props.item.type == 'chart'"
							:item="(props.item as WorkbookDashboardChart)"
						/>

						<DashboardText
							v-else-if="props.item.type === 'text'"
							:item="(props.item as WorkbookDashboardText)"
						/>

						<DashboardFilter
							v-else-if="props.item.type === 'filter'"
							:item="(props.item as WorkbookDashboardFilter)"
						/>
					</div>
				</div>
			</template>
			<template #body>
				<DashboardItemActions
					:dashboard="dashboard"
					:item-index="index"
					:item="dashboard.doc.items[index]"
				/>
			</template>
		</Popover>
	</div>
</template>
