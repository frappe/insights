<script setup>
import DashboardTitle from '@/dashboard/DashboardTitle.vue'
import useDashboard from '@/dashboard/useDashboard'
import VueGridLayout from '@/dashboard/VueGridLayout.vue'
import BaseLayout from '@/layouts/BaseLayout.vue'
import { updateDocumentTitle } from '@/utils'
import widgets from '@/widgets/widgets'
import { computed, provide, ref } from 'vue'
import DashboardEmptyState from './DashboardEmptyState.vue'
import DashboardItem from './DashboardItem.vue'
import DashboardNavbarButtons from './DashboardNavbarButtons.vue'
import DashboardQueryOption from './DashboardQueryOption.vue'
import DashboardSidebarWidgets from './DashboardWidgetsOptions.vue'
import UseDropZone from './UseDropZone.vue'

const props = defineProps({
	name: { type: String, required: true },
})

const dashboard = useDashboard(props.name)
provide('dashboard', dashboard)

window.dashboard = dashboard

const draggingWidget = ref(false)
function addWidget(dropEvent) {
	const initialXandY = calcInitialXY(dropEvent)
	draggingWidget.value = false
	const widgetType = dashboard.draggingWidget?.type
	if (widgetType) {
		const itemID = Math.floor(Math.random() * 1000000)
		dashboard.addItem({
			item_id: itemID,
			item_type: widgetType,
			initialX: initialXandY.x,
			initialY: initialXandY.y,
		})
		dashboard.setCurrentItem(itemID)
		dashboard.draggingWidget = null
	}
}

const gridLayout = ref(null)
function calcInitialXY({ x, y }) {
	const colWidth = gridLayout.value.getBoundingClientRect().width / 20
	const rowHeight = 30
	return {
		x: Math.round(x / colWidth),
		y: Math.round(y / rowHeight),
	}
}

const pageMeta = computed(() => {
	return {
		title: props.name,
		subtitle: 'Dashboard',
	}
})
updateDocumentTitle(pageMeta)
</script>

<template>
	<BaseLayout v-if="dashboard.doc.name">
		<template #navbar>
			<div class="flex flex-shrink-0 items-center space-x-4">
				<DashboardTitle
					:title="dashboard.doc.title"
					:disabled="!dashboard.editing"
					@update="dashboard.updateTitle"
				/>
			</div>
			<DashboardNavbarButtons />
		</template>

		<template #content>
			<div class="h-full w-full overflow-y-scroll p-2">
				<div
					ref="gridLayout"
					class="relative flex h-fit min-h-screen w-full flex-1 flex-col"
				>
					<UseDropZone
						v-if="dashboard.editing && draggingWidget"
						class="absolute top-0 left-0 z-10 h-full w-full"
						:onDrop="addWidget"
						:showCollision="true"
						colliderClass=".dashboard-item"
						:ghostWidth="(dashboard.draggingWidget?.defaultWidth || 4) * 50.8"
						:ghostHeight="(dashboard.draggingWidget?.defaultHeight || 2) * 30"
					>
					</UseDropZone>

					<VueGridLayout
						class="h-fit w-full"
						:class="[dashboard.editing ? 'mb-[20rem] ' : '']"
						:items="dashboard.doc.items"
						:disabled="!dashboard.editing"
						v-model:layouts="dashboard.itemLayouts"
					>
						<template #item="{ item }">
							<DashboardItem :item="item" :key="item.item_id" />
						</template>
					</VueGridLayout>

					<DashboardEmptyState
						v-if="!dashboard.doc.items.length"
						class="absolute top-1/2 left-1/2 mx-auto -translate-x-1/2 -translate-y-1/2 transform"
					/>
				</div>
			</div>
		</template>

		<template #sidebar v-if="dashboard.editing && dashboard.sidebar.open">
			<div class="w-[21rem] overflow-scroll border-l bg-white p-3 px-4 shadow-sm">
				<div v-if="!dashboard.currentItem">
					<div class="mb-3 font-semibold text-gray-800">Widgets</div>
					<DashboardSidebarWidgets @dragChange="draggingWidget = $event" />
				</div>

				<div v-else class="space-y-4">
					<!-- Widget Options -->
					<div class="flex items-center text-lg font-medium text-gray-400">
						<Button
							appearance="white"
							icon="arrow-left"
							@click="dashboard.currentItem = undefined"
						></Button>
						<div class="ml-2 text-gray-800">Back</div>
					</div>

					<Input
						type="select"
						label="Widget Type"
						class="w-full"
						:options="widgets.list.map((widget) => widget.type)"
						v-model="dashboard.currentItem.item_type"
					/>

					<DashboardQueryOption
						v-if="dashboard.isChart(dashboard.currentItem)"
						v-model="dashboard.currentItem.options.query"
					/>

					<component
						:is="widgets.getOptionComponent(dashboard.currentItem.item_type)"
						v-model="dashboard.currentItem.options"
						:key="dashboard.currentItem.item_id"
					/>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>
