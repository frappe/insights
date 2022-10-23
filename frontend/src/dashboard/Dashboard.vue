<template>
	<BasePage>
		<template #header>
			<DashboardHeader
				@addChart="() => (showAddDialog = true)"
				@commitLayout="dashboard.commitLayout"
			/>
		</template>
		<template #main>
			<div
				v-if="dashboard.items && dashboard.items.length > 0"
				class="-mx-1 h-full w-full overflow-scroll pt-1"
				:class="{
					'blur-[4px]': dashboard.refreshing,
					'rounded-md bg-slate-50 shadow-inner': dashboard.editingLayout,
				}"
			>
				<GridLayout
					:items="dashboard.items"
					itemKey="name"
					@layoutChange="dashboard.updateLayout"
					:disabled="!dashboard.editingLayout"
					:options="{
						float: true,
						margin: 4,
						column: 20,
						cellHeight: 30,
					}"
				>
					<template #item="{ item }">
						<DashboardItem :item="item" />
					</template>
				</GridLayout>
			</div>
			<div
				v-if="dashboard.items && dashboard.items.length == 0"
				class="flex flex-1 flex-col items-center justify-center space-y-1"
			>
				<div class="text-base font-light text-gray-500">You haven't added any charts.</div>
				<div
					class="cursor-pointer text-sm font-light text-blue-500 hover:underline"
					@click="showAddDialog = true"
				>
					Add one?
				</div>
			</div>
		</template>
	</BasePage>

	<Dialog :options="{ title: 'Add Chart' }" v-model="showAddDialog" :dismissable="true">
		<template #body-content>
			<div class="space-y-4">
				<Autocomplete
					ref="autocomplete"
					placeholder="Select a chart"
					v-model="newChart"
					:options="dashboard.newChartOptions"
				/>
			</div>
		</template>
		<template #actions>
			<Button
				appearance="primary"
				@click="
					() =>
						dashboard.addChart(newChart.value).then(() => {
							newChart = {}
							showAddDialog = false
						})
				"
				:loading="dashboard.addingChart"
			>
				Add
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import DashboardHeader from '@/dashboard/DashboardHeader.vue'
import DashboardItem from '@/dashboard/DashboardItem.vue'
import GridLayout from '@/dashboard/GridLayout.vue'

import { computed, ref, provide, watch } from 'vue'
import { updateDocumentTitle } from '@/utils'
import useDashboard from '@/dashboard/useDashboard'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const dashboard = useDashboard(props.name)
provide('dashboard', dashboard)

const showAddDialog = ref(false)
const newChart = ref({})

const autocomplete = ref(null)
watch(showAddDialog, (show) => {
	if (show) {
		setTimeout(() => {
			autocomplete.value.input.$el.blur()
			autocomplete.value.input.$el.focus()
		}, 400)
	}
})

const pageMeta = computed(() => {
	return {
		title: props.name,
		subtitle: 'Dashboard',
	}
})
updateDocumentTitle(pageMeta)
</script>
