<script setup lang="ts">
import { XIcon } from 'lucide-vue-next'
import { TableChartConfig } from '../../types/chart.types'
import { DimensionOption, MeasureOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import { watchEffect } from 'vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'
import DraggableList from '../../components/DraggableList.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	measures: MeasureOption[]
}>()

const config = defineModel<TableChartConfig>({
	required: true,
	default: () => ({
		rows: [],
		columns: [],
		values: [],
	}),
})
watchEffect(() => {
	if (!config.value.rows?.length) {
		config.value.rows = [{} as any]
	}
	if (!config.value.columns?.length) {
		config.value.columns = [{} as any]
	}
	if (!config.value.values?.length) {
		config.value.values = [{} as any]
	}
})
</script>

<template>
	<CollapsibleSection title="Rows">
		<div>
			<DraggableList v-model:items="config.rows" group="rows">
				<template #item="{ item, index }">
					<DimensionPicker
						:options="props.dimensions"
						:model-value="item"
						@update:model-value="Object.assign(item, $event || {})"
						@remove="config.rows.splice(index, 1)"
					/>
				</template>
			</DraggableList>
			<button
				class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
				@click="config.rows.push({} as any)"
			>
				+ Add column
			</button>
		</div>
	</CollapsibleSection>

	<CollapsibleSection title="Columns">
		<div>
			<DraggableList v-model:items="config.columns" group="columns">
				<template #item="{ item, index }">
					<DimensionPicker
						:options="props.dimensions"
						:model-value="item"
						@update:model-value="Object.assign(item, $event || {})"
						@remove="config.columns.splice(index, 1)"
					/>
				</template>
			</DraggableList>
			<button
				class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
				@click="config.columns.push({} as any)"
			>
				+ Add column
			</button>
		</div>
	</CollapsibleSection>

	<CollapsibleSection title="Values">
		<div class="flex flex-col gap-3">
			<div>
				<DraggableList v-model:items="config.values" group="values">
					<template #item="{ item, index }">
						<MeasurePicker
							:options="props.measures"
							:model-value="item"
							@update:model-value="Object.assign(item, $event || {})"
							@remove="config.values.splice(index, 1)"
						/>
					</template>
				</DraggableList>
				<button
					class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
					@click="config.values.push({} as any)"
				>
					+ Add column
				</button>
			</div>
			<Checkbox label="Show Filters" v-model="config.show_filter_row" />
			<Checkbox label="Show Row Totals" v-model="config.show_row_totals" />
			<Checkbox label="Show Column Totals" v-model="config.show_column_totals" />
			<!-- <Checkbox label="Conditional Formatting" v-model="config.conditional_formatting" /> -->
		</div>
	</CollapsibleSection>
</template>
