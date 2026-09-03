<script setup lang="ts">
import { computed } from 'vue'
import { __ } from '../../translation'
import { FIELDTYPES } from '../../helpers/constants'
import { DonutChartConfig } from '../../types/chart.types'
import { ColumnOption, DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'
import NumberFormatFields from './NumberFormatFields.vue'

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

const discrete_dimensions = computed(() =>
	props.dimensions.filter((d) => FIELDTYPES.DISCRETE.includes(d.data_type)),
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
			>
				<template #config-fields>
					<NumberFormatFields
						:config="config"
						:measure-name="config.value_column?.measure_name"
					/>
				</template>
			</MeasurePicker>
			<FormControl
				v-if="!config.show_inline_labels"
				v-model="config.legend_position"
				label="Legend Position"
				type="select"
				:options="[
					{ label: __('Top'), value: 'top' },
					{ label: __('Bottom'), value: 'bottom' },
					{ label: __('Left'), value: 'left' },
					{ label: __('Right'), value: 'right' },
				]"
			/>
			<FormControl v-model="config.max_slices" label="Max Slices" type="number" min="1" />
			<Toggle v-model="config.show_inline_labels" label="Inline Labels" />
		</div>
	</CollapsibleSection>
</template>
