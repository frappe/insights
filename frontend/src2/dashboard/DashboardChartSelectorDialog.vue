<script setup lang="ts">
import { CheckSquare, SearchIcon, SquareIcon } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import ChartIcon from '../charts/components/ChartIcon.vue'
import { copy } from '../helpers'
import { WorkbookChart } from '../types/workbook.types'
import { Dashboard } from './dashboard'

const showDialog = defineModel()
const props = defineProps<{ chartOptions: WorkbookChart[] }>()

const dashboard = inject('dashboard') as Dashboard

const searchQuery = ref('')
const filteredCharts = computed(() => {
	if (!props.chartOptions.length) return []
	if (!searchQuery.value) return props.chartOptions
	return props.chartOptions.filter((chart) => {
		return chart.name.toLowerCase().includes(searchQuery.value.toLowerCase())
	})
})

const selectedCharts = ref<WorkbookChart[]>(
	copy(
		props.chartOptions.filter((chart) =>
			dashboard.doc.items.some((item) => item.type === 'chart' && item.chart === chart.name)
		)
	)
)
function isSelected(chart: WorkbookChart) {
	return selectedCharts.value.find((c) => c && c.name === chart.name)
}
function toggleChart(chart: WorkbookChart) {
	const index = selectedCharts.value.findIndex((c) => c && c.name === chart.name)
	if (index === -1) {
		selectedCharts.value.push(chart)
	} else {
		selectedCharts.value.splice(index, 1)
	}
}
function toggleSelectAll() {
	if (areAllSelected.value) {
		selectedCharts.value = []
	} else {
		selectedCharts.value = [...props.chartOptions]
	}
}
const areAllSelected = computed(() => selectedCharts.value.length === props.chartOptions.length)
const areNoneSelected = computed(() => selectedCharts.value.length === 0)
function confirmSelection() {
	dashboard.addChart(selectedCharts.value)
	selectedCharts.value = []
	showDialog.value = false
}
</script>

<template>
	<Dialog
		v-model="showDialog"
		:options="{
			size: 'sm',
			title: 'Select Charts',
			actions: [
				{
					label: 'Add',
					variant: 'solid',
					disabled: areNoneSelected,
					onClick: confirmSelection,
				},
				{
					label: 'Cancel',
					onClick: () => (showDialog = false),
				},
			],
		}"
	>
		<template #body-content>
			<div class="-mb-5 flex flex-col gap-2 p-0.5">
				<div class="flex gap-2">
					<FormControl
						class="flex-1"
						autocomplete="off"
						placeholder="Search by name"
						v-model="searchQuery"
					>
						<template #prefix>
							<SearchIcon class="h-4 w-4 text-gray-500" />
						</template>
					</FormControl>
					<Button @click="toggleSelectAll">
						{{
							areAllSelected
								? `Deselect All (${selectedCharts.length})`
								: `Select All (${selectedCharts.length})`
						}}
					</Button>
				</div>
				<div
					class="flex h-[15rem] flex-col overflow-y-scroll rounded border p-0.5 text-base"
				>
					<template v-for="chart in filteredCharts">
						<div
							class="flex h-7 flex-shrink-0 cursor-pointer items-center justify-between rounded px-2 hover:bg-gray-100"
							@click="toggleChart(chart)"
						>
							<div class="flex items-center gap-1.5">
								<ChartIcon :chartType="chart.chart_type" />
								<span>{{ chart.title || chart.name }}</span>
							</div>
							<component
								class="h-4 w-4"
								stroke-width="1.5"
								:is="isSelected(chart) ? CheckSquare : SquareIcon"
								:class="isSelected(chart) ? 'text-gray-900' : 'text-gray-600'"
							/>
						</div>
					</template>
				</div>
			</div>
		</template>
	</Dialog>
</template>
