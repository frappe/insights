<template>
	<BasePage>
		<template #header>
			<DashboardHeader
				@addChart="() => (showAddDialog = true)"
				@commitLayout="commitLayout"
			/>
		</template>
		<template #main>
			<div
				v-if="charts && charts.length > 0"
				class="-mx-1 h-full w-full overflow-scroll pt-1"
				:class="{
					'blur-[4px]': dashboard.refreshing,
					'rounded-md bg-slate-50 shadow-inner': dashboard.editingLayout,
				}"
			>
				<GridLayout
					:items="charts"
					itemKey="name"
					@layoutChange="updateLayout"
					:disabled="!dashboard.editingLayout"
					:options="{
						float: true,
						margin: 4,
						column: 20,
						cellHeight: 30,
					}"
				>
					<template #item="{ item }">
						<DashboardCard
							:chartID="item.chartID"
							:queryID="item.query"
							@edit="editChart"
							@remove="removeChart"
						/>
					</template>
				</GridLayout>
			</div>
			<div
				v-if="charts && charts.length == 0"
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
			<Button appearance="primary" @click="addChart" :loading="addingChart"> Add </Button>
		</template>
	</Dialog>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import DashboardHeader from '@/components/Dashboard/DashboardHeader.vue'
import DashboardCard from '@/components/Dashboard/DashboardCard.vue'

import { computed, ref, provide, reactive, watch } from 'vue'
import useDashboard from '@/utils/dashboard'
import { updateDocumentTitle } from '@/utils'

import GridLayout from '@/components/Dashboard/GridLayout.vue'
import { safeJSONParse } from '@/utils'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const dashboard = useDashboard(props.name)
provide('dashboard', dashboard)

const charts = computed(() =>
	dashboard.doc?.items.map((v) => {
		const layout = safeJSONParse(v.layout, {})
		return {
			...v,
			...layout,
			chartID: v.query_chart,
		}
	})
)

const updatedLayout = reactive({})
const updateLayout = (changedItems) => {
	changedItems.forEach((item) => {
		const name = item.id
		delete item.id
		updatedLayout[name] = item
	})
}

const commitLayout = () => {
	dashboard.updateLayout.submit({
		updated_layout: updatedLayout,
	})
	dashboard.editingLayout = false
}

const showAddDialog = ref(false)
const newChart = ref({})

const addChart = () => {
	dashboard.addChart
		.submit({
			query_chart: newChart.value.value,
		})
		.then(() => {
			newChart.value = {}
			showAddDialog.value = false
			dashboard.updateNewChartOptions()
		})
}
const addingChart = computed(() => dashboard.addChart.loading)

const removeChart = (chartID) => {
	dashboard.removeChart
		.submit({
			query_chart: chartID,
		})
		.then(() => {
			dashboard.updateNewChartOptions()
		})
}

const editChart = (queryID) => {
	window.open(`/insights/query/${queryID}`, '_blank')
}

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
		title: dashboard.doc?.name,
		subtitle: 'Dashboard',
	}
})
updateDocumentTitle(pageMeta)
</script>
