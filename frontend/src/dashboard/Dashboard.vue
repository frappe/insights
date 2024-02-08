<script setup>
import ContentEditable from '@/components/ContentEditable.vue'
import VueGridLayout from '@/dashboard/VueGridLayout.vue'
import useDashboard from '@/dashboard/useDashboard'
import BaseLayout from '@/layouts/BaseLayout.vue'
import { updateDocumentTitle } from '@/utils'
import widgets from '@/widgets/widgets'
import { debounce } from 'frappe-ui'
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
		title: dashboard.doc.title || props.name,
		subtitle: 'Dashboard',
	}
})
updateDocumentTitle(pageMeta)

const debouncedUpdateTitle = debounce((value) => dashboard.updateTitle(value), 500)
</script>

<template>
	<BaseLayout v-if="dashboard.doc.name">
		<template #navbar>
			<div class="flex flex-shrink-0 items-center space-x-4">
				<ContentEditable
					class="rounded-sm text-lg font-medium !text-gray-800 focus:ring-2 focus:ring-gray-700 focus:ring-offset-4"
					:class="[dashboard.editing ? '' : 'cursor-default']"
					:value="dashboard.doc.title"
					:disabled="!dashboard.editing"
					@change="dashboard.updateTitle($event)"
					placeholder="Untitled Dashboard"
				></ContentEditable>
			</div>
			<DashboardNavbarButtons />
		</template>

		<template #content>
			<div class="h-full w-full overflow-y-auto p-2">
				<div
					ref="gridLayout"
					class="dashboard relative flex h-fit min-h-screen w-full flex-1 flex-col"
				>
					<UseDropZone
						v-if="dashboard.editing && draggingWidget"
						class="absolute left-0 top-0 z-10 h-full w-full"
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
						class="absolute left-1/2 top-1/2 mx-auto -translate-x-1/2 -translate-y-1/2 transform"
					/>
				</div>
			</div>
		</template>

		<template #sidebar v-if="dashboard.editing && dashboard.sidebar.open">
			<div class="w-[21rem] overflow-y-auto border-l bg-white p-3 px-4 shadow-sm">
				<div v-if="!dashboard.currentItem">
					<div class="mb-3 font-semibold text-gray-800">Widgets</div>
					<DashboardSidebarWidgets @dragChange="draggingWidget = $event" />
				</div>

				<div v-else class="space-y-4">
					<!-- Widget Options -->
					<div class="flex items-center text-lg font-medium text-gray-500">
						<Button
							variant="outline"
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
						@update:model-value="dashboard.loadCurrentItemQuery"
					/>

					<component
						v-if="widgets.getOptionComponent(dashboard.currentItem.item_type)"
						:is="widgets.getOptionComponent(dashboard.currentItem.item_type)"
						v-model="dashboard.currentItem.options"
						:columns="dashboard.currentItem.query?.results.columns"
						:key="
							dashboard.currentItem.item_id &&
							dashboard.currentItem.item_type &&
							dashboard.currentItem.query?.doc?.name
						"
					/>

					<div class="flex space-x-2">
						<Button
							iconLeft="refresh-ccw"
							variant="outline"
							@click="dashboard.resetOptions(dashboard.currentItem)"
						>
							Reset Options
						</Button>
						<Button
							iconLeft="trash"
							variant="outline"
							class="ml-auto text-red-500"
							@click="dashboard.removeItem(dashboard.currentItem)"
						>
							Delete Widget
						</Button>
					</div>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>
