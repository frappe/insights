<script setup lang="ts">
import { computed, ref } from 'vue'
import { BubbleChartConfig } from '../../types/chart.types'
import { ColumnOption, Dimension, DimensionOption, Measure } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import MeasurePicker from './MeasurePicker.vue'
import BubbleChartOptionsDialog from './BubbleChartOptionsDialog.vue'
import { Plus } from 'lucide-vue-next'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<BubbleChartConfig>({
	required: true,
	default: () => ({
		xAxis: {} as Measure,
		yAxis: {} as Measure,
		size_column: {} as Measure,
		dimension: {} as Dimension,
		quadrant_column: {} as Dimension,
		show_data_labels: false,
		show_quadrants: false,
	}),
})


if (!config.value.xAxis) {
	config.value.xAxis = {} as Measure
}
if (!config.value.yAxis) {
	config.value.yAxis = {} as Measure
}
if (!config.value.size_column) {
	config.value.size_column = {} as Measure
}

const showOptionsDialog = ref(false)
const dialogTab = ref<'color' | 'labels' | 'reference_lines'>('color')

const hasColorConfig = computed(() => !!config.value.quadrant_column?.column_name || !!config.value.dimension?.column_name)
const hasLabelsConfig = computed(() => config.value.show_data_labels === true)
const hasRefLinesConfig = computed(() => config.value.show_quadrants === true)

function getColorDescription() {
	const parts = []
	if (config.value.quadrant_column?.column_name) parts.push(`Color by: ${config.value.quadrant_column.column_name}`)
	if (config.value.dimension?.column_name) parts.push(`Name: ${config.value.dimension.column_name}`)
	return parts.join(', ') || 'Not configured'
}

function getLabelsDescription() {
	return config.value.show_data_labels ? 'Data labels enabled' : 'Not configured'
}

function getRefLinesDescription() {
	if (config.value.show_quadrants) {
		return `X: ${config.value.xAxis_refLine}, Y: ${config.value.yAxis_refLine}`
	}
	return 'Not configured'
}

function openDialog(tab: 'color' | 'labels' | 'reference_lines') {
	dialogTab.value = tab
	showOptionsDialog.value = true
}

function removeColorConfig() {
	config.value.quadrant_column = {} as Dimension
	config.value.dimension = {} as Dimension
}

function removeLabelsConfig() {
	config.value.show_data_labels = false
}

function removeRefLinesConfig() {
	config.value.show_quadrants = false
	config.value.xAxis_refLine = undefined
	config.value.yAxis_refLine = undefined
}
</script>

<template>
	<CollapsibleSection title="Setup">
		<div class="flex flex-col gap-3 pt-1">
			<MeasurePicker
				label="X Axis"
				v-model="config.xAxis"
				:column-options="props.columnOptions"
			/>

			<MeasurePicker
				label="Y Axis"
				v-model="config.yAxis"
				:column-options="props.columnOptions"
			/>

			<MeasurePicker
				label="Size Column"
				v-model="config.size_column!"
				:column-options="props.columnOptions"
				@remove="config.size_column = {} as Measure"
			/>
		</div>
	</CollapsibleSection>

	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-2 pt-1">
			<div class="flex flex-col gap-2">
				<div
					v-if="hasColorConfig"
					class="group flex items-center justify-between rounded border border-gray-200 bg-gray-50 px-3 py-2 hover:bg-gray-100"
				>
					<button
						class="flex flex-1 flex-col items-start text-left"
						@click="openDialog('color')"
					>
						<span class="text-sm font-medium text-gray-900">Color</span>
						<span class="text-xs text-gray-600">{{ getColorDescription() }}</span>
					</button>
					<Button
						variant="ghost"
						icon="x"
						size="sm"
						@click="removeColorConfig"
						class="opacity-0 group-hover:opacity-100"
					/>
				</div>

				<div
					v-if="hasLabelsConfig"
					class="group flex items-center justify-between rounded border border-gray-200 bg-gray-50 px-3 py-2 hover:bg-gray-100"
				>
					<button
						class="flex flex-1 flex-col items-start text-left"
						@click="openDialog('labels')"
					>
						<span class="text-sm font-medium text-gray-900">Labels</span>
						<span class="text-xs text-gray-600">{{ getLabelsDescription() }}</span>
					</button>
					<Button
						variant="ghost"
						icon="x"
						size="sm"
						@click="removeLabelsConfig"
						class="opacity-0 group-hover:opacity-100"
					/>
				</div>

				<div
					v-if="hasRefLinesConfig"
					class="group flex items-center justify-between rounded border border-gray-200 bg-gray-50 px-3 py-2 hover:bg-gray-100"
				>
					<button
						class="flex flex-1 flex-col items-start text-left"
						@click="openDialog('reference_lines')"
					>
						<span class="text-sm font-medium text-gray-900">Reference Lines</span>
						<span class="text-xs text-gray-600">{{ getRefLinesDescription() }}</span>
					</button>
					<Button
						variant="ghost"
						icon="x"
						size="sm"
						@click="removeRefLinesConfig"
						class="opacity-0 group-hover:opacity-100"
					/>
				</div>
			</div>
			<Button class="w-full" @click="openDialog('color')">
			<template #prefix>
				<Plus class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
			Add Options
		</Button>
			<!-- <Button
				label="Add Options"
				variant="outline"
				@click="openDialog('color')"
				class="w-full"
			/> -->
		</div>
	</CollapsibleSection>

	<BubbleChartOptionsDialog
		v-model="showOptionsDialog"
		:dimensions="props.dimensions"
		:column-options="props.columnOptions"
		:config="config"
		:initial-tab="dialogTab"
	/>
</template>
