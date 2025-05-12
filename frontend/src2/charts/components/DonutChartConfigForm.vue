<script setup lang="ts">
import { computed, watchEffect } from 'vue'
import { FIELDTYPES } from '../../helpers/constants'
import { DonutChartConfig } from '../../types/chart.types'
import { ColumnOption, Dimension, DimensionOption, Measure } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<DonutChartConfig>({
	required: true,
	default: () => ({
		label_column: {},
		value_column: {},
	}),
})

watchEffect(() => {
	if (!config.value.label_column) {
		config.value.label_column = {} as Dimension
	}
	if (!config.value.value_column) {
		config.value.value_column = {} as Measure
	}
})

const discrete_dimensions = computed(() =>
	props.dimensions.filter((d) => FIELDTYPES.DISCRETE.includes(d.data_type))
)
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker
				label="Label"
				v-model="config.label_column"
				:options="discrete_dimensions"
			/>
			<MeasurePicker
				label="Value"
				v-model="config.value_column"
				:column-options="props.columnOptions"
			/>
			<FormControl
				v-if="!config.show_inline_labels"
				v-model="config.legend_position"
				label="Legend Position"
				type="select"
				:options="[
					{ label: 'Top', value: 'top' },
					{ label: 'Bottom', value: 'bottom' },
					{ label: 'Left', value: 'left' },
					{ label: 'Right', value: 'right' },
				]"
			/>
			<FormControl v-model="config.max_slices" label="Max Slices" type="number" min="1" />
			<Toggle v-model="config.show_inline_labels" label="Inline Labels" />
		</div>
	</CollapsibleSection>
</template>
