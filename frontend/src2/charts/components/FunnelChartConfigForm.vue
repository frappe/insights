<script setup lang="ts">
import { computed } from 'vue'
import { __ } from '../../translation'
import { FIELDTYPES } from '../../helpers/constants'
import { FunnelChartConfig } from '../../types/chart.types'
import {
	ColumnOption,
	Dimension,
	DimensionOption,
	Measure,
	MeasureOption,
} from '../../types/query.types'
import DraggableList from '../../components/DraggableList.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import MeasurePicker from './MeasurePicker.vue'
import DimensionPicker from './DimensionPicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<FunnelChartConfig>({
	required: true,
	default: () => ({
		measures: [],
		label_column: {},
		value_column: {},
	}),
})

// Measures mode is active once any stage has a picked measure. When it isn't,
// we fall back to the grouped (label + value) controls so existing funnels and
// long-format data stay configurable.
const hasMeasures = computed(() => config.value.measures?.some((m) => m.measure_name))

function addStage() {
	if (!config.value.measures) {
		config.value.measures = []
	}
	config.value.measures.push({} as MeasureOption)
}

const discrete_dimensions = computed(() =>
	props.dimensions.filter((d) => FIELDTYPES.DISCRETE.includes(d.data_type)),
)
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<div>
				<p class="mb-1.5 text-xs text-ink-gray-5">Stages</p>
				<div>
					<DraggableList v-model:items="config.measures" group="funnel-stages">
						<template #item="{ item, index }">
							<MeasurePicker
								:model-value="item"
								:column-options="props.columnOptions"
								@update:model-value="Object.assign(item, $event || {})"
								@remove="config.measures!.splice(index, 1)"
							/>
						</template>
					</DraggableList>
					<button
						class="mt-1.5 text-left text-xs text-ink-gray-5 hover:underline"
						@click="addStage"
					>
						+ Add stage
					</button>
				</div>
			</div>

			<template v-if="!hasMeasures">
				<DimensionPicker
					label="Label"
					:options="discrete_dimensions"
					:model-value="config.label_column as Dimension"
					@update:model-value="config.label_column = $event || ({} as Dimension)"
				/>
				<MeasurePicker
					label="Value"
					:column-options="props.columnOptions"
					:model-value="config.value_column as Measure"
					@update:model-value="config.value_column = $event || ({} as Measure)"
				/>
			</template>

			<Toggle v-model="config.show_percentage" :label="__('Show Percentage')" />
		</div>
	</CollapsibleSection>
</template>
