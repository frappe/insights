<script setup lang="ts">
import { CheckSquare, SearchIcon, SquareIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { WorkbookChart } from '../workbook/workbook'
import ChartIcon from '../charts/components/ChartIcon.vue'

const showDialog = defineModel()
const props = defineProps<{ options: WorkbookChart[] }>()
const emit = defineEmits({
	select: (charts: string[]) => true,
})

const searchQuery = ref('')
const filteredCharts = computed(() => {
	if (!props.options.length) return []
	if (!searchQuery.value) return props.options
	return props.options.filter((chart) => {
		return chart.name.toLowerCase().includes(searchQuery.value.toLowerCase())
	})
})

const selectedCharts = ref<string[]>([])
function isSelected(chart: string) {
	return selectedCharts.value.includes(chart)
}
function toggleChart(chart: string) {
	const index = selectedCharts.value.indexOf(chart)
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
		selectedCharts.value = [...props.options.map((c) => c.name)]
	}
}
const areAllSelected = computed(() => selectedCharts.value.length === props.options.length)
const areNoneSelected = computed(() => selectedCharts.value.length === 0)
function confirmSelection() {
	emit('select', selectedCharts.value)
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
			<div class="-mb-5 flex max-h-[20rem] flex-col gap-2 p-0.5">
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
				<div class="flex flex-col overflow-y-scroll rounded border p-0.5 text-base">
					<template v-for="chart in filteredCharts">
						<div
							class="flex h-7 flex-shrink-0 cursor-pointer items-center justify-between rounded px-2 hover:bg-gray-100"
							@click="toggleChart(chart.name)"
						>
							<div class="flex items-center gap-1.5">
								<ChartIcon :chartType="chart.chart_type" />
								<span>{{ chart.name }}</span>
							</div>
							<component
								class="h-4 w-4"
								stroke-width="1.5"
								:is="isSelected(chart.name) ? CheckSquare : SquareIcon"
								:class="isSelected(chart.name) ? 'text-gray-900' : 'text-gray-600'"
							/>
						</div>
					</template>
				</div>
			</div>
		</template>
	</Dialog>
</template>
