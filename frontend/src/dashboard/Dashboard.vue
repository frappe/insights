<script setup>
import DashboardTitle from '@/dashboard/DashboardTitle.vue'
import useDashboard from '@/dashboard/useDashboard'
import VueGridLayout from '@/dashboard/VueGridLayout.vue'
import { updateDocumentTitle } from '@/utils'
import { computed, provide, ref } from 'vue'
import DashboardEmptyState from './DashboardEmptyState.vue'
import DashboardItem from './DashboardItem.vue'
import DashboardNavbarButtons from './DashboardNavbarButtons.vue'
import DashboardSidebarWidgets from './DashboardSidebarWidgets.vue'
import UseDropZone from './UseDropZone.vue'
import widgets from './widgets/widgets'

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
	<div v-if="dashboard.doc.name" class="flex h-full w-full flex-col bg-gray-100">
		<!-- Dashboard Navbar -->
		<div class="flex h-14 items-center justify-between border-b bg-white px-3 shadow-sm">
			<div class="flex flex-shrink-0 items-center space-x-4">
				<DashboardTitle
					:title="dashboard.doc.title"
					:disabled="!dashboard.editing"
					@update="dashboard.updateTitle"
				/>
			</div>
			<DashboardNavbarButtons />
		</div>

		<div class="flex flex-1 overflow-hidden">
			<div class="h-full w-full overflow-y-scroll p-4">
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
						v-if="dashboard.doc.items.length"
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

			<div
				v-if="dashboard.editing && dashboard.sidebar.open"
				class="w-[21rem] flex-shrink-0 border-l bg-white p-3 px-4 shadow-sm"
			>
				<div v-if="!dashboard.currentItem">
					<div class="mb-3 font-semibold text-gray-800">Charts</div>
					<DashboardSidebarWidgets @dragChange="draggingWidget = $event" />
				</div>

				<div v-else>
					<!-- Widget Options -->
					<div class="mb-4 flex items-center text-lg font-medium text-gray-400">
						<Button
							appearance="white"
							icon="arrow-left"
							@click="dashboard.currentItem = undefined"
						></Button>
						<div class="ml-2 text-gray-800">Back</div>
					</div>

					<component
						:is="widgets.getOptionComponent(dashboard.currentItem.item_type)"
						v-model="dashboard.currentItem.options"
					/>
				</div>
			</div>
		</div>
	</div>
</template>
